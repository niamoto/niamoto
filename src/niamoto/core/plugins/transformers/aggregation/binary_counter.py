"""
Plugin for counting binary values.
"""

from typing import Dict, Any, Literal
from pydantic import Field, ConfigDict, model_validator

import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry


class BinaryCounterParams(BasePluginParams):
    """Typed parameters for binary counter plugin.

    This plugin counts binary (0/1) values in a field and returns
    the count for each value with customizable labels.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Count binary values with customizable labels",
            "examples": [
                {
                    "source": "occurrences",
                    "field": "in_um",
                    "true_label": "um",
                    "false_label": "num",
                    "include_percentages": True,
                }
            ],
        }
    )

    source: str = Field(
        default="occurrences",
        description="Data source table name",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["occurrences", "taxonomy", "plots"],
        },
    )

    field: str = Field(
        ...,
        description="Name of the binary field to count (values should be 0 or 1)",
        json_schema_extra={"ui:widget": "field-select", "ui:depends": "source"},
    )

    true_label: str = Field(
        default="oui",
        description="Label for true/1 values in output",
        json_schema_extra={"ui:widget": "text"},
    )

    false_label: str = Field(
        default="non",
        description="Label for false/0 values in output",
        json_schema_extra={"ui:widget": "text"},
    )

    include_percentages: bool = Field(
        default=False,
        description="Whether to include percentage calculations in the output",
        json_schema_extra={"ui:widget": "checkbox"},
    )

    @model_validator(mode="after")
    def validate_labels_different(self):
        """Validate that labels are different and not empty."""
        if not self.true_label.strip() or not self.false_label.strip():
            raise ValueError("Labels cannot be empty")
        if self.true_label == self.false_label:
            raise ValueError("true_label and false_label must be different")
        return self


class BinaryCounterConfig(PluginConfig):
    """Configuration for binary counter plugin"""

    plugin: Literal["binary_counter"] = "binary_counter"
    params: BinaryCounterParams


@register("binary_counter", PluginType.TRANSFORMER)
class BinaryCounter(TransformerPlugin):
    """Plugin for counting binary values"""

    config_model = BinaryCounterConfig

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
            logical_name: Entity name from config (e.g., "occurrences", "plots")

        Returns:
            Physical table name (e.g., "entity_occurrences", "entity_plots")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> BinaryCounterConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get source data if different from occurrences
            if params.source != "occurrences":
                # Resolve logical entity name to physical table name
                table_name = self._resolve_table_name(params.source)
                sql_query = f"SELECT * FROM {table_name}"
                result = self.db.execute_select(sql_query)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            true_count = 0
            false_count = 0
            total_count = 0

            # Get field data only if data is not empty
            if not data.empty and params.field:
                field_data = data.get(params.field)
                if field_data is not None and not field_data.empty:
                    # Filter out any values that are not 0 or 1
                    valid_mask = (field_data == 0) | (field_data == 1)
                    field_data = field_data[valid_mask]

                    if not field_data.empty:
                        # Count values (1 = true, 0 = false)
                        true_count = len(field_data[field_data == 1])
                        false_count = len(field_data[field_data == 0])
                        total_count = true_count + false_count

            # Prepare result
            result = {
                params.true_label: true_count,
                params.false_label: false_count,
            }

            # Add percentages if requested
            if params.include_percentages:
                true_percent = (
                    round(true_count / total_count * 100, 2) if total_count > 0 else 0.0
                )
                false_percent = (
                    round(false_count / total_count * 100, 2)
                    if total_count > 0
                    else 0.0
                )
                result.update(
                    {
                        f"{params.true_label}_percent": true_percent,
                        f"{params.false_label}_percent": false_percent,
                    }
                )

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
