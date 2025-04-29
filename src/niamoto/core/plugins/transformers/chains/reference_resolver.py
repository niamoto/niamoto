"""
Advanced reference resolver for transform chains.
"""

from typing import Dict, Any
import re
import numpy as np


class ReferenceResolver:
    """
    Advanced reference resolver for transform chains.

    Supports:
    - Simple references: @step.field
    - Nested references: @step.field.subfield
    - Array indexing: @step.field[0]
    - Function calls: @step.field|function(args)
    """

    # Regular expression for parsing references
    REF_PATTERN = re.compile(
        r"@([a-zA-Z0-9_]+)\.([a-zA-Z0-9_\.\[\]]+)(?:\|([a-zA-Z0-9_]+)(?:\(([^)]*)\))?)?"
    )

    # Available transformation functions
    FUNCTIONS = {
        # Math functions
        "sum": sum,
        "mean": np.mean,
        "max": max,
        "min": min,
        "abs": abs,
        "round": round,
        # List functions
        "length": len,
        "first": lambda x: x[0] if x else None,
        "last": lambda x: x[-1] if x else None,
        # Type conversions
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        # Data processing
        "unique": lambda x: list(set(x)) if isinstance(x, list) else x,
        "sort": sorted,
        "reverse": lambda x: list(reversed(x)) if isinstance(x, list) else x,
        "filter_null": lambda x: [i for i in x if i is not None]
        if isinstance(x, list)
        else x,
    }

    def __init__(self, context: Dict[str, Any]):
        """
        Initialize the resolver with a context.

        Args:
            context: Dictionary of named results from previous transformations
        """
        self.context = context

    def resolve(self, value: Any) -> Any:
        """
        Resolve all references in a value.

        Args:
            value: Value potentially containing references

        Returns:
            Resolved value
        """
        if isinstance(value, str) and value.startswith("@"):
            return self._resolve_reference(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        else:
            return value

    def _resolve_reference(self, ref_str: str) -> Any:
        """
        Resolve a single reference string.

        Args:
            ref_str: Reference string (e.g., "@step.field|function(arg)")

        Returns:
            Resolved value
        """
        match = self.REF_PATTERN.match(ref_str)
        if not match:
            raise ValueError(f"Invalid reference format: {ref_str}")

        step_name, path, func_name, func_args = match.groups()

        # Check if referenced step exists
        if step_name not in self.context:
            available_steps = list(self.context.keys())
            raise ValueError(
                f"Step '{step_name}' not found. Available steps: {available_steps}"
            )

        # Get base value from context
        value = self.context[step_name]

        # Resolve path
        if path:
            value = self._resolve_path(value, path)

        # Apply function if specified
        if func_name:
            value = self._apply_function(value, func_name, func_args)

        return value

    def _resolve_path(self, value: Any, path: str) -> Any:
        """
        Resolve a path within a value.

        Args:
            value: Base value
            path: Path to resolve (e.g., "field.subfield[0].key[1]")

        Returns:
            Value at the specified path
        """
        # Use regex to find segments: either a key or an index [n]
        # Capture non-digit indexes as well with [^]]+
        segments = re.findall(r"\.?([^.[\]]+)|\[([^\]]+)\]", path)

        current_value = value

        for key, index_str in segments:
            if key:
                # Dictionary key access
                if not isinstance(current_value, dict) or key not in current_value:
                    raise ValueError(
                        f"Field '{key}' not found or not accessible in {type(current_value).__name__}"
                    )
                current_value = current_value[key]
            elif index_str:
                # Add check for non-digit index format
                if not index_str.isdigit():
                    raise ValueError(f"Invalid index format: '[{index_str}]'")
                # List index access
                try:
                    index = int(index_str)
                    if not isinstance(current_value, list) or index >= len(
                        current_value
                    ):
                        raise IndexError(
                            f"Index {index} out of bounds for list of length {len(current_value)}"
                        )
                    current_value = current_value[index]
                except (ValueError, IndexError, TypeError) as e:
                    # Catch potential int conversion errors (shouldn't happen with regex) or indexing errors
                    raise ValueError(
                        f"Invalid index access '[{index_str}]': {str(e)} on {type(current_value).__name__}"
                    )
            else:
                # Should not happen with the regex pattern
                raise ValueError(f"Invalid path segment found in '{path}'")

        return current_value

    def _apply_function(self, value: Any, func_name: str, func_args_str: str) -> Any:
        """
        Apply a function to a value.

        Args:
            value: Input value
            func_name: Function name
            func_args_str: Function arguments as string

        Returns:
            Function result
        """
        # Check if function exists
        if func_name not in self.FUNCTIONS:
            available_funcs = list(self.FUNCTIONS.keys())
            raise ValueError(
                f"Function '{func_name}' not found. Available functions: {available_funcs}"
            )

        # Parse arguments
        args = []
        if func_args_str:
            for arg_str in func_args_str.split(","):
                arg_str = arg_str.strip()
                # Convert to appropriate type
                if arg_str.startswith("@"):
                    # Resolve nested reference
                    args.append(self._resolve_reference(arg_str))
                elif arg_str.isdigit():
                    args.append(int(arg_str))
                elif arg_str.replace(".", "", 1).isdigit():
                    args.append(float(arg_str))
                elif arg_str.lower() in ("true", "false"):
                    args.append(arg_str.lower() == "true")
                else:
                    # String (remove quotes if present)
                    if arg_str.startswith('"') and arg_str.endswith('"'):
                        arg_str = arg_str[1:-1]
                    args.append(arg_str)

        # Apply function
        func = self.FUNCTIONS[func_name]
        if args:
            return func(value, *args)
        else:
            return func(value)


# Example usage:
# context = {
#     'step1': {'values': [1, 2, 3, 4, 5]},
#     'step2': {'matrix': [[1, 2], [3, 4]]}
# }
# resolver = ReferenceResolver(context)
# result = resolver.resolve('@step1.values|mean')  # Returns 3.0
# result = resolver.resolve('@step2.matrix[1][0]')  # Returns 3
