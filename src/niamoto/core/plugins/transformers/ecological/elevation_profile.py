"""
Plugin for creating elevation profiles for shapes.
Analyzes the altitude distribution and allows for overlaying forest coverage
to create complete altitude distribution graphs.
"""

from typing import Dict, Any, Union
from pydantic import Field, field_validator
import pandas as pd
import geopandas as gpd
import numpy as np
import os
import rasterio
from rasterio.mask import mask
import rasterio.features
from shapely.geometry import Polygon, MultiPolygon

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class ElevationProfileConfig(PluginConfig):
    """Configuration for the elevation profile plugin"""

    plugin: str = "elevation_profile"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "dem_path": "",  # Path to the DEM
            "shape_field": "geometry",  # Field containing the main geometry
            "bins": 10,  # Number of altitude classes
            "custom_bins": None,  # Custom altitude classes
            "nodata": -9999,  # 'Nodata' value of the DEM
            "overlay_forest": False,  # Overlay with forest coverage
            "forest_path": None,  # Path to the forest coverage layer
            "area_unit": "ha",  # Unit of area: ha, km2, m2
        }
    )

    @field_validator("params")
    def validate_paths(cls, v):
        """Validates the paths to the source data."""
        if "dem_path" not in v or not v["dem_path"]:
            raise ValueError("The path to the DEM is required")

        # Check that the path to the forest coverage layer is provided if overlay_forest is True
        if v.get("overlay_forest", False) and not v.get("forest_path"):
            raise ValueError(
                "The path to the forest coverage layer is required when overlay_forest is True"
            )

        # Validate the bins
        if "bins" in v and not isinstance(v["bins"], int):
            raise ValueError("The number of classes (bins) must be an integer")

        if "custom_bins" in v and v["custom_bins"] is not None:
            if not isinstance(v["custom_bins"], list) or len(v["custom_bins"]) < 2:
                raise ValueError("custom_bins must be a list with at least 2 values")

            # Check that the custom bins are in ascending order
            if not all(
                v["custom_bins"][i] < v["custom_bins"][i + 1]
                for i in range(len(v["custom_bins"]) - 1)
            ):
                raise ValueError("Custom altitude classes must be in ascending order")

        # Check the unit of area
        if "area_unit" in v:
            if v["area_unit"] not in ["ha", "km2", "m2"]:
                raise ValueError(
                    f"Invalid unit of area: {v['area_unit']}. Use 'ha', 'km2' or 'm2'"
                )

        return v


@register("elevation_profile", PluginType.TRANSFORMER)
class ElevationProfile(TransformerPlugin):
    """
    Plugin for creating elevation profiles.

    This plugin analyzes the altitude distribution of a geographic zone using a
    Digital Elevation Model (DEM). It can also overlay this analysis with a forest
    coverage layer to study the distribution of the forest by altitude.

    The results are formatted for visualization as a graph showing the distribution
    of surfaces by altitude class, with optional overlay of the forest.
    """

    config_model = ElevationProfileConfig

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the plugin configuration."""
        try:
            return self.config_model(**config)
        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates an elevation profile for a shape.

        Args:
            data: GeoDataFrame containing the shape
            config: Configuration with paths and options

        Returns:
            Dictionary with the elevation profile and optionally the forest distribution
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Extract the geometry
            if not isinstance(data, gpd.GeoDataFrame):
                raise DataTransformError(
                    "Input data must be a GeoDataFrame",
                    details={"data_type": type(data).__name__},
                )

            shape_field = params.get("shape_field", "geometry")
            if shape_field not in data.columns and shape_field != "geometry":
                geometry = data.geometry
            else:
                geometry = data[shape_field]

            if geometry.empty:
                raise DataTransformError("No geometry found in the input data")

            # Use the first geometry (usually one per analysis)
            main_geom = geometry.iloc[0]

            # Resolve the DEM path
            dem_path = params["dem_path"]
            if not os.path.isabs(dem_path):
                base_dir = self._get_base_directory()
                dem_path = os.path.join(base_dir, dem_path)

            # Open the DEM
            try:
                with rasterio.open(dem_path) as src:
                    # Mask the DEM with the geometry
                    masked, mask_transform = mask(
                        src, [main_geom], crop=True, nodata=params["nodata"]
                    )

                    # Get the elevation data (first band)
                    elevation_data = masked[0]

                    # Filter nodata values
                    nodata = params["nodata"]
                    valid_mask = elevation_data != nodata
                    valid_data = elevation_data[valid_mask]

                    if len(valid_data) == 0:
                        return {"error": "No valid elevation data found in the shape"}
            except Exception as e:
                raise DataTransformError(
                    f"Error opening the DEM: {str(e)}", details={"dem_path": dem_path}
                )

            # Create the altitude classes
            custom_bins = params.get("custom_bins")
            if custom_bins:
                bins = np.array(custom_bins)
            else:
                num_bins = params["bins"]
                min_elev = np.floor(np.min(valid_data) / 100) * 100
                max_elev = np.ceil(np.max(valid_data) / 100) * 100
                bins = np.linspace(min_elev, max_elev, num_bins + 1)

            # Calculate the histogram
            hist, bin_edges = np.histogram(valid_data, bins=bins)

            # Create the class names (altitude ranges)
            class_names = []
            for i in range(len(bin_edges) - 1):
                class_names.append(f"{int(bin_edges[i])}-{int(bin_edges[i + 1])}")

            # Calculate the area of the pixels to convert to surface
            pixel_area = abs(mask_transform[0] * mask_transform[4])

            # Convert to the appropriate surface unit
            area_unit = params.get("area_unit", "ha")
            if area_unit == "ha":
                area_factor = 0.0001  # m² to ha
            elif area_unit == "km2":
                area_factor = 0.000001  # m² to km²
            else:
                area_factor = 1.0  # m²

            # Calculate the surfaces by class
            areas = hist * pixel_area * area_factor

            # Create the elevation profile
            elevation_profile = {
                "class_name": class_names,
                "pixel_count": hist.tolist(),
                "area": [float(area) for area in areas],
                "bin_edges": [float(edge) for edge in bin_edges],
                "area_unit": area_unit,
            }

            # If overlay forest coverage is requested, calculate the forest distribution by altitude
            if params.get("overlay_forest") and params.get("forest_path"):
                forest_distribution = self._calculate_forest_distribution(
                    params["forest_path"],
                    main_geom,
                    data.crs,
                    elevation_data,
                    bin_edges,
                    valid_mask,
                    mask_transform,
                    pixel_area,
                    area_factor,
                )

                if forest_distribution:
                    elevation_profile["forest_distribution"] = forest_distribution

            return elevation_profile

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Failed to create the elevation profile: {str(e)}",
                details={"config": config},
            )

    def _calculate_forest_distribution(
        self,
        forest_path: str,
        main_geom: Union[Polygon, MultiPolygon],
        crs: Any,
        elevation_data: np.ndarray,
        bin_edges: np.ndarray,
        valid_mask: np.ndarray,
        mask_transform: Any,
        pixel_area: float,
        area_factor: float,
    ) -> Dict[str, Any]:
        """
        Calculates the forest distribution by elevation class.

        Args:
            forest_path: Path to the forest layer
            main_geom: Geometry of the study area
            crs: Coordinate reference system
            elevation_data: Elevation data
            bin_edges: Elevation class boundaries
            valid_mask: Mask of valid pixels
            mask_transform: Raster transformation
            pixel_area: Area of a pixel in m²
            area_factor: Unit conversion factor for area

        Returns:
            Dictionary with the forest distribution
        """
        try:
            # Resolve the forest layer path
            if not os.path.isabs(forest_path):
                base_dir = self._get_base_directory()
                forest_path = os.path.join(base_dir, forest_path)

            # Load the forest layer
            forest_gdf = gpd.read_file(forest_path)

            if forest_gdf.empty:
                return {
                    "forest_area": [0] * (len(bin_edges) - 1),
                    "forest_percentage": [0] * (len(bin_edges) - 1),
                }

            # Ensure the CRS matches
            if crs != forest_gdf.crs:
                forest_gdf = forest_gdf.to_crs(crs)

            # Clip the forest to the main geometry
            forest_in_area = gpd.clip(
                forest_gdf, gpd.GeoDataFrame(geometry=[main_geom], crs=crs)
            )

            if forest_in_area.empty:
                return {
                    "forest_area": [0] * (len(bin_edges) - 1),
                    "forest_percentage": [0] * (len(bin_edges) - 1),
                }

            # Create a raster mask for the forest
            forest_shapes = [(geom, 1) for geom in forest_in_area.geometry]
            forest_mask = rasterio.features.rasterize(
                forest_shapes,
                out_shape=elevation_data.shape,
                transform=mask_transform,
                fill=0,
                dtype=np.uint8,
            )

            # Calculate the forest distribution by elevation class
            forest_areas = []
            forest_percentages = []
            forest_pixels = []
            total_pixels = []

            for i in range(len(bin_edges) - 1):
                # Mask for pixels in this elevation class
                bin_mask = (
                    (elevation_data >= bin_edges[i])
                    & (elevation_data < bin_edges[i + 1])
                    & valid_mask
                )

                # Count the forest pixels in this class
                forest_pixel_count = np.sum((forest_mask == 1) & bin_mask)
                total_pixel_count = np.sum(bin_mask)

                forest_pixels.append(int(forest_pixel_count))
                total_pixels.append(int(total_pixel_count))

                # Calculate the area and percentage
                forest_area = forest_pixel_count * pixel_area * area_factor
                forest_percentage = (
                    (forest_pixel_count / total_pixel_count * 100)
                    if total_pixel_count > 0
                    else 0
                )

                forest_areas.append(float(forest_area))
                forest_percentages.append(float(forest_percentage))

            return {
                "forest_area": forest_areas,
                "forest_percentage": forest_percentages,
                "forest_pixels": forest_pixels,
                "total_pixels": total_pixels,
            }

        except Exception as e:
            self.logger.error(f"Error calculating forest distribution: {str(e)}")
            return None

    def _get_base_directory(self) -> str:
        """Gets the base directory for relative paths."""
        try:
            # Try to get the Niamoto config directory first
            from niamoto.common.config import Config

            config = Config()
            return os.path.dirname(config.config_dir)
        except Exception:
            # Fallback: use the current directory
            return os.getcwd()
