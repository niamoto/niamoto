"""
Plugin for aggregating field values from shape statistics.
Supports single fields, ranges (min/max), and multiple fields.
"""

from typing import Dict, Any, List, Union, Optional
from pydantic import BaseModel, Field
import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class FieldConfig(BaseModel):
    """Configuration for a field"""

    class_object: Union[str, List[str]]  # Can be string or list for ranges
    source: str  # Source of the data
    target: str
    units: str = ""
    format: Optional[str] = None  # "range" for min/max fields


class ClassObjectFieldAggregatorConfig(PluginConfig):
    """Configuration for field aggregator plugin"""

    plugin: str = "class_object_field_aggregator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "fields": [
                {
                    "class_object": "land_area_ha",
                    "source": "shape_stats",
                    "target": "land_area_ha",
                    "units": "ha",
                },
                {
                    "class_object": ["rainfall_min", "rainfall_max"],
                    "source": "shape_stats",
                    "target": "rainfall",
                    "units": "mm/an",
                    "format": "range",
                },
            ]
        }
    )


@register("class_object_field_aggregator", PluginType.TRANSFORMER)
class ClassObjectFieldAggregator(TransformerPlugin):
    """Plugin for aggregating fields from class objects"""

    config_model = ClassObjectFieldAggregatorConfig

    def _get_field_value(self, field: FieldConfig, data: pd.DataFrame) -> Any:
        """Get field value from data"""
        # For range fields (min/max)
        if field.format == "range":
            if not isinstance(field.class_object, list) or len(field.class_object) != 2:
                raise DataTransformError(
                    "Range fields must specify exactly two fields",
                    details={"fields": field.class_object},
                )

            # Get min/max values
            try:
                min_data = data[data["class_object"] == field.class_object[0]]
                max_data = data[data["class_object"] == field.class_object[1]]

                if min_data.empty:
                    raise DataTransformError(
                        f"Field '{field.class_object[0]}' not found in data",
                        details={
                            "field": field.class_object[0],
                            "available_fields": data["class_object"].unique().tolist(),
                        },
                    )
                if max_data.empty:
                    raise DataTransformError(
                        f"Field '{field.class_object[1]}' not found in data",
                        details={
                            "field": field.class_object[1],
                            "available_fields": data["class_object"].unique().tolist(),
                        },
                    )

                min_value = float(min_data["class_value"].iloc[0])
                max_value = float(max_data["class_value"].iloc[0])

                return {"min": min_value, "max": max_value}
            except IndexError:
                raise DataTransformError(
                    f"No values found for fields {field.class_object}",
                    details={
                        "fields": field.class_object,
                        "available_fields": data["class_object"].unique().tolist(),
                    },
                )

        # For single fields
        else:
            if not isinstance(field.class_object, str):
                raise DataTransformError(
                    "Single field format requires a string field name"
                )

            # Get value
            try:
                field_data = data[data["class_object"] == field.class_object]
                if field_data.empty:
                    raise DataTransformError(
                        f"Field '{field.class_object}' not found in data",
                        details={
                            "field": field.class_object,
                            "available_fields": data["class_object"].unique().tolist(),
                        },
                    )
                value = float(field_data["class_value"].iloc[0])
                return {"value": value}
            except IndexError:
                raise DataTransformError(
                    f"No value found for field '{field.class_object}'",
                    details={
                        "field": field.class_object,
                        "available_fields": data["class_object"].unique().tolist(),
                    },
                )

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = self.config_model(**config)
        params = validated_config.params

        # Validate fields configuration
        fields = params.get("fields", [])
        if not fields:
            raise DataTransformError(
                "At least one field must be specified", details={"config": config}
            )

        # Validate each field configuration
        for field in fields:
            if "source" not in field:
                raise DataTransformError(
                    "source must be specified for each field",
                    details={"field": field},
                )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform shape statistics data into field aggregations.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.fields: List of field configurations with:
                    - class_object: Field name or list of fields for ranges
                    - source: Source of the data
                    - target: Name for output
                    - units: Optional units for output
                    - format: Optional format for output (range)

        Returns:
            Dictionary with aggregated fields

        Example output:
            {
                "land_area_ha": {
                    "value": 1000,
                    "units": "ha"
                },
                "rainfall": {
                    "min": 1000,
                    "max": 2000,
                    "units": "mm/an"
                }
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

                # Get field data
                result = self._get_field_value(field, data)

                # Add units if specified
                if field.units:
                    result["units"] = field.units

                results[field.target] = result

            return results

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to transform field aggregations",
                details={"error": str(e), "config": config},
            )
