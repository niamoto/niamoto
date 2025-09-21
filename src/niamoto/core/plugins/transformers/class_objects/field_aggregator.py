"""
Plugin for aggregating field values from shape statistics.
Supports single fields, ranges (min/max), and multiple fields.
"""

from typing import Dict, Any, List, Union, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class FieldConfig(BaseModel):
    """Configuration for a field"""

    source: Optional[str] = (
        None  # Optional source, will use parent source if not specified
    )
    class_object: Union[str, List[str]]  # Can be string or list for ranges
    target: str
    units: str = ""
    format: Optional[str] = None  # "range" for min/max fields


class FieldAggregatorParams(BasePluginParams):
    """Parameters for field aggregator plugin"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Aggregate field values from shape statistics",
            "examples": [
                {
                    "source": "shape_stats",
                    "fields": [
                        {
                            "class_object": "land_area_ha",
                            "target": "land_area_ha",
                            "units": "ha",
                        },
                        {
                            "class_object": ["rainfall_min", "rainfall_max"],
                            "target": "rainfall",
                            "units": "mm/an",
                            "format": "range",
                        },
                    ],
                }
            ],
        }
    )

    source: str = Field(
        default="shape_stats",
        description="Source table containing class_object data",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["raw_shape_stats", "shape_stats"],
        },
    )

    fields: List[FieldConfig] = Field(
        ...,
        min_length=1,
        description="List of field configurations",
        json_schema_extra={"ui:widget": "json"},
    )

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: List[FieldConfig]) -> List[FieldConfig]:
        """Validate field configurations."""
        if not v:
            raise ValueError("At least one field must be specified")
        return v


class ClassObjectFieldAggregatorConfig(PluginConfig):
    """Configuration for field aggregator plugin"""

    plugin: Literal["class_object_field_aggregator"] = "class_object_field_aggregator"
    params: FieldAggregatorParams


@register("class_object_field_aggregator", PluginType.TRANSFORMER)
class ClassObjectFieldAggregator(TransformerPlugin):
    """Plugin for aggregating fields from class objects"""

    config_model = ClassObjectFieldAggregatorConfig

    def _get_field_value(self, field: FieldConfig, data: pd.DataFrame) -> Any:
        """Get field value from data"""
        # Handle empty data (e.g., for hierarchical nodes like countries)
        if data.empty:
            # Return None values for empty data instead of raising error
            if field.format == "range":
                return {"min": None, "max": None}
            else:
                return {"value": None}

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

                if min_data.empty or max_data.empty:
                    # Return None values for missing range fields
                    return {"min": None, "max": None}

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
                    # Return None instead of error for missing fields
                    # This is normal for hierarchical nodes
                    return {"value": None}
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

    def validate_config(
        self, config: Dict[str, Any]
    ) -> ClassObjectFieldAggregatorConfig:
        """Validate plugin configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(
        self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform shape statistics data into field aggregations.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.fields: List of field configurations with:
                    - class_object: Field name or list of fields for ranges
                    - target: Name for output
                    - units: Optional units for output
                    - format: Optional format for output (range)
                - params.source: Optional source name (handled by TransformerService)

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
            for field in params.fields:
                # Determine which source to use
                # Priority: field.source -> params.source -> first available
                source_name = field.source if field.source else params.source

                if isinstance(data, dict):
                    # Multiple data sources available
                    source_data = data.get(source_name, pd.DataFrame())
                    if source_data.empty and data:
                        # Fallback to first available data if source not found
                        source_data = list(data.values())[0]
                else:
                    # Single DataFrame case
                    source_data = data

                # Get field data
                result = self._get_field_value(field, source_data)

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
