"""
Plugin for extracting a series of values from a specific class_object.
Handles extraction of values along a size/class axis, with optional sorting and numeric conversion.
"""

from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
import numpy as np
import logging

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry
from niamoto.common.exceptions import DataTransformError

logger = logging.getLogger(__name__)


class FieldConfig(BaseModel):
    """Configuration for input/output field mapping with options"""

    input: str = ""
    output: str
    numeric: bool = True
    sort: bool = True


class ClassObjectSeriesParams(BasePluginParams):
    """Parameters for series extractor plugin"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Extract a series of values from a specific class_object",
            "examples": [
                {
                    "source": "raw_shape_stats",
                    "class_object": "forest_fragmentation",
                    "size_field": {
                        "input": "class_name",
                        "output": "sizes",
                        "numeric": True,
                        "sort": True,
                    },
                    "value_field": {
                        "input": "class_value",
                        "output": "values",
                        "numeric": True,
                    },
                }
            ],
        }
    )

    source: str = Field(
        default="raw_shape_stats",
        description="Transform source name (from transform.yml sources)",
        json_schema_extra={
            "ui:widget": "transform-source-select",
            # Will dynamically load sources from current group_by context
        },
    )

    class_object: str = Field(
        default="",
        description="The class_object to extract from",
        json_schema_extra={"ui:widget": "text"},
    )

    size_field: FieldConfig = Field(
        default=FieldConfig(
            input="class_name", output="sizes", numeric=True, sort=True
        ),
        description="Configuration for size/class axis",
        json_schema_extra={"ui:widget": "json"},
    )

    value_field: FieldConfig = Field(
        default=FieldConfig(input="class_value", output="values", numeric=True),
        description="Configuration for value axis",
        json_schema_extra={"ui:widget": "json"},
    )


class ClassObjectSeriesConfig(PluginConfig):
    """Configuration for series extractor plugin"""

    plugin: Literal["class_object_series_extractor"] = "class_object_series_extractor"
    params: ClassObjectSeriesParams


@register("class_object_series_extractor", PluginType.TRANSFORMER)
class ClassObjectSeriesExtractor(TransformerPlugin):
    """Plugin for extracting series from class_object data"""

    config_model = ClassObjectSeriesConfig

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
            logical_name: Entity name from config (e.g., "raw_shape_stats", "occurrences")

        Returns:
            Physical table name (e.g., "entity_raw_shape_stats", "entity_occurrences")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> ClassObjectSeriesConfig:
        """Validate plugin configuration and return typed config."""
        try:
            validated_config = self.config_model(**config)

            # Check for specific validation that tests expect
            if not validated_config.params.class_object:
                raise DataTransformError(
                    "class_object must be specified", details={"config": config}
                )

            if not validated_config.params.size_field.input:
                raise DataTransformError(
                    "size_field.input must be specified", details={"config": config}
                )

            if not validated_config.params.value_field.input:
                raise DataTransformError(
                    "value_field.input must be specified", details={"config": config}
                )

            return validated_config
        except DataTransformError:
            raise
        except Exception as e:
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, List]:
        """Produce a one-dimensional series from class-object statistics.

        The configuration must provide a ``class_object`` to extract along with the
        field definitions that describe how to map input columns to output lists.

        Returns
        -------
        dict
            A dictionary containing the ordered axis values and their corresponding
            measurements.
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get class_object configuration
            class_object = params.class_object

            # Filter data for specified class_object
            filtered_data = data[data["class_object"] == class_object].copy()

            if filtered_data.empty:
                # Return empty result instead of raising an error
                logger.debug(
                    f"No data found for class_object {class_object}, returning empty result"
                )
                size_config = params.size_field
                value_config = params.value_field
                return {
                    size_config.output: [],
                    value_config.output: [],
                }

            # Get size field configuration
            size_config = params.size_field

            # Validate size field exists
            if size_config.input not in filtered_data.columns:
                raise DataTransformError(
                    f"Size field {size_config.input} not found in data",
                    details={"available_columns": list(filtered_data.columns)},
                )

            # Process size values
            size_values = filtered_data[size_config.input].fillna(-1)

            # Convert to numeric if requested
            if size_config.numeric:
                try:
                    size_values = pd.to_numeric(size_values)
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert size values to numeric",
                        details={"error": str(e)},
                    )

            # Sort if requested
            if size_config.sort:
                sorted_indices = np.argsort(size_values.values)
                size_values = size_values.iloc[sorted_indices]
                filtered_data = filtered_data.iloc[sorted_indices]

            # Get value field configuration
            value_config = params.value_field

            # Validate value field exists
            if value_config.input not in filtered_data.columns:
                raise DataTransformError(
                    f"Value field {value_config.input} not found in data",
                    details={"available_columns": list(filtered_data.columns)},
                )

            # Process value values
            value_values = filtered_data[value_config.input]

            # Convert to numeric if requested
            if value_config.numeric:
                try:
                    value_values = pd.to_numeric(value_values)
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert values to numeric", details={"error": str(e)}
                    )

            # Construct result
            result = {
                size_config.output: size_values.tolist(),
                value_config.output: value_values.tolist(),
            }

            # Remove -1 values from result
            result[size_config.output] = [
                x for x in result[size_config.output] if x != -1
            ]
            result[value_config.output] = [
                x for x in result[value_config.output] if x != -1
            ]

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to extract series", details={"error": str(e), "config": config}
            )
