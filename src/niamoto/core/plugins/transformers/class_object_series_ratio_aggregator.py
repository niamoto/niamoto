"""
Plugin for calculating ratios between series of distributions.
Handles cases where we need to compare a subset distribution against a total distribution,
such as forest elevation distribution vs total land elevation distribution.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
    PluginConfig,
)
from niamoto.common.exceptions import DataTransformError


class DistributionConfig(BaseModel):
    """Configuration for a distribution ratio calculation"""

    total: str  # Field containing total distribution
    subset: str  # Field containing subset distribution


class ClassObjectSeriesRatioConfig(PluginConfig):
    """Configuration for series ratio aggregator plugin"""

    plugin: str = "class_object_series_ratio_aggregator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "shape_stats",
            "distributions": {
                "elevation": {"total": "land_elevation", "subset": "forest_elevation"}
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

        return validated_config

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, Dict[str, List]]:
        """
        Transform shape statistics data into ratio distributions.

        Args:
            data: DataFrame containing shape statistics
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

            # Get distributions configuration
            distributions = params["distributions"]
            numeric_class_name = params.get("numeric_class_name", True)

            result = {}

            # Process each distribution
            for dist_name, dist_config in distributions.items():
                # Validate distribution configuration
                dist = DistributionConfig(**dist_config)

                # Validate fields exist
                if dist.total not in data.columns:
                    raise DataTransformError(
                        f"Total field {dist.total} not found in data",
                        details={"available_columns": list(data.columns)},
                    )

                if dist.subset not in data.columns:
                    raise DataTransformError(
                        f"Subset field {dist.subset} not found in data",
                        details={"available_columns": list(data.columns)},
                    )

                # Get class names (assuming they're in class_name column)
                classes = data["class_name"].unique()

                # Convert to numeric if requested
                if numeric_class_name:
                    try:
                        classes = pd.to_numeric(classes)
                        classes = np.sort(classes)
                    except Exception as e:
                        raise DataTransformError(
                            "Failed to convert class names to numeric",
                            details={"error": str(e)},
                        )

                # Initialize arrays for subset and total values
                subset_values = []
                complement_values = []

                # Calculate ratios for each class
                for class_val in classes:
                    mask = data["class_name"] == class_val

                    if not data[mask].empty:
                        total = float(data.loc[mask, dist.total].iloc[0])
                        subset = float(data.loc[mask, dist.subset].iloc[0])

                        if total > 0:
                            ratio = subset / total
                            subset_values.append(ratio)
                            complement_values.append(1 - ratio)
                        else:
                            subset_values.append(0)
                            complement_values.append(0)
                    else:
                        subset_values.append(0)
                        complement_values.append(0)

                # Store results for this distribution
                result[dist_name] = {
                    "classes": classes.tolist(),
                    "subset": subset_values,
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
