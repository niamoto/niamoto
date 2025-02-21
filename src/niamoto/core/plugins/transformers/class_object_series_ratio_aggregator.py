"""
Plugin for calculating ratios between series of distributions.
Handles cases where we need to compare a subset distribution against a total distribution,
such as forest elevation distribution vs total land elevation distribution.
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
from niamoto.common.exceptions import DataTransformError


class DistributionConfig(BaseModel):
    """Configuration for a distribution ratio calculation"""

    total: str  # Field name to match in class_object for total distribution
    subset: str  # Field name to match in class_object for subset distribution
    complement_mode: str = (
        "ratio"  # Mode for complement calculation: "ratio" or "difference"
    )


class ClassObjectSeriesRatioConfig(PluginConfig):
    """Configuration for series ratio aggregator plugin"""

    plugin: str = "class_object_series_ratio_aggregator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "shape_stats",
            "distributions": {
                "elevation": {
                    "total": "land_elevation",
                    "subset": "forest_elevation",
                    "complement_mode": "difference",
                }
            },
            "numeric_class_name": True,
        }
    )


@register("class_object_series_ratio_aggregator", PluginType.TRANSFORMER)
class ClassObjectSeriesRatioAggregator(TransformerPlugin):
    """Plugin for calculating ratios between series distributions"""

    config_model = ClassObjectSeriesRatioConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        # Validate distributions configuration
        distributions = validated_config.params.get("distributions", {})
        if not distributions:
            raise DataTransformError(
                "At least one distribution must be specified",
                details={"config": config},
            )

        # Validate each distribution has total and subset fields
        for dist_name, dist_config in distributions.items():
            if not isinstance(dist_config, dict):
                raise DataTransformError(
                    f"Distribution {dist_name} configuration must be a dictionary",
                    details={"config": dist_config},
                )

            if "total" not in dist_config or "subset" not in dist_config:
                raise DataTransformError(
                    f"Distribution {dist_name} must specify both 'total' and 'subset' fields",
                    details={"config": dist_config},
                )

            # Validate complement_mode if specified
            complement_mode = dist_config.get("complement_mode", "ratio")
            if complement_mode not in ["ratio", "difference"]:
                raise DataTransformError(
                    f"Invalid complement_mode '{complement_mode}' for distribution {dist_name}. Must be 'ratio' or 'difference'",
                    details={"config": dist_config},
                )

        return validated_config

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, Dict[str, List]]:
        """
        Transform shape statistics data into ratio distributions.

        Args:
            data: DataFrame containing shape statistics in long format with columns:
                - class_object: The type of data (e.g. land_elevation)
                - class_name: The class name (e.g. elevation values)
                - class_value: The value for this class
            config: Configuration dictionary with:
                - params.distributions: Mapping of distribution names to total/subset field pairs
                - params.numeric_class_name: Whether to convert class names to numeric

        Returns:
            Dictionary with distribution ratios for each configured distribution

        Example output:
            {
                "elevation": {
                    "classes": [0, 200, 400, 600, 800],
                    "subset": [0.1, 0.2, 0.3, 0.2, 0.1],
                    "complement": [0.1, 0.2, 0.3, 0.2, 0.1]
                }
            }
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

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

            # Get distributions configuration
            distributions = params["distributions"]
            numeric_class_name = params.get("numeric_class_name", True)

            result = {}

            # Process each distribution
            for dist_name, dist_config in distributions.items():
                # Validate distribution configuration
                dist = DistributionConfig(**dist_config)

                # Get total and subset data
                total_data = data[data["class_object"] == dist.total].copy()
                subset_data = data[data["class_object"] == dist.subset].copy()

                if len(total_data) == 0:
                    raise DataTransformError(
                        f"No data found for total field {dist.total}",
                        details={
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist(),
                        },
                    )

                if len(subset_data) == 0:
                    raise DataTransformError(
                        f"No data found for subset field {dist.subset}",
                        details={
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist(),
                        },
                    )

                # Convert class names to numeric if requested
                if numeric_class_name:
                    try:
                        total_data.loc[:, "class_name"] = pd.to_numeric(
                            total_data["class_name"]
                        )
                        subset_data.loc[:, "class_name"] = pd.to_numeric(
                            subset_data["class_name"]
                        )
                    except Exception as e:
                        raise DataTransformError(
                            "Failed to convert class names to numeric",
                            details={"error": str(e)},
                        )

                # Sort by class name
                total_data = total_data.sort_values("class_name").reset_index(drop=True)
                subset_data = subset_data.sort_values("class_name").reset_index(
                    drop=True
                )

                # Calculate complement values based on mode
                complement_mode = dist.complement_mode
                if complement_mode == "difference":
                    complement_values = (
                        (total_data["class_value"] - subset_data["class_value"])
                        .astype(float)
                        .tolist()
                    )
                else:  # ratio mode
                    complement_values = []
                    for total, subset in zip(
                        total_data["class_value"], subset_data["class_value"]
                    ):
                        total = float(total)
                        subset = float(subset)
                        if total > 0:
                            ratio = subset / total
                            complement_values.append(1 - ratio)
                        else:
                            complement_values.append(0)

                # Store results for this distribution
                result[dist_name] = {
                    "classes": total_data["class_name"].tolist(),
                    "subset": subset_data["class_value"].astype(float).tolist(),
                    "complement": complement_values,
                }

            return result

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to calculate distribution ratios",
                details={"error": str(e), "config": config},
            )
