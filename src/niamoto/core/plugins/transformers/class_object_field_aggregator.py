"""
Plugin for aggregating field values from shape statistics.
Supports single fields, ranges (min/max), and multiple fields.
"""

from typing import Dict, Any, List, Union, Optional
from pydantic import BaseModel, Field
import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.exceptions import DataTransformError


class FieldConfig(BaseModel):
    """Configuration for a field"""

    source: str
    class_object: Union[str, List[str]]  # Can be string or list for ranges
    target: str
    units: str = ""
    format: Optional[str] = None  # "range" for min/max fields


class ClassObjectFieldAggregatorConfig(PluginConfig):
    """Configuration for field aggregator plugin"""

    plugin: str = "class_object_field_aggregator"
    source: str = "shape_stats"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "fields": [
                {
                    "source": "shape_stats",
                    "class_object": "land_area_ha",
                    "target": "land_area_ha",
                    "units": "ha",
                },
                {
                    "source": "shape_stats",
                    "class_object": ["rainfall_min", "rainfall_max"],
                    "target": "rainfall",
                    "units": "mm/an",
                    "format": "range",
                },
            ]
        }
    )


@register("class_object_field_aggregator", PluginType.TRANSFORMER)
class ClassObjectFieldAggregator(TransformerPlugin):
    """Plugin for aggregating field values"""

    config_model = ClassObjectFieldAggregatorConfig

    def _get_field_value(self, field: FieldConfig, data: pd.DataFrame) -> Any:
        """
        Get value for a field configuration.

        Args:
            field: Field configuration
            data: DataFrame containing the data

        Returns:
            Field value (single value, or dict for ranges)

        Raises:
            DataTransformError: If field is missing or invalid
        """
        try:
            # Handle range format (multiple fields)
            if field.format == "range" and isinstance(field.class_object, list):
                if len(field.class_object) != 2:
                    raise DataTransformError(
                        "Range format requires exactly 2 fields",
                        details={"fields": field.class_object},
                    )

                # Get min and max values
                min_field, max_field = field.class_object
                if min_field not in data.columns or max_field not in data.columns:
                    raise DataTransformError(
                        "Range fields not found in data",
                        details={
                            "min_field": min_field,
                            "max_field": max_field,
                            "available_columns": list(data.columns),
                        },
                    )

                return {
                    "min": float(data[min_field].iloc[0])
                    if not data[min_field].empty
                    else None,
                    "max": float(data[max_field].iloc[0])
                    if not data[max_field].empty
                    else None,
                }

            # Handle single field
            elif isinstance(field.class_object, str):
                if field.class_object not in data.columns:
                    raise DataTransformError(
                        f"Field {field.class_object} not found in data",
                        details={"available_columns": list(data.columns)},
                    )

                return (
                    float(data[field.class_object].iloc[0])
                    if not data[field.class_object].empty
                    else None
                )

            else:
                raise DataTransformError(
                    "Invalid field configuration", details={"field": field.dict()}
                )

        except Exception as e:
            if not isinstance(e, DataTransformError):
                raise DataTransformError(
                    "Error getting field value",
                    details={"error": str(e), "field": field.dict()},
                )
            raise

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        params = validated_config.params

        # Validate fields configuration
        fields = params.get("fields", {})
        if not fields:
            raise DataTransformError(
                "At least one field must be specified", details={"config": config}
            )

        # Validate each field configuration
        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                raise DataTransformError(
                    f"Field {field_name} configuration must be a dictionary",
                    details={"config": field_config},
                )

            # Check if it's a range configuration
            if "start" in field_config or "end" in field_config:
                if "start" not in field_config:
                    raise DataTransformError(
                        f"Field {field_name} range must specify 'start'",
                        details={"config": field_config},
                    )

                if "end" not in field_config:
                    raise DataTransformError(
                        f"Field {field_name} range must specify 'end'",
                        details={"config": field_config},
                    )

                if not isinstance(field_config["start"], (int, float, str)):
                    raise DataTransformError(
                        f"Field {field_name} start must be a number or string",
                        details={"config": field_config},
                    )

                if not isinstance(field_config["end"], (int, float, str)):
                    raise DataTransformError(
                        f"Field {field_name} end must be a number or string",
                        details={"config": field_config},
                    )
            else:
                # Single field configuration
                if "field" not in field_config:
                    raise DataTransformError(
                        f"Field {field_name} must specify 'field'",
                        details={"config": field_config},
                    )

                if not isinstance(field_config["field"], str):
                    raise DataTransformError(
                        f"Field {field_name} field must be a string",
                        details={"config": field_config},
                    )

            # Optional numeric validation
            if "numeric" in field_config and not isinstance(
                field_config["numeric"], bool
            ):
                raise DataTransformError(
                    f"Field {field_name} numeric must be a boolean",
                    details={"config": field_config},
                )

            # Optional units validation
            if "units" in field_config and not isinstance(field_config["units"], str):
                raise DataTransformError(
                    f"Field {field_name} units must be a string",
                    details={"config": field_config},
                )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and aggregate field values from shape statistics data.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.fields: List of field configurations with:
                    - source: Source of the data
                    - class_object: Field name or list of fields for ranges
                    - target: Name for output
                    - units: Optional units for the value
                    - format: Optional format (e.g. "range" for min/max)

        Returns:
            Dictionary with field values

        Example output:
            {
                "land_area_ha": 941252.41,
                "forest_area_ha": 321711.77,
                "rainfall": {"min": 510, "max": 4820},
                "elevation_median": 214
            }
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Initialize results
            results = {}

            # Process each field
            for field_config in params["fields"]:
                field = FieldConfig(**field_config)

                # Get and validate field value
                value = self._get_field_value(field, data)

                # Add to results if value exists
                if value is not None:
                    results[field.target] = value

            return results

        except Exception as e:
            raise DataTransformError(
                "Failed to aggregate field values",
                details={"error": str(e), "config": config},
            )
