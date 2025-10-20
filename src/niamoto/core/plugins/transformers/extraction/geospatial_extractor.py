"""
Plugin for extracting and formatting geospatial data.
"""

from typing import Dict, Any, Optional, List, Literal, Union
import os

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt
from pydantic import BaseModel, Field, ConfigDict
from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.config import Config
from niamoto.common.exceptions import DatabaseQueryError
from niamoto.core.imports.registry import EntityRegistry


class HierarchyConfig(BaseModel):
    """Configuration for hierarchical data extraction.

    Supports both nested sets (lft/rght) and adjacency list (parent_field) models.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Configuration for extracting hierarchical data",
            "examples": [
                {
                    "type_field": "plot_type",
                    "leaf_type": "plot",
                    "parent_field": "parent_id",
                },
                {
                    "type_field": "plot_type",
                    "leaf_type": "plot",
                    "left_field": "lft",
                    "right_field": "rght",
                },
            ],
        }
    )

    type_field: Optional[str] = Field(
        None, description="Field that contains the entity type (e.g., 'plot_type')"
    )
    leaf_type: Optional[str] = Field(
        None, description="Value that identifies leaf entities (e.g., 'plot')"
    )
    parent_field: Optional[str] = Field(
        None, description="Field for adjacency list parent reference (preferred)"
    )
    left_field: Optional[str] = Field(
        None, description="Field for nested set left value (legacy)"
    )
    right_field: Optional[str] = Field(
        None, description="Field for nested set right value (legacy)"
    )


class GeospatialExtractorParams(BasePluginParams):
    """Parameters for geospatial data extraction.

    This plugin extracts and formats geospatial data from various sources,
    supporting multiple geometry formats and hierarchical data structures.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Extract and format geospatial data into GeoJSON",
            "examples": [
                {
                    "source": "plots",
                    "field": "geometry",
                    "format": "geojson",
                    "properties": ["name", "type", "area"],
                },
                {
                    "source": "occurrences",
                    "field": "location",
                    "format": "geojson",
                    "group_by_coordinates": True,
                    "properties": ["species_name", "count"],
                },
                {
                    "source": "hierarchical_plots",
                    "field": "geometry",
                    "extract_children": True,
                    "hierarchy_config": {
                        "type_field": "plot_type",
                        "leaf_type": "subplot",
                        "left_field": "lft",
                        "right_field": "rght",
                    },
                },
            ],
        }
    )

    source: str = Field(
        ...,
        description="Data source name (table or import)",
        json_schema_extra={"ui:widget": "select"},
    )
    field: str = Field(
        ...,
        description="Field name containing geometry data",
        json_schema_extra={"ui:widget": "field-select", "ui:depends": "source"},
    )
    format: Literal["geojson"] = Field(
        default="geojson", description="Output format for geospatial data"
    )
    properties: List[str] = Field(
        default_factory=list,
        description="List of properties to include in the output features",
        json_schema_extra={"ui:widget": "multi-field-select", "ui:depends": "source"},
    )
    group_by_coordinates: bool = Field(
        default=False,
        description="Group points with the same coordinates and add count property",
    )
    extract_children: bool = Field(
        default=False,
        description="Extract child entities instead of the main entity (for hierarchical data)",
    )
    children_properties: List[str] = Field(
        default_factory=list,
        description="Properties to include from children when extract_children is True",
    )
    hierarchy_config: HierarchyConfig = Field(
        default_factory=lambda: HierarchyConfig(),
        description="Configuration for hierarchical data extraction using nested sets",
    )


class GeospatialExtractorConfig(PluginConfig):
    """Complete configuration for geospatial extractor plugin."""

    plugin: Literal["geospatial_extractor"] = "geospatial_extractor"
    params: GeospatialExtractorParams


@register("geospatial_extractor", PluginType.TRANSFORMER)
class GeospatialExtractor(TransformerPlugin):
    """Plugin for extracting geospatial data"""

    config_model = GeospatialExtractorConfig

    def __init__(self, db, registry=None):
        super().__init__(db, registry)
        self.config = Config()
        # Use registry from parent if provided, otherwise create new instance
        if not self.registry:
            self.registry = EntityRegistry(db)

    def validate_config(self, config: Dict[str, Any]) -> GeospatialExtractorConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _convert_to_geometry(self, geom_data: Any) -> Optional[BaseGeometry]:
        """Convert various formats to shapely geometry (Point, MultiPoint, etc)."""
        try:
            if pd.isna(geom_data):  # Check that the data is not NaN
                return None

            if isinstance(geom_data, BaseGeometry):
                return geom_data

            # Try to parse as WKB
            try:
                if isinstance(geom_data, bytes):
                    geom = load_wkb(geom_data)
                else:
                    # Try to parse as hex string
                    geom = load_wkb(bytes.fromhex(str(geom_data)))
                if isinstance(geom, BaseGeometry):
                    return geom
            except (ValueError, TypeError):
                pass

            # Try to parse as WKT
            try:
                geom = load_wkt(str(geom_data))
                if isinstance(geom, BaseGeometry):
                    return geom
            except (ValueError, TypeError):
                pass

            # Try to parse as 'POINT (x y)' format
            try:
                geom_str = str(geom_data)
                if geom_str.startswith("POINT ("):
                    coords = geom_str.replace("POINT (", "").replace(")", "").split()
                    if len(coords) == 2:
                        return Point(float(coords[0]), float(coords[1]))
            except (ValueError, TypeError):
                pass

            return None

        except Exception:
            import traceback

            traceback.print_exc()
            return None

    def _get_data_from_source(self, source: str, id_value: int = None) -> pd.DataFrame:
        """Get data from a source (table or import)."""
        try:
            table_name = self._resolve_table_name(source)
            if self.db.has_table(table_name):
                if id_value is not None:
                    query = f"SELECT * FROM {table_name} WHERE id = :id"
                    params = {"id": id_value}
                else:
                    query = f"SELECT * FROM {table_name}"
                    params = {}
                return pd.read_sql(query, self.db.engine, params=params or None)

            # Fallback to connector configuration if available
            try:
                metadata = self.registry.get(source)
                if metadata and hasattr(metadata, "config") and metadata.config:
                    connector = metadata.config.get("connector", {})
                    if connector:
                        df = self._load_from_connector(connector, id_value)
                        if df is not None:
                            return df
            except (DatabaseQueryError, AttributeError):
                # Registry lookup failed or metadata is invalid, skip connector path
                pass
        except Exception as e:
            raise ValueError(f"Error getting data from {source}: {str(e)}") from e

        # Final fallback: check if source exists in registry
        try:
            entity_info = self.registry.get(source)
            if entity_info and hasattr(entity_info, "table_name"):
                # Source exists in registry, try loading from its table
                table_name = entity_info.table_name
                try:
                    query = f"SELECT * FROM {table_name} WHERE id = :id"
                    df = pd.read_sql(query, self.db.engine, params={"id": id_value})
                    if not df.empty:
                        return df
                except Exception as e:
                    raise ValueError(
                        f"Error loading from {table_name}: {str(e)}"
                    ) from e
        except (DatabaseQueryError, AttributeError):
            # Registry lookup failed, proceed to final error
            pass

        raise ValueError(f"Unknown data source: {source}")

    def _get_children_from_source(
        self, source: str, parent_id: int, hierarchy_config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Get children data from a hierarchical source.

        Supports both nested sets (lft/rght) and adjacency list (parent_field) models.
        Auto-detects which model is available in the table.
        """
        try:
            # Check if we have hierarchy configuration
            type_field = hierarchy_config.get("type_field")
            leaf_type = hierarchy_config.get("leaf_type")
            parent_field = hierarchy_config.get("parent_field")
            left_field = hierarchy_config.get("left_field")
            right_field = hierarchy_config.get("right_field")

            # If no hierarchy config, just return the entity itself
            if not type_field or not leaf_type:
                return self._get_data_from_source(source, parent_id)

            table_name = self._resolve_table_name(source)

            # Determine which hierarchy model to use
            # Priority: parent_field (adjacency list) > left/right (nested sets)
            use_adjacency_list = parent_field is not None
            use_nested_sets = left_field is not None and right_field is not None

            # Auto-detect if not explicitly configured
            if not use_adjacency_list and not use_nested_sets:
                # Check which columns exist in the table
                try:
                    table_columns = self.db.get_table_columns(table_name)
                    if "parent_id" in table_columns:
                        use_adjacency_list = True
                        parent_field = "parent_id"
                    elif "lft" in table_columns and "rght" in table_columns:
                        use_nested_sets = True
                        left_field = "lft"
                        right_field = "rght"
                except Exception:
                    # Fallback to legacy nested sets
                    use_nested_sets = True
                    left_field = "lft"
                    right_field = "rght"

            # Get parent entity type
            type_query = f"SELECT {type_field} FROM {table_name} WHERE id = :id"
            type_df = pd.read_sql(type_query, self.db.engine, params={"id": parent_id})

            if type_df.empty:
                return pd.DataFrame()

            entity_type = type_df.iloc[0][type_field]

            # If it's already a leaf entity, return itself
            if entity_type == leaf_type:
                query = f"SELECT * FROM {table_name} WHERE id = :id"
                return pd.read_sql(query, self.db.engine, params={"id": parent_id})

            # Get all leaf descendants based on hierarchy model
            if use_adjacency_list:
                # Use recursive CTE for adjacency list
                query = f"""
                    WITH RECURSIVE descendants AS (
                        -- Base case: direct children
                        SELECT * FROM {table_name}
                        WHERE {parent_field} = :parent_id

                        UNION ALL

                        -- Recursive case: children of children
                        SELECT t.*
                        FROM {table_name} t
                        INNER JOIN descendants d ON t.{parent_field} = d.id
                    )
                    SELECT * FROM descendants
                    WHERE {type_field} = :leaf_type
                    ORDER BY id
                """
                return pd.read_sql(
                    query,
                    self.db.engine,
                    params={"parent_id": parent_id, "leaf_type": leaf_type},
                )
            else:
                # Use nested sets query (legacy)
                parent_query = f"""
                    SELECT {left_field}, {right_field}
                    FROM {table_name}
                    WHERE id = :parent_id
                """
                parent_df = pd.read_sql(
                    parent_query, self.db.engine, params={"parent_id": parent_id}
                )

                if parent_df.empty:
                    return pd.DataFrame()

                parent_row = parent_df.iloc[0]
                lft = parent_row[left_field]
                rght = parent_row[right_field]

                query = f"""
                    SELECT * FROM {table_name}
                    WHERE {left_field} > :lft AND {right_field} < :rght
                    AND {type_field} = :leaf_type
                    ORDER BY {left_field}
                """
                return pd.read_sql(
                    query,
                    self.db.engine,
                    params={"lft": lft, "rght": rght, "leaf_type": leaf_type},
                )

        except Exception as e:
            raise ValueError(f"Error getting children from {source}: {str(e)}")

    def _load_from_connector(
        self, connector: Dict[str, Any], id_value: Optional[int]
    ) -> Optional[pd.DataFrame]:
        if not connector:
            return None
        connector_type = connector.get("type")
        path = connector.get("path")
        if not connector_type or not path:
            return None

        base_dir = os.path.dirname(self.config.config_dir)
        file_path = os.path.join(base_dir, path)

        if connector_type in {"file", "duckdb_csv", "csv"}:
            df = pd.read_csv(file_path)
        elif connector_type == "vector":
            df = gpd.read_file(file_path)
        else:
            raise ValueError(f"Unsupported connector type: {connector_type}")

        identifier = connector.get("identifier")
        if id_value is not None and identifier in df.columns:
            df = df[df[identifier] == id_value]
        return df

    def _resolve_table_name(self, logical_name: str) -> str:
        """Resolve logical entity name to physical table name via registry.

        Falls back to the logical name if:
        - Entity not found in registry (DatabaseQueryError)
        - Registry returns invalid/missing metadata (AttributeError)
        - Any other unexpected error occurs
        """
        try:
            metadata = self.registry.get(logical_name)
            if not metadata or not hasattr(metadata, "table_name"):
                return logical_name
            return metadata.table_name
        except (DatabaseQueryError, AttributeError):
            return logical_name

    def transform(
        self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)
            params = validated_config.params
            source = params.source
            field = params.field
            format_type = params.format
            properties = params.properties
            group_by_coordinates = params.group_by_coordinates
            extract_children = params.extract_children
            hierarchy_config = params.hierarchy_config

            # Get source data if different from occurrences
            # Exception: if source is "plots" but we already have aggregated data from nested_set,
            # use the provided data instead of fetching from source
            if source != "occurrences" and not (source == "plots" and not data.empty):
                group_id = config.get("group_id")

                # If extract_children is True, get children instead of the entity itself
                if extract_children:
                    data = self._get_children_from_source(
                        source, group_id, hierarchy_config.model_dump()
                    )
                else:
                    data = self._get_data_from_source(source, group_id)

            # Check if field exists
            if field not in data.columns:
                return {"type": "FeatureCollection", "features": []}

            geometry_data = data[field]

            if not geometry_data.empty:
                # Convert WKB/WKT to geometry if needed
                if not isinstance(geometry_data.iloc[0], BaseGeometry):
                    geometry_data = geometry_data.apply(self._convert_to_geometry)

                # Create a mask for valid geometries
                valid_mask = ~geometry_data.isna()

                # Filter data to keep only rows with valid geometries
                valid_data = data[valid_mask]
                valid_geometry = geometry_data.dropna()

                if not valid_geometry.empty:
                    gdf = gpd.GeoDataFrame(valid_data, geometry=valid_geometry)

                    # Convert to GeoJSON
                    if format_type == "geojson":
                        if group_by_coordinates:
                            # Dictionary to store unique coordinates and their features
                            unique_features = {}

                            for idx, row in gdf.iterrows():
                                try:
                                    if row.geometry is not None:
                                        # Handle different geometry types
                                        if isinstance(row.geometry, Point):
                                            # Get coordinates as a tuple for dictionary key
                                            coords = (row.geometry.x, row.geometry.y)

                                            # Include only essential properties
                                            properties_to_include = [
                                                prop
                                                for prop in properties
                                                if prop in row.index
                                                and not pd.isna(row[prop])
                                            ]

                                            # Create properties dictionary
                                            props = {
                                                prop: row[prop]
                                                for prop in properties_to_include
                                            }

                                            # If coordinates already exist, update count and merge properties
                                            if coords in unique_features:
                                                # Increment count
                                                unique_features[coords]["properties"][
                                                    "count"
                                                ] = (
                                                    unique_features[coords][
                                                        "properties"
                                                    ].get("count", 1)
                                                    + 1
                                                )

                                                # Merge other properties if needed
                                                for prop, value in props.items():
                                                    if (
                                                        prop
                                                        in unique_features[coords][
                                                            "properties"
                                                        ]
                                                    ):
                                                        # If property already exists, we could implement custom merging logic here
                                                        # For now, we keep the first value
                                                        pass
                                                    else:
                                                        unique_features[coords][
                                                            "properties"
                                                        ][prop] = value
                                            else:
                                                # Create new feature with count=1
                                                props["count"] = 1
                                                unique_features[coords] = {
                                                    "type": "Feature",
                                                    "geometry": {
                                                        "type": "Point",
                                                        "coordinates": [
                                                            coords[0],
                                                            coords[1],
                                                        ],
                                                    },
                                                    "properties": props,
                                                }
                                except Exception:
                                    continue

                            # Convert dictionary values to list for GeoJSON
                            features_list = list(unique_features.values())
                            return {
                                "type": "FeatureCollection",
                                "features": features_list,
                            }
                        else:
                            # Use GeoPandas to_json for proper geometry handling
                            # First filter columns if properties are specified
                            if properties:
                                # Keep geometry column plus requested properties
                                cols_to_keep = ["geometry"] + [
                                    col for col in properties if col in gdf.columns
                                ]
                                gdf_filtered = gdf[cols_to_keep]
                            else:
                                gdf_filtered = gdf

                            # Convert to GeoJSON using GeoPandas
                            import json

                            geojson_str = gdf_filtered.to_json()
                            return json.loads(geojson_str)

            return {"type": "FeatureCollection", "features": []}

        except Exception:
            return {"type": "FeatureCollection", "features": []}
