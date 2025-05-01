"""
Plugin for creating distributions based on specified bins.
"""

from typing import Dict, Any
from pydantic import field_validator, Field

import pandas as pd
import numpy as np

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
)


class BinnedDistributionConfig(PluginConfig):
    """Configuration for binned distribution plugin"""

    plugin: str = "binned_distribution"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": None,
            "bins": [],
            "labels": [],
            "include_percentages": False,
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "field", "bins"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(v["bins"], list):
            raise ValueError("bins must be a list")

        if len(v["bins"]) < 2:
            raise ValueError("bins must have at least 2 values")

        # Check that bins are valid numbers and ascending
        for i, value in enumerate(v["bins"]):
            if value is None:
                raise ValueError(f"bin value at index {i} cannot be None")
            if not isinstance(value, (int, float)):
                raise ValueError(f"bin value at index {i} must be a number")
            if i > 0 and value <= v["bins"][i - 1]:
                raise ValueError("bins must be in strictly ascending order")

        if "labels" in v and v["labels"]:
            if not isinstance(v["labels"], list):
                raise ValueError("labels must be a list")
            if len(v["labels"]) != len(v["bins"]) - 1:
                raise ValueError("number of labels must be equal to number of bins - 1")

        return v


@register("binned_distribution", PluginType.TRANSFORMER)
class BinnedDistribution(TransformerPlugin):
    """Plugin for creating binned distributions"""

    config_model = BinnedDistributionConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            validated_config = self.config_model(**config)
            # Additional validation if needed
            if not isinstance(validated_config.params["bins"], list):
                raise ValueError("bins parameter must be a list")
            if len(validated_config.params["bins"]) < 2:
                raise ValueError("bins parameter must contain at least 2 values")
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Set default parameters if not provided
            if "params" not in config:
                config["params"] = {}
            if "bins" not in config["params"]:
                config["params"]["bins"] = [0, 100, 200, 300, 400, 500]
            if "labels" not in config["params"]:
                config["params"]["labels"] = []

            # Ensure all bin values are numbers and integers
            config["params"]["bins"] = [
                int(float(x)) if x is not None else 0 for x in config["params"]["bins"]
            ]

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

            # Get field data
            if validated_config.params["field"] is not None:
                field_data = data[validated_config.params["field"]]
            else:
                field_data = data

            # Remove any None or NaN values
            field_data = pd.to_numeric(field_data, errors="coerce").dropna()

            if field_data.empty:
                return {
                    "bins": validated_config.params["bins"],
                    "counts": [0] * (len(validated_config.params["bins"]) - 1),
                }

            # Calculate bin counts
            counts, _ = np.histogram(field_data, bins=validated_config.params["bins"])

            result = {
                "bins": validated_config.params["bins"],
                "counts": [int(x) for x in counts],
            }

            # Add labels if they exist
            if (
                "labels" in validated_config.params
                and validated_config.params["labels"]
            ):
                result["labels"] = validated_config.params["labels"]

            # Calculate percentages if requested
            if validated_config.params.get("include_percentages", False):
                total = sum(counts)
                if total > 0:
                    percentages = [round((count / total) * 100, 2) for count in counts]
                else:
                    percentages = [0] * len(counts)
                result["percentages"] = percentages

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
