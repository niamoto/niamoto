"""
Plugin for performing custom calculations on data from other transformers.
Allows mathematical operations, ecological indices calculations and advanced statistical transformations.
"""

from typing import Dict, Any, List, Optional, Literal, Union
from pydantic import Field, model_validator, ConfigDict
import pandas as pd
import numpy as np
from enum import Enum

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class Operation(str, Enum):
    """Types of operations supported by the calculator."""

    ARRAY_DIVISION = "array_division"
    ARRAY_MULTIPLICATION = "array_multiplication"
    NORMALIZE_ARRAY = "normalize_array"
    WEIGHTED_SUM = "weighted_sum"
    SHANNON_ENTROPY = "shannon_entropy"
    PIELOU_EVENNESS = "pielou_evenness"
    SUM_ARRAY_SLICE = "sum_array_slice"
    RATIO_CALCULATION = "ratio_calculation"
    CSR_STRATEGY = "csr_strategy"
    RESILIENCE_SCORE = "resilience_score"
    BIOMASS_BY_STRATA = "biomass_by_strata"
    CONFORMITY_INDEX = "conformity_index"
    CUSTOM_FORMULA = "custom_formula"
    PEAK_DETECTION = "peak_detection"
    ACTIVE_PERIODS = "active_periods"


class WeightedSumValue(Dict[str, Any]):
    """Value configuration for weighted sum operations."""

    value: float = Field(..., description="Value to include in weighted sum")
    weight: float = Field(default=1.0, description="Weight for this value")
    max: Optional[float] = Field(
        default=None, description="Maximum value for normalization"
    )


class CSRValues(Dict[str, Any]):
    """CSR strategy values."""

    competitive: float = Field(..., description="Competitive strategy value")
    stress_tolerant: float = Field(..., description="Stress tolerant strategy value")
    ruderal: float = Field(..., description="Ruderal strategy value")


class CustomCalculatorParams(BasePluginParams):
    """Typed parameters for custom calculator plugin.

    This plugin performs custom mathematical calculations and ecological indices.
    It supports various operations including array calculations, ecological indices,
    normalization, and specialized forest analysis calculations.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Perform custom mathematical calculations and ecological indices",
            "examples": [
                {
                    "operation": "shannon_entropy",
                    "probabilities": [0.5, 0.3, 0.2],
                    "normalize": True,
                },
                {
                    "operation": "weighted_sum",
                    "values": [
                        {"value": 10, "weight": 0.6},
                        {"value": 8, "weight": 0.4},
                    ],
                    "normalization": [0, 100],
                },
            ],
        }
    )

    operation: Literal[
        "array_division",
        "array_multiplication",
        "normalize_array",
        "weighted_sum",
        "shannon_entropy",
        "pielou_evenness",
        "sum_array_slice",
        "ratio_calculation",
        "csr_strategy",
        "resilience_score",
        "biomass_by_strata",
        "conformity_index",
        "custom_formula",
        "peak_detection",
        "active_periods",
    ] = Field(
        ...,
        description="Type of mathematical operation to perform",
        json_schema_extra={"ui:widget": "select"},
    )

    # Array operations
    numerator: Optional[Union[List[float], float]] = Field(
        default=None,
        description="Numerator value or array for division operations",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'array_division'",
        },
    )

    denominator: Optional[Union[List[float], float]] = Field(
        default=None,
        description="Denominator value or array for division operations",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'array_division'",
        },
    )

    array1: Optional[List[float]] = Field(
        default=None,
        description="First array for multiplication",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'array_multiplication'",
        },
    )

    array2: Optional[List[float]] = Field(
        default=None,
        description="Second array for multiplication",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'array_multiplication'",
        },
    )

    scale_factor: float = Field(
        default=1.0,
        description="Scale factor to apply to results",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "operation === 'array_division' || operation === 'array_multiplication' || operation === 'ratio_calculation'",
        },
    )

    # Normalization
    input: Optional[List[float]] = Field(
        default=None,
        description="Input array to normalize",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'normalize_array'",
        },
    )

    method: Optional[
        Literal["minmax", "zscore", "percentage", "relative", "absolute"]
    ] = Field(
        default="minmax",
        description="Normalization or comparison method",
        json_schema_extra={
            "ui:widget": "select",
            "ui:condition": "operation in ['normalize_array', 'conformity_index']",
        },
    )

    # Weighted sum
    values: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of values with weights for weighted sum",
        json_schema_extra={
            "ui:widget": "object-array",
            "ui:condition": "operation === 'weighted_sum'",
        },
    )

    normalization: Optional[List[float]] = Field(
        default=None,
        description="Normalization bounds [min, max]",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'weighted_sum'",
        },
    )

    # Shannon entropy
    probabilities: Optional[List[float]] = Field(
        default=None,
        description="Probability values for Shannon entropy calculation",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'shannon_entropy'",
        },
    )

    normalize: bool = Field(
        default=True,
        description="Whether to normalize probabilities",
        json_schema_extra={
            "ui:widget": "checkbox",
            "ui:condition": "operation === 'shannon_entropy'",
        },
    )

    # Pielou evenness
    shannon_entropy: Optional[float] = Field(
        default=None,
        description="Shannon entropy value for Pielou evenness",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "operation === 'pielou_evenness'",
        },
    )

    max_bins: Optional[int] = Field(
        default=None,
        description="Maximum number of bins for Pielou evenness",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "operation === 'pielou_evenness'",
        },
    )

    # Array slice
    array: Optional[List[float]] = Field(
        default=None,
        description="Input array for slice operations",
        json_schema_extra={
            "ui:widget": "array",
            "ui:condition": "operation === 'sum_array_slice'",
        },
    )

    start_index: Optional[int] = Field(
        default=None,
        description="Start index for array slice",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "operation === 'sum_array_slice'",
        },
    )

    end_index: Optional[int] = Field(
        default=None,
        description="End index for array slice",
        json_schema_extra={
            "ui:widget": "number",
            "ui:condition": "operation === 'sum_array_slice'",
        },
    )

    # Custom formula
    formula: Optional[str] = Field(
        default=None,
        description="Mathematical formula to evaluate",
        json_schema_extra={
            "ui:widget": "textarea",
            "ui:condition": "operation === 'custom_formula'",
        },
    )

    variables: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Variables to use in formula (can be numbers, dictionaries, or other types)",
        json_schema_extra={
            "ui:widget": "object",
            "ui:condition": "operation === 'custom_formula'",
        },
    )

    @model_validator(mode="after")
    def validate_operation_params(self):
        """Validate operation-specific parameters."""
        operation = self.operation

        if operation == "array_division":
            if not self.numerator:
                raise ValueError("numerator is required for array_division")
            if not self.denominator:
                raise ValueError("denominator is required for array_division")

        elif operation == "array_multiplication":
            if not self.array1:
                raise ValueError("array1 is required for array_multiplication")
            if not self.array2:
                raise ValueError("array2 is required for array_multiplication")

        elif operation == "normalize_array":
            if not self.input:
                raise ValueError("input is required for normalize_array")

        elif operation == "weighted_sum":
            if not self.values:
                raise ValueError("values is required for weighted_sum")

        elif operation == "shannon_entropy":
            if not self.probabilities:
                raise ValueError("probabilities is required for shannon_entropy")

        elif operation == "pielou_evenness":
            if self.shannon_entropy is None:
                raise ValueError("shannon_entropy is required for pielou_evenness")
            if self.max_bins is None:
                raise ValueError("max_bins is required for pielou_evenness")

        elif operation == "sum_array_slice":
            if not self.array:
                raise ValueError("array is required for sum_array_slice")
            if self.start_index is None:
                raise ValueError("start_index is required for sum_array_slice")

        elif operation == "custom_formula":
            if not self.formula:
                raise ValueError("formula is required for custom_formula")
            if not self.variables:
                raise ValueError("variables is required for custom_formula")

        return self


class CustomCalculatorConfig(PluginConfig):
    """Configuration for custom calculator plugin"""

    plugin: Literal["custom_calculator"] = "custom_calculator"
    params: CustomCalculatorParams


@register("custom_calculator", PluginType.TRANSFORMER)
class CustomCalculator(TransformerPlugin):
    """
    Plugin for performing custom calculations on data from other transformers.

    Supports various operations:
    - Array calculations (division, multiplication)
    - Ecological indices (Shannon, Pielou)
    - Normalization and weighting operations
    - Forest analysis specific calculations

    This plugin is particularly useful in transformation chains
    for creating composite metrics and specialized indices.
    """

    config_model = CustomCalculatorConfig

    def validate_config(self, config: Dict[str, Any]) -> CustomCalculatorConfig:
        """Validate configuration and return typed config."""
        try:
            return self.config_model(**config)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs custom calculations according to the operation specified.

        Args:
            data: Input DataFrame (may be ignored for some operations)
            config: Configuration with the operation and its parameters

        Returns:
            Dictionary with the calculation results
        """
        try:
            # Validate the configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get the operation
            operation = Operation(params.operation)

            # Execute the corresponding operation
            if operation == Operation.ARRAY_DIVISION:
                return self._array_division(params)

            elif operation == Operation.ARRAY_MULTIPLICATION:
                return self._array_multiplication(params)

            elif operation == Operation.NORMALIZE_ARRAY:
                return self._normalize_array(params)

            elif operation == Operation.WEIGHTED_SUM:
                return self._weighted_sum(params)

            elif operation == Operation.SHANNON_ENTROPY:
                return self._shannon_entropy(params)

            elif operation == Operation.PIELOU_EVENNESS:
                return self._pielou_evenness(params)

            elif operation == Operation.SUM_ARRAY_SLICE:
                return self._sum_array_slice(params)

            elif operation == Operation.RATIO_CALCULATION:
                return self._ratio_calculation(params)

            elif operation == Operation.CSR_STRATEGY:
                return self._csr_strategy(params, data)

            elif operation == Operation.RESILIENCE_SCORE:
                return self._resilience_score(params)

            elif operation == Operation.BIOMASS_BY_STRATA:
                return self._biomass_by_strata(params, data)

            elif operation == Operation.CONFORMITY_INDEX:
                return self._conformity_index(params)

            elif operation == Operation.CUSTOM_FORMULA:
                return self._custom_formula(params)

            elif operation == Operation.PEAK_DETECTION:
                return self._peak_detection(params)

            elif operation == Operation.ACTIVE_PERIODS:
                return self._active_periods(params)

            else:
                raise DataTransformError(
                    f"Unsupported operation: {operation}",
                    details={"operation": operation},
                )

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during custom calculation: {str(e)}", details={"config": config}
            )

    def _array_multiplication(self, params: CustomCalculatorParams) -> Dict[str, Any]:
        """
        Multiply two arrays element-wise.

        Args:
            params: Parameters with:
                - array1: First array
                - array2: Second array
                - scale_factor: Optional scale factor

        Returns:
            Result of the multiplication
        """
        try:
            # Convert params to dict if needed
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the arrays
            array1 = np.array(params_dict["array1"], dtype=float)
            array2 = np.array(params_dict["array2"], dtype=float)

            # Check the dimensions
            if array1.size != array2.size and array2.size != 1:
                raise DataTransformError(
                    "The arrays must have the same size, or the second array must be a scalar",
                    details={"array1_size": array1.size, "array2_size": array2.size},
                )

            # Apply a scale factor if specified
            scale_factor = params_dict.get("scale_factor", 1.0)

            # Perform the multiplication
            if array2.size == 1:
                # Multiplication by a scalar
                result = array1 * array2[0] * scale_factor
            else:
                # Element-wise multiplication
                result = np.multiply(array1, array2) * scale_factor

            # Format the result
            return {"values": result.tolist(), "scale_factor": scale_factor}

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during array multiplication: {str(e)}",
                details={"params": params},
            )

    def _normalize_array(self, params: Any) -> Dict[str, Any]:
        """
        Normalize an array according to different methods.

        Args:
            params: Parameters with:
                - input: Array to normalize
                - method: Normalization method (minmax, zscore, percentage)
                - min_value, max_value: Bounds for minmax (optional)

        Returns:
            Normalized array
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the array
            input_array = np.array(params_dict["input"], dtype=float)

            # Normalization method
            method = params_dict.get("method", "minmax")

            if method == "minmax":
                # Min-max normalization
                min_value = params_dict.get("min_value", input_array.min())
                max_value = params_dict.get("max_value", input_array.max())

                # Avoid division by zero
                if max_value == min_value:
                    normalized = np.zeros_like(input_array)
                else:
                    normalized = (input_array - min_value) / (max_value - min_value)

                result = {
                    "values": normalized.tolist(),
                    "min": float(min_value),
                    "max": float(max_value),
                    "method": method,
                }

            elif method == "zscore":
                # Z-score normalization
                mean = np.mean(input_array)
                std = np.std(input_array)

                # Avoid division by zero
                if std == 0:
                    normalized = np.zeros_like(input_array)
                else:
                    normalized = (input_array - mean) / std

                result = {
                    "values": normalized.tolist(),
                    "mean": float(mean),
                    "std": float(std),
                    "method": method,
                }

            elif method == "percentage":
                # Normalization to percentage
                total = np.sum(input_array)

                # Avoid division by zero
                if total == 0:
                    normalized = np.zeros_like(input_array)
                else:
                    normalized = (input_array / total) * 100

                result = {
                    "values": normalized.tolist(),
                    "total": float(total),
                    "method": method,
                }

            else:
                raise DataTransformError(
                    f"Unsupported normalization method: {method}",
                    details={"supported_methods": ["minmax", "zscore", "percentage"]},
                )

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during normalization: {str(e)}", details={"params": params}
            )

    def _weighted_sum(self, params: Any) -> Dict[str, Any]:
        """
        Calculate a weighted sum of values.

        Args:
            params: Parameters with:
                - values: List of dictionaries {value, weight, max (optional)}
                - normalization: Bounds for normalizing the result [min, max]

        Returns:
            Result of the weighted sum
        """
        try:
            # Convert params to dict if needed
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the values and weights
            values_config = params_dict["values"]

            if not isinstance(values_config, list):
                raise DataTransformError(
                    "The 'values' parameter must be a list of dictionaries",
                    details={"values": values_config},
                )

            weighted_sum = 0.0
            total_weight = 0.0

            # Calculate the weighted sum
            for item in values_config:
                if not isinstance(item, dict):
                    raise DataTransformError(
                        "Each element in 'values' must be a dictionary",
                        details={"item": item},
                    )

                if "value" not in item:
                    raise DataTransformError(
                        "Each element must contain a 'value' key",
                        details={"item": item},
                    )

                value = float(item["value"])
                weight = float(item.get("weight", 1.0))

                # Normalize the value if max is specified
                if "max" in item:
                    max_value = float(item["max"])
                    value = value / max_value if max_value > 0 else 0

                weighted_sum += value * weight
                total_weight += weight

            # Calculate the result
            if total_weight > 0:
                result = weighted_sum / total_weight
            else:
                result = 0.0

            # Normalize the result if specified
            normalization = params_dict.get("normalization")
            if (
                normalization
                and isinstance(normalization, list)
                and len(normalization) == 2
            ):
                min_value, max_value = normalization
                result = min_value + (max_value - min_value) * result

            return {
                "value": float(result),
                "weighted_sum": float(weighted_sum),
                "total_weight": float(total_weight),
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during weighted sum calculation: {str(e)}",
                details={"params": params},
            )

    def _shannon_entropy(self, params: Any) -> Dict[str, Any]:
        """
        Calculate the Shannon entropy of a probability distribution.

        Args:
            params: Parameters with:
                - probabilities: Array of probabilities or frequencies
                - normalize: Normalize the probabilities (True/False)

        Returns:
            Shannon entropy
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the probabilities
            probabilities = np.array(params_dict["probabilities"], dtype=float)

            # Normalize if specified or if the sum is not 1
            normalize = params_dict.get("normalize", True)
            if normalize or abs(np.sum(probabilities) - 1.0) > 1e-6:
                total = np.sum(probabilities)
                if total > 0:
                    probabilities = probabilities / total

            # Calculate the entropy (ignore zeros)
            with np.errstate(divide="ignore", invalid="ignore"):
                log_probs = np.log2(probabilities)
                log_probs[~np.isfinite(log_probs)] = 0
                entropy = -np.sum(probabilities * log_probs)

            # Calculate the maximum possible entropy (log2 of the number of non-zero classes)
            non_zero_count = np.count_nonzero(probabilities)
            max_entropy = np.log2(non_zero_count) if non_zero_count > 0 else 0

            return {
                "value": float(entropy),
                "max_entropy": float(max_entropy),
                "classes_count": int(len(probabilities)),
                "non_zero_classes": int(non_zero_count),
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during Shannon entropy calculation: {str(e)}",
                details={"params": params},
            )

    def _pielou_evenness(self, params: Any) -> Dict[str, Any]:
        """
        Calculates the Pielou evenness index (J') from Shannon entropy.

        Args:
            params: Parameters with:
                - shannon_entropy: Shannon entropy value
                - max_bins: Maximum number of possible classes

        Returns:
            Pielou evenness index
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the entropy and the number of classes
            shannon_entropy = float(params_dict["shannon_entropy"])
            max_bins = int(params_dict["max_bins"])

            # Calculate the maximum possible entropy
            max_entropy = np.log2(max_bins) if max_bins > 0 else 0

            # Calculate the Pielou evenness
            evenness = shannon_entropy / max_entropy if max_entropy > 0 else 0

            return {
                "value": float(evenness),
                "shannon_entropy": shannon_entropy,
                "max_entropy": float(max_entropy),
                "max_bins": max_bins,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during Pielou evenness calculation: {str(e)}",
                details={"params": params},
            )

    def _sum_array_slice(self, params: Any) -> Dict[str, Any]:
        """
        Calculates the sum of an array slice.

        Args:
            params: Parameters with:
                - array: Input array
                - start_index: Start index
                - end_index: End index (optional)
                - total: Calculation mode for the total (sum, len, value)

        Returns:
            Sum of the slice and ratio compared to the total
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the array
            array = np.array(params_dict["array"], dtype=float)

            # Indices of the slice
            start_index = int(params_dict["start_index"])
            end_index = int(params_dict.get("end_index", len(array)))

            # Check the indices
            if start_index < 0 or start_index >= len(array):
                raise DataTransformError(
                    f"Invalid start index: {start_index}",
                    details={"array_length": len(array)},
                )

            if end_index < start_index or end_index > len(array):
                raise DataTransformError(
                    f"Invalid end index: {end_index}",
                    details={"array_length": len(array), "start_index": start_index},
                )

            # Calculate the sum of the slice
            slice_sum = np.sum(array[start_index:end_index])

            # Calculate the total according to the specified mode
            total_mode = params_dict.get("total", "sum")

            if total_mode == "sum":
                total = np.sum(array)
            elif total_mode == "len":
                total = len(array)
            elif total_mode == "value":
                total = float(params_dict.get("total_value", np.sum(array)))
            else:
                raise DataTransformError(
                    f"Unsupported total calculation mode: {total_mode}",
                    details={"supported_modes": ["sum", "len", "value"]},
                )

            # Calculate the ratio
            ratio = slice_sum / total if total > 0 else 0

            return {
                "value": float(ratio),
                "slice_sum": float(slice_sum),
                "total": float(total),
                "start_index": start_index,
                "end_index": end_index,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during sum of slice calculation: {str(e)}",
                details={"params": params},
            )

    def _ratio_calculation(self, params: Any) -> Dict[str, Any]:
        """
        Calculates a ratio between two values.

        Args:
            params: Parameters with:
                - numerator: Value of the numerator
                - denominator: Value of the denominator
                - scale_factor: Scale factor (optional)

        Returns:
            Calculated ratio
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the values
            numerator = float(params_dict["numerator"])
            denominator = float(params_dict["denominator"])

            # Apply a scale factor if specified
            scale_factor = float(params_dict.get("scale_factor", 1.0))

            # Calculate the ratio
            ratio = (numerator / denominator) * scale_factor if denominator != 0 else 0

            return {
                "value": float(ratio),
                "numerator": numerator,
                "denominator": denominator,
                "scale_factor": scale_factor,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during ratio calculation: {str(e)}", details={"params": params}
            )

    def _csr_strategy(
        self, params: Dict[str, Any], data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Calculates ecological strategy (CSR) indices.

        Args:
            params: Parameters with:
                - wood_density: Average wood density
                - leaf_thickness: Average leaf thickness
                - leaf_sla: Average leaf surface area
                - substrate: Substrate type

        Returns:
            CSR values and dominant strategy
        """
        try:
            # Convert params to dict if needed
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the functional traits
            wood_density = float(params_dict["wood_density"])
            leaf_thickness = float(params_dict["leaf_thickness"])
            leaf_sla = float(params_dict["leaf_sla"])
            substrate = params_dict.get("substrate", "NUM")  # UM or NUM by default

            # Normalize the traits (simplification)
            norm_wd = min(1.0, wood_density / 1.0)  # 1.0 g/cm³ is a high value
            norm_lt = min(1.0, leaf_thickness / 500.0)  # 500 µm is a high value
            norm_sla = min(1.0, leaf_sla / 40.0)  # 40 m²/kg is a high value

            # Stress factor for the substrate (UM more stressful)
            substrate_factor = 1.2 if substrate == "UM" else 1.0

            # Calculate the CSR components
            # C: High wood density, thick leaves, low SLA
            # S: High wood density, thick leaves, very low SLA
            # R: Low wood density, thin leaves, high SLA

            c_value = (0.7 * norm_wd + 0.4 * norm_lt - 0.3 * norm_sla) / 0.8
            s_value = (
                (0.5 * norm_wd + 0.8 * norm_lt - 0.7 * norm_sla)
                * substrate_factor
                / 1.2
            )
            r_value = (0.3 - 0.7 * norm_wd - 0.8 * norm_lt + 0.9 * norm_sla) / 1.0

            # Normalize for C+S+R = 1
            total = c_value + s_value + r_value
            if total > 0:
                c_value /= total
                s_value /= total
                r_value /= total
            else:
                c_value = s_value = r_value = 1 / 3

            # Dominant strategy
            strategies = ["C", "S", "R"]
            values = [c_value, s_value, r_value]
            dominant_idx = np.argmax(values)
            dominant_strategy = strategies[dominant_idx]

            # Secondary strategy
            values[dominant_idx] = -1  # Exclude the dominant one
            secondary_idx = np.argmax(values)
            secondary_strategy = strategies[secondary_idx]

            # CSR classification
            csr_class = f"{dominant_strategy}{secondary_strategy}"
            if max(c_value, s_value, r_value) < 0.45:
                csr_class = "CSR"  # Intermediate strategy

            return {
                "values": {
                    "competitive": float(c_value),
                    "stress_tolerant": float(s_value),
                    "ruderal": float(r_value),
                },
                "dominant_strategy": dominant_strategy,
                "secondary_strategy": secondary_strategy,
                "csr_class": csr_class,
                "traits": {
                    "wood_density": wood_density,
                    "leaf_thickness": leaf_thickness,
                    "leaf_sla": leaf_sla,
                    "substrate": substrate,
                },
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during CSR calculation: {str(e)}", details={"params": params}
            )

    def _resilience_score(self, params: Any) -> Dict[str, Any]:
        """
        Calculates a resilience score based on CSR and other factors.

        Args:
            params: Parameters with:
                - csr_values: CSR values
                - functional_diversity: Functional diversity index
                - substrate_type: Substrate type

        Returns:
            Resilience score
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the CSR values
            csr_values = params_dict["csr_values"]
            if not isinstance(csr_values, dict):
                raise DataTransformError(
                    "The 'csr_values' parameter must be a dictionary",
                    details={"csr_values": csr_values},
                )

            c_value = float(csr_values.get("competitive", 0))
            s_value = float(csr_values.get("stress_tolerant", 0))
            r_value = float(csr_values.get("ruderal", 0))

            # Functional diversity (e.g. Shannon)
            functional_diversity = float(params_dict["functional_diversity"])

            # Substrate type
            substrate_type = params_dict.get("substrate_type", "NUM")

            # Weighting factors
            substrate_factor = 0.8 if substrate_type == "UM" else 1.0

            # Calculate the resilience score
            # Simplified assumptions:
            # - High resilience: R high, diversity high
            # - Medium resilience: C high, diversity medium
            # - Low resilience: S high, diversity low

            # Normalize the diversity (0-1)
            norm_diversity = min(1.0, functional_diversity / 5.0)

            # Calculate the resilience score (0-100)
            resilience_score = (
                20 * c_value + 10 * s_value + 40 * r_value + 30 * norm_diversity
            ) * substrate_factor

            # Resilience class
            if resilience_score >= 80:
                resilience_class = "Very high"
            elif resilience_score >= 60:
                resilience_class = "High"
            elif resilience_score >= 40:
                resilience_class = "Medium"
            elif resilience_score >= 20:
                resilience_class = "Low"
            else:
                resilience_class = "Very low"

            return {
                "value": float(resilience_score),
                "class": resilience_class,
                "factors": {
                    "competitive": c_value,
                    "stress_tolerant": s_value,
                    "ruderal": r_value,
                    "functional_diversity": functional_diversity,
                    "substrate_factor": substrate_factor,
                },
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during resilience score calculation: {str(e)}",
                details={"params": params},
            )

    def _array_division(self, params: Any) -> Dict[str, Any]:
        """
        Divide two arrays element-wise.

        Args:
            params: Parameters with:
                - numerator: Numerator array
                - denominator: Denominator array
                - scale_factor: Optional scale factor
                - default_value: Value to use when denominator is zero (default: 0)

        Returns:
            Result of the division
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the arrays
            numerator = np.array(params_dict["numerator"], dtype=float)
            denominator = np.array(params_dict["denominator"], dtype=float)

            # Check dimensions
            if numerator.shape != denominator.shape:
                raise DataTransformError(
                    "Arrays must have the same dimensions",
                    details={
                        "numerator_shape": numerator.shape,
                        "denominator_shape": denominator.shape,
                    },
                )

            # Get the scale factor if specified
            scale_factor = float(params_dict.get("scale_factor", 1.0))
            default_value = float(params_dict.get("default_value", 0.0))

            # Perform the division with handling for division by zero
            with np.errstate(divide="ignore", invalid="ignore"):
                result = np.divide(numerator, denominator)
                result = np.where(np.isfinite(result), result, default_value)

            # Apply the scale factor
            result = result * scale_factor

            return {
                "value": result.tolist(),
                "mean": float(np.mean(result)),
                "min": float(np.min(result)),
                "max": float(np.max(result)),
                "sum": float(np.sum(result)),
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during array division: {str(e)}",
                details={"params": params},
            )

    def _biomass_by_strata(
        self, params: Dict[str, Any], data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Calculates biomass distribution by forest strata.

        Args:
            params: Parameters with:
                - height_column: Column containing tree heights
                - dbh_column: Column containing tree diameters
                - strata_bounds: List of height boundaries for strata
                - strata_names: Optional names for the strata
                - wood_density: Wood density value or column name
            data: Input DataFrame with tree data

        Returns:
            Biomass by strata and distribution statistics
        """
        try:
            # Convert params to dict if needed
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the columns
            height_column = params_dict["height_column"]
            dbh_column = params_dict["dbh_column"]

            # Check if columns exist
            if height_column not in data.columns:
                raise DataTransformError(
                    f"Height column '{height_column}' not found in data",
                    details={"available_columns": list(data.columns)},
                )
            if dbh_column not in data.columns:
                raise DataTransformError(
                    f"DBH column '{dbh_column}' not found in data",
                    details={"available_columns": list(data.columns)},
                )

            # Get strata boundaries and names
            strata_bounds = params_dict["strata_bounds"]
            if not isinstance(strata_bounds, list) or len(strata_bounds) < 2:
                raise DataTransformError(
                    "Strata bounds must be a list with at least 2 elements",
                    details={"strata_bounds": strata_bounds},
                )

            # Get strata names (optional)
            strata_names = params_dict.get("strata_names", None)
            if strata_names is None:
                # Generate default names: S1, S2, etc.
                strata_names = [f"S{i + 1}" for i in range(len(strata_bounds) - 1)]
            elif len(strata_names) != len(strata_bounds) - 1:
                raise DataTransformError(
                    "Number of strata names must match number of strata",
                    details={
                        "strata_names_count": len(strata_names),
                        "strata_count": len(strata_bounds) - 1,
                    },
                )

            # Get wood density
            wood_density_param = params_dict.get("wood_density", 0.6)  # Default value
            if (
                isinstance(wood_density_param, str)
                and wood_density_param in data.columns
            ):
                wood_density = data[wood_density_param]
            else:
                wood_density = float(wood_density_param)

            # Extract height and dbh data
            heights = data[height_column].values
            dbhs = data[dbh_column].values

            # Calculate biomass using a simplified allometric equation
            # Biomass = π * (DBH/2)^2 * Height * WoodDensity
            if isinstance(wood_density, float):
                biomass = np.pi * (dbhs / 200) ** 2 * heights * wood_density
            else:
                biomass = np.pi * (dbhs / 200) ** 2 * heights * wood_density.values

            # Classify trees into strata based on height
            strata_indices = np.digitize(heights, strata_bounds) - 1
            strata_indices = np.clip(strata_indices, 0, len(strata_names) - 1)

            # Calculate biomass by strata
            strata_biomass = {}
            total_biomass = np.sum(biomass)

            for i, name in enumerate(strata_names):
                mask = strata_indices == i
                strata_biomass[name] = float(np.sum(biomass[mask]))

            # Calculate percentages
            strata_percentages = {
                name: (value / total_biomass * 100 if total_biomass > 0 else 0)
                for name, value in strata_biomass.items()
            }

            # Determine dominant strata (highest biomass)
            dominant_strata = (
                max(strata_biomass.items(), key=lambda x: x[1])[0]
                if strata_biomass
                else None
            )

            return {
                "value": strata_biomass,
                "total_biomass": float(total_biomass),
                "percentages": strata_percentages,
                "dominant_strata": dominant_strata,
                "strata_bounds": strata_bounds,
                "strata_names": strata_names,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during biomass by strata calculation: {str(e)}",
                details={"params": params},
            )

    def _peak_detection(self, params: Any) -> Dict[str, Any]:
        """
        Detects peaks in a time series.

        Args:
            params: Parameters with:
                - time_series: Array of time series values or dictionary of named time series
                - threshold: Detection threshold (default: mean + std)
                - min_distance: Minimum distance between peaks
                - prominence: Minimum prominence of peaks

        Returns:
            Detected peaks and their properties
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the time series
            time_series_data = params_dict.get("time_series")

            # Get detection parameters
            threshold = params_dict.get("threshold", None)
            min_distance = int(params_dict.get("min_distance", 1))
            prominence = float(params_dict.get("prominence", 0.0))

            # Check if time_series is a dictionary or a single array
            if isinstance(time_series_data, dict):
                # Process each time series separately
                results = {}
                for key, series in time_series_data.items():
                    results[key] = self._process_single_time_series(
                        np.array(series, dtype=float),
                        threshold,
                        min_distance,
                        prominence,
                    )
                return results
            else:
                # Process a single time series
                time_series = np.array(time_series_data, dtype=float)
                return self._process_single_time_series(
                    time_series, threshold, min_distance, prominence
                )

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during peak detection: {str(e)}",
                details={"params": params},
            )

    def _process_single_time_series(
        self, time_series, threshold, min_distance, prominence
    ):
        """
        Process a single time series for peak detection.

        Args:
            time_series: NumPy array of time series values
            threshold: Detection threshold or None for automatic
            min_distance: Minimum distance between peaks
            prominence: Minimum prominence of peaks

        Returns:
            Dictionary with peak detection results
        """
        # Calculate default threshold if not provided
        if threshold is None:
            threshold = np.mean(time_series) + np.std(time_series)
        else:
            threshold = float(threshold)

        # Find peaks
        peaks = []
        peak_heights = []

        # Simple peak detection algorithm
        for i in range(1, len(time_series) - 1):
            # Check if the point is higher than its neighbors
            if (
                time_series[i] > time_series[i - 1]
                and time_series[i] > time_series[i + 1]
                and time_series[i] >= threshold
            ):
                # Check if it's far enough from previously detected peaks
                if not peaks or i - peaks[-1] >= min_distance:
                    # Check prominence
                    left_min = (
                        np.min(time_series[max(0, i - min_distance) : i])
                        if i > 0
                        else time_series[0]
                    )
                    right_min = (
                        np.min(
                            time_series[
                                i + 1 : min(len(time_series), i + min_distance + 1)
                            ]
                        )
                        if i < len(time_series) - 1
                        else time_series[-1]
                    )
                    peak_prominence = time_series[i] - max(left_min, right_min)

                    if peak_prominence >= prominence:
                        peaks.append(i)
                        peak_heights.append(float(time_series[i]))

        return {
            "value": peaks,
            "count": len(peaks),
            "heights": peak_heights,
            "threshold": float(threshold),
            "mean": float(np.mean(time_series)),
            "std": float(np.std(time_series)),
            "min": float(np.min(time_series)),
            "max": float(np.max(time_series)),
        }

    def _active_periods(self, params: Any) -> Dict[str, Any]:
        """
        Detect active periods in time series.

        Args:
            params: Parameters with:
                - time_series: Dictionary of time series
                - threshold: Detection threshold
                - min_duration: Minimum duration of an active period
                - labels: Month labels

        Returns:
            Active periods for each time series
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the time series
            time_series = params_dict.get("time_series")
            if not isinstance(time_series, dict):
                raise DataTransformError(
                    "Time series must be a dictionary",
                    details={"time_series": time_series},
                )

            # Get parameters
            threshold = float(params_dict.get("threshold", 0.0))
            min_duration = int(params_dict.get("min_duration", 1))
            labels = params_dict.get("labels", None)

            # Generate default labels if not provided
            if labels is None:
                labels = [str(i + 1) for i in range(12)]  # Default to month numbers

            # Process each time series
            results = {}

            for name, values in time_series.items():
                # Convert to numpy array
                values = np.array(values, dtype=float)

                # Find active periods (where values > threshold)
                active_mask = values > threshold

                # Find contiguous active periods
                active_periods = []
                current_start = None

                for i, active in enumerate(active_mask):
                    if active and current_start is None:
                        # Start of a new active period
                        current_start = i
                    elif not active and current_start is not None:
                        # End of an active period
                        duration = i - current_start
                        if duration >= min_duration:
                            active_periods.append((current_start, i - 1, duration))
                        current_start = None

                # Check if there's an active period at the end
                if current_start is not None:
                    duration = len(values) - current_start
                    if duration >= min_duration:
                        active_periods.append(
                            (current_start, len(values) - 1, duration)
                        )

                # Format the results
                formatted_periods = []
                for start, end, duration in active_periods:
                    formatted_periods.append(
                        {
                            "start": int(start),
                            "end": int(end),
                            "duration": int(duration),
                            "start_label": labels[start % len(labels)],
                            "end_label": labels[end % len(labels)],
                            "mean_value": float(np.mean(values[start : end + 1])),
                            "max_value": float(np.max(values[start : end + 1])),
                        }
                    )

                results[name] = {
                    "periods": formatted_periods,
                    "count": len(formatted_periods),
                    "total_active_duration": sum(p[2] for p in active_periods),
                    "activity_percentage": sum(active_mask) / len(values) * 100
                    if len(values) > 0
                    else 0,
                }

            return {
                "value": results,
                "series_count": len(results),
                "threshold": threshold,
                "min_duration": min_duration,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during active periods detection: {str(e)}",
                details={"params": params},
            )

    def _custom_formula(self, params: Any) -> Dict[str, Any]:
        """
        Evaluates a custom mathematical formula with provided variables.

        Args:
            params: Parameters with:
                - formula: Mathematical formula as string
                - variables: Dictionary of variable values
                - description: Optional description of the formula

        Returns:
            Result of the formula evaluation
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get the formula and variables
            formula = params_dict.get("formula")
            variables = params_dict.get("variables", {})
            description = params_dict.get("description", "Custom formula")

            if not isinstance(formula, str):
                raise DataTransformError(
                    "Formula must be a string",
                    details={"formula": formula},
                )

            if not isinstance(variables, dict):
                raise DataTransformError(
                    "Variables must be a dictionary",
                    details={"variables": variables},
                )

            # Create a safe namespace for evaluation
            # Only allow basic mathematical functions
            safe_dict = {
                "abs": abs,
                "max": max,
                "min": min,
                "sum": sum,
                "len": len,
                "round": round,
                "pow": pow,
                "int": int,
                "float": float,
            }

            # Add NumPy functions
            safe_dict.update(
                {
                    "np": np,
                    "sin": np.sin,
                    "cos": np.cos,
                    "tan": np.tan,
                    "exp": np.exp,
                    "log": np.log,
                    "log10": np.log10,
                    "sqrt": np.sqrt,
                    "square": np.square,
                    "mean": np.mean,
                    "median": np.median,
                    "std": np.std,
                    "var": np.var,
                    "pi": np.pi,
                    "e": np.e,
                }
            )

            # Add user variables
            safe_dict.update(variables)

            # Evaluate the formula
            result = eval(formula, {"__builtins__": {}}, safe_dict)

            # Convert result to a standard Python type if it's a NumPy type
            if isinstance(result, np.ndarray):
                if result.size == 1:
                    result = result.item()  # Convert single-item array to scalar
                else:
                    result = result.tolist()  # Convert array to list
            elif isinstance(result, np.number):
                result = result.item()  # Convert NumPy scalar to Python scalar

            return {
                "value": result,
                "formula": formula,
                "description": description,
                "variables": variables,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during custom formula evaluation: {str(e)}",
                details={
                    "formula": params_dict.get("formula"),
                    "variables": params_dict.get("variables"),
                },
            )

    def _conformity_index(self, params: Any) -> Dict[str, Any]:
        """
        Calculates a conformity index comparing observed values to reference values.

        Args:
            params: Parameters with:
                - observed: Observed values (array or single value)
                - reference: Reference values (array or single value)
                - tolerance: Tolerance percentage (default: 10)
                - method: Comparison method (absolute, relative, percentage)

        Returns:
            Conformity index and classification
        """
        try:
            # Convert params to dict
            params_dict = (
                params.model_dump() if hasattr(params, "model_dump") else dict(params)
            )

            # Get observed and reference values
            observed = params_dict["observed"]
            reference = params_dict["reference"]

            # Convert to numpy arrays if they're not already
            if not isinstance(observed, (list, np.ndarray)):
                observed = np.array([float(observed)])
            else:
                observed = np.array(observed, dtype=float)

            if not isinstance(reference, (list, np.ndarray)):
                reference = np.array([float(reference)])
            else:
                reference = np.array(reference, dtype=float)

            # Check dimensions
            if observed.shape != reference.shape:
                raise DataTransformError(
                    "Observed and reference values must have the same dimensions",
                    details={
                        "observed_shape": observed.shape,
                        "reference_shape": reference.shape,
                    },
                )

            # Get tolerance and method
            tolerance = float(params_dict.get("tolerance", 10.0))  # Default 10%
            method = params_dict.get("method", "relative")

            # Calculate differences based on method
            if method == "absolute":
                differences = observed - reference
                max_allowed_diff = tolerance
                conformity = np.abs(differences) <= max_allowed_diff

            elif method == "relative":
                # Avoid division by zero
                with np.errstate(divide="ignore", invalid="ignore"):
                    relative_diff = np.where(
                        reference != 0, (observed - reference) / reference * 100, np.inf
                    )
                    relative_diff = np.where(
                        np.isfinite(relative_diff), relative_diff, 0
                    )

                differences = relative_diff
                max_allowed_diff = tolerance
                conformity = np.abs(differences) <= max_allowed_diff

            elif method == "percentage":
                # Calculate percentage of reference
                with np.errstate(divide="ignore", invalid="ignore"):
                    percentage = np.where(
                        reference != 0, observed / reference * 100, np.inf
                    )
                    percentage = np.where(np.isfinite(percentage), percentage, 0)

                differences = percentage - 100
                max_allowed_diff = tolerance
                conformity = np.abs(differences) <= max_allowed_diff

            else:
                raise DataTransformError(
                    f"Unknown method: {method}",
                    details={"valid_methods": ["absolute", "relative", "percentage"]},
                )

            # Calculate overall conformity
            conformity_count = np.sum(conformity)
            total_count = len(conformity)
            conformity_percentage = (
                (conformity_count / total_count * 100) if total_count > 0 else 0
            )

            # Determine conformity class
            if conformity_percentage >= 90:
                conformity_class = "Excellent"
            elif conformity_percentage >= 75:
                conformity_class = "Good"
            elif conformity_percentage >= 50:
                conformity_class = "Moderate"
            elif conformity_percentage >= 25:
                conformity_class = "Poor"
            else:
                conformity_class = "Very poor"

            return {
                "value": float(conformity_percentage),
                "class": conformity_class,
                "conforming_count": int(conformity_count),
                "total_count": int(total_count),
                "differences": differences.tolist(),
                "method": method,
                "tolerance": tolerance,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during conformity index calculation: {str(e)}",
                details={"params": params},
            )
