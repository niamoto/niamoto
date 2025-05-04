"""
Plugin for creating categorical distributions.
"""

from typing import Dict, Any
from pydantic import field_validator, Field

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


class CategoricalDistributionConfig(PluginConfig):
    """Configuration for categorical distribution plugin"""

    plugin: str = "categorical_distribution"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": None,
            "categories": [],
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

        required_fields = ["source", "field"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

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
            return self.config_model(**config).model_dump()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)

            # Get source data if different from occurrences
            if validated_config["params"]["source"] != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {validated_config["params"]["source"]}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Get field data
            if validated_config["params"]["field"] is not None:
                field_data = data[validated_config["params"]["field"]]
            else:
                field_data = data

            # Remove any None values
            field_data = field_data.dropna()

            categories = validated_config["params"].get("categories", [])
            labels = validated_config["params"].get("labels", [])
            include_percentages = validated_config["params"].get(
                "include_percentages", False
            )

            if field_data.empty:
                if not categories and labels:
                    categories = []
                elif not categories:
                    categories = []

                if not labels:
                    labels = categories

                result = {
                    "categories": categories,
                    "counts": [0] * len(categories),
                    "labels": labels,
                }
                if include_percentages:
                    result["percentages"] = [0.0] * len(categories)
                return result

            if not categories:
                categories = sorted(field_data.unique())

            # Calculate counts for each category
            value_counts = field_data.value_counts()
            counts = [int(value_counts.get(cat, 0)) for cat in categories]

            result = {
                "categories": categories,
                "counts": counts,
                "labels": validated_config["params"].get("labels", categories),
            }

            if include_percentages:
                total = sum(counts)
                if total > 0:
                    percentages = [round((count / total) * 100, 2) for count in counts]
                else:
                    percentages = [0.0] * len(counts)
                result["percentages"] = percentages

            return result

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
