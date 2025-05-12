"""
Plugin for processing complex shapes with additional layers.
"""

from typing import Dict, Any
import os
from pydantic import BaseModel, Field
import pandas as pd
import geopandas as gpd
from shapely.wkb import loads
from shapely.geometry import mapping
import topojson as tp
import yaml

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.database import Database

from shapely.ops import transform
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely import make_valid
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union


class LayerConfig(BaseModel):
    """Configuration for an additional layer"""

    path: str
    field: str = "geometry"
    clip: bool = True
    simplify: bool = True


class ShapeProcessorConfig(PluginConfig):
    """Configuration for shape processor plugin"""

    plugin: str = "shape_processor"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "shape_ref",
            "field": "location",
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

    def __init__(self, db: Database, config: Dict[str, Any] = None):
        """Initialize the plugin with database connection and configuration."""
        try:
            self.db = db

            self.config_dir = os.getcwd()

            possible_paths = [
                os.path.join(self.config_dir, "config", "import.yml"),
            ]

            import_config_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    import_config_path = path
                    break

            if import_config_path and os.path.exists(import_config_path):
                with open(import_config_path, "r") as f:
                    self.imports_config = yaml.safe_load(f)
            else:
                self.imports_config = {}

            self.config = ShapeProcessorConfig(plugin="shape_processor", params={})

            if config:
                self.config = self.validate_config(config)

        except Exception as e:
            raise ValueError(f"Error initializing shape processor: {str(e)}")

    def validate_config(self, config: Dict[str, Any]) -> Any:
        """Validate the configuration."""
        try:
            if not isinstance(config, dict):
                raise ValueError("Configuration must be a dictionary")

            if "params" not in config:
                raise ValueError("Configuration must contain 'params' key")

            params = config["params"]
            if not isinstance(params, dict):
                raise ValueError("params must be a dictionary")

            if "layers" in params:
                layers = params["layers"]
                if not isinstance(layers, list):
                    raise ValueError("layers must be a list")

                for layer_config in layers:
                    if isinstance(layer_config, str):
                        continue
                    elif isinstance(layer_config, dict):
                        if "name" not in layer_config:
                            raise ValueError(
                                f"Layer configuration must contain 'name' key: {layer_config}"
                            )
                    else:
                        raise ValueError(
                            f"Invalid layer configuration format: {layer_config}"
                        )

            return config

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def load_shape_geometry(self, wkb_str: str) -> gpd.GeoDataFrame:
        """Load a geometry from a WKB hex string."""
        try:
            geometry = loads(bytes.fromhex(wkb_str))

            if hasattr(self.config, "params") and isinstance(self.config.params, dict):
                simplify = self.config.params.get("simplify", True)
            else:
                simplify = True

            if simplify:
                geometry = self._simplify_with_utm(geometry)

            return gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
        except Exception as e:
            raise ValueError(f"Error loading shape geometry: {str(e)}")

    def load_layer_as_gdf(
        self,
        base_gdf: gpd.GeoDataFrame,
        layer_name: str,
        layer_type: str,
        layer_params: Dict[str, Any] = None,
    ):
        """Load a layer as a GeoDataFrame and process it according to configuration."""
        try:
            if layer_params is None:
                layer_params = {"clip": True, "simplify": True}

            return self._process_layer(layer_name, layer_params, base_gdf)

        except Exception:
            return None

    def get_simplified_coordinates(self, geometry_location: str) -> Dict[str, Any]:
        """Get simplified coordinates for a geometry and convert to TopoJSON."""
        try:
            geometry = loads(bytes.fromhex(geometry_location))
            if hasattr(self.config, "params") and isinstance(self.config.params, dict):
                simplify = self.config.params.get("simplify", True)
            else:
                simplify = True

            if simplify:
                geometry = self._simplify_with_utm(geometry)
            return self._convert_to_topojson(geometry)
        except Exception as e:
            raise ValueError(f"Error simplifying coordinates: {str(e)}")

    def get_coordinates_from_gdf(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Get simplified coordinates from a GeoDataFrame and convert to TopoJSON."""
        try:
            if gdf is None or gdf.empty:
                return {}

            valid_geometries = []
            for geom in gdf.geometry:
                if geom is not None and not pd.isna(geom):
                    if not geom.is_valid:
                        geom = make_valid(geom)
                    valid_geometries.append(geom)

            if not valid_geometries:
                return {}

            merged = unary_union(valid_geometries)
            if not merged.is_valid:
                merged = make_valid(merged)

            merged = self._simplify_with_utm(merged)

            return self._convert_to_topojson(merged)

        except Exception as e:
            raise ValueError(f"Error converting GeoDataFrame to TopoJSON: {str(e)}")

    def _convert_to_topojson(self, geometry: BaseGeometry) -> Dict[str, Any]:
        """Convert a geometry to optimized TopoJSON format."""
        try:
            if not geometry.is_valid:
                geometry = make_valid(geometry)

            if isinstance(geometry, GeometryCollection):
                all_geoms = list(geometry.geoms)
                polygons = [
                    geom
                    for geom in all_geoms
                    if isinstance(geom, (Polygon, MultiPolygon))
                ]
                if polygons:
                    geometry = unary_union(polygons)
                else:
                    geometry = all_geoms[0] if all_geoms else None
                    if geometry is None:
                        raise ValueError("Empty geometry collection")

            elif isinstance(geometry, MultiPolygon):
                valid_polygons = [poly for poly in geometry.geoms if poly.is_valid]
                if valid_polygons:
                    geometry = MultiPolygon(valid_polygons)
                else:
                    raise ValueError("No valid polygons in MultiPolygon")

            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {}, "geometry": mapping(geometry)}
                ],
            }

            topology = tp.Topology(geojson, prequantize=True)
            return topology.to_dict()

        except Exception:
            return {
                "type": "Topology",
                "objects": {"shape": {"type": "GeometryCollection", "geometries": []}},
                "arcs": [],
            }

    def _simplify_with_utm(
        self, geometry: BaseGeometry, log_area: bool = False
    ) -> BaseGeometry:
        """
        Simplify a geometry using UTM-based adaptive simplification.
        The simplification is done in UTM projection to ensure accurate measurements and consistent simplification.

        The process:
        1. Converts the geometry to appropriate UTM zone based on its centroid
        2. Calculates area and determines simplification tolerance:
           - For areas > 1000 km², tolerance increases with area (adaptive)
           - For smaller areas, uses fixed 5m tolerance
        3. Simplifies in UTM coordinates then converts back to WGS84

        Args:
            geometry: The geometry to simplify (in WGS84 coordinates)
            log_area: If True, logs the area of the geometry in km²

        Returns:
            The simplified geometry in WGS84 coordinates

        Note:
            If simplification fails, the original geometry is returned.
        """
        try:
            # Calculate centroid for UTM zone determination
            lon, lat = geometry.centroid.x, geometry.centroid.y

            # Calculate UTM zone from longitude
            # Formula: ((longitude + 180)/6) + 1
            zone_number = int((lon + 180) / 6) + 1
            hemisphere = "south" if lat < 0 else "north"

            # Set up the projection transformers
            wgs84 = pyproj.CRS("EPSG:4326")
            utm = pyproj.CRS(
                f"+proj=utm +zone={zone_number} +{hemisphere} +ellps=WGS84"
            )
            project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
            project_back = pyproj.Transformer.from_crs(
                utm, wgs84, always_xy=True
            ).transform

            # Convert geometry to UTM
            utm_geom = transform(project, geometry)

            # Calculate area in square kilometers
            area_km2 = utm_geom.area / 1_000_000
            if log_area:
                print(f"Area: {area_km2:.2f} km²")

            # Calculate simplification tolerance
            # The formula adapts the tolerance based on the area, following these rules:
            # - Areas < 1000 km² : fixed 5m tolerance to preserve detail
            # - Areas > 1000 km² : adaptive tolerance using the formula: 10 * (area_km²/1000)^0.25
            #
            # Examples of resulting tolerances:
            # - 1000 km² → 10.00m (base tolerance)
            # - 4000 km² → 14.14m
            # - 9000 km² → 17.32m
            # - 16000 km² → 20.00m
            if area_km2 > 1000:
                # Use a fourth root (0.25 power) to ensure tolerance doesn't grow too quickly with area
                tolerance = 10 * (area_km2 / 1000) ** 0.25
            else:
                tolerance = 5  # 5 meters minimum for small areas

            # Perform simplification in UTM coordinates with topology preservation
            simplified = utm_geom.simplify(tolerance, preserve_topology=True)

            # Convert back to WGS84
            return transform(project_back, simplified)

        except Exception as e:
            # Log the error but return the original geometry to avoid breaking the pipeline
            if log_area:
                print(f"Error simplifying geometry: {e}")
            return geometry

    def _process_layer(
        self, layer_name: str, layer_config: Dict[str, Any], shape_gdf: gpd.GeoDataFrame
    ):
        """Process an additional layer according to configuration."""
        try:
            layer_import = None

            if "layers" in self.imports_config:
                for layer in self.imports_config["layers"]:
                    if layer.get("name") == layer_name:
                        layer_import = layer
                        break

            if not layer_import and "shapes" in self.imports_config:
                for shape in self.imports_config["shapes"]:
                    if shape.get("category") == layer_name:
                        layer_import = shape
                        break

            if not layer_import:
                raise ValueError(f"Layer {layer_name} not found in import.yml")

            layer_path = layer_import["path"]
            if not os.path.isabs(layer_path):
                layer_path = os.path.join(self.config_dir, layer_path)

            format_type = layer_import.get("format", "").lower()

            if format_type == "directory_shapefiles":
                import glob

                shp_files = glob.glob(os.path.join(layer_path, "*.shp"))
                if not shp_files:
                    raise ValueError(f"No shapefile found in {layer_path}")
                layer_path = shp_files[0]
            elif format_type == "shapefile":
                if not os.path.exists(layer_path):
                    raise ValueError(f"Shapefile not found: {layer_path}")
            elif format_type == "geopackage":
                if not os.path.exists(layer_path):
                    raise ValueError(f"Geopackage not found: {layer_path}")

            layer_gdf = gpd.read_file(layer_path)

            if layer_config.get("clip", True):
                layer_gdf = gpd.clip(layer_gdf, shape_gdf)

            if layer_config.get("simplify", True):
                layer_gdf.geometry = layer_gdf.geometry.apply(
                    lambda geom: self._simplify_with_utm(geom) if geom else None
                )

            return layer_gdf

        except Exception as e:
            raise ValueError(f"Error processing layer {layer_name}: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)

            self.config = validated_config

            params = validated_config["params"]
            source = params.get("source", "shape_ref")
            field = params.get("field", "location")

            query = f"SELECT {field} FROM {source} WHERE id = {data['id'].iloc[0]}"

            result = self.db.execute_select(query)
            if not result:
                raise ValueError(
                    f"No data found in {source} for id {data['id'].iloc[0]}"
                )

            wkb_data = result.fetchone()[0]

            shape_gdf = self.load_shape_geometry(str(wkb_data))

            layers_result = {}
            layers = params.get("layers", [])

            for layer_config in layers:
                if isinstance(layer_config, str):
                    layer_name = layer_config
                    layer_params = {"clip": True, "simplify": True}
                else:
                    layer_name = layer_config.get("name")
                    if not layer_name:
                        continue
                    layer_params = {
                        "clip": layer_config.get("clip", True),
                        "simplify": layer_config.get("simplify", True),
                    }

                layer_gdf = self.load_layer_as_gdf(
                    shape_gdf, layer_name, "vector", layer_params
                )
                if layer_gdf is not None:
                    layers_result[f"{layer_name}_coords"] = (
                        self.get_coordinates_from_gdf(layer_gdf)
                    )

            result = {
                "shape_coords": self.get_simplified_coordinates(str(wkb_data)),
                **layers_result,
            }
            return result

        except Exception as e:
            raise ValueError(str(e))
