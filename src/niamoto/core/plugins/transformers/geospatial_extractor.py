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

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.config import Config


class GeospatialExtractorConfig(PluginConfig):
    """Configuration for geospatial extractor plugin"""

    plugin: str = "geospatial_extractor"
    params: Dict[str, Any] = {"source": "", "field": "", "format": "geojson"}


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
        if pd.isna(point):  # Check that the point is not NaN
            return None

        try:
            if isinstance(point, Point):
                # If the point is already a shapely Point object
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
                    return Point(float(coords[0]), float(coords[1]))
            except (ValueError, TypeError):
                pass

            return None
        except Exception as e:
            raise ValueError(f"Failed to convert geometry: {str(e)}")

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
            return pd.DataFrame(
                result.fetchall(),
                columns=[desc[0] for desc in result.cursor.description],
            )

        except Exception as e:
            raise ValueError(f"Error getting data from {source}: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        validated_config = self.config_model(**config)

        # Get source data if different from occurrences
        if validated_config.params.get("source") != "occurrences":
            # Get group ID from config
            group_id = config.get("group_id")
            data = self._get_data_from_source(
                validated_config.params.get("source"), group_id
            )

        # Convert to GeoDataFrame
        geometry_data = data[validated_config.params.get("field")]
        if not geometry_data.empty:
            # Convert WKB/WKT to geometry
            geometry_data = geometry_data.apply(self._convert_to_geometry)
            geometry_data = geometry_data.dropna()  # Remove any failed conversions

            if not geometry_data.empty:
                gdf = gpd.GeoDataFrame(data, geometry=geometry_data)

                # Convert to GeoJSON
                if validated_config.params.get("format") == "geojson":
                    features = []
                    for idx, row in gdf.iterrows():
                        if row.geometry is not None:
                            feature = {
                                "type": "Feature",
                                "geometry": row.geometry.__geo_interface__,
                                "properties": {},
                            }
                            features.append(feature)

                    return {"type": "FeatureCollection", "features": features}

        return {"type": "FeatureCollection", "features": []}
