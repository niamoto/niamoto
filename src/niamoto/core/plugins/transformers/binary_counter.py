"""
Plugin for counting binary values.
"""

from typing import Dict, Any
from pydantic import Field, field_validator

import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)


class BinaryCounterConfig(PluginConfig):
    """Configuration for binary counter plugin"""

    plugin: str = "binary_counter"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": None,
            "true_label": "oui",
            "false_label": "non",
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["source", "field", "true_label", "false_label"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(v["true_label"], str):
            raise ValueError("true_label must be a string")

        if not isinstance(v["false_label"], str):
            raise ValueError("false_label must be a string")

        return v


@register("binary_counter", PluginType.TRANSFORMER)
class BinaryCounter(TransformerPlugin):
    """Plugin for counting binary values"""

    config_model = BinaryCounterConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            validated_config = self.config_model(**config)
            # Additional validation if needed
            if (
                validated_config.params["true_label"]
                == validated_config.params["false_label"]
            ):
                raise ValueError("true_label and false_label must be different")
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Ensure params exists
            if "params" not in config:
                config["params"] = {}

            # Set default parameters if not provided
            default_params = {"true_label": "oui", "false_label": "non"}

            # Update defaults with provided params
            config["params"] = {**default_params, **config["params"]}

            # Validate configuration
            validated_config = self.config_model(**config)

            if (
                validated_config.params["true_label"]
                == validated_config.params["false_label"]
            ):
                raise ValueError("true_label and false_label must be different")

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

            if field_data.empty:
                return {
                    validated_config.params["true_label"]: 0,
                    validated_config.params["false_label"]: 0,
                }

            # Filter out any values that are not 0 or 1
            valid_mask = (field_data == 0) | (field_data == 1)
            field_data = field_data[valid_mask]

            if field_data.empty:
                return {
                    validated_config.params["true_label"]: 0,
                    validated_config.params["false_label"]: 0,
                }

            # Count values (1 = true, 0 = false)
            true_count = len(field_data[field_data == 1])
            false_count = len(field_data[field_data == 0])

            # Debug logs
            result = {
                validated_config.params["true_label"]: true_count,
                validated_config.params["false_label"]: false_count,
            }

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
