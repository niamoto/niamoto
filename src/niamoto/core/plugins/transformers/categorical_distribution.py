"""
Plugin for creating categorical distributions.
"""

from typing import Dict, Any, Optional
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)


class CategoricalDistributionConfig(PluginConfig):
    """Configuration for categorical distribution plugin"""

    plugin: str = "categorical_distribution"
    source: str
    field: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params configuration."""
        if not isinstance(v, dict):
            raise ValueError("params must be a dictionary")

        if "categories" in v and not isinstance(v["categories"], list):
            raise ValueError("categories must be a list")

        if "labels" in v:
            if not isinstance(v["labels"], list):
                raise ValueError("labels must be a list")
            if "categories" in v and len(v["labels"]) != len(v["categories"]):
                raise ValueError(
                    "number of labels must be equal to number of categories"
                )

        return v


@register("categorical_distribution", PluginType.TRANSFORMER)
class CategoricalDistribution(TransformerPlugin):
    """Plugin for creating categorical distributions"""

    config_model = CategoricalDistributionConfig

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            return self.config_model(**config).dict()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)

            # Get source data if different from occurrences
            if validated_config["source"] != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {validated_config["source"]}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Get field data
            if validated_config["field"] is not None:
                field_data = data[validated_config["field"]]
            else:
                field_data = data

            # Remove any None values
            field_data = field_data.dropna()

            if field_data.empty:
                return {
                    "categories": validated_config["params"].get("categories", []),
                    "counts": [0]
                    * len(validated_config["params"].get("categories", [])),
                    "labels": validated_config["params"].get("labels", []),
                }

            # If categories not provided, get unique values from data
            categories = validated_config["params"].get(
                "categories", sorted(field_data.unique())
            )

            # Calculate counts for each category
            value_counts = field_data.value_counts()
            counts = [int(value_counts.get(cat, 0)) for cat in categories]

            return {
                "categories": categories,
                "counts": counts,
                "labels": validated_config["params"].get("labels", categories),
            }

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
