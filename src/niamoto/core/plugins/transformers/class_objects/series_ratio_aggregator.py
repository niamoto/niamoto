"""
Plugin for calculating ratios between series of distributions.
Handles cases where we need to compare a subset distribution against a total distribution,
such as forest elevation distribution vs total land elevation distribution.
"""

from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import pandas as pd
import numpy as np

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.imports.registry import EntityRegistry
from niamoto.common.exceptions import DataTransformError


class DistributionConfig(BaseModel):
    """Configuration for a distribution ratio calculation"""

    total: str  # Field name to match in class_object for total distribution
    subset: str  # Field name to match in class_object for subset distribution
    complement_mode: str = (
        "ratio"  # Mode for complement calculation: "ratio" or "difference"
    )


class SeriesRatioParams(BasePluginParams):
    """Parameters for series ratio aggregator plugin"""

    model_config = ConfigDict(
        json_schema_extra={
            "description": "Calculate ratios between series of distributions",
            "examples": [
                {
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
            ],
        }
    )

    source: str = Field(
        default="shape_stats",
        description="Source table containing class_object data",
        json_schema_extra={
            "ui:widget": "select",
            "ui:options": ["raw_shape_stats", "shape_stats"],
        },
    )

    distributions: Dict[str, DistributionConfig] = Field(
        default_factory=dict,
        description="Mapping of distribution names to total/subset field pairs",
        json_schema_extra={"ui:widget": "json"},
    )

    numeric_class_name: bool = Field(
        default=True,
        description="Whether to convert class names to numeric",
        json_schema_extra={"ui:widget": "checkbox"},
    )

    @field_validator("distributions")
    @classmethod
    def validate_distributions(
        cls, v: Dict[str, DistributionConfig]
    ) -> Dict[str, DistributionConfig]:
        """Validate distributions configuration."""
        if not v:
            raise ValueError("At least one distribution must be specified")
        return v


class ClassObjectSeriesRatioConfig(PluginConfig):
    """Configuration for series ratio aggregator plugin"""

    plugin: Literal["class_object_series_ratio_aggregator"] = (
        "class_object_series_ratio_aggregator"
    )
    params: SeriesRatioParams


@register("class_object_series_ratio_aggregator", PluginType.TRANSFORMER)
class ClassObjectSeriesRatioAggregator(TransformerPlugin):
    """Plugin for calculating ratios between series distributions"""

    config_model = ClassObjectSeriesRatioConfig

    def __init__(self, db, registry=None):
        """Initialize with database and optional EntityRegistry.

        Args:
            db: Database instance
            registry: EntityRegistry instance (created if not provided)
        """
        super().__init__(db)
        self.registry = registry or EntityRegistry(db)

    def _resolve_table_name(self, logical_name: str) -> str:
        """Resolve logical entity name to physical table name via EntityRegistry.

        Args:
            logical_name: Entity name from config (e.g., "shape_stats", "occurrences")

        Returns:
            Physical table name (e.g., "entity_shape_stats", "entity_occurrences")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> ClassObjectSeriesRatioConfig:
        """Validate plugin configuration and return typed config."""
        try:
            validated_config = self.config_model(**config)
            # Check for specific validation that tests expect
            if not validated_config.params.distributions:
                raise DataTransformError(
                    "At least one distribution must be specified",
                    details={"config": config},
                )
            return validated_config
        except DataTransformError:
            raise
        except Exception as e:
            raise DataTransformError(
                f"Invalid configuration: {str(e)}", details={"config": config}
            )

    def transform(
        self, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Dict[str, Dict[str, List]]:
        """Compute ratios between subset and total series stored as class objects.

        The configuration describes the distributions to compare; each entry identifies
        the ``class_object`` representing the total population and the subset to be
        contrasted. Optionally the class names can be coerced to numeric values before
        aggregation.

        Returns
        -------
        dict
            A mapping from distribution name to the combined series information.
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
            distributions = params.distributions
            numeric_class_name = params.numeric_class_name

            result = {}

            # Process each distribution
            for dist_name, dist_config in distributions.items():
                # Get distribution configuration
                dist = dist_config

                # Get total and subset data
                total_data_raw = data[data["class_object"] == dist.total].copy()
                subset_data_raw = data[data["class_object"] == dist.subset].copy()

                if len(total_data_raw) == 0:
                    raise DataTransformError(
                        f"No data found for total field {dist.total}",
                        details={
                            "available_class_objects": data["class_object"]
                            .unique()
                            .tolist(),
                        },
                    )

                if len(subset_data_raw) == 0:
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
                        total_data_raw.loc[:, "class_name"] = pd.to_numeric(
                            total_data_raw["class_name"]
                        )
                        subset_data_raw.loc[:, "class_name"] = pd.to_numeric(
                            subset_data_raw["class_name"]
                        )
                    except Exception as e:
                        raise DataTransformError(
                            "Failed to convert class names to numeric",
                            details={"error": str(e)},
                        )

                # Get all unique classes from both datasets
                all_classes = sorted(
                    pd.unique(
                        np.concatenate(
                            (
                                total_data_raw["class_name"].unique(),
                                subset_data_raw["class_name"].unique(),
                            )
                        )
                    )
                )

                # Set class_name as index for alignment
                total_data = total_data_raw.set_index("class_name")["class_value"]
                subset_data = subset_data_raw.set_index("class_name")["class_value"]

                # Reindex both series to the full set of classes, fill missing with 0
                total_data = total_data.reindex(all_classes, fill_value=0)
                subset_data = subset_data.reindex(all_classes, fill_value=0)

                # Calculate complement values based on mode
                complement_mode = dist.complement_mode
                if complement_mode == "difference":
                    complement_values = (
                        (total_data - subset_data).astype(float).tolist()
                    )
                else:  # ratio mode
                    complement_values = []
                    # Use aligned data for calculation
                    for total, subset in zip(total_data, subset_data):
                        total = float(total)
                        subset = float(subset)
                        # Avoid division by zero
                        if total > 0:
                            ratio = subset / total
                            # Ensure ratio is not greater than 1 (can happen with float inaccuracies or bad data)
                            complement_values.append(max(0.0, 1.0 - ratio))
                        # If total is 0, complement depends on subset
                        elif subset > 0:
                            # If total is 0 but subset > 0, means the class is only in the subset.
                            # Test expects complement ratio of 1 in this case (implies subset/total ratio is 0).
                            complement_values.append(1.0)
                        else:
                            # If both total and subset are 0, complement ratio is 1 (or could be NaN)
                            complement_values.append(1.0)

                # Store results for this distribution using the complete class list
                result[dist_name] = {
                    "classes": all_classes,  # Use the complete sorted list
                    "subset": subset_data.astype(
                        float
                    ).tolist(),  # Use reindexed subset data
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
