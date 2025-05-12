"""
Plugin for calculating statistical summaries.
"""

from typing import Dict, Any
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


class StatisticalSummaryConfig(PluginConfig):
    """Configuration for statistical summary plugin"""

    plugin: str = "statistical_summary"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": None,
            "stats": ["min", "mean", "max"],
            "units": "",
            "max_value": 100,
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "field"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if "stats" in v and not isinstance(v["stats"], list):
            raise ValueError("stats must be a list")

        if "stats" in v:
            valid_stats = ["min", "mean", "max"]
            for stat in v["stats"]:
                if stat not in valid_stats:
                    raise ValueError(
                        f"Invalid stat: {stat}. Must be one of {valid_stats}"
                    )

        if "units" in v and not isinstance(v["units"], str):
            raise ValueError("units must be a string")

        if "max_value" in v and not isinstance(v["max_value"], (int, float)):
            raise ValueError("max_value must be a number")

        return v


@register("statistical_summary", PluginType.TRANSFORMER)
class StatisticalSummary(TransformerPlugin):
    """Plugin for calculating statistical summaries"""

    config_model = StatisticalSummaryConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            validated_config = self.config_model(**config)
            # Additional validation if needed
            valid_stats = {"min", "max", "mean", "median", "std"}
            invalid_stats = set(validated_config.params.get("stats", [])) - valid_stats
            if invalid_stats:
                raise ValueError(
                    f"Invalid statistics: {invalid_stats}. Valid options are: {valid_stats}"
                )
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Validate config first
            validated_config = self.config_model(**config)

            # Initialize params from validated config
            params = validated_config.params

            # Set default parameters if not provided
            stats = params.get("stats", ["min", "mean", "max"])
            units = params.get("units", "")
            max_value = params.get("max_value", 100)

            # Get source data if different from occurrences
            if params["source"] != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {params["source"]}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Get field data
            if params["field"] is not None:
                field_data = data[params["field"]]
            else:
                field_data = data

            if field_data.empty:
                return {
                    "min": None,
                    "mean": None,
                    "max": None,
                    "units": units,
                    "max_value": max_value,
                }

            # Calculate statistics
            result = {}
            if "min" in stats:
                result["min"] = (
                    round(float(field_data.min()), 2)
                    if not pd.isna(field_data.min())
                    else None
                )
            if "mean" in stats:
                result["mean"] = (
                    round(float(field_data.mean()), 2)
                    if not pd.isna(field_data.mean())
                    else None
                )
            if "max" in stats:
                result["max"] = (
                    round(float(field_data.max()), 2)
                    if not pd.isna(field_data.max())
                    else None
                )

            # Ajouter les unités de la configuration
            result["units"] = units

            if not field_data.empty and not pd.isna(field_data.max()):
                data_max = round(float(field_data.max()), 2)
                result["max_value"] = data_max if data_max > max_value else max_value
            else:
                result["max_value"] = max_value

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
