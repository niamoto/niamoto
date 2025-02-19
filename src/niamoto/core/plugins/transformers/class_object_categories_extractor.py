"""
Plugin for extracting categorical values from shape statistics.
Extracts values for ordered categories from a single field.
"""

from typing import Dict, Any, List
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
    """Configuration for categories extractor plugin"""

    plugin: str = "class_object_categories_extractor"
    source: str = "shape_stats"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "class_object": "land_use",
            "categories_order": [
                "NUM",
                "UM",
                "Sec",
                "Humide",
                "Très Humide",
                "Réserve",
                "PPE",
                "Concessions",
                "Forêt",
            ],
        }
    )


@register("class_object_categories_extractor", PluginType.TRANSFORMER)
class ClassObjectCategoriesExtractor(TransformerPlugin):
    """Plugin for extracting ordered categorical values"""

    config_model = ClassObjectCategoriesConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        params = validated_config.params

        # Validate class_object is specified
        if not params.get("class_object"):
            raise DataTransformError(
                "class_object must be specified", details={"config": config}
            )

        # Validate axis configuration
        axis_config = params.get("axis", {})
        if not isinstance(axis_config, dict):
            raise DataTransformError(
                "axis configuration must be a dictionary", details={"config": config}
            )

        if not axis_config.get("field"):
            raise DataTransformError(
                "axis.field must be specified", details={"config": config}
            )

        if not axis_config.get("output"):
            raise DataTransformError(
                "axis.output must be specified", details={"config": config}
            )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, List]:
        """
        Extract values for ordered categories from shape statistics data.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.class_object: Field name to extract categories from
                - params.categories_order: List of categories in desired order

        Returns:
            Dictionary with categories list and corresponding values

        Example output:
            {
                "categories": ["NUM", "UM", "Sec", "Humide", "Très Humide", "Réserve", "PPE", "Concessions", "Forêt"],
                "values": [720516.37, 220736.05, 245865.63, 564601.88, 130784.90, 14272.87, 94334.71, 121703.50, 321711.77]
            }
        """
        try:
            # Validate configuration
            validated_config = self.config_model(**config)
            params = validated_config.params

            # Get parameters
            field = params["class_object"]
            categories = params["categories_order"]

            # Validate field exists
            if field not in data.columns:
                raise DataTransformError(
                    f"Field {field} not found in data",
                    details={"available_columns": list(data.columns)},
                )

            # Initialize results with ordered categories
            results = {"categories": categories, "values": []}

            # Extract values for each category in order
            for category in categories:
                # Sum values where field equals category
                mask = data[field] == category
                value = float(data.loc[mask, field].count())
                results["values"].append(value)

            return results

        except Exception as e:
            raise DataTransformError(
                "Failed to extract categorical values",
                details={"error": str(e), "config": config},
            )
