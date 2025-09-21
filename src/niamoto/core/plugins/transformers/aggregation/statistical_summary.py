"""
Plugin for calculating statistical summaries.
"""

from typing import Dict, Any, List, Literal, Union
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


class StatisticalSummaryParams(BasePluginParams):
    """Typed parameters for statistical summary plugin."""

    source: str = Field(
        ...,
        description="Data source table name",
        json_schema_extra={
            "examples": ["occurrences", "taxonomy", "plots"],
            "ui_component": "select",
            "ui_options": ["occurrences", "taxonomy", "plots"],
        },
    )

    field: str = Field(
        ...,
        description="Name of the numeric field to analyze",
        json_schema_extra={
            "examples": ["elevation", "height", "dbh"],
            "ui_component": "field_selector",
        },
    )

    stats: List[Literal["min", "mean", "max", "median", "std"]] = Field(
        default=["min", "mean", "max"],
        description="List of statistics to calculate",
        json_schema_extra={
            "ui_component": "multi_select",
            "ui_options": [
                {"value": "min", "label": "Minimum"},
                {"value": "mean", "label": "Mean (Average)"},
                {"value": "max", "label": "Maximum"},
                {"value": "median", "label": "Median"},
                {"value": "std", "label": "Standard Deviation"},
            ],
        },
    )

    units: str = Field(
        default="",
        description="Units of measurement for display purposes",
        json_schema_extra={
            "examples": ["m", "cm", "kg", "°C", "%"],
            "ui_component": "text",
        },
    )

    max_value: Union[int, float] = Field(
        default=100,
        description="Maximum value for scaling/display purposes. Will be overridden if data maximum is higher.",
        ge=0,
        json_schema_extra={"ui_component": "number", "ui_step": 1},
    )


class StatisticalSummaryConfig(PluginConfig):
    """Configuration for statistical summary plugin"""

    plugin: str = "statistical_summary"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": "",
            "stats": ["min", "mean", "max"],
            "units": "",
            "max_value": 100,
        },
        description="Parameters for statistical summary calculation",
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params using the typed model."""
        # Convert to typed model for validation
        StatisticalSummaryParams(**v)
        return v


@register("statistical_summary", PluginType.TRANSFORMER)
class StatisticalSummary(TransformerPlugin):
    """Plugin for calculating statistical summaries"""

    config_model = StatisticalSummaryConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            # Validate using both the general config model and the typed params
            validated_config = self.config_model(**config)
            # Additional validation with typed params model
            StatisticalSummaryParams(**validated_config.params)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Validate config and get typed parameters
            validated_config = self.config_model(**config)
            # Convert to typed params for easier access
            params = StatisticalSummaryParams(**validated_config.params)

            # Get source data if different from occurrences
            if params.source != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {params.source}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Get field data
            field_data = data[params.field]

            if field_data.empty:
                # Return None values for all requested stats
                result = {stat: None for stat in params.stats}
                result["units"] = params.units
                result["max_value"] = params.max_value
                return result

            # Calculate statistics
            result = {}
            if "min" in params.stats:
                result["min"] = (
                    round(float(field_data.min()), 2)
                    if not pd.isna(field_data.min())
                    else None
                )
            if "mean" in params.stats:
                result["mean"] = (
                    round(float(field_data.mean()), 2)
                    if not pd.isna(field_data.mean())
                    else None
                )
            if "max" in params.stats:
                result["max"] = (
                    round(float(field_data.max()), 2)
                    if not pd.isna(field_data.max())
                    else None
                )
            if "median" in params.stats:
                result["median"] = (
                    round(float(field_data.median()), 2)
                    if not pd.isna(field_data.median())
                    else None
                )
            if "std" in params.stats:
                result["std"] = (
                    round(float(field_data.std()), 2)
                    if not pd.isna(field_data.std())
                    else None
                )

            # Add units from configuration
            result["units"] = params.units

            # Set max_value, override with actual data max if higher
            if not field_data.empty and not pd.isna(field_data.max()):
                data_max = round(float(field_data.max()), 2)
                result["max_value"] = (
                    data_max if data_max > params.max_value else params.max_value
                )
            else:
                result["max_value"] = params.max_value

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
