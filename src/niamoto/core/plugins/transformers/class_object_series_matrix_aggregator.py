"""
Plugin for aggregating series of distributions by type from shape statistics.
Handles data where multiple distributions (e.g. forest/non-forest) are measured
across a common axis (e.g. elevation) for different types (e.g. UM/NUM).
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


class AxisConfig(BaseModel):
    """Configuration for the common axis"""

    field: str
    numeric: bool = True
    sort: bool = True


class TypeConfig(BaseModel):
    """Configuration for a distribution type"""

    class_object: str
    scale: float = 1.0


class DistributionConfig(BaseModel):
    """Configuration for a distribution group"""

    um: TypeConfig
    num: TypeConfig


class ClassObjectSeriesMatrixConfig(PluginConfig):
    """Configuration for series matrix aggregator plugin"""

    plugin: str = "class_object_series_matrix_aggregator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "raw_shape_stats",
            "axis": {"field": "class_name", "numeric": True, "sort": True},
            "distributions": {
                "forest": {
                    "um": {"class_object": "ratio_forest_um_elevation", "scale": 100},
                    "num": {"class_object": "ratio_forest_num_elevation", "scale": 100},
                }
            },
        }
    )


@register("class_object_series_matrix_aggregator", PluginType.TRANSFORMER)
class ClassObjectSeriesMatrixAggregator(TransformerPlugin):
    """Plugin for aggregating series matrix distributions"""

    config_model = ClassObjectSeriesMatrixConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        # Validate that at least one distribution is specified
        distributions = validated_config.params.get("distributions", {})
        if not distributions:
            raise DataTransformError(
                "At least one distribution must be specified",
                details={"config": config},
            )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, List]:
        """
        Transform shape statistics data into series of distributions.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.axis: Configuration for common axis
                - params.distributions: Configuration for distribution groups

        Returns:
            Dictionary with axis values and distribution series

        Example output:
            {
                "class_name": [0, 200, 400, 600, 800],  # Altitudes
                "forest_um": [20, 30, 40, 30, 20],      # % forêt UM
                "forest_num": [25, 35, 45, 35, 25],     # % forêt NUM
                "hors_foret_um": [80, 70, 60, 70, 80],  # % hors-forêt UM
                "hors_foret_num": [75, 65, 55, 65, 75]  # % hors-forêt NUM
            }
        """
        try:
            # Validate configuration
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get axis configuration
            axis_config = AxisConfig(**params["axis"])

            # Validate axis field exists
            if axis_config.field not in data.columns:
                raise DataTransformError(
                    f"Axis field {axis_config.field} not found in data",
                    details={"available_columns": list(data.columns)},
                )

            # Get unique axis values
            axis_values = data[axis_config.field].unique()

            # Convert to numeric if requested
            if axis_config.numeric:
                try:
                    axis_values = pd.to_numeric(axis_values)
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert axis values to numeric",
                        details={"error": str(e)},
                    )

            # Sort if requested
            if axis_config.sort:
                axis_values = np.sort(axis_values)

            # Initialize results with axis
            results = {"class_name": axis_values.tolist()}

            # Process each distribution group
            for group_name, group_config in params["distributions"].items():
                # Validate group configuration
                group = DistributionConfig(**group_config)

                # Process UM distribution
                um_config = group.um
                if um_config.class_object not in data.columns:
                    raise DataTransformError(
                        f"UM field {um_config.class_object} not found in data",
                        details={"available_columns": list(data.columns)},
                    )

                # Get UM values for each axis point
                um_values = []
                for axis_val in axis_values:
                    mask = data[axis_config.field] == axis_val
                    value = (
                        data.loc[mask, um_config.class_object].iloc[0]
                        if not data[mask].empty
                        else 0
                    )
                    um_values.append(float(value) * um_config.scale)

                results[f"{group_name}_um"] = um_values
                results[f"hors_{group_name}_um"] = [100 - val for val in um_values]

                # Process NUM distribution
                num_config = group.num
                if num_config.class_object not in data.columns:
                    raise DataTransformError(
                        f"NUM field {num_config.class_object} not found in data",
                        details={"available_columns": list(data.columns)},
                    )

                # Get NUM values for each axis point
                num_values = []
                for axis_val in axis_values:
                    mask = data[axis_config.field] == axis_val
                    value = (
                        data.loc[mask, num_config.class_object].iloc[0]
                        if not data[mask].empty
                        else 0
                    )
                    num_values.append(float(value) * num_config.scale)

                results[f"{group_name}_num"] = num_values
                results[f"hors_{group_name}_num"] = [100 - val for val in num_values]

            return results

        except Exception as e:
            raise DataTransformError(
                "Failed to aggregate series matrix",
                details={"error": str(e), "config": config},
            )
