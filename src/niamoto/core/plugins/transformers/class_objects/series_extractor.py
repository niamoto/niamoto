"""
Plugin for extracting a series of values from a specific class_object.
Handles extraction of values along a size/class axis, with optional sorting and numeric conversion.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import logging

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError

logger = logging.getLogger(__name__)


class FieldConfig(BaseModel):
    """Configuration for input/output field mapping with options"""

    input: str
    output: str
    numeric: bool = True
    sort: bool = True


class ClassObjectSeriesConfig(PluginConfig):
    """Configuration for series extractor plugin"""

    plugin: str = "class_object_series_extractor"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "raw_shape_stats",
            "class_object": "forest_fragmentation",
            "size_field": {
                "input": "class_name",
                "output": "sizes",
                "numeric": True,
                "sort": True,
            },
            "value_field": {
                "input": "class_value",
                "output": "values",
                "numeric": True,
            },
        }
    )


@register("class_object_series_extractor", PluginType.TRANSFORMER)
class ClassObjectSeriesExtractor(TransformerPlugin):
    """Plugin for extracting series from class_object data"""

    config_model = ClassObjectSeriesConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = self.config_model(**config)

        # Validate required fields are specified
        params = validated_config.params
        if not params.get("class_object"):
            raise DataTransformError(
                "class_object must be specified", details={"config": config}
            )

        if not params.get("size_field", {}).get("input"):
            raise DataTransformError(
                "size_field.input must be specified", details={"config": config}
            )

        if not params.get("value_field", {}).get("input"):
            raise DataTransformError(
                "value_field.input must be specified", details={"config": config}
            )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, List]:
        """
        Transform shape statistics data into a series.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.class_object: The class_object to extract from
                - params.size_field: Configuration for size/class axis
                - params.value_field: Configuration for value axis

        Returns:
            Dictionary with size and value arrays

        Example output:
            {
                "sizes": [10, 20, 30, 40, 50],  # Valeurs triées de class_name
                "values": [15, 25, 35, 25, 15]  # Valeurs correspondantes de class_value
            }
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get class_object configuration
            class_object = params["class_object"]

            # Filter data for specified class_object
            filtered_data = data[data["class_object"] == class_object].copy()

            if filtered_data.empty:
                # Return empty result instead of raising an error
                logger.debug(
                    f"No data found for class_object {class_object}, returning empty result"
                )
                size_config = FieldConfig(**params["size_field"])
                value_config = FieldConfig(**params["value_field"])
                return {
                    size_config.output: [],
                    value_config.output: [],
                }

            # Get size field configuration
            size_config = FieldConfig(**params["size_field"])

            # Validate size field exists
            if size_config.input not in filtered_data.columns:
                raise DataTransformError(
                    f"Size field {size_config.input} not found in data",
                    details={"available_columns": list(filtered_data.columns)},
                )

            # Process size values
            size_values = filtered_data[size_config.input].fillna(-1)

            # Convert to numeric if requested
            if size_config.numeric:
                try:
                    size_values = pd.to_numeric(size_values)
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert size values to numeric",
                        details={"error": str(e)},
                    )

            # Sort if requested
            if size_config.sort:
                sorted_indices = np.argsort(size_values.values)
                size_values = size_values.iloc[sorted_indices]
                filtered_data = filtered_data.iloc[sorted_indices]

            # Get value field configuration
            value_config = FieldConfig(**params["value_field"])

            # Validate value field exists
            if value_config.input not in filtered_data.columns:
                raise DataTransformError(
                    f"Value field {value_config.input} not found in data",
                    details={"available_columns": list(filtered_data.columns)},
                )

            # Process value values
            value_values = filtered_data[value_config.input]

            # Convert to numeric if requested
            if value_config.numeric:
                try:
                    value_values = pd.to_numeric(value_values)
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert values to numeric", details={"error": str(e)}
                    )

            # Construct result
            result = {
                size_config.output: size_values.tolist(),
                value_config.output: value_values.tolist(),
            }

            # Remove -1 values from result
            result[size_config.output] = [
                x for x in result[size_config.output] if x != -1
            ]
            result[value_config.output] = [
                x for x in result[value_config.output] if x != -1
            ]

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to extract series", details={"error": str(e), "config": config}
            )
