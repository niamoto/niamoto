"""
Plugin for analyzing the distribution of forest types by elevation.
Permits to study the altitudinal distribution of different forest types in a landscape.
"""

from typing import Dict, Any, List
from pydantic import Field, field_validator
import pandas as pd
import geopandas as gpd
import numpy as np
import os
import rasterio
from rasterio.mask import mask
import rasterio.features

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class ForestElevationConfig(PluginConfig):
    """Configuration for the forest elevation analysis plugin"""

    plugin: str = "forest_elevation_analysis"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "forest_types_path": "",  # Path to the forest types layer
            "dem_path": "",  # Path to the elevation raster (DEM)
            "shape_field": "geometry",  # Field containing the main geometry
            "elevation_bins": [
                0,
                200,
                400,
                600,
                800,
                1000,
                1200,
                1400,
                1600,
            ],  # Elevation classes
            "forest_type_field": "type",  # Field containing the forest type
            "forest_types": [
                "Core forest",
                "Mature forest",
                "Secondary forest",
            ],  # Types to analyze
            "nodata": -9999,  # No data value
        }
    )

    @field_validator("params")
    def validate_paths(cls, v):
        """Validate the paths to the source data."""
        if "forest_types_path" not in v or not v["forest_types_path"]:
            raise ValueError("The path to the forest types layer is required")

        if "dem_path" not in v or not v["dem_path"]:
            raise ValueError("The path to the elevation raster is required")

        # Validate the elevation classes
        if "elevation_bins" in v:
            bins = v["elevation_bins"]
            if not isinstance(bins, list) or len(bins) < 2:
                raise ValueError("elevation_bins must be a list with at least 2 values")

            # Check that the bins are in ascending order
            if not all(bins[i] < bins[i + 1] for i in range(len(bins) - 1)):
                raise ValueError("The elevation classes must be in ascending order")

        # Validate the forest types
        if "forest_types" in v:
            if not isinstance(v["forest_types"], list) or not v["forest_types"]:
                raise ValueError("forest_types must be a non-empty list")

        return v


@register("forest_elevation_analysis", PluginType.TRANSFORMER)
class ForestElevationAnalysis(TransformerPlugin):
    """
    Plugin for analyzing the distribution of forest types by elevation.

    This plugin allows to study how different forest types (core, mature,
    secondary) are distributed along an elevational gradient. It intersects a
    vector layer of forest types with a digital elevation model (DEM).

    The results are formatted to be visualized as a stacked area chart showing
    the proportion of each forest type per elevation class.
    """

    config_model = ForestElevationConfig

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the plugin configuration."""
        try:
            validated_config = self.config_model(**config)
            # All validations are already done by the field validator in
            # ForestElevationConfig, so we don't need additional checks here.

            return validated_config
        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the distribution of forest types by elevation.

        Args:
            data: GeoDataFrame containing the shape
            config: Configuration with paths and options

        Returns:
            Dictionary with the distribution of forest types by elevation
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)

            # Extract the geometry
            if not isinstance(data, gpd.GeoDataFrame):
                raise DataTransformError(
                    "Input data must be a GeoDataFrame",
                    details={"data_type": type(data).__name__},
                )

            shape_field = validated_config.params.get("shape_field", "geometry")
            if shape_field not in data.columns and shape_field != "geometry":
                geometry = data.geometry
            else:
                geometry = data[shape_field]

            if geometry.empty:
                raise DataTransformError("No geometry found in the data")

            # Use the first geometry (usually one per analysis)
            main_geom = geometry.iloc[0]

            # Get the elevation bins
            elevation_bins = np.array(validated_config.params["elevation_bins"])

            # Resolve relative paths
            base_dir = self._get_base_directory()

            forest_types_path = validated_config.params["forest_types_path"]
            if not os.path.isabs(forest_types_path):
                forest_types_path = os.path.join(base_dir, forest_types_path)

            dem_path = validated_config.params["dem_path"]
            if not os.path.isabs(dem_path):
                dem_path = os.path.join(base_dir, dem_path)

            # Open the DEM
            try:
                with rasterio.open(dem_path) as src:
                    # Mask the DEM with the geometry
                    masked, mask_transform = mask(
                        src,
                        [main_geom],
                        crop=True,
                        nodata=validated_config.params["nodata"],
                    )

                    # Get the elevation data (first band)
                    elevation_data = masked[0]

                    # Filter out nodata values
                    nodata = validated_config.params["nodata"]
                    valid_mask = elevation_data != nodata

                    if np.sum(valid_mask) == 0:
                        return self._empty_results(
                            elevation_bins, validated_config.params["forest_types"]
                        )
            except Exception as e:
                self.logger.error(f"Error opening the DEM: {str(e)}")
                return self._empty_results(
                    elevation_bins, validated_config.params["forest_types"]
                )

            # Load the forest types layer
            try:
                forest_gdf = gpd.read_file(forest_types_path)

                if forest_gdf.empty:
                    return self._empty_results(
                        elevation_bins, validated_config.params["forest_types"]
                    )

                # Ensure the CRS matches
                if data.crs != forest_gdf.crs:
                    forest_gdf = forest_gdf.to_crs(data.crs)
            except Exception as e:
                self.logger.error(f"Error loading the forest types layer: {str(e)}")
                return self._empty_results(
                    elevation_bins, validated_config.params["forest_types"]
                )

            # Clip the forest layer to the main geometry
            try:
                forest_in_area = gpd.clip(
                    forest_gdf, gpd.GeoDataFrame(geometry=[main_geom], crs=data.crs)
                )

                if forest_in_area.empty:
                    return self._empty_results(
                        elevation_bins, validated_config.params["forest_types"]
                    )
            except Exception as e:
                self.logger.error(f"Error clipping the forest layer: {str(e)}")
                return self._empty_results(
                    elevation_bins, validated_config.params["forest_types"]
                )

            # Verify the forest type field
            forest_type_field = validated_config.params["forest_type_field"]
            if forest_type_field not in forest_in_area.columns:
                raise DataTransformError(
                    f"Field '{forest_type_field}' not found in the forest types layer",
                    details={"available_fields": list(forest_in_area.columns)},
                )

            # Create masks for each forest type
            forest_types = validated_config.params["forest_types"]
            type_masks = {}

            for forest_type in forest_types:
                # Filter by forest type
                try:
                    type_gdf = forest_in_area[
                        forest_in_area[forest_type_field] == forest_type
                    ]

                    if type_gdf.empty:
                        # If no data for this type, create an empty mask
                        type_masks[forest_type] = np.zeros_like(
                            elevation_data, dtype=np.uint8
                        )
                    else:
                        # Create a mask for this forest type
                        type_shapes = [(geom, 1) for geom in type_gdf.geometry]
                        type_mask = rasterio.features.rasterize(
                            type_shapes,
                            out_shape=elevation_data.shape,
                            transform=mask_transform,
                            fill=0,
                            dtype=np.uint8,
                        )
                        type_masks[forest_type] = type_mask
                except Exception as e:
                    self.logger.error(
                        f"Error creating the mask for {forest_type}: {str(e)}"
                    )
                    type_masks[forest_type] = np.zeros_like(
                        elevation_data, dtype=np.uint8
                    )

            # Calculate the distribution for each forest type
            result = {
                "elevation_bins": elevation_bins.tolist(),
            }

            # Get the total pixels per elevation bin
            total_pixels_by_bin = []
            for i in range(len(elevation_bins) - 1):
                bin_mask = (
                    (elevation_data >= elevation_bins[i])
                    & (elevation_data < elevation_bins[i + 1])
                    & valid_mask
                )
                total_pixels_by_bin.append(np.sum(bin_mask))

            # Calculate the distribution for each forest type
            for forest_type in forest_types:
                # Convert the forest type name to a key (lowercase, underscore)
                key = (
                    forest_type.lower()
                    .replace(" ", "_")
                    .replace("é", "e")
                    .replace("ê", "e")
                )
                type_mask = type_masks[forest_type]

                # Calculate the pixels per elevation bin
                type_by_bin = []
                for i in range(len(elevation_bins) - 1):
                    bin_mask = (
                        (elevation_data >= elevation_bins[i])
                        & (elevation_data < elevation_bins[i + 1])
                        & valid_mask
                    )
                    type_pixels = np.sum((type_mask == 1) & bin_mask)

                    # Calculate the percentage
                    percentage = (
                        (type_pixels / total_pixels_by_bin[i] * 100)
                        if total_pixels_by_bin[i] > 0
                        else 0
                    )
                    type_by_bin.append(float(percentage))

                result[f"forest_{key}"] = type_by_bin

            # Add the total for verification
            forest_pixels_by_bin = []
            for i in range(len(elevation_bins) - 1):
                bin_mask = (
                    (elevation_data >= elevation_bins[i])
                    & (elevation_data < elevation_bins[i + 1])
                    & valid_mask
                )

                # Sum the forest pixels (all types combined) in this bin
                forest_pixels = 0
                for type_mask in type_masks.values():
                    forest_pixels += np.sum((type_mask == 1) & bin_mask)

                forest_percentage = (
                    (forest_pixels / total_pixels_by_bin[i] * 100)
                    if total_pixels_by_bin[i] > 0
                    else 0
                )
                forest_pixels_by_bin.append(float(forest_percentage))

            result["forest_total"] = forest_pixels_by_bin

            # Add metadata for interpretation
            result["metadata"] = {
                "forest_types": forest_types,
                "elevation_unit": "m",
                "distribution_unit": "%",
            }

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Failed to analyze the distribution of forest types by elevation: {str(e)}",
                details={"config": config},
            )

    def _empty_results(
        self, elevation_bins: np.ndarray, forest_types: List[str]
    ) -> Dict[str, Any]:
        """Creates an empty result with the specified elevation bins and forest types."""
        result = {
            "elevation_bins": elevation_bins.tolist(),
        }

        # Add empty series for each forest type
        for forest_type in forest_types:
            key = (
                forest_type.lower()
                .replace(" ", "_")
                .replace("é", "e")
                .replace("ê", "e")
            )
            result[f"forest_{key}"] = [0.0] * (len(elevation_bins) - 1)

        result["forest_total"] = [0.0] * (len(elevation_bins) - 1)

        # Add metadata for interpretation
        result["metadata"] = {
            "forest_types": forest_types,
            "elevation_unit": "m",
            "distribution_unit": "%",
        }

        return result

    def _get_base_directory(self) -> str:
        """Gets the base directory for relative paths."""
        try:
            # Try to get the Niamoto config directory
            from niamoto.common.config import Config

            config = Config()
            return os.path.dirname(config.config_dir)
        except Exception:
            # Fallback: use the current working directory
            return os.getcwd()
