"""
Plugin for extracting and formatting geospatial data.
"""

from typing import Dict, Any, Optional
import os

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.config import Config
from pydantic import field_validator


class GeospatialExtractorConfig(PluginConfig):
    """Configuration for geospatial extractor plugin"""

    plugin: str = "geospatial_extractor"
    params: Dict[str, Any] = {
        "source": "",
        "field": "",
        "format": "geojson",  # default format
        "properties": [],  # optional, empty by default
        "group_by_coordinates": False,  # optional, group points with same coordinates
        "extract_children": False,  # optional, extract child entities instead of aggregated geometry
        "children_properties": [],  # optional, properties to include from children
        "hierarchy_config": {  # optional, configuration for hierarchical extraction
            "type_field": None,  # field that contains the entity type (e.g., "plot_type")
            "leaf_type": None,  # value that identifies leaf entities (e.g., "plot")
            "left_field": "lft",  # field for nested set left value
            "right_field": "rght",  # field for nested set right value
        },
    }

    @field_validator("params")
    @classmethod
    def validate_params(cls, v):
        """Validate configuration parameters."""
        # Ensure we have a dictionary
        if not isinstance(v, dict):
            v = {}

        # Validate required fields
        if not v.get("source"):
            raise ValueError("Source is required")
        if not v.get("field"):
            raise ValueError("Field is required")

        # Set default format if not provided
        if "format" not in v:
            v["format"] = "geojson"
        elif v["format"] not in {"geojson"}:
            raise ValueError("Format must be 'geojson'")

        # Set empty properties list if not provided
        if "properties" not in v:
            v["properties"] = []

        # Set default for group_by_coordinates if not provided
        if "group_by_coordinates" not in v:
            v["group_by_coordinates"] = False

        # Set default for extract_children if not provided
        if "extract_children" not in v:
            v["extract_children"] = False

        # Set default for children_properties if not provided
        if "children_properties" not in v:
            v["children_properties"] = []

        # Set default for hierarchy_config if not provided
        if "hierarchy_config" not in v:
            v["hierarchy_config"] = {
                "type_field": None,
                "leaf_type": None,
                "left_field": "lft",
                "right_field": "rght",
            }
        else:
            # Ensure all keys exist with defaults
            hierarchy_config = v["hierarchy_config"]
            if "type_field" not in hierarchy_config:
                hierarchy_config["type_field"] = None
            if "leaf_type" not in hierarchy_config:
                hierarchy_config["leaf_type"] = None
            if "left_field" not in hierarchy_config:
                hierarchy_config["left_field"] = "lft"
            if "right_field" not in hierarchy_config:
                hierarchy_config["right_field"] = "rght"

        return v


@register("geospatial_extractor", PluginType.TRANSFORMER)
class GeospatialExtractor(TransformerPlugin):
    """Plugin for extracting geospatial data"""

    config_model = GeospatialExtractorConfig

    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            validated_config = self.config_model(**config)
            # Additional validation if needed
            valid_formats = {"geojson"}
            if validated_config.params.get("format") not in valid_formats:
                raise ValueError(
                    f"Invalid format: {validated_config.params.get('format')}. Valid options are: {valid_formats}"
                )
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
            # D'abord vérifier si la source est dans import.yml
            if source in self.imports_config:
                import_config = self.imports_config[source]

                # Construire le chemin complet du fichier
                file_path = os.path.join(
                    os.path.dirname(self.config.config_dir), import_config["path"]
                )

                # Charger les données selon le type
                if import_config["type"] == "csv":
                    df = pd.read_csv(file_path)
                elif import_config["type"] == "vector":
                    df = gpd.read_file(file_path)
                else:
                    raise ValueError(
                        f"Unsupported import type: {import_config['type']}"
                    )

                # Si on a un id_value, filtrer les données
                if id_value is not None:
                    identifier = import_config["identifier"]
                    df = df[df[identifier] == id_value]

                return df

            # Sinon, c'est une table de la base
            query = f"""
                SELECT * FROM {source}
            """
            if id_value is not None:
                query += f" WHERE id = {id_value}"

            result = self.db.execute_select(query)
            # Pour SQLAlchemy moderne, on utilise .keys() pour obtenir les noms de colonnes
            df = pd.DataFrame(
                result.fetchall(),
                columns=result.keys(),
            )
            return df

        except Exception as e:
            import traceback

            traceback.print_exc()
            raise ValueError(f"Error getting data from {source}: {str(e)}")

    def _get_children_from_source(
        self, source: str, parent_id: int, hierarchy_config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Get children data from a hierarchical source."""
        try:
            # Check if we have hierarchy configuration
            type_field = hierarchy_config.get("type_field")
            leaf_type = hierarchy_config.get("leaf_type")
            left_field = hierarchy_config.get("left_field", "lft")
            right_field = hierarchy_config.get("right_field", "rght")

            # If no hierarchy config, just return the entity itself
            if not type_field or not leaf_type:
                return self._get_data_from_source(source, parent_id)

            # Build column list for parent query
            columns = [left_field, right_field]
            if type_field:
                columns.append(type_field)

            # First get the parent's nested set values
            parent_query = f"""
                SELECT {", ".join(columns)}
                FROM {source}
                WHERE id = {parent_id}
            """
            result = self.db.execute_select(parent_query)
            parent_row = result.fetchone()

            if not parent_row:
                return pd.DataFrame()

            # Extract values
            lft = parent_row[0]
            rght = parent_row[1]
            entity_type = parent_row[2] if len(parent_row) > 2 else None

            # If it's already a leaf entity, return itself
            if entity_type == leaf_type:
                query = f"""
                    SELECT * FROM {source}
                    WHERE id = {parent_id}
                """
                result = self.db.execute_select(query)
            else:
                # Get all leaf descendants
                query = f"""
                    SELECT * FROM {source}
                    WHERE {left_field} > {lft} AND {right_field} < {rght}
                    AND {type_field} = '{leaf_type}'
                    ORDER BY {left_field}
                """
                result = self.db.execute_select(query)

            df = pd.DataFrame(
                result.fetchall(),
                columns=result.keys(),
            )
            return df

        except Exception as e:
            import traceback

            traceback.print_exc()
            raise ValueError(f"Error getting children from {source}: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Make sure we have a params dictionary
            if "params" not in config:
                config["params"] = {}

            # Get required parameters from config
            params = config["params"]
            if "source" in config:
                params["source"] = config["source"]
            if "field" in config:
                params["field"] = config["field"]

            validated_config = self.config_model(**config)
            params = validated_config.params
            source = params["source"]
            field = params["field"]
            format = params["format"]
            properties = params["properties"]
            group_by_coordinates = params.get("group_by_coordinates", False)
            extract_children = params.get("extract_children", False)
            hierarchy_config = params.get("hierarchy_config", {})

            # Get source data if different from occurrences
            # Exception: if source is "plots" but we already have aggregated data from nested_set,
            # use the provided data instead of fetching from source
            if source != "occurrences" and not (source == "plots" and not data.empty):
                group_id = config.get("group_id")

                # If extract_children is True, get children instead of the entity itself
                if extract_children:
                    data = self._get_children_from_source(
                        source, group_id, hierarchy_config
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
                    if format == "geojson":
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
