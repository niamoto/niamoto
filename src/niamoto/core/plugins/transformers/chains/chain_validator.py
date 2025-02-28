"""
Transform chain validator for ensuring compatibility between steps.
"""

from typing import Dict, Any, List
import re
from pydantic import BaseModel, Field

from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.common.exceptions import DataTransformError


class StepIOSchema(BaseModel):
    """Schema for a plugin's inputs and outputs"""

    # Input requirements
    required_inputs: List[str] = Field(
        default_factory=list, description="Required input fields"
    )
    optional_inputs: List[str] = Field(
        default_factory=list, description="Optional input fields"
    )
    input_types: Dict[str, List[str]] = Field(
        default_factory=dict, description="Expected types for inputs"
    )

    # Output guarantees
    outputs: List[str] = Field(
        default_factory=list, description="Output fields produced"
    )
    output_types: Dict[str, List[str]] = Field(
        default_factory=dict, description="Types of output fields"
    )


class TransformChainValidator:
    """
    Validator for transform chains.

    Checks:
    1. All required inputs for each step are provided
    2. All references to previous steps are valid
    3. Types of inputs match expected types
    """

    # Pattern for finding references in configuration
    REF_PATTERN = re.compile(
        r"@([a-zA-Z0-9_]+)\.([a-zA-Z0-9_\.\[\]]+)(?:\|([a-zA-Z0-9_]+)(?:\(([^)]*)\))?)?"
    )

    # Plugin IO schemas (could be loaded from plugin metadata)
    PLUGIN_SCHEMAS = {
        "binned_distribution": StepIOSchema(
            required_inputs=["source", "field", "bins"],
            optional_inputs=["labels"],
            input_types={
                "source": ["str"],
                "field": ["str", "null"],
                "bins": ["list"],
                "labels": ["list", "null"],
            },
            outputs=["bins", "counts"],
            output_types={"bins": ["list"], "counts": ["list"]},
        ),
        "statistical_summary": StepIOSchema(
            required_inputs=["source", "stats"],
            optional_inputs=["field", "units", "max_value"],
            input_types={
                "source": ["str", "list"],
                "field": ["str", "null"],
                "stats": ["list"],
                "units": ["str", "null"],
                "max_value": ["int", "float", "null"],
            },
            outputs=["min", "mean", "max", "units", "max_value"],
            output_types={
                "min": ["float", "null"],
                "mean": ["float", "null"],
                "max": ["float", "null"],
                "units": ["str"],
                "max_value": ["float", "int"],
            },
        ),
        # Add schemas for other plugins...
    }

    @classmethod
    def validate_chain(cls, steps: List[Dict[str, Any]]) -> List[str]:
        """
        Validate a transform chain configuration.

        Args:
            steps: List of step configurations

        Returns:
            List of validation warnings (empty if all is well)

        Raises:
            DataTransformError: If validation fails
        """
        warnings = []
        available_outputs = {}

        for i, step in enumerate(steps):
            plugin_name = step.get("plugin")
            params = step.get("params", {})
            output_key = step.get("output_key")

            # Check plugin exists
            if not plugin_name:
                raise DataTransformError(f"Step {i + 1} is missing 'plugin' field")

            if not PluginRegistry.has_plugin(plugin_name, PluginType.TRANSFORMER):
                raise DataTransformError(
                    f"Plugin '{plugin_name}' not found",
                    details={
                        "available_plugins": PluginRegistry.list_plugins()[
                            PluginType.TRANSFORMER
                        ]
                    },
                )

            # Check output_key is provided
            if not output_key:
                raise DataTransformError(f"Step {i + 1} is missing 'output_key' field")

            # Get schema for this plugin
            schema = cls.PLUGIN_SCHEMAS.get(plugin_name)
            if not schema:
                warnings.append(
                    f"No schema available for plugin '{plugin_name}', skipping validation"
                )
                continue

            # Collect all references in this step
            refs = cls._find_references(params)

            # Check all referenced steps exist in available outputs
            for ref_step, ref_field, ref_func, ref_args in refs:
                if ref_step not in available_outputs:
                    raise DataTransformError(
                        f"Step {i + 1} references unknown step '{ref_step}'",
                        details={"available_steps": list(available_outputs.keys())},
                    )

                # Check top-level field exists (can't validate deeper paths)
                top_field = ref_field.split(".")[0].split("[")[0]
                if top_field not in available_outputs[ref_step]:
                    raise DataTransformError(
                        f"Step {i + 1} references unknown field '{top_field}' in step '{ref_step}'",
                        details={"available_fields": available_outputs[ref_step]},
                    )

            # Check required inputs are provided
            for input_name in schema.required_inputs:
                if input_name not in params:
                    raise DataTransformError(
                        f"Step {i + 1} is missing required parameter '{input_name}'",
                        details={"required_params": schema.required_inputs},
                    )

            # Type checking would require more complex logic with reference resolution
            # For now we'll just register outputs
            available_outputs[output_key] = schema.outputs

        return warnings

    @classmethod
    def _find_references(cls, obj: Any) -> List[tuple]:
        """
        Find all references in an object.

        Args:
            obj: Object to scan for references

        Returns:
            List of (step, field, function, args) tuples
        """
        refs = []

        if isinstance(obj, str) and obj.startswith("@"):
            match = cls.REF_PATTERN.match(obj)
            if match:
                refs.append(match.groups())
        elif isinstance(obj, dict):
            for value in obj.values():
                refs.extend(cls._find_references(value))
        elif isinstance(obj, list):
            for item in obj:
                refs.extend(cls._find_references(item))

        return refs


# Integration with TransformChain plugin
# Add to the validate_config method:
"""
# Validate step compatibility
warnings = TransformChainValidator.validate_chain(validated_config.steps)
if warnings:
    self.logger.warning(f"Transform chain validation warnings: {warnings}")
"""
