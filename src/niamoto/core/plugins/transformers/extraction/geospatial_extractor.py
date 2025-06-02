"""
Plugin for extracting and formatting geospatial data.
"""

from typing import Dict, Any, Optional
import os

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
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

    def _convert_to_geometry(self, point: Any) -> Optional[Point]:
        """Convert various formats to shapely Point."""
        try:
            if pd.isna(point):  # Check that the point is not NaN
                return None

            if isinstance(point, Point):
                return point

            # Try to parse as WKB
            try:
                if isinstance(point, bytes):
                    geom = load_wkb(point)
                else:
                    # Try to parse as hex string
                    geom = load_wkb(bytes.fromhex(str(point)))
                if isinstance(geom, Point):
                    return geom
            except (ValueError, TypeError):
                pass

            # Try to parse as WKT
            try:
                geom = load_wkt(str(point))
                if isinstance(geom, Point):
                    return geom
            except (ValueError, TypeError):
                pass

            # Try to parse as 'POINT (x y)' format
            try:
                coords = str(point).replace("POINT (", "").replace(")", "").split()
                if len(coords) == 2:
                    point = Point(float(coords[0]), float(coords[1]))
                    return point
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

            # Get source data if different from occurrences
            # Exception: if source is "plots" but we already have aggregated data from nested_set,
            # use the provided data instead of fetching from source
            if source != "occurrences" and not (source == "plots" and not data.empty):
                group_id = config.get("group_id")
                data = self._get_data_from_source(source, group_id)

            # Check if field exists
            if field not in data.columns:
                return {"type": "FeatureCollection", "features": []}

            geometry_data = data[field]

            if not geometry_data.empty:
                # Convert WKB/WKT to geometry if needed
                if not isinstance(geometry_data.iloc[0], Point):
                    geometry_data = geometry_data.apply(self._convert_to_geometry)

                geometry_data = geometry_data.dropna()  # Remove any failed conversions

                if not geometry_data.empty:
                    gdf = gpd.GeoDataFrame(data, geometry=geometry_data)

                    # Convert to GeoJSON
                    if format == "geojson":
                        if group_by_coordinates:
                            # Dictionary to store unique coordinates and their features
                            unique_features = {}

                            for idx, row in gdf.iterrows():
                                try:
                                    if row.geometry is not None:
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

                            # Convert dictionary values to list
                            features = list(unique_features.values())
                        else:
                            # Original behavior without grouping
                            features = []
                            for idx, row in gdf.iterrows():
                                try:
                                    if row.geometry is not None:
                                        # Include only essential properties
                                        properties_to_include = [
                                            prop
                                            for prop in properties
                                            if prop in row.index
                                            and not pd.isna(row[prop])
                                        ]
                                        feature = {
                                            "type": "Feature",
                                            "geometry": {
                                                "type": "Point",
                                                "coordinates": [
                                                    row.geometry.x,
                                                    row.geometry.y,
                                                ],
                                            },
                                            "properties": {
                                                prop: row[prop]
                                                for prop in properties_to_include
                                            },
                                        }
                                        features.append(feature)
                                except Exception:
                                    continue

                        if features:
                            return {"type": "FeatureCollection", "features": features}

            return {"type": "FeatureCollection", "features": []}

        except Exception:
            return {"type": "FeatureCollection", "features": []}
