"""Plugin for mapping class object values to a nested category structure."""

from typing import Dict, Any

import pandas as pd
from pydantic import BaseModel, ValidationError
from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, register, PluginType
from niamoto.common.exceptions import DataTransformError


# Specific model for the mapping within each category
class CategoryMappingDetail(BaseModel):
    class_object: str
    mapping: Dict[str, str]


# Specific model for the 'params' structure
class CategoriesMapperParams(BaseModel):
    categories: Dict[str, CategoryMappingDetail]
    source: str | None = None


# Updated Config model
class ClassObjectCategoriesMapperConfig(PluginConfig):
    """Configuration for categories mapper plugin"""

    plugin: str = "class_object_categories_mapper"
    params: CategoriesMapperParams


@register("class_object_categories_mapper", PluginType.TRANSFORMER)
class ClassObjectCategoriesMapper(TransformerPlugin):
    """Plugin for mapping class object data into categories"""

    config_model = ClassObjectCategoriesMapperConfig

    def validate_config(
        self, config: Dict[str, Any]
    ) -> ClassObjectCategoriesMapperConfig:
        """Validate plugin configuration using Pydantic model."""
        try:
            # Pydantic validation handles structure and types
            validated_config = self.config_model(**config)
            # Removed check for empty categories dict, Pydantic allows it.
            return validated_config
        except ValidationError as e:
            plugin_name = config.get("plugin", "unknown_plugin")
            raise DataTransformError(
                f"Invalid configuration for {plugin_name}: {e}",
                details={"pydantic_error": e.errors(), "config": config},
            )
        except Exception as e:
            plugin_name = config.get("plugin", "unknown_plugin")
            raise DataTransformError(
                f"Unexpected error validating configuration for {plugin_name}",
                details={"error": str(e), "config": config},
            )

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
                - params.source: Source identifier (e.g., 'shape_stats')
                - params.categories: Mapping of categories to their class objects and value mappings

        Returns:
            Dictionary with nested category structure
        """
        try:
            # Use validated config directly if passed or re-validate
            if isinstance(config, self.config_model):
                validated_config = config
            else:
                validated_config = self.validate_config(config)

            params = validated_config.params
            source = params.source

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

            # Process each category using attribute access
            for category, category_config in params.categories.items():
                # Get data for this class object
                class_object = category_config.class_object
                category_data = data[data["class_object"] == class_object]

                if len(category_data) == 0:
                    raise DataTransformError(
                        f"No data found for class_object {class_object}",
                        details={
                            "category": category,
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist(),
                        },
                    )

                # Process each subcategory mapping
                category_values = {}
                for subcategory_name, class_name in category_config.mapping.items():
                    try:
                        # Find the row matching the class name for this category
                        row = category_data[category_data["class_name"] == class_name]
                        if len(row) == 0:
                            # Class name specified in mapping not found in data for this class_object
                            # Assign 0.0 as per expected behavior for missing source classes
                            value = 0.0
                        else:
                            # Convert value, handle potential errors
                            try:
                                value = float(row["class_value"].iloc[0])
                            except (ValueError, TypeError) as conv_err:
                                raise DataTransformError(
                                    f"Failed to convert value for '{subcategory_name}' (class_name: '{class_name}') in category '{category}'",
                                    details={
                                        "category": category,
                                        "subcategory": subcategory_name,
                                        "class_object": class_object,
                                        "class_name": class_name,
                                        "original_value": row["class_value"].iloc[0],
                                        "error": str(conv_err),
                                    },
                                )

                        category_values[subcategory_name] = value

                    except Exception as e:
                        # Catch potential issues like missing columns during processing, though Pydantic should catch most config errors
                        # Re-raise as DataTransformError for consistent error handling
                        # Avoid catching the DataTransformError raised internally for conversion issues
                        if isinstance(e, DataTransformError):
                            raise e

                        # Log unexpected processing errors for debugging
                        # self.logger.error(f"Error processing subcategory {subcategory_name}: {e}", exc_info=True)
                        raise DataTransformError(
                            f"Failed processing subcategory '{subcategory_name}' (class_name: '{class_name}') in category '{category}'",
                            details={
                                "category": category,
                                "subcategory": subcategory_name,
                                "class_object": class_object,
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
            plugin_name = config.get("plugin", "unknown_plugin")
            # Include config in details for better debugging
            error_details = {"error": str(e), "config": config}
            # Attempt to add relevant data state if possible
            if "category" in locals():
                error_details["current_category"] = category
            if "subcategory_name" in locals():
                error_details["current_subcategory"] = subcategory_name

            raise DataTransformError(
                f"Failed to map categories for plugin {plugin_name}",
                details=error_details,
            )
