"""
Plugin for aggregating categorical distributions from shape statistics.
Handles multiple fields (e.g. forest/non-forest) with predefined categories.
Can optionally group by a field and normalize distributions.
"""

from typing import Dict, Any
from pydantic import Field
import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.exceptions import DataTransformError


class ClassObjectCategoriesConfig(PluginConfig):
    """Configuration for categorical distributions aggregator plugin"""

    plugin: str = "class_object_categories_aggregator"
    source: str = "shape_stats"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "fields": {
                "forest": "holdridge_forest",
                "non_forest": "holdridge_forest_out",
            },
            "categories": ["Sec", "Humide", "Très Humide"],
            "normalize": True,
            "group_by": "altitude",  # optionnel
        }
    )


@register("class_object_categories_aggregator", PluginType.TRANSFORMER)
class ClassObjectCategoriesAggregator(TransformerPlugin):
    """Plugin for aggregating categorical distributions"""

    config_model = ClassObjectCategoriesConfig

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
            if not isinstance(categories, dict):
                raise DataTransformError(
                    f"Distribution {dist_name} categories must be a dictionary",
                    details={"config": dist_config},
                )

            if not categories:
                raise DataTransformError(
                    f"Distribution {dist_name} categories cannot be empty",
                    details={"config": dist_config},
                )

            # Validate each category configuration
            for cat_name, cat_config in categories.items():
                if not isinstance(cat_config, dict):
                    raise DataTransformError(
                        f"Category {cat_name} in distribution {dist_name} must be a dictionary",
                        details={"config": cat_config},
                    )

                if "values" not in cat_config:
                    raise DataTransformError(
                        f"Category {cat_name} in distribution {dist_name} must specify 'values'",
                        details={"config": cat_config},
                    )

                values = cat_config["values"]
                if not isinstance(values, list) or len(values) < 1:
                    raise DataTransformError(
                        f"Category {cat_name} values in distribution {dist_name} must be a non-empty list",
                        details={"config": cat_config},
                    )

        return validated_config

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, Dict[str, float]]:
        """
        Transform shape statistics data into categorical distributions.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.fields: Dict mapping output keys to data columns
                - params.categories: List of categories in order
                - params.normalize: Whether to normalize distributions
                - params.group_by: Optional field to group by

        Returns:
            Dictionary with distributions for each field

        Example output:
            {
                "forest": {
                    "sec": 0.022,
                    "humide": 0.223,
                    "tres_humide": 0.096
                },
                "non_forest": {
                    "sec": 0.239,
                    "humide": 0.376,
                    "tres_humide": 0.043
                }
            }
        """
        try:
            # Validate configuration
            validated_config = self.config_model(**config)
            params = validated_config.params

            # Get parameters
            fields = params["fields"]
            categories = params["categories"]
            normalize = params.get("normalize", True)
            group_by = params.get("group_by")

            # Validate fields exist in data
            missing_fields = [f for f in fields.values() if f not in data.columns]
            if missing_fields:
                raise DataTransformError(
                    "Missing required fields in data",
                    details={"missing_fields": missing_fields},
                )

            # Initialize results
            results = {key: {cat: 0.0 for cat in categories} for key in fields.keys()}

            # Process each field
            for key, field in fields.items():
                # Get field data
                field_data = data[field]

                # Group by if specified
                if group_by:
                    if group_by not in data.columns:
                        raise DataTransformError(
                            f"Group by field {group_by} not found in data",
                            details={"available_columns": list(data.columns)},
                        )

                    # Calculate distribution for each group
                    grouped = field_data.groupby(data[group_by])
                    for cat in categories:
                        cat_sum = grouped[field_data == cat].sum()
                        results[key][cat] = float(cat_sum.sum())
                else:
                    # Calculate simple distribution
                    for cat in categories:
                        results[key][cat] = float((field_data == cat).sum())

                # Normalize if requested
                if normalize:
                    total = sum(results[key].values())
                    if total > 0:
                        results[key] = {
                            cat: value / total for cat, value in results[key].items()
                        }

            return results

        except Exception as e:
            raise DataTransformError(
                "Failed to transform categorical distributions",
                details={"error": str(e), "config": config},
            )
