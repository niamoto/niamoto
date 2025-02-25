"""
Plugin for chaining multiple transformations.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import pandas as pd

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.common.exceptions import DataTransformError


class TransformStepConfig(BaseModel):
    """Configuration for a single step in a transform chain"""

    plugin: str = Field(..., description="Transformer plugin to use")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the transformer"
    )
    output_key: str = Field(..., description="Key under which to store the output")


class TransformChainConfig(PluginConfig):
    """Configuration for transform chain plugin"""

    plugin: str = "transform_chain"
    steps: List[TransformStepConfig] = Field(
        ..., description="Steps in the transform chain"
    )


@register("transform_chain", PluginType.TRANSFORMER)
class TransformChain(TransformerPlugin):
    """Plugin for chaining multiple transformations"""

    config_model = TransformChainConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        try:
            validated_config = self.config_model(**config)
            # Validate each step
            for step in validated_config.steps:
                # Check if the referenced plugin exists
                if not PluginRegistry.has_plugin(step.plugin, PluginType.TRANSFORMER):
                    raise DataTransformError(
                        f"Plugin {step.plugin} not found",
                        details={
                            "available_plugins": PluginRegistry.list_plugins()[
                                PluginType.TRANSFORMER
                            ]
                        },
                    )
        except Exception as e:
            raise DataTransformError(f"Invalid transform chain configuration: {str(e)}")

        return validated_config

    def _resolve_references(
        self, params: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve references to previous transformation outputs.

        References are strings starting with '@', like '@step1.field'.
        """
        resolved_params = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("@"):
                # Parse reference
                ref_parts = value[1:].split(".")
                if len(ref_parts) != 2:
                    raise DataTransformError(
                        f"Invalid reference format: {value}. Expected format: @step.field",
                        details={"available_context": list(context.keys())},
                    )

                step_key, field_key = ref_parts

                # Check if referenced step exists
                if step_key not in context:
                    raise DataTransformError(
                        f"Referenced step '{step_key}' not found in context",
                        details={"available_steps": list(context.keys())},
                    )

                # Check if referenced field exists
                step_result = context[step_key]
                if not isinstance(step_result, dict) or field_key not in step_result:
                    raise DataTransformError(
                        f"Field '{field_key}' not found in step '{step_key}'",
                        details={
                            "available_fields": list(step_result.keys())
                            if isinstance(step_result, dict)
                            else "not a dict"
                        },
                    )

                resolved_params[key] = step_result[field_key]
            elif isinstance(value, dict):
                # Recursively resolve nested dictionaries
                resolved_params[key] = self._resolve_references(value, context)
            elif isinstance(value, list):
                # Recursively resolve lists
                resolved_params[key] = [
                    self._resolve_references(item, context)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                resolved_params[key] = value

        return resolved_params

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a chain of transformations.

        Args:
            data: Input DataFrame
            config: Configuration dictionary with:
                - steps: List of transformation steps

        Returns:
            Dictionary with combined results from all steps

        Raises:
            DataTransformError: If any step fails
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)

            # Initialize result and context
            result = {}
            context = {}
            current_data = data.copy()

            # Execute each step
            for step_config in validated_config.steps:
                # Get plugin class
                plugin_class = PluginRegistry.get_plugin(
                    step_config.plugin, PluginType.TRANSFORMER
                )
                plugin_instance = plugin_class(self.db)

                # Resolve references in parameters
                resolved_params = self._resolve_references(step_config.params, context)

                # Prepare step configuration
                step_full_config = {
                    "plugin": step_config.plugin,
                    "params": resolved_params,
                    # Copy group_id if present
                    "group_id": config.get("group_id"),
                }

                # Execute transformation
                step_result = plugin_instance.transform(current_data, step_full_config)

                # Store result in context and final result
                context[step_config.output_key] = step_result
                result[step_config.output_key] = step_result

                # Update current data if result contains a DataFrame
                for value in step_result.values():
                    if isinstance(value, pd.DataFrame):
                        current_data = value
                        break

            return result

        except Exception as e:
            raise DataTransformError(
                "Failed to execute transform chain",
                details={"error": str(e), "config": config},
            )
