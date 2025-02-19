"""
Plugin for processing complex shapes with additional layers.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import os

import geopandas as gpd
from shapely.geometry.base import BaseGeometry
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt
from shapely.ops import transform
import pyproj
import pandas as pd
import numpy as np

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.config import Config


class LayerConfig(BaseModel):
    """Configuration for an additional layer"""

    path: str
    field: str = "geometry"
    clip: bool = True
    simplify: bool = True


class ShapeProcessorConfig(PluginConfig):
    """Configuration for shape processor plugin"""

    plugin: str = "shape_processor"
    source: str
    field: str = "geometry"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "format": "topojson",
            "simplify": True,
            "layers": {
                "forest_cover": {
                    "path": "imports/forest_cover.gpkg",
                    "clip": True,
                    "simplify": True,
                }
            },
        }
    )


@register("shape_processor", PluginType.TRANSFORMER)
class ShapeProcessor(TransformerPlugin):
    """Plugin for processing complex shapes with additional layers"""

    config_model = ShapeProcessorConfig

    def __init__(self, db):
        super().__init__(db)
        self.config = Config()
        self.imports_config = self.config.get_imports_config()

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            validated_config = self.config_model(**config)
            valid_formats = {"geojson", "topojson"}
            if validated_config.params.get("format") not in valid_formats:
                raise ValueError(
                    f"Invalid format: {validated_config.params.get('format')}. Valid options are: {valid_formats}"
                )

            # Validate layer configurations
            layers = validated_config.params.get("layers", {})
            for layer_name, layer_config in layers.items():
                LayerConfig(**layer_config)

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _simplify_with_utm(
        self, geometry: BaseGeometry, log_area: bool = False
    ) -> BaseGeometry:
        """
        Simplify a geometry using UTM-based adaptive simplification.
        The simplification is done in UTM projection to ensure accurate measurements.
        """
        try:
            # Get centroid for UTM zone calculation
            centroid = geometry.centroid
            lon, lat = centroid.x, centroid.y

            # Calculate UTM zone
            zone_number = int((lon + 180) / 6) + 1
            hemisphere = "south" if lat < 0 else "north"

            # Create UTM CRS
            utm_crs = f"+proj=utm +zone={zone_number} +{hemisphere} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"

            # Create transformers
            project_to_utm = pyproj.Transformer.from_crs(
                "EPSG:4326", utm_crs, always_xy=True
            ).transform
            project_to_wgs84 = pyproj.Transformer.from_crs(
                utm_crs, "EPSG:4326", always_xy=True
            ).transform

            # Transform to UTM
            geom_utm = transform(project_to_utm, geometry)

            # Calculate area and determine tolerance
            area_km2 = geom_utm.area / 1_000_000
            if log_area:
                print(f"Area: {area_km2:.2f} km²")

            # Adaptive tolerance based on area
            if area_km2 > 1000:
                # For large areas, increase tolerance with area
                tolerance = 5 * np.sqrt(area_km2)
            else:
                # For smaller areas, use fixed tolerance
                tolerance = 5

            # Simplify in UTM coordinates
            simplified_utm = geom_utm.simplify(tolerance, preserve_topology=True)

            # Transform back to WGS84
            simplified_wgs84 = transform(project_to_wgs84, simplified_utm)

            return simplified_wgs84

        except Exception as e:
            raise ValueError(f"Error in UTM simplification: {str(e)}")

    def _convert_to_topojson(
        self, geometry: BaseGeometry, name: str = "shape"
    ) -> Dict[str, Any]:
        """Convert a geometry to optimized TopoJSON format."""
        try:
            # Convert to GeoJSON first
            geojson = gpd.GeoSeries([geometry]).__geo_interface__

            # Extract coordinates and type
            coords = geojson["features"][0]["geometry"]["coordinates"]
            geom_type = geojson["features"][0]["geometry"]["type"]

            # Create optimized TopoJSON structure
            return {
                "type": "Topology",
                "objects": {name: {"type": geom_type, "coordinates": coords}},
            }
        except Exception as e:
            raise ValueError(f"Error converting to TopoJSON: {str(e)}")

    def _load_shape_geometry(self, geometry_str: str) -> Optional[BaseGeometry]:
        """Load a geometry from WKB/WKT string."""
        try:
            # Try WKB first
            try:
                if isinstance(geometry_str, bytes):
                    return load_wkb(geometry_str)
                return load_wkb(bytes.fromhex(str(geometry_str)))
            except (ValueError, TypeError):
                pass

            # Try WKT format
            try:
                return load_wkt(str(geometry_str))
            except (ValueError, TypeError):
                pass

            raise ValueError("Could not parse geometry string")

        except Exception as e:
            raise ValueError(f"Error loading geometry: {str(e)}")

    def _process_layer(
        self, layer_name: str, layer_config: Dict[str, Any], shape_gdf: gpd.GeoDataFrame
    ) -> Optional[BaseGeometry]:
        """Process an additional layer according to configuration."""
        try:
            # Convert layer config to model
            layer_config = LayerConfig(**layer_config)

            # Get layer path from imports if relative
            if not os.path.isabs(layer_config.path):
                # Check imports config first
                imports_config = self.imports_config
                if imports_config and layer_name in imports_config:
                    layer_config.path = os.path.join(
                        os.path.dirname(self.config.config_dir),
                        imports_config[layer_name]["path"],
                    )
                else:
                    # Use path relative to config dir
                    layer_config.path = os.path.join(
                        os.path.dirname(self.config.config_dir), layer_config.path
                    )

            # Load layer
            layer_gdf = gpd.read_file(layer_config.path)

            # Clip to shape if requested
            if layer_config.clip:
                layer_gdf = gpd.clip(layer_gdf, shape_gdf)

            if layer_gdf.empty:
                return None

            # Union all geometries
            layer_geom = layer_gdf.unary_union

            # Simplify if requested
            if layer_config.simplify:
                layer_geom = self._simplify_with_utm(layer_geom)

            return layer_geom

        except Exception as e:
            raise ValueError(f"Error processing layer {layer_name}: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.config_model(**config)
            result = {}

            # Get source data
            if validated_config.source != "occurrences":
                group_id = config.get("group_id")
                data = self._get_data_from_source(validated_config.source, group_id)

            if data.empty:
                return result

            # Get main geometry
            geometry_str = data[validated_config.field].iloc[0]
            geometry = self._load_shape_geometry(geometry_str)

            if geometry is None:
                return result

            # Simplify if requested
            if validated_config.params.get("simplify", True):
                geometry = self._simplify_with_utm(geometry)

            # Convert to requested format
            if validated_config.params.get("format") == "topojson":
                result["shape_coords"] = self._convert_to_topojson(geometry)
            else:  # geojson
                result["shape_coords"] = gpd.GeoSeries([geometry]).__geo_interface__

            # Process additional layers
            shape_gdf = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
            layers = validated_config.params.get("layers", {})

            for layer_name, layer_config in layers.items():
                layer_geom = self._process_layer(layer_name, layer_config, shape_gdf)

                if layer_geom is not None:
                    # Convert to requested format
                    if validated_config.params.get("format") == "topojson":
                        result[f"{layer_name}_coords"] = self._convert_to_topojson(
                            layer_geom, name=layer_name
                        )
                    else:  # geojson
                        result[f"{layer_name}_coords"] = gpd.GeoSeries(
                            [layer_geom]
                        ).__geo_interface__

            return result

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
