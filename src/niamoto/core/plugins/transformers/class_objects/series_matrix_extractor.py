"""
Plugin for extracting and transforming multiple series from class objects into a matrix format.
Each series can be scaled and optionally complemented (100 - value).
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
import pandas as pd
import numpy as np
import logging

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError

log = logging.getLogger(__name__)


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


class SeriesMatrixParams(BaseModel):
    """Specific model for the 'params' structure"""

    source: str | None = None
    axis: AxisConfig
    series: List[SeriesConfig] = Field(..., min_length=1)


class ClassObjectSeriesMatrixConfig(PluginConfig):
    """Configuration for series matrix extractor plugin"""

    plugin: str = "class_object_series_matrix_extractor"
    params: SeriesMatrixParams


@register("class_object_series_matrix_extractor", PluginType.TRANSFORMER)
class ClassObjectSeriesMatrixExtractor(TransformerPlugin):
    """Plugin for extracting and transforming series into a matrix format"""

    config_model = ClassObjectSeriesMatrixConfig

    def validate_config(self, config: Dict[str, Any]) -> ClassObjectSeriesMatrixConfig:
        """Validate plugin configuration"""
        try:
            validated_config = self.config_model(**config)
            return validated_config
        except ValidationError as e:
            plugin_name = config.get("plugin", "class_object_series_matrix_extractor")
            raise DataTransformError(
                f"Invalid configuration for {plugin_name}: {e}",
                details={"pydantic_error": e.errors(), "config": config},
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform shape statistics data into series matrix.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary (validated by Pydantic)

        Returns:
            Dictionary with axis values and series data matrix.
        """
        try:
            validated_config = self.validate_config(config)
            params = validated_config.params
            axis_config = params.axis
            series_list = params.series

            first_series_config = series_list[0]
            initial_axis_data = data[
                data["class_object"] == first_series_config.class_object
            ].copy()

            if initial_axis_data.empty:
                raise DataTransformError(
                    f"No data found for initial class_object '{first_series_config.class_object}' needed for axis",
                    details={"config": config},
                )

            if axis_config.field not in initial_axis_data.columns:
                raise DataTransformError(
                    f"Axis field '{axis_config.field}' not found in data for initial class_object '{first_series_config.class_object}'",
                    details={"available_columns": initial_axis_data.columns.tolist()},
                )

            initial_axis_data = initial_axis_data.dropna(subset=[axis_config.field])
            if initial_axis_data.empty:
                raise DataTransformError(
                    f"Axis field '{axis_config.field}' contains only null values for initial class_object '{first_series_config.class_object}'",
                    details={"config": config},
                )

            axis_values = initial_axis_data[axis_config.field]
            if axis_config.numeric:
                try:
                    axis_values = pd.to_numeric(axis_values)
                except ValueError as e:
                    raise DataTransformError(
                        f"Failed to convert axis values to numeric for initial class_object '{first_series_config.class_object}'",
                        details={"error": str(e)},
                    )

            common_axis = axis_values.unique()
            if axis_config.sort:
                if pd.api.types.is_numeric_dtype(common_axis) or axis_config.numeric:
                    common_axis = np.sort(common_axis)
                else:
                    try:
                        common_axis = sorted(common_axis.astype(str))
                    except Exception:
                        log.warning(
                            f"Could not sort non-numeric axis '{axis_config.field}'. Using unique values as is."
                        )

            result = {axis_config.field: common_axis.tolist(), "series": {}}
            axis_df = pd.DataFrame({axis_config.field: common_axis})

            for series_config in series_list:
                series_data = data[
                    data["class_object"] == series_config.class_object
                ].copy()

                if series_data.empty:
                    log.warning(
                        f"No data found for class_object '{series_config.class_object}'. Filling series '{series_config.name}' with NaN."
                    )
                    result["series"][series_config.name] = [np.nan] * len(common_axis)
                    continue

                required_cols = [axis_config.field, "class_value"]
                if not all(col in series_data.columns for col in required_cols):
                    log.warning(
                        f"Missing required columns ({required_cols}) for class_object '{series_config.class_object}'. Filling series '{series_config.name}' with NaN."
                    )
                    result["series"][series_config.name] = [np.nan] * len(common_axis)
                    continue

                series_data = series_data.dropna(subset=required_cols)
                if series_data.empty:
                    log.warning(
                        f"No valid data points (after dropping nulls in {required_cols}) for class_object '{series_config.class_object}'. Filling series '{series_config.name}' with NaN."
                    )
                    result["series"][series_config.name] = [np.nan] * len(common_axis)
                    continue

                current_axis_values = series_data[axis_config.field]
                if axis_config.numeric:
                    try:
                        current_axis_values = pd.to_numeric(current_axis_values)
                    except Exception as e:
                        log.warning(
                            f"Failed to convert axis values to numeric for class_object '{series_config.class_object}'. Skipping series '{series_config.name}'. Error: {e}"
                        )
                        result["series"][series_config.name] = [np.nan] * len(
                            common_axis
                        )
                        continue
                series_data.loc[:, axis_config.field] = current_axis_values

                try:
                    values = (
                        series_data["class_value"].astype(float) * series_config.scale
                    )
                    if series_config.complement:
                        values = 100 - values
                except Exception as e:
                    log.warning(
                        f"Failed to process values for class_object '{series_config.class_object}'. Skipping series '{series_config.name}'. Error: {e}"
                    )
                    result["series"][series_config.name] = [np.nan] * len(common_axis)
                    continue

                current_series_df = (
                    pd.DataFrame(
                        {
                            axis_config.field: series_data[axis_config.field],
                            "value": values,
                        }
                    )
                    .groupby(axis_config.field)
                    .mean()
                    .reset_index()
                )

                aligned_series = pd.merge(
                    axis_df, current_series_df, on=axis_config.field, how="left"
                )

                result["series"][series_config.name] = aligned_series["value"].tolist()

            return result

        except DataTransformError:
            raise
        except Exception as e:
            log.exception(f"Unexpected error during series matrix extraction: {e}")
            raise DataTransformError(
                "Failed to extract series matrix due to an unexpected error.",
                details={"error": str(e), "config": config},
                cause=e,
            )
