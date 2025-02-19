"""
Plugin for handling binary/ternary class distributions from class_value format.
Specifically handles data where distributions are represented as binary choices
(e.g. forest/non-forest) or ternary choices.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.exceptions import DataTransformError


class GroupConfig(BaseModel):
    """Configuration for a binary/ternary group"""

    label: str
    field: str
    classes: Optional[List[str]] = ["forest", "non_forest"]


class ClassObjectBinaryConfig(PluginConfig):
    """Configuration for binary class aggregator plugin"""

    plugin: str = "class_object_binary_aggregator"
    source: str = "raw_shape_stats"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "groups": [
                {
                    "label": "emprise",
                    "field": "cover_forest",
                    "classes": ["forest", "non_forest"],
                },
                {"label": "um", "field": "cover_forestum"},
                {"label": "num", "field": "cover_forestnum"},
            ]
        }
    )


@register("class_object_binary_aggregator", PluginType.TRANSFORMER)
class ClassObjectBinaryAggregator(TransformerPlugin):
    """Plugin for handling binary/ternary class distributions"""

    config_model = ClassObjectBinaryConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        # Validate that at least one distribution is specified
        distributions = validated_config.params.get("distributions", {})
        if not distributions:
            raise DataTransformError(
                "At least one distribution must be specified",
                details={"config": config},
            )

        # Validate each distribution configuration
        for dist_name, dist_config in distributions.items():
            if not isinstance(dist_config, dict):
                raise DataTransformError(
                    f"Distribution {dist_name} configuration must be a dictionary",
                    details={"config": dist_config},
                )

            if "class_object" not in dist_config:
                raise DataTransformError(
                    f"Distribution {dist_name} must specify 'class_object'",
                    details={"config": dist_config},
                )

            if "categories" not in dist_config:
                raise DataTransformError(
                    f"Distribution {dist_name} must specify 'categories'",
                    details={"config": dist_config},
                )

            categories = dist_config["categories"]
            if not isinstance(categories, list) or len(categories) < 1:
                raise DataTransformError(
                    f"Distribution {dist_name} categories must be a non-empty list",
                    details={"config": dist_config},
                )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform shape statistics data into binary/ternary distributions.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.groups: List of group configurations with:
                    - label: Name of the distribution
                    - field: Field name in data
                    - classes: Optional list of class names (default: ["forest", "non_forest"])

        Returns:
            Dictionary with distributions for each group

        Example output:
            {
                "emprise": {
                    "forest": 0.7,
                    "non_forest": 0.3
                },
                "um": {
                    "forest": 0.6,
                    "non_forest": 0.4
                }
            }
        """
        try:
            # Validate configuration
            validated_config = self.config_model(**config)

            # Initialize results
            results = {}

            # Process each group
            for group_config in validated_config.params["groups"]:
                group = GroupConfig(**group_config)

                # Get field data
                if group.field not in data.columns:
                    raise DataTransformError(
                        f"Field {group.field} not found in data",
                        details={"available_columns": list(data.columns)},
                    )

                values = data[group.field].values
                if len(values) == 0:
                    continue

                # Calculate distribution
                total = np.sum(values)
                if total == 0:
                    distribution = {cls: 0.0 for cls in group.classes}
                else:
                    distribution = {
                        group.classes[0]: float(values[0]) / total,
                        group.classes[1]: 1.0 - float(values[0]) / total,
                    }

                results[group.label] = distribution

            return results

        except Exception as e:
            raise DataTransformError(
                "Failed to transform binary/ternary distributions",
                details={"error": str(e), "config": config},
            )
