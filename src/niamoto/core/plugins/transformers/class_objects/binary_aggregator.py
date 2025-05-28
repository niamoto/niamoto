"""
Plugin for handling binary/ternary class distributions from class_value format.
Specifically handles data where distributions are represented as binary choices
(e.g. forest/non-forest) or ternary choices.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class GroupConfig(BaseModel):
    """Configuration for a binary/ternary group"""

    label: str
    field: str
    classes: Optional[List[str]] = ["forest", "non_forest"]
    class_mapping: Optional[Dict[str, str]] = None


class ClassObjectBinaryConfig(PluginConfig):
    """Configuration for binary class aggregator plugin"""

    plugin: str = "class_object_binary_aggregator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "raw_shape_stats",
            "groups": [
                {
                    "label": "emprise",
                    "field": "cover_forest",
                    "classes": ["forest", "non_forest"],
                    "class_mapping": {"Forêt": "forest", "Hors-forêt": "non_forest"},
                },
                {
                    "label": "um",
                    "field": "cover_forestum",
                    "class_mapping": {"Forêt": "forest", "Hors-forêt": "non_forest"},
                },
                {
                    "label": "num",
                    "field": "cover_forestnum",
                    "class_mapping": {"Forêt": "forest", "Hors-forêt": "non_forest"},
                },
            ],
        }
    )


@register("class_object_binary_aggregator", PluginType.TRANSFORMER)
class ClassObjectBinaryAggregator(TransformerPlugin):
    """Plugin for handling binary/ternary class distributions"""

    config_model = ClassObjectBinaryConfig

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate plugin configuration."""
        validated_config = self.config_model(**config)
        params = validated_config.params

        # Validate that source is specified
        if "source" not in params:
            raise DataTransformError(
                "source must be specified",
                details={"config": config},
            )

        # Validate that at least one group is specified
        groups = params.get("groups", [])
        if not groups:
            raise DataTransformError(
                "At least one group must be specified",
                details={"config": config},
            )

        # Validate each group configuration
        for group in groups:
            if not isinstance(group, dict):
                raise DataTransformError(
                    "Group configuration must be a dictionary",
                    details={"config": group},
                )

            if "label" not in group:
                raise DataTransformError(
                    "Group must specify 'label'",
                    details={"config": group},
                )

            if "field" not in group:
                raise DataTransformError(
                    "Group must specify 'field'",
                    details={"config": group},
                )

        return validated_config

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform shape statistics data into binary/ternary distributions.

        Args:
            data: DataFrame containing shape statistics in long format with columns:
                - class_object: The type of data (e.g. cover_forest)
                - class_name: The class name (e.g. Forêt, Hors-forêt)
                - class_value: The value for this class
            config: Configuration dictionary with:
                - params.source: Source of the data
                - params.groups: List of group configurations with:
                    - label: Name of the distribution
                    - field: Field name to match in class_object
                    - classes: Optional list of class names (default: ["forest", "non_forest"])
                    - class_mapping: Optional dict mapping input class names to output class names

        Returns:
            Dictionary with distributions for each group

        Example output:
            {
                "emprise": {
                    "forest": 0.34,
                    "non_forest": 0.66
                },
                "um": {
                    "forest": 0.23,
                    "non_forest": 0.77
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

            # Initialize results
            results = {}

            # Process each group
            for group_config in params["groups"]:
                group = GroupConfig(**group_config)

                # Filter data for this field
                field_data = data[data["class_object"] == group.field]

                if len(field_data) == 0:
                    raise DataTransformError(
                        f"No data found for class_object {group.field}",
                        details={
                            "field": group.field,
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist(),
                        },
                    )

                # Get unique class names from data for this field
                unique_classes_in_field = field_data["class_name"].unique()

                # Use class mapping if provided, otherwise create a default one
                class_mapping = group.class_mapping or {
                    cls: cls for cls in unique_classes_in_field
                }

                # Validate that all classes in the data have a mapping
                missing_mappings = [
                    cls for cls in unique_classes_in_field if cls not in class_mapping
                ]
                if missing_mappings:
                    raise DataTransformError(
                        f"Missing class mapping for classes: {missing_mappings}",
                        details={
                            "field": group.field,
                            "missing_mappings": missing_mappings,
                            "provided_mappings": class_mapping,
                        },
                    )

                # Create distribution dictionary
                # Initialize distribution for all unique output classes from mapping
                output_classes = set(class_mapping.values())
                distribution = {out_cls: 0.0 for out_cls in output_classes}

                # Map classes and aggregate values
                for input_class in unique_classes_in_field:
                    output_class = class_mapping[input_class]
                    class_data = field_data[field_data["class_name"] == input_class]
                    if len(class_data) > 0:
                        distribution[output_class] += float(
                            class_data.iloc[0]["class_value"]
                        )

                results[group.label] = distribution

            return results

        except Exception as e:
            if isinstance(e, DataTransformError):
                raise e
            raise DataTransformError(
                "Failed to transform binary/ternary distributions",
                details={"error": str(e), "config": config},
            )
