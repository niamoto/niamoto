"""
Plugin for analyzing time series data.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import field_validator, Field, ConfigDict, model_validator

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


class TimeSeriesAnalysisParams(BasePluginParams):
    """Parameters for time series analysis plugin."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Analyze time series data by aggregating values over time periods",
            "examples": [
                {
                    "source": "occurrences",
                    "field": "presence",
                    "time_field": "month_obs",
                    "labels": [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ],
                },
                {
                    "source": "occurrences",
                    "fields": {"flowers": "has_flowers", "fruits": "has_fruits"},
                    "time_field": "month_obs",
                },
            ],
        }
    )

    source: str = Field(
        default="occurrences",
        description="Source table for time series data",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["occurrences", "plots", "observations"],
        },
    )

    field: Optional[str] = Field(
        default=None,
        description="Single field to analyze over time",
        json_schema_extra={
            "ui:widget": "field-select",
            "ui:depends": "source",
            "ui:condition": "!fields || Object.keys(fields).length === 0",
        },
    )

    fields: Dict[str, str] = Field(
        default_factory=dict,
        description="Multiple fields to analyze (key: display name, value: field name)",
        json_schema_extra={"ui:widget": "json", "ui:condition": "!field"},
    )

    time_field: str = Field(
        default="month_obs",
        description="Field containing time period values (e.g., month number)",
        json_schema_extra={"ui:widget": "field-select", "ui:depends": "source"},
    )

    labels: List[str] = Field(
        default=[
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        min_length=12,
        max_length=12,
        description="Labels for the 12 time periods (e.g., month names)",
        json_schema_extra={"ui:widget": "tags"},
    )

    @model_validator(mode="after")
    def validate_field_configuration(self):
        """Validate that either field or fields is provided."""
        if not self.field and not self.fields:
            raise ValueError("Either 'field' or 'fields' must be provided")
        return self

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: List[str]) -> List[str]:
        """Validate labels list."""
        if len(v) != 12:
            raise ValueError("labels must contain exactly 12 items")
        return v


class TimeSeriesAnalysisConfig(PluginConfig):
    """Configuration for time series analysis plugin"""

    plugin: Literal["time_series_analysis"] = "time_series_analysis"
    params: TimeSeriesAnalysisParams


@register("time_series_analysis", PluginType.TRANSFORMER)
class TimeSeriesAnalysis(TransformerPlugin):
    """Plugin for analyzing time series data"""

    config_model = TimeSeriesAnalysisConfig

    # Default labels in English
    DEFAULT_LABELS = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    def validate_config(self, config: Dict[str, Any]) -> TimeSeriesAnalysisConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get source data if different from occurrences
            if params.source != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {params.source}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Check required fields
            time_field = params.time_field
            required_fields = [time_field]

            # Add fields from the fields dictionary
            if params.fields:
                required_fields.extend(list(params.fields.values()))
            # Or add the single field if provided
            elif params.field:
                required_fields.append(params.field)

            missing_fields = [
                field for field in required_fields if field not in data.columns
            ]
            if missing_fields:
                return {"month_data": {}, "labels": params.labels}

            # Convert time field to numeric
            data[time_field] = pd.to_numeric(data[time_field], errors="coerce")

            # Initialize month data
            month_data = {}

            # Process fields dictionary if provided
            if params.fields:
                # Convert phenology fields to numeric
                for field_name in params.fields.values():
                    data[field_name] = pd.to_numeric(data[field_name], errors="coerce")

                # Initialize month data structure
                month_data = {name: [0] * 12 for name in params.fields.keys()}

                # Process each month
                for month in range(1, 13):
                    month_df = data[data[time_field] == month]
                    if not month_df.empty:
                        for phenology_name, field_name in params.fields.items():
                            if field_name in month_df:
                                # Calculate percentage of presence
                                total = len(month_df)
                                present = month_df[field_name].fillna(0).sum()
                                value = (present / total) * 100 if total > 0 else 0
                                month_data[phenology_name][month - 1] = round(value, 2)

            # Process single field if provided and fields is empty
            elif params.field:
                field_name = params.field
                data[field_name] = pd.to_numeric(data[field_name], errors="coerce")

                # Initialize month data with a single series
                month_data = {"value": [0] * 12}

                # Process each month
                for month in range(1, 13):
                    month_df = data[data[time_field] == month]
                    if not month_df.empty:
                        # Calculate percentage of presence
                        total = len(month_df)
                        present = month_df[field_name].fillna(0).sum()
                        value = (present / total) * 100 if total > 0 else 0
                        month_data["value"][month - 1] = round(value, 2)

            return {
                "month_data": month_data,
                "labels": params.labels,
            }

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
