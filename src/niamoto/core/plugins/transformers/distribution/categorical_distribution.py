"""
Plugin for creating categorical distributions.
"""

from typing import Dict, Any, List, Union
from pydantic import BaseModel, field_validator, Field, ValidationInfo

import pandas as pd

from niamoto.core.plugins.models import PluginConfig
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register


class CategoricalDistributionParams(BaseModel):
    """Parameters for categorical distribution plugin"""

    source: str = Field(
        ...,
        description="Data source table or view name",
        json_schema_extra={"ui:widget": "text", "ui:placeholder": "occurrences"},
    )
    field: str = Field(
        ...,
        description="Field name containing categorical data",
        json_schema_extra={"ui:widget": "text", "ui:placeholder": "category_field"},
    )
    categories: List[Union[int, float, str]] = Field(
        default_factory=list,
        description="List of category values to include in distribution",
        json_schema_extra={"ui:widget": "array", "ui:items": {"ui:widget": "text"}},
    )
    labels: List[str] = Field(
        default_factory=list,
        description="Optional labels for categories (must match categories length if provided)",
        json_schema_extra={"ui:widget": "array", "ui:items": {"ui:widget": "text"}},
    )
    include_percentages: bool = Field(
        default=False,
        description="Whether to include percentage values in output",
        json_schema_extra={"ui:widget": "checkbox"},
    )

    @field_validator("labels")
    @classmethod
    def validate_labels_length(cls, v: List[str], info: ValidationInfo) -> List[str]:
        """Validate that labels length matches categories length if both are provided."""
        if v:  # Only validate if labels are provided (non-empty list)
            categories = info.data.get("categories", [])
            if categories and len(v) != len(categories):
                raise ValueError(
                    f"number of labels ({len(v)}) must equal number of categories ({len(categories)})"
                )
        return v


class CategoricalDistributionConfig(PluginConfig):
    """Configuration for categorical distribution plugin"""

    plugin: str = "categorical_distribution"
    params: Dict[str, Any] = Field(
        default_factory=lambda: CategoricalDistributionParams(
            source="occurrences", field="category_field"
        ).model_dump(),
        description="Plugin parameters",
    )


@register("categorical_distribution", PluginType.TRANSFORMER)
class CategoricalDistribution(TransformerPlugin):
    """Plugin for creating categorical distributions"""

    config_model = CategoricalDistributionConfig

    def _validate_params(self, params: Dict[str, Any]) -> CategoricalDistributionParams:
        """Validate params as CategoricalDistributionParams."""
        try:
            return CategoricalDistributionParams(**params)
        except Exception as e:
            # Convert Pydantic errors to more readable messages for backward compatibility
            error_str = str(e)

            # Handle missing field errors (check more specifically)
            if "source\n  Field required" in error_str:
                raise ValueError("Missing required field: source")
            elif "field\n  Field required" in error_str:
                raise ValueError("Missing required field: field")

            # Handle type errors
            elif (
                "categories" in error_str
                and "Input should be a valid list" in error_str
            ):
                raise ValueError("categories must be a list")
            elif "labels" in error_str and "Input should be a valid list" in error_str:
                raise ValueError("labels must be a list")

            # Handle validation errors
            elif (
                "number of labels" in error_str
                and "must equal number of categories" in error_str
            ):
                raise ValueError(
                    "number of labels must be equal to number of categories"
                )

            # Default fallback
            raise ValueError(f"Invalid configuration: {str(e)}")

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            validated = self.config_model(**config)
            # Also validate the params specifically
            self._validate_params(validated.params)
            return validated.model_dump()
        except Exception as e:
            if "Invalid configuration:" not in str(e):
                raise ValueError(f"Invalid configuration: {str(e)}")
            raise

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data according to configuration."""
        try:
            validated_config = self.validate_config(config)
            params = self._validate_params(validated_config["params"])

            # Get source data if different from occurrences
            if params.source != "occurrences":
                result = self.db.execute_select(f"""
                    SELECT * FROM {params.source}
                """)
                data = pd.DataFrame(
                    result.fetchall(),
                    columns=[desc[0] for desc in result.cursor.description],
                )

            # Get field data
            if params.field is not None:
                field_data = data[params.field]
            else:
                field_data = data

            # Remove any None values
            field_data = field_data.dropna()

            categories = params.categories
            labels = params.labels
            include_percentages = params.include_percentages

            if field_data.empty:
                if not categories and labels:
                    categories = []
                elif not categories:
                    categories = []

                if not labels:
                    labels = [str(cat) for cat in categories]

                result = {
                    "categories": categories,
                    "counts": [0] * len(categories),
                    "labels": labels,
                }
                if include_percentages:
                    result["percentages"] = [0.0] * len(categories)
                return result

            if not categories:
                categories = sorted(field_data.unique())

            # Calculate counts for each category
            value_counts = field_data.value_counts()
            counts = [int(value_counts.get(cat, 0)) for cat in categories]

            result = {
                "categories": categories,
                "counts": counts,
                "labels": labels if labels else [str(cat) for cat in categories],
            }

            if include_percentages:
                total = sum(counts)
                if total > 0:
                    percentages = [round((count / total) * 100, 2) for count in counts]
                else:
                    percentages = [0.0] * len(counts)
                result["percentages"] = percentages

            return result

        except Exception as e:
            raise ValueError(f"Error transforming data: {str(e)}")
