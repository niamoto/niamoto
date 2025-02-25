"""Plugin for mapping class object values to a nested category structure."""

from typing import Dict, Any

import pandas as pd
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.exceptions import DataTransformError


class CategoryMapping(BaseModel):
    """Configuration for a category mapping"""

    class_object: str  # Field name to match in class_object
    mapping: Dict[str, str]  # Mapping of subcategories to their class_names


class ClassObjectCategoriesMapperConfig(PluginConfig):
    """Configuration for categories mapper plugin"""

    plugin: str = "class_object_categories_mapper"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "shape_stats",
            "categories": {
                "forest": {
                    "class_object": "holdridge_forest",
                    "mapping": {
                        "sec": "Sec",
                        "humide": "Humide",
                        "tres_humide": "Très Humide",
                    },
                },
                "non_forest": {
                    "class_object": "holdridge_forest_out",
                    "mapping": {
                        "sec": "Sec",
                        "humide": "Humide",
                        "tres_humide": "Très Humide",
                    },
                },
            },
        }
    )


@register("class_object_categories_mapper", PluginType.TRANSFORMER)
class ClassObjectCategoriesMapper(TransformerPlugin):
    """Plugin for mapping class object values to a nested category structure"""

    config_model = ClassObjectCategoriesMapperConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        # Validate categories configuration
        categories = validated_config.params.get("categories", {})
        if not categories:
            raise DataTransformError(
                "At least one category must be specified",
                details={"config": config},
            )

        return validated_config

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, Dict[str, float]]:
        """
        Transform shape statistics data into nested category structure.

        Args:
            data: DataFrame containing shape statistics in long format with columns:
                - class_object: The type of data (e.g. holdridge_forest)
                - class_name: The class name (e.g. "Sec", "Humide")
                - class_value: The value for this class
            config: Configuration dictionary with:
                - params.categories: Mapping of categories to their class objects and value mappings

        Returns:
            Dictionary with nested category structure

        Example output:
            {
                "forest": {
                    "sec": 0.1,
                    "humide": 0.2,
                    "tres_humide": 0.7
                },
                "non_forest": {
                    "sec": 0.3,
                    "humide": 0.4,
                    "tres_humide": 0.3
                }
            }
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Check required columns exist
            required_columns = ["class_object", "class_name", "class_value"]
            missing_columns = [
                col for col in required_columns if col not in data.columns
            ]
            if missing_columns:
                raise DataTransformError(
                    f"Required columns missing from data: {missing_columns}",
                    details={
                        "missing_columns": missing_columns,
                        "available_columns": list(data.columns),
                    },
                )

            result = {}

            # Process each category
            for category, category_config in params["categories"].items():
                # Get data for this class object
                class_object = category_config["class_object"]
                category_data = data[data["class_object"] == class_object]

                if len(category_data) == 0:
                    raise DataTransformError(
                        f"No data found for class_object {class_object}",
                        details={
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist(),
                        },
                    )

                # Process each subcategory mapping
                category_values = {}
                for subcategory_name, class_name in category_config["mapping"].items():
                    try:
                        value = float(
                            category_data[category_data["class_name"] == class_name][
                                "class_value"
                            ].iloc[0]
                        )
                        category_values[subcategory_name] = value
                    except (IndexError, KeyError) as e:
                        raise DataTransformError(
                            f"Failed to find value for {subcategory_name} in {category}",
                            details={
                                "class_name": class_name,
                                "available_class_names": category_data["class_name"]
                                .unique()
                                .tolist(),
                                "error": str(e),
                            },
                        )

                result[category] = category_values

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to map categories",
                details={"error": str(e), "config": config},
            )
