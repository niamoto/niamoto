"""
Plugin for analyzing the distribution of forests in Holdridge life zones.
Combines a forest layer with a Holdridge raster to calculate the distribution of forest
and non-forest areas in each life zone.
"""

from typing import Dict, Any, Literal
from pydantic import Field, ConfigDict, model_validator
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import rasterio.features

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class ForestHoldridgeParams(BasePluginParams):
    """Typed parameters for Holdridge forest analysis plugin.

    This plugin analyzes the distribution of forests in Holdridge life zones.
    Combines a forest layer with a Holdridge raster to calculate the distribution
    of forest and non-forest areas in each life zone.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Analyze forest distribution in Holdridge life zones",
            "examples": [
                {
                    "forest_path": "imports/forest_cover.shp",
                    "holdridge_path": "rasters/holdridge_zones.tif",
                    "shape_field": "geometry",
                    "holdridge_values": {1: "Dry", 2: "Humid", 3: "Very Humid"},
                    "nodata": -9999,
                }
            ],
        }
    )

    forest_path: str = Field(
        ...,
        description="Path to the forest layer (shapefile, geopackage, etc.)",
        json_schema_extra={
            "ui:widget": "file-select",
            "ui:accept": ".shp,.gpkg,.geojson",
        },
    )

    holdridge_path: str = Field(
        ...,
        description="Path to the Holdridge life zones raster file",
        json_schema_extra={"ui:widget": "file-select", "ui:accept": ".tif,.tiff"},
    )

    shape_field: str = Field(
        default="geometry",
        description="Field containing the main geometry",
        json_schema_extra={"ui:widget": "text"},
    )

    holdridge_values: Dict[int, str] = Field(
        default_factory=lambda: {1: "Dry", 2: "Humid", 3: "Very Humid"},
        description="Mapping of Holdridge raster values to life zone names",
        json_schema_extra={"ui:widget": "mapping"},
    )

    nodata: int = Field(
        default=-9999,
        description="Nodata value in the Holdridge raster",
        json_schema_extra={"ui:widget": "number"},
    )

    @model_validator(mode="after")
    def validate_paths(self):
        """Validate that required paths are provided."""
        if not self.forest_path.strip():
            raise ValueError("forest_path is required")
        if not self.holdridge_path.strip():
            raise ValueError("holdridge_path is required")
        if not self.holdridge_values:
            raise ValueError("holdridge_values mapping is required")
        return self


class ForestHoldridgeConfig(PluginConfig):
    """Configuration for the Holdridge forest analysis plugin"""

    plugin: Literal["forest_holdridge_analysis"] = "forest_holdridge_analysis"
    params: ForestHoldridgeParams


@register("forest_holdridge_analysis", PluginType.TRANSFORMER)
class ForestHoldridgeAnalysis(TransformerPlugin):
    """
    Plugin for analyzing the distribution of forests in Holdridge life zones.

    This plugin combines a forest layer with a Holdridge raster to calculate the distribution
    of forest and non-forest areas in each life zone.
    """

    config_model = ForestHoldridgeConfig

    def validate_config(self, config: Dict[str, Any]) -> ForestHoldridgeConfig:
        """Validate configuration and return typed config."""
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
        Analyzes the distribution of forests in Holdridge life zones.

        Args:
            data: GeoDataFrame containing the shape
            config: Configuration with paths and options

        Returns:
            Dictionary with the Holdridge analysis structured
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Extract the geometry
            if not isinstance(data, gpd.GeoDataFrame):
                raise DataTransformError(
                    "The input data must be a GeoDataFrame",
                    details={"data_type": type(data).__name__},
                )

            if (
                params["shape_field"] not in data.columns
                and params["shape_field"] != "geometry"
            ):
                geometry = data.geometry
            else:
                geometry = data[params["shape_field"]]

            if geometry.empty:
                raise DataTransformError("No geometry found in the data")

            # Use the first geometry (usually one per shape analysis)
            main_geom = geometry.iloc[0]

            # Get the correspondence of Holdridge values
            holdridge_values = params["holdridge_values"]

            # Open the Holdridge raster
            with rasterio.open(params["holdridge_path"]) as src:
                # Mask the raster with the geometry
                masked, mask_transform = mask(
                    src, [main_geom], crop=True, nodata=params["nodata"]
                )

                # Get the Holdridge data (first band)
                holdridge_data = masked[0]

                # Filter the nodata values
                nodata = params["nodata"]
                valid_mask = holdridge_data != nodata
                valid_data = holdridge_data[valid_mask]

                if len(valid_data) == 0:
                    return {
                        "error": "No valid Holdridge data found in the shape",
                        "forest": {"dry": 0.0, "humid": 0.0, "very_humid": 0.0},
                        "non_forest": {"dry": 0.0, "humid": 0.0, "very_humid": 0.0},
                    }

                # Load the forest layer
                forest_gdf = gpd.read_file(params["forest_path"])

                if forest_gdf.empty:
                    raise DataTransformError(
                        f"No data found in the forest layer: {params['forest_path']}"
                    )

                # Ensure the CRS matches
                if data.crs != forest_gdf.crs:
                    forest_gdf = forest_gdf.to_crs(data.crs)

                # Clip the forest to the main geometry
                forest_in_area = gpd.clip(
                    forest_gdf, gpd.GeoDataFrame(geometry=[main_geom], crs=data.crs)
                )

                # Create a raster mask for the forest
                if forest_in_area.empty:
                    forest_mask = np.zeros_like(holdridge_data, dtype=np.uint8)
                else:
                    forest_shapes = [(geom, 1) for geom in forest_in_area.geometry]
                    forest_mask = rasterio.features.rasterize(
                        forest_shapes,
                        out_shape=holdridge_data.shape,
                        transform=mask_transform,
                        fill=0,
                        dtype=np.uint8,
                    )

                # Calculate the area of each pixel
                # pixel_area = abs(mask_transform[0] * mask_transform[4])

                # Initialize the results
                forest_result = {key: 0.0 for key in ["dry", "humid", "very_humid"]}
                non_forest_result = {key: 0.0 for key in ["dry", "humid", "very_humid"]}

                # Calculate the area for each Holdridge zone, divided by forest/non-forest
                total_valid_pixels = np.sum(valid_mask)

                for holdridge_code, holdridge_name in holdridge_values.items():
                    # Convert the Holdridge name to a key (lowercase, underscore)
                    key = holdridge_name.lower().replace(" ", "_").replace("è", "e")

                    # Calculate the forest pixels in this Holdridge zone
                    zone_mask = holdridge_data == holdridge_code
                    zone_forest_pixels = np.sum((forest_mask == 1) & zone_mask)
                    zone_total_pixels = np.sum(zone_mask)

                    # Calculate the percentages relative to the total surface
                    forest_pct = (
                        zone_forest_pixels / total_valid_pixels
                        if total_valid_pixels > 0
                        else 0
                    )
                    non_forest_pct = (
                        (zone_total_pixels - zone_forest_pixels) / total_valid_pixels
                        if total_valid_pixels > 0
                        else 0
                    )

                    # Store the results
                    forest_result[key] = round(forest_pct, 4)
                    non_forest_result[key] = round(non_forest_pct, 4)

                return {"forest": forest_result, "non_forest": non_forest_result}

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Failed to analyze the Holdridge zones: {str(e)}",
                details={"config": config},
            )
