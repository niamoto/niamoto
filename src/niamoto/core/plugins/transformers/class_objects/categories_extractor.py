"""
Plugin for extracting categorical values from shape statistics.
Extracts values for ordered categories from a single field.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, ValidationError
import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class CategoriesExtractorParams(BaseModel):
    """Specific parameters for the Categories Extractor plugin."""

    class_object: str
    categories_order: List[str]  # Enforce list of strings


class ClassObjectCategoriesConfig(PluginConfig):
    """Configuration for categories extractor plugin"""

    plugin: str = "class_object_categories_extractor"
    source: str = "shape_stats"
    # Use the specific params model instead of Dict[str, Any]
    params: CategoriesExtractorParams


@register("class_object_categories_extractor", PluginType.TRANSFORMER)
class ClassObjectCategoriesExtractor(TransformerPlugin):
    """Plugin for extracting ordered categorical values"""

    config_model = ClassObjectCategoriesConfig

    def validate_config(self, config: Dict[str, Any]) -> ClassObjectCategoriesConfig:
        """Validate plugin configuration using Pydantic model."""
        try:
            # Pydantic validation handles structure and types (including List[str])
            validated_config = self.config_model(**config)
            return validated_config
        except ValidationError as e:
            # Re-raise Pydantic errors as DataTransformError for consistency
            # Get plugin name from input config dict
            plugin_name = config.get("plugin", "unknown_plugin")
            raise DataTransformError(
                f"Invalid configuration for {plugin_name}: {e}",
                details={"pydantic_error": e.errors(), "config": config},
            )
        except Exception as e:  # Catch other potential errors during validation
            # Get plugin name from input config dict
            plugin_name = config.get("plugin", "unknown_plugin")
            raise DataTransformError(
                f"Unexpected error validating configuration for {plugin_name}",
                details={"error": str(e), "config": config},
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, List]:
        """
        Extract values for ordered categories from shape statistics data.

        Args:
            data: DataFrame containing shape statistics in long format with columns:
                - class_object: The type of data (e.g. land_use)
                - class_name: The class name (e.g. NUM, UM, etc.)
                - class_value: The value for this class
            config: Configuration dictionary with:
                - params.class_object: Field name to match in class_object
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
            # Use validated config directly if passed or re-validate
            if isinstance(config, self.config_model):
                validated_config = config
            else:
                validated_config = self.validate_config(config)

            params = validated_config.params
            class_object_name = params.class_object
            categories_order = params.categories_order

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

            # Filter data for this class_object
            field_data = data[data["class_object"] == class_object_name]

            if len(field_data) == 0:
                raise DataTransformError(
                    f"No data found for class_object {class_object_name}",
                    details={
                        "field": class_object_name,
                        "available_class_objects": data["class_object"]
                        .unique()
                        .tolist(),
                    },
                )

            # Initialize results with ordered categories
            results = {"categories": categories_order, "values": []}

            # Extract values for each category in order
            for category in categories_order:
                # Get value where class_name equals category
                category_data = field_data[field_data["class_name"] == category]
                if len(category_data) > 0:
                    value = float(category_data.iloc[0]["class_value"])
                else:
                    value = 0.0
                results["values"].append(value)

            return results

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to extract categorical values",
                details={"error": str(e), "config": config},
            )
