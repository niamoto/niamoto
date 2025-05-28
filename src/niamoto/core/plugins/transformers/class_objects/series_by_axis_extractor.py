"""
Plugin for extracting multiple series by axis from class objects.
Each series represents a different type (e.g. forest types) measured across a common axis (e.g. elevation).
"""

from typing import Dict, Any
from pydantic import BaseModel, Field
import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class AxisConfig(BaseModel):
    """Configuration for the axis"""

    field: str = Field(..., description="Field to use for axis values")
    output_field: str = Field(..., description="Name of the field in output")
    numeric: bool = Field(True, description="Convert values to numeric")
    sort: bool = Field(True, description="Sort axis values")


class ClassObjectSeriesByAxisConfig(PluginConfig):
    """Configuration for series by axis extractor plugin"""

    plugin: str = "class_object_series_by_axis_extractor"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "shape_stats",
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


@register("class_object_series_by_axis_extractor", PluginType.TRANSFORMER)
class ClassObjectSeriesByAxisExtractor(TransformerPlugin):
    """Plugin for extracting series by axis from class objects"""

    config_model = ClassObjectSeriesByAxisConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration"""
        validated_config = self.config_model(**config)

        # Validate that at least one type is specified
        types = validated_config.params.get("types", {})
        if not types:
            raise DataTransformError(
                "At least one type must be specified",
                details={"config": config},
            )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform shape statistics data into series by axis.

        Args:
            data: DataFrame containing shape statistics
            config: Configuration dictionary with:
                - params.axis: Configuration for axis
                - params.types: Mapping of output names to class_objects

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
            validated_config = self.validate_config(config)
            params = validated_config.params

            # Get axis configuration
            axis_config = AxisConfig(**params["axis"])

            # Initialize result with the configured output field name
            result = {axis_config.output_field: []}

            # Get first type to extract axis values
            first_type = next(iter(params["types"].values()))
            axis_data = data[data["class_object"] == first_type].copy()

            if axis_data.empty:
                raise DataTransformError(
                    f"No data found for class_object {first_type}",
                    details={
                        "available_class_objects": data["class_object"]
                        .unique()
                        .tolist()
                    },
                )

            # Convert and sort axis values if configured
            if axis_config.numeric:
                try:
                    axis_data.loc[:, axis_config.field] = pd.to_numeric(
                        axis_data[axis_config.field]
                    )
                except Exception as e:
                    raise DataTransformError(
                        "Failed to convert axis values to numeric",
                        details={"error": str(e)},
                    )

            if axis_config.sort:
                axis_data = axis_data.sort_values(axis_config.field)

            # Store axis values
            result[axis_config.output_field] = axis_data[axis_config.field].tolist()

            # Process each type
            for output_name, class_object in params["types"].items():
                # Get type data
                type_data = data[data["class_object"] == class_object].copy()

                if type_data.empty:
                    raise DataTransformError(
                        f"No data found for class_object {class_object}",
                        details={
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist()
                        },
                    )

                # Convert and sort values
                if axis_config.numeric:
                    type_data.loc[:, axis_config.field] = pd.to_numeric(
                        type_data[axis_config.field]
                    )
                if axis_config.sort:
                    type_data = type_data.sort_values(axis_config.field)

                # Store type values
                result[output_name] = type_data["class_value"].astype(float).tolist()

            return result

        except Exception as e:
            # If it's already a DataTransformError, re-raise it to preserve the specific message
            if isinstance(e, DataTransformError):
                raise e
            # Otherwise, wrap it in a generic DataTransformError
            raise DataTransformError(
                "Failed to extract series by axis",
                details={"error": str(e), "config": config},
            )
