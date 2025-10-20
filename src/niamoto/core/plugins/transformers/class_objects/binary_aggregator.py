"""
Plugin for handling binary/ternary class distributions from class_value format.
Specifically handles data where distributions are represented as binary choices
(e.g. forest/non-forest) or ternary choices.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import pandas as pd

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.common.exceptions import DataTransformError


class GroupConfig(BaseModel):
    """Configuration for a binary/ternary group"""

    label: str = Field(..., description="Label for this distribution group")
    field: str = Field(..., description="Field name to match in class_object column")
    classes: List[str] = Field(
        default=["forest", "non_forest"], description="List of output class names"
    )
    class_mapping: Optional[Dict[str, str]] = Field(
        default=None, description="Mapping from input class names to output class names"
    )


class ClassObjectBinaryParams(BasePluginParams):
    """Parameters for binary class aggregator plugin"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Handle binary/ternary class distributions from class_value format",
            "examples": [
                {
                    "source": "raw_shape_stats",
                    "groups": [
                        {
                            "label": "emprise",
                            "field": "cover_forest",
                            "classes": ["forest", "non_forest"],
                            "class_mapping": {
                                "Forêt": "forest",
                                "Hors-forêt": "non_forest",
                            },
                        }
                    ],
                }
            ],
        }
    )

    source: str = Field(
        default="",
        description="Source table containing class_object data",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["raw_shape_stats", "shape_stats"],
        },
    )

    groups: List[GroupConfig] = Field(
        default_factory=list,
        min_length=1,
        description="List of group configurations for binary/ternary distributions",
        json_schema_extra={"ui:widget": "json"},
    )

    @field_validator("groups")
    @classmethod
    def validate_groups(cls, v: List[GroupConfig]) -> List[GroupConfig]:
        """Validate group configurations."""
        if not v:
            raise ValueError("At least one group must be specified")

        # Check for duplicate labels
        labels = [g.label for g in v]
        if len(labels) != len(set(labels)):
            raise ValueError("Group labels must be unique")

        return v


class ClassObjectBinaryConfig(PluginConfig):
    """Configuration for binary class aggregator plugin"""

    plugin: Literal["class_object_binary_aggregator"] = "class_object_binary_aggregator"
    params: ClassObjectBinaryParams


@register("class_object_binary_aggregator", PluginType.TRANSFORMER)
class ClassObjectBinaryAggregator(TransformerPlugin):
    """Plugin for handling binary/ternary class distributions"""

    config_model = ClassObjectBinaryConfig

    def validate_config(self, config: Dict[str, Any]) -> ClassObjectBinaryConfig:
        """Validate plugin configuration and return typed config."""
        try:
            # Check specific items that tests expect
            params = config.get("params", {})

            # Check for source
            if not params.get("source"):
                raise DataTransformError(
                    "source must be specified", details={"config": config}
                )

            # Check for groups
            if not params.get("groups"):
                raise DataTransformError(
                    "At least one group must be specified", details={"config": config}
                )

            # Check each group for required fields
            for i, group in enumerate(params.get("groups", [])):
                if "label" not in group:
                    raise DataTransformError(
                        "Group must specify 'label'",
                        details={"config": config, "group_index": i},
                    )
                if "field" not in group:
                    raise DataTransformError(
                        "Group must specify 'field'",
                        details={"config": config, "group_index": i},
                    )

            return self.config_model(**config)
        except DataTransformError:
            raise
        except Exception as e:
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate class-object statistics into binary or ternary distributions.

        Parameters
        ----------
        data:
            Long-format DataFrame containing ``class_object``, ``class_name`` and
            ``class_value`` columns.
        config:
            Raw configuration mapping produced by the transformer service.

        Returns
        -------
        dict[str, dict[str, float]]
            Normalized values for each configured group.
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
            for group in params.groups:
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
