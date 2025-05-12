"""
Plugin for analyzing time series data.
"""

from typing import Dict, Any
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


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

        # Check for required fields
        required_fields = ["source", "time_field"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        # Either 'field' or 'fields' must be provided
        if "field" not in v and ("fields" not in v or not v["fields"]):
            raise ValueError("Either 'field' or 'fields' must be provided")

        # Validate fields if provided
        if "fields" in v:
            if not isinstance(v["fields"], dict):
                raise ValueError("fields must be a dictionary")

            # If fields is provided and not empty, field is optional
            if v["fields"] and "field" not in v:
                v["field"] = None  # Set a default value to satisfy other validations

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
            if "fields" in validated_config.params:
                if not isinstance(validated_config.params["fields"], dict):
                    raise ValueError("fields must be a dictionary")

                # Either field or fields must be provided and valid
                if not validated_config.params["fields"] and (
                    "field" not in validated_config.params
                    or not validated_config.params["field"]
                ):
                    raise ValueError(
                        "Either 'field' or 'fields' must be provided and not empty"
                    )

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

            # Ensure field is set if not provided but needed for validation
            if "field" not in config["params"] and config["params"]["fields"]:
                config["params"]["field"] = None

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
            time_field = validated_config.params["time_field"]
            required_fields = [time_field]

            # Add fields from the fields dictionary
            if validated_config.params["fields"]:
                required_fields.extend(list(validated_config.params["fields"].values()))
            # Or add the single field if provided
            elif (
                "field" in validated_config.params and validated_config.params["field"]
            ):
                required_fields.append(validated_config.params["field"])

            missing_fields = [
                field for field in required_fields if field not in data.columns
            ]
            if missing_fields:
                return {"month_data": {}, "labels": validated_config.params["labels"]}

            # Convert time field to numeric
            data[time_field] = pd.to_numeric(data[time_field], errors="coerce")

            # Initialize month data
            month_data = {}

            # Process fields dictionary if provided
            if validated_config.params["fields"]:
                # Convert phenology fields to numeric
                for field_name in validated_config.params["fields"].values():
                    data[field_name] = pd.to_numeric(data[field_name], errors="coerce")

                # Initialize month data structure
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

            # Process single field if provided and fields is empty
            elif (
                "field" in validated_config.params and validated_config.params["field"]
            ):
                field_name = validated_config.params["field"]
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
                "labels": validated_config.params["labels"],
            }

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
