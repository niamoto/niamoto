"""
Plugin for extracting statistics from raster data.
Permits to calculate various statistics (min, max, mean, etc.) from raster data
for a given geographic zone defined by a shape.
"""

from typing import Dict, Any, List
from pydantic import Field, field_validator
import pandas as pd
import geopandas as gpd
import numpy as np
import os
import logging
import rasterio
from rasterio.mask import mask

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class RasterStatsConfig(PluginConfig):
    """Configuration for the raster statistics plugin"""

    plugin: str = "raster_stats"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "raster_path": "",  # Path to the raster
            "shape_field": "geometry",  # Field containing the geometry
            "stats": [
                "min",
                "max",
                "mean",
                "median",
                "sum",
                "count",
                "std",
                "histogram",
            ],
            "bins": 10,  # Number of classes for the histogram
            "nodata": None,  # No data value for the raster
            "band": 1,  # Band to use (starts at 1)
            "scale_factor": 1.0,  # Scale factor to apply to the values
            "offset": 0.0,  # Offset to apply to the values
            "units": "",  # Units for the values
            "area_unit": "ha",  # Unit for the areas (ha ou km2)
        }
    )

    @field_validator("params")
    def validate_params(cls, v):
        """Validate the plugin parameters."""
        if "raster_path" not in v or not v["raster_path"]:
            raise ValueError("The path to the raster is required")

        # Validate the statistics
        valid_stats = [
            "min",
            "max",
            "mean",
            "median",
            "sum",
            "count",
            "std",
            "histogram",
            "percentile_5",
            "percentile_95",
            "majority",
            "minority",
            "unique",
            "range",
            "variance",
            "area",
        ]

        if "stats" in v:
            for stat in v["stats"]:
                if stat not in valid_stats:
                    raise ValueError(
                        f"Unsupported statistic: {stat}. Valid ones: {valid_stats}"
                    )

        # Validate the band
        if "band" in v and (not isinstance(v["band"], int) or v["band"] < 1):
            raise ValueError("The band must be a positive integer (starts at 1)")

        # Validate the number of classes
        if "bins" in v and (not isinstance(v["bins"], int) or v["bins"] < 2):
            raise ValueError("The number of classes (bins) must be an integer >= 2")

        # Validate the unit
        if "area_unit" in v and v["area_unit"] not in ["ha", "km2"]:
            raise ValueError("The unit for the areas must be 'ha' or 'km2'")

        return v


@register("raster_stats", PluginType.TRANSFORMER)
class RasterStats(TransformerPlugin):
    """
    Plugin for extracting statistics from raster data.

    This plugin permits to calculate various statistics (minimum, maximum, mean,
    median, etc.) from raster data (MNT, rainfall, etc.) for a given geographic
    zone defined by a shape.

    The results can be used for environmental data analysis, terrain characterization,
    ecological modeling, etc.
    """

    config_model = RasterStatsConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the plugin configuration."""
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
        Calculate statistics from a raster for a given shape.

        Args:
            data: GeoDataFrame containing the shape
            config: Configuration with extraction options

        Returns:
            Dictionary with the calculated statistics
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # 1. Extract the geometry
            main_geom = self._extract_geometry(data, params)

            # 2. Open the raster and extract the data
            raster_path = self._resolve_raster_path(params["raster_path"])
            masked_data = self._extract_raster_data(raster_path, main_geom, params)

            # 3. Calculate the statistics
            result = self._calculate_statistics(masked_data, main_geom, params)

            return result

        except Exception as e:
            self.logger.error(f"Failed to extract raster statistics: {str(e)}")
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Failed to extract raster statistics: {str(e)}",
                details={"config": config},
            )

    def _extract_geometry(self, data: pd.DataFrame, params: Dict[str, Any]):
        """
        Extracts the geometry from the input data.

        Args:
            data: Input data
            params: Configuration parameters

        Returns:
            Extracted geometry
        """
        self.logger.debug(f"Extracting geometry, input type: {type(data).__name__}")

        # If data is already a GeoDataFrame
        if isinstance(data, gpd.GeoDataFrame):
            self.logger.debug(
                f"Input is already a GeoDataFrame, columns: {list(data.columns)}"
            )
            if data.empty:
                raise DataTransformError("The GeoDataFrame is empty")
            return data.geometry.iloc[0]

        # Case where data is not a GeoDataFrame
        raise DataTransformError(
            "Input data must be a GeoDataFrame",
            details={"data_type": type(data).__name__},
        )

    def _resolve_raster_path(self, raster_path: str) -> str:
        """
        Resolves the raster path.

        Args:
            raster_path: Path to resolve

        Returns:
            Absolute path to the raster
        """
        if os.path.isabs(raster_path):
            return raster_path

        base_dir = self._get_base_directory()
        resolved_path = os.path.join(base_dir, raster_path)

        if not os.path.exists(resolved_path):
            raise DataTransformError(
                f"The raster file does not exist: {resolved_path}",
                details={"raster_path": raster_path, "base_dir": base_dir},
            )

        return resolved_path

    def _extract_raster_data(
        self, raster_path: str, geometry, params: Dict[str, Any]
    ) -> np.ndarray:
        """
        Extracts the raster data for the given geometry.

        Args:
            raster_path: Path to the raster
            geometry: Geometry to use as a mask
            params: Configuration parameters

        Returns:
            Array of valid raster values
        """
        try:
            with rasterio.open(raster_path) as src:
                # Check the band
                band = params["band"] - 1  # Convert to 0-based index
                if band < 0 or band >= src.count:
                    raise DataTransformError(
                        f"Invalid band: {params['band']}. The raster has {src.count} bands.",
                        details={"bands_available": src.count},
                    )

                # Mask the raster with the geometry
                masked, mask_transform = mask(
                    src, [geometry], crop=True, nodata=params.get("nodata")
                )

                # Get the raster data (specified band)
                band_data = masked[band]

                # Filter out nodata values
                nodata = params.get("nodata")
                if nodata is not None:
                    valid_data = band_data[band_data != nodata]
                else:
                    valid_data = band_data[~np.isnan(band_data)]

                if len(valid_data) == 0:
                    raise DataTransformError(
                        "No valid data found in the raster for this shape",
                        details={"raster_path": raster_path},
                    )

                # Apply scale factor and offset
                scale_factor = params.get("scale_factor", 1.0)
                offset = params.get("offset", 0.0)
                if scale_factor != 1.0 or offset != 0.0:
                    valid_data = valid_data * scale_factor + offset

                return valid_data

        except rasterio.errors.RasterioError as e:
            raise DataTransformError(
                f"Error opening or processing the raster: {str(e)}",
                details={"raster_path": raster_path},
            )

    def _calculate_statistics(
        self, data: np.ndarray, geometry, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculates the requested statistics.

        Args:
            data: Valid raster data
            geometry: Geometry used for the mask
            params: Configuration parameters

        Returns:
            Dictionary of calculated statistics
        """
        result = {}
        stats = params.get("stats", ["min", "max", "mean"])

        # Basic statistics
        self._calculate_basic_stats(data, stats, result)

        # Percentiles
        self._calculate_percentiles(data, stats, result)

        # Distribution statistics
        self._calculate_distribution_stats(data, stats, params, result)

        # Histogram
        if "histogram" in stats:
            self._calculate_histogram(data, params, result)

        # Area calculation
        if "area" in stats:
            self._calculate_area(geometry, params, result)

        # Add units if specified
        if "units" in params and params["units"]:
            result["units"] = params["units"]

        # Add metadata
        result["metadata"] = {
            "raster_source": os.path.basename(params["raster_path"]),
            "band": params["band"],
            "pixel_count": len(data),
            "scale_factor": params.get("scale_factor", 1.0),
            "offset": params.get("offset", 0.0),
        }

        return result

    def _calculate_basic_stats(
        self, data: np.ndarray, stats: List[str], result: Dict[str, Any]
    ) -> None:
        """
        Calculates the basic statistics.

        Args:
            data: Raster data
            stats: List of statistics to calculate
            result: Dictionary to update with the results
        """
        if "min" in stats:
            result["min"] = float(np.nanmin(data))

        if "max" in stats:
            result["max"] = float(np.nanmax(data))

        if "mean" in stats:
            result["mean"] = float(np.nanmean(data))

        if "median" in stats:
            result["median"] = float(np.nanmedian(data))

        if "sum" in stats:
            result["sum"] = float(np.nansum(data))

        if "count" in stats:
            result["count"] = int(len(data))

        if "std" in stats:
            result["std"] = float(np.nanstd(data))

        if "variance" in stats:
            result["variance"] = float(np.nanvar(data))

        if "range" in stats:
            result["range"] = float(np.nanmax(data) - np.nanmin(data))

    def _calculate_percentiles(
        self, data: np.ndarray, stats: List[str], result: Dict[str, Any]
    ) -> None:
        """
        Calculates the percentiles.

        Args:
            data: Raster data
            stats: List of statistics to calculate
            result: Dictionary to update with the results
        """
        if "percentile_5" in stats:
            result["percentile_5"] = float(np.percentile(data, 5))

        if "percentile_95" in stats:
            result["percentile_95"] = float(np.percentile(data, 95))

    def _calculate_distribution_stats(
        self,
        data: np.ndarray,
        stats: List[str],
        params: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """
        Calculates the distribution statistics.

        Args:
            data: Raster data
            stats: List of statistics to calculate
            params: Configuration parameters
            result: Dictionary to update with the results
        """
        if "majority" in stats or "minority" in stats or "unique" in stats:
            unique_values, counts = np.unique(data, return_counts=True)

            if "majority" in stats:
                majority_idx = np.argmax(counts)
                result["majority"] = float(unique_values[majority_idx])
                result["majority_count"] = int(counts[majority_idx])

            if "minority" in stats:
                minority_idx = np.argmin(counts)
                result["minority"] = float(unique_values[minority_idx])
                result["minority_count"] = int(counts[minority_idx])

            if "unique" in stats:
                result["unique_count"] = len(unique_values)

    def _calculate_histogram(
        self, data: np.ndarray, params: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        """
        Calculates the histogram of the data.

        Args:
            data: Raster data
            params: Configuration parameters
            result: Dictionary to update with the results
        """
        num_bins = params.get("bins", 10)
        hist, bin_edges = np.histogram(data, bins=num_bins)

        # Create class labels
        class_labels = []
        for i in range(len(bin_edges) - 1):
            class_labels.append(f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}")

        result["histogram"] = {
            "counts": hist.tolist(),
            "bin_edges": bin_edges.tolist(),
            "class_labels": class_labels,
        }

    def _calculate_area(
        self, geometry, params: Dict[str, Any], result: Dict[str, Any]
    ) -> None:
        """
        Calculates the surface area of the geometry.

        Args:
            geometry: Geometry
            params: Configuration parameters
            result: Dictionary to update with the results
        """
        try:
            area_unit = params.get("area_unit", "ha")
            area_factor = self._get_area_factor(area_unit)

            # Temporarily create a GeoDataFrame for easy projection
            temp_gdf = gpd.GeoDataFrame(
                geometry=[geometry], crs=getattr(geometry, "crs", None)
            )

            # Project to an appropriate CRS for a precise calculation if necessary
            if temp_gdf.crs and temp_gdf.crs.is_geographic:
                self.logger.debug("Projecting to a suitable CRS for area calculation")
                projected_gdf = self._project_to_appropriate_utm(temp_gdf)
                total_area = projected_gdf.geometry.area.iloc[0] * area_factor
            else:
                total_area = temp_gdf.geometry.area.iloc[0] * area_factor

            result["total_area"] = float(total_area)
            result["area_unit"] = area_unit

        except Exception as e:
            self.logger.warning(f"Error calculating area: {str(e)}")
            result["area_error"] = str(e)

    def _get_area_factor(self, area_unit: str) -> float:
        """
        Gets the conversion factor for the area unit.

        Args:
            area_unit: Area unit (ha, km2)

        Returns:
            Conversion factor
        """
        if area_unit == "ha":
            return 0.0001  # m² to ha
        elif area_unit == "km2":
            return 0.000001  # m² to km²
        else:
            return 1.0  # m²

    def _project_to_appropriate_utm(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Projects a GeoDataFrame to an appropriate UTM zone determined dynamically.

        Args:
            gdf: GeoDataFrame to project

        Returns:
            Projected GeoDataFrame
        """
        try:
            # Check that the GeoDataFrame has a projection defined
            if not gdf.crs:
                self.logger.warning(
                    "The GeoDataFrame has no CRS defined, cannot project"
                )
                return gdf

            # Ensure the GDF is in WGS84 (EPSG:4326) for correct UTM zone calculation
            if gdf.crs != "EPSG:4326":
                gdf_wgs84 = gdf.to_crs("EPSG:4326")
            else:
                gdf_wgs84 = gdf

            # Calculate the centroid to determine the UTM zone
            centroid = gdf_wgs84.unary_union.centroid

            # Calculate the UTM zone number from the longitude
            # Formula: ((longitude + 180)/6) + 1 (gives a zone number between 1-60)
            zone_number = int((centroid.x + 180) // 6) + 1

            # Determine the hemisphere from the latitude
            zone_hemisphere = "N" if centroid.y >= 0 else "S"

            # Special case for New Caledonia (if necessary)
            if 162 <= centroid.x <= 169 and -23 <= centroid.y <= -19:
                self.logger.debug("Using UTM 58S for New Caledonia")
                return gdf.to_crs("EPSG:3163")  # UTM 58S

            # Get the EPSG code for the UTM zone
            # Range: 32601-32660 for the North, 32701-32760 for the South
            utm_epsg = (
                32600 + zone_number if zone_hemisphere == "N" else 32700 + zone_number
            )

            self.logger.debug(
                f"Projecting to UTM zone {zone_number}{zone_hemisphere} (EPSG:{utm_epsg})"
            )

            # Project the GeoDataFrame to the calculated UTM zone
            return gdf.to_crs(f"EPSG:{utm_epsg}")

        except Exception as e:
            self.logger.warning(f"Error projecting to UTM: {str(e)}")
            # In case of error, return the original GeoDataFrame
            return gdf

    def _get_base_directory(self) -> str:
        """
        Gets the base directory for relative paths.

        Returns:
            Base directory path
        """
        try:
            # Try to get the Niamoto config directory first
            from niamoto.common.config import Config

            config = Config()
            return os.path.dirname(config.config_dir)
        except Exception as e:
            self.logger.warning(f"Cannot get the config directory: {str(e)}")
            # Fallback: use the current working directory
            return os.getcwd()
