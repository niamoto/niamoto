"""
Plugin for analyzing time series data.
"""

from typing import Dict, Any
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)


class TimeSeriesAnalysisConfig(PluginConfig):
    """Configuration for time series analysis plugin"""

    plugin: str = "time_series_analysis"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": None,
            "fields": {},
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
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "field", "fields", "time_field"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(v["fields"], dict):
            raise ValueError("fields must be a dictionary")

        if not isinstance(v["time_field"], str):
            raise ValueError("time_field must be a string")

        # Validate labels if provided
        if "labels" in v:
            if not isinstance(v["labels"], list):
                raise ValueError("labels must be a list")
            if len(v["labels"]) != 12:
                raise ValueError("labels must contain exactly 12 items")

        return v


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

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            validated_config = self.config_model(**config)
            # Additional validation if needed
            if not isinstance(validated_config.params["fields"], dict):
                raise ValueError("fields must be a dictionary")
            if not validated_config.params["fields"]:
                raise ValueError("fields cannot be empty")
            if not isinstance(validated_config.params["time_field"], str):
                raise ValueError("time_field must be a string")
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Initialize params if not present
            if "params" not in config:
                config["params"] = {}

            # Set default parameters if not provided
            if "fields" not in config["params"]:
                config["params"]["fields"] = {}
            if "time_field" not in config["params"]:
                config["params"]["time_field"] = "month_obs"
            if "labels" not in config["params"]:
                config["params"]["labels"] = self.DEFAULT_LABELS

            validated_config = self.config_model(**config)

            # Get source data if different from occurrences
            if validated_config.params["source"] != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {validated_config.params["source"]}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Check required fields
            required_fields = [validated_config.params["time_field"]] + list(
                validated_config.params["fields"].values()
            )
            missing_fields = [
                field for field in required_fields if field not in data.columns
            ]
            if missing_fields:
                return {"month_data": {}, "labels": validated_config.params["labels"]}

            # Convert time field to numeric
            time_field = validated_config.params["time_field"]
            data[time_field] = pd.to_numeric(data[time_field], errors="coerce")

            # Convert phenology fields to numeric
            for field_name in validated_config.params["fields"].values():
                data[field_name] = pd.to_numeric(data[field_name], errors="coerce")

            # Initialize month data
            month_data = {
                name: [0] * 12 for name in validated_config.params["fields"].keys()
            }

            # Process each month
            for month in range(1, 13):
                month_df = data[data[time_field] == month]
                if not month_df.empty:
                    for phenology_name, field_name in validated_config.params[
                        "fields"
                    ].items():
                        if field_name in month_df:
                            # Calculate percentage of presence
                            total = len(month_df)
                            present = month_df[field_name].fillna(0).sum()
                            value = (present / total) * 100 if total > 0 else 0
                            month_data[phenology_name][month - 1] = round(value, 2)

            return {
                "month_data": month_data,
                "labels": validated_config.params["labels"],
            }

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
