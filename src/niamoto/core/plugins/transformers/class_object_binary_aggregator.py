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
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "raw_shape_stats",
            "groups": [
                {
                    "label": "emprise",
                    "field": "cover_forest",
                    "classes": ["forest", "non_forest"],
                },
                {"label": "um", "field": "cover_forestum"},
                {"label": "num", "field": "cover_forestnum"},
            ],
        }
    )


@register("class_object_binary_aggregator", PluginType.TRANSFORMER)
class ClassObjectBinaryAggregator(TransformerPlugin):
    """Plugin for handling binary/ternary class distributions"""

    config_model = ClassObjectBinaryConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)
        params = validated_config.params

        # Validate that source is specified
        if "source" not in params:
            raise DataTransformError(
                "source must be specified",
                details={"config": config},
            )

        # Validate that at least one group is specified
        groups = params.get("groups", [])
        if not groups:
            raise DataTransformError(
                "At least one group must be specified",
                details={"config": config},
            )

        # Validate each group configuration
        for group in groups:
            if not isinstance(group, dict):
                raise DataTransformError(
                    "Group configuration must be a dictionary",
                    details={"config": group},
                )

            if "label" not in group:
                raise DataTransformError(
                    "Group must specify 'label'",
                    details={"config": group},
                )

            if "field" not in group:
                raise DataTransformError(
                    "Group must specify 'field'",
                    details={"config": group},
                )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform shape statistics data into binary/ternary distributions.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.source: Source of the data
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
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Initialize results
            results = {}

            # Process each group
            for group_config in params["groups"]:
                group = GroupConfig(**group_config)

                # Get field data
                if group.field not in data.columns:
                    raise DataTransformError(
                        f"Field {group.field} not found in data",
                        details={
                            "field": group.field,
                            "available_columns": list(data.columns),
                        },
                    )

                # Get values for the field
                values = data[group.field].values

                # Skip if no values
                if len(values) == 0:
                    continue

                # Calculate distribution
                total = np.sum(values)
                if total == 0:
                    distribution = {cls: 0.0 for cls in group.classes}
                else:
                    # For binary fields, first value is forest, second is non-forest
                    forest_value = values[0]
                    distribution = {
                        group.classes[0]: float(forest_value) / total,
                        group.classes[1]: 1.0 - float(forest_value) / total,
                    }

                results[group.label] = distribution

            return results

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to transform binary/ternary distributions",
                details={"error": str(e), "config": config},
            )
