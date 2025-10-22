"""
Plugin for extracting categorical values from shape statistics.
Extracts values for ordered categories from a single field.
"""

from typing import Dict, Any, List, Literal
from pydantic import Field, ConfigDict, ValidationError
import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry
from niamoto.common.exceptions import DataTransformError


class CategoriesExtractorParams(BasePluginParams):
    """Specific parameters for the Categories Extractor plugin."""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Extract values for ordered categories from shape statistics",
            "examples": [
                {
                    "class_object": "land_use",
                    "categories_order": [
                        "NUM",
                        "UM",
                        "Sec",
                        "Humide",
                        "Très Humide",
                        "Réserve",
                    ],
                }
            ],
        }
    )

    class_object: str = Field(
        ...,
        description="Field name to match in class_object column",
        json_schema_extra={"ui:widget": "text"},
    )

    categories_order: List[str] = Field(
        ...,
        min_length=1,
        description="List of categories in desired order",
        json_schema_extra={"ui:widget": "tags"},
    )


class ClassObjectCategoriesConfig(PluginConfig):
    """Configuration for categories extractor plugin"""

    plugin: Literal["class_object_categories_extractor"] = (
        "class_object_categories_extractor"
    )
    source: str = Field(
        default="shape_stats",
        description="Transform source name (from transform.yml sources)",
        json_schema_extra={
            "ui:widget": "transform-source-select",
            # Will dynamically load sources from current group_by context
        },
    )
    params: CategoriesExtractorParams


@register("class_object_categories_extractor", PluginType.TRANSFORMER)
class ClassObjectCategoriesExtractor(TransformerPlugin):
    """Plugin for extracting ordered categorical values"""

    config_model = ClassObjectCategoriesConfig

    def __init__(self, db, registry=None):
        """Initialize with database and optional EntityRegistry.

        Args:
            db: Database instance
            registry: EntityRegistry instance (created if not provided)
        """
        super().__init__(db)
        self.registry = registry or EntityRegistry(db)

    def _resolve_table_name(self, logical_name: str) -> str:
        """Resolve logical entity name to physical table name via EntityRegistry.

        Args:
            logical_name: Entity name from config (e.g., "shape_stats", "occurrences")

        Returns:
            Physical table name (e.g., "entity_shape_stats", "entity_occurrences")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            return logical_name

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
        """Return ordered category/value pairs for a given class object.

        Parameters
        ----------
        data:
            Long-format DataFrame with ``class_object``, ``class_name`` and
            ``class_value`` columns.
        config:
            Raw configuration describing the target ``class_object`` and the desired
            category ordering.

        Returns
        -------
        dict[str, list]
            Lists of category labels and their associated values.
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
