"""
Plugin for counting binary values.
"""

from typing import Dict, Any, Optional
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
    source: str
    field: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        # Skip validation if no params provided
        if not v:
            return v

        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        required_fields = ["true_label", "false_label"]
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

            # Move true_label and false_label from root to params if they exist
            if "true_label" in config:
                config["params"]["true_label"] = config.pop("true_label")
            if "false_label" in config:
                config["params"]["false_label"] = config.pop("false_label")

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
            if validated_config.source != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {validated_config.source}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Get field data
            if validated_config.field is not None:
                field_data = data[validated_config.field]
            else:
                field_data = data

            if field_data.empty:
                return {
                    validated_config.params["true_label"]: 0,
                    validated_config.params["false_label"]: 0,
                }

            # Count values
            true_count = len(field_data[field_data])
            false_count = len(field_data[~field_data])

            # Debug logs
            result = {
                validated_config.params["true_label"]: true_count,
                validated_config.params["false_label"]: false_count,
            }

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
