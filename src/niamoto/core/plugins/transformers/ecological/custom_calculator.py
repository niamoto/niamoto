"""
Plugin for performing custom calculations on data from other transformers.
Allows mathematical operations, ecological indices calculations and advanced statistical transformations.
"""

from typing import Dict, Any
from pydantic import Field, field_validator
import pandas as pd
import numpy as np
from enum import Enum

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
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


class CustomCalculatorConfig(PluginConfig):
    """Configuration for the custom calculator plugin"""

    plugin: str = "custom_calculator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "operation": "weighted_sum",  # Type of operation to perform
            # Specific parameters for the operation
        }
    )

    @field_validator("params")
    def validate_params(cls, v):
        """Validates the parameters according to the operation."""
        if "operation" not in v:
            raise ValueError("The 'operation' parameter is required")

        try:
            operation = Operation(v["operation"])
        except ValueError:
            valid_operations = ", ".join([op.value for op in Operation])
            raise ValueError(
                f"Unsupported operation: {v['operation']}. "
                f"Valid operations: {valid_operations}"
            )

        # Specific validation according to the operation
        if operation == Operation.ARRAY_DIVISION:
            if "numerator" not in v:
                raise ValueError(
                    "The 'numerator' parameter is required for array_division"
                )
            if "denominator" not in v:
                raise ValueError(
                    "The 'denominator' parameter is required for array_division"
                )

        elif operation == Operation.WEIGHTED_SUM:
            if "values" not in v:
                raise ValueError("The 'values' parameter is required for weighted_sum")
            if not isinstance(v["values"], list):
                raise ValueError("The 'values' parameter must be a list")

        elif operation == Operation.SHANNON_ENTROPY:
            if "probabilities" not in v:
                raise ValueError(
                    "The 'probabilities' parameter is required for shannon_entropy"
                )

        elif operation == Operation.PIELOU_EVENNESS:
            if "shannon_entropy" not in v:
                raise ValueError(
                    "The 'shannon_entropy' parameter is required for pielou_evenness"
                )
            if "max_bins" not in v:
                raise ValueError(
                    "The 'max_bins' parameter is required for pielou_evenness"
                )

        # And so on for the other operations...

        return v


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

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates the plugin configuration."""
        try:
            return self.config_model(**config)
        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

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
            operation = Operation(params["operation"])

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

    def _array_multiplication(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the arrays
            array1 = np.array(params["array1"], dtype=float)
            array2 = np.array(params["array2"], dtype=float)

            # Check the dimensions
            if array1.size != array2.size and array2.size != 1:
                raise DataTransformError(
                    "The arrays must have the same size, or the second array must be a scalar",
                    details={"array1_size": array1.size, "array2_size": array2.size},
                )

            # Apply a scale factor if specified
            scale_factor = params.get("scale_factor", 1.0)

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

    def _normalize_array(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the array
            input_array = np.array(params["input"], dtype=float)

            # Normalization method
            method = params.get("method", "minmax")

            if method == "minmax":
                # Min-max normalization
                min_value = params.get("min_value", input_array.min())
                max_value = params.get("max_value", input_array.max())

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

    def _weighted_sum(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the values and weights
            values_config = params["values"]

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
            normalization = params.get("normalization")
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

    def _shannon_entropy(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the probabilities
            probabilities = np.array(params["probabilities"], dtype=float)

            # Normalize if specified or if the sum is not 1
            normalize = params.get("normalize", True)
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

    def _pielou_evenness(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the entropy and the number of classes
            shannon_entropy = float(params["shannon_entropy"])
            max_bins = int(params["max_bins"])

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

    def _sum_array_slice(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the array
            array = np.array(params["array"], dtype=float)

            # Indices of the slice
            start_index = int(params["start_index"])
            end_index = int(params.get("end_index", len(array)))

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
            total_mode = params.get("total", "sum")

            if total_mode == "sum":
                total = np.sum(array)
            elif total_mode == "len":
                total = len(array)
            elif total_mode == "value":
                total = float(params.get("total_value", np.sum(array)))
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

    def _ratio_calculation(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the values
            numerator = float(params["numerator"])
            denominator = float(params["denominator"])

            # Apply a scale factor if specified
            scale_factor = float(params.get("scale_factor", 1.0))

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
            # Get the functional traits
            wood_density = float(params["wood_density"])
            leaf_thickness = float(params["leaf_thickness"])
            leaf_sla = float(params["leaf_sla"])
            substrate = params.get("substrate", "NUM")  # UM or NUM by default

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

    def _resilience_score(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Get the CSR values
            csr_values = params["csr_values"]
            if not isinstance(csr_values, dict):
                raise DataTransformError(
                    "The 'csr_values' parameter must be a dictionary",
                    details={"csr_values": csr_values},
                )

            c_value = float(csr_values.get("competitive", 0))
            s_value = float(csr_values.get("stress_tolerant", 0))
            r_value = float(csr_values.get("ruderal", 0))

            # Functional diversity (e.g. Shannon)
            functional_diversity = float(params["functional_diversity"])

            # Substrate type
            substrate_type = params.get("substrate_type", "NUM")

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

            # Get the time series
            time_series = params["time_series"]

            # Detection threshold
            threshold = params.get("threshold", 0.0)

            # Minimum duration of an active period
            min_duration = params.get("min_duration", 1)

            # Month labels
            labels = params.get("labels", [str(i) for i in range(1, 13)])

            # Results
            results = {}

            # Process each series
            for series_name, series_data in time_series.items():
                array = np.array(series_data, dtype=float)

                # Detect active periods
                active_periods = []
                start = None
                for i in range(len(array)):
                    if array[i] > threshold and start is None:
                        start = i
                    elif array[i] <= threshold and start is not None:
                        if i - start >= min_duration:
                            active_periods.append((start, i - 1))
                        start = None
                if start is not None and len(array) - start >= min_duration:
                    active_periods.append((start, len(array) - 1))

                # Format active periods with labels
                formatted_periods = []
                for start, end in active_periods:
                    formatted_periods.append(
                        {
                            "start": labels[start],
                            "end": labels[end],
                            "start_index": start,
                            "end_index": end,
                            "duration": end - start + 1,
                        }
                    )

                results[series_name] = formatted_periods

            return {
                "periods": results,
                "threshold": threshold,
                "min_duration": min_duration,
            }

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                f"Error during active period detection: {str(e)}",
                details={"params": params},
            )
