"""
Plugin for extracting multiple series along a common axis from shape statistics.
Handles data where multiple series (e.g. forest types) share a common axis (e.g. elevation).
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

    field: str  # Field containing axis values
    output_field: str  # Name of axis field in output
    numeric: bool = True  # Convert to numeric
    sort: bool = True  # Sort values


class ClassObjectSeriesByAxisConfig(PluginConfig):
    """Configuration for series by axis aggregator plugin"""

    plugin: str = "class_object_series_by_axis_aggregator"
    source: str = "raw_shape_stats"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "axis": {
                "field": "class_name",
                "output_field": "altitudes",
                "numeric": True,
                "sort": True,
            },
            "types": {
                "secondaire": "forest_secondary_elevation",
                "mature": "forest_mature_elevation",
                "coeur": "forest_core_elevation",
            },
        }
    )


@register("class_object_series_by_axis_aggregator", PluginType.TRANSFORMER)
class ClassObjectSeriesByAxisAggregator(TransformerPlugin):
    """Plugin for aggregating series by axis"""

    config_model = ClassObjectSeriesByAxisConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = super().validate_config(config)

        params = validated_config.params

        # Validate axis configuration
        axis_config = params.get("axis", {})
        if not isinstance(axis_config, dict):
            raise DataTransformError(
                "axis configuration must be a dictionary", details={"config": config}
            )

        if not axis_config.get("field"):
            raise DataTransformError(
                "axis.field must be specified", details={"config": config}
            )

        # Validate series configuration
        series = params.get("series", {})
        if not series:
            raise DataTransformError(
                "At least one series must be specified", details={"config": config}
            )

        # Validate each series configuration
        for series_name, series_config in series.items():
            if not isinstance(series_config, dict):
                raise DataTransformError(
                    f"Series {series_name} configuration must be a dictionary",
                    details={"config": series_config},
                )

            if "class_object" not in series_config:
                raise DataTransformError(
                    f"Series {series_name} must specify 'class_object'",
                    details={"config": series_config},
                )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, List]:
        """
        Extract multiple series along a common axis from shape statistics data.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.axis: Configuration for common axis:
                    - field: Field containing axis values
                    - output_field: Name for axis in output
                    - numeric: Convert to numeric
                    - sort: Sort values
                - params.types: Mapping of output names to data fields

        Returns:
            Dictionary with axis values and series data

        Example output:
            {
                "altitudes": [0, 200, 400, 600, 800],
                "secondaire": [10, 15, 20, 15, 10],
                "mature": [30, 40, 45, 40, 30],
                "coeur": [20, 25, 30, 25, 20]
            }
        """
        try:
            # Validate configuration
            validated_config = self.config_model(**config)
            params = validated_config.params

            # Get axis configuration
            axis_config = AxisConfig(**params["axis"])

            # Validate fields exist
            missing_fields = []
            if axis_config.field not in data.columns:
                missing_fields.append(axis_config.field)
            for field in params["types"].values():
                if field not in data.columns:
                    missing_fields.append(field)

            if missing_fields:
                raise DataTransformError(
                    "Missing required fields in data",
                    details={"missing_fields": missing_fields},
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
            results = {axis_config.output_field: axis_values.tolist()}

            # Process each series
            for output_name, field in params["types"].items():
                # Initialize series values
                series_values = []

                # Get value for each axis point
                for axis_val in axis_values:
                    mask = data[axis_config.field] == axis_val
                    value = data.loc[mask, field].sum()
                    series_values.append(float(value))

                results[output_name] = series_values

            return results

        except Exception as e:
            raise DataTransformError(
                "Failed to aggregate series by axis",
                details={"error": str(e), "config": config},
            )
