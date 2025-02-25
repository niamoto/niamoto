"""
Plugin for extracting and transforming multiple series from class objects into a matrix format.
Each series can be scaled and optionally complemented (100 - value).
"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.exceptions import DataTransformError


class SeriesConfig(BaseModel):
    """Configuration for a single series"""

    name: str = Field(..., description="Name of the series in the output")
    class_object: str = Field(..., description="Class object to extract data from")
    scale: float = Field(1.0, description="Scale factor to apply to values")
    complement: bool = Field(False, description="If True, return 100 - value")


class AxisConfig(BaseModel):
    """Configuration for the axis"""

    field: str = Field(..., description="Field to use for axis values")
    numeric: bool = Field(True, description="Convert values to numeric")
    sort: bool = Field(True, description="Sort axis values")


class ClassObjectSeriesMatrixConfig(PluginConfig):
    """Configuration for series matrix extractor plugin"""

    plugin: str = "class_object_series_matrix_extractor"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "shape_stats",
            "axis": {"field": "class_name", "numeric": True, "sort": True},
            "series": [
                {
                    "name": "forest_um",
                    "class_object": "ratio_forest_um_elevation",
                    "scale": 100,
                }
            ],
        }
    )


@register("class_object_series_matrix_extractor", PluginType.TRANSFORMER)
class ClassObjectSeriesMatrixExtractor(TransformerPlugin):
    """Plugin for extracting and transforming series into a matrix format"""

    config_model = ClassObjectSeriesMatrixConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration"""
        validated_config = super().validate_config(config)

        # Validate that at least one series is specified
        series = validated_config.params.get("series", [])
        if not series:
            raise DataTransformError(
                "At least one series must be specified",
                details={"config": config},
            )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform shape statistics data into series matrix.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.axis: Configuration for common axis
                - params.series: List of series configurations

        Returns:
            Dictionary with class_name (axis values) and series data

        Example output:
            {
                "class_name": [0, 200, 400, 600, 800],
                "series": {
                    "forest_um": [20, 30, 40, 30, 20],
                    "forest_num": [25, 35, 45, 35, 25],
                    "hors_foret_um": [80, 70, 60, 70, 80],
                    "hors_foret_num": [75, 65, 55, 65, 75]
                }
            }
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get axis configuration
            axis_config = AxisConfig(**params["axis"])

            # Initialize result structure
            result = {"class_name": [], "series": {}}

            # Process first series to get axis values
            if not params["series"]:
                return result

            first_series = params["series"][0]
            axis_data = data[
                data["class_object"] == first_series["class_object"]
            ].copy()

            # Convert and sort axis values if configured
            if axis_config.numeric:
                try:
                    axis_data.loc[:, axis_config.field] = pd.to_numeric(
                        axis_data[axis_config.field]
                    )
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert axis values to numeric",
                        details={"error": str(e)},
                    )

            if axis_config.sort:
                axis_data = axis_data.sort_values(axis_config.field)

            # Store axis values
            result["class_name"] = axis_data[axis_config.field].tolist()

            # Process each series
            for series_config in params["series"]:
                series = SeriesConfig(**series_config)

                # Get series data
                series_data = data[data["class_object"] == series.class_object].copy()

                if series_data.empty:
                    raise DataTransformError(
                        f"No data found for class_object {series.class_object}",
                        details={
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist()
                        },
                    )

                # Convert and sort values
                if axis_config.numeric:
                    series_data.loc[:, axis_config.field] = pd.to_numeric(
                        series_data[axis_config.field]
                    )
                if axis_config.sort:
                    series_data = series_data.sort_values(axis_config.field)

                # Convert values to float and apply scale
                values = series_data["class_value"].astype(float) * series.scale

                # Apply complement if configured
                if series.complement:
                    values = 100 - values

                # Store series values
                result["series"][series.name] = values.tolist()

            return result

        except Exception as e:
            raise DataTransformError(
                "Failed to extract series matrix",
                details={"error": str(e), "config": config},
            )
