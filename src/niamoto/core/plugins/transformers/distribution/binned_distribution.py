"""
Plugin for creating distributions based on specified bins.
"""

from typing import Dict, Any, List, Optional
from pydantic import field_validator, Field, ValidationInfo

import pandas as pd
import numpy as np

from niamoto.core.plugins.models import PluginConfig, BasePluginParams
from niamoto.core.plugins.base import (
    TransformerPlugin,
    PluginType,
    register,
)
from niamoto.core.imports.registry import EntityRegistry


class BinnedDistributionParams(BasePluginParams):
    """Typed parameters for binned distribution plugin."""

    source: str = Field(
        default="occurrences",
        description="Data source entity name",
        json_schema_extra={
            "ui:widget": "entity-select",
            # No filter - allow all entities (datasets + references)
        },
    )

    field: str = Field(
        ...,
        description="Name of the numeric field to bin",
        json_schema_extra={
            "examples": ["elevation", "height", "dbh", "temperature"],
            "ui_component": "field_selector",
        },
    )

    bins: List[float] = Field(
        ...,
        description="List of bin edges in ascending order (at least 2 values)",
        min_length=2,
        json_schema_extra={
            "examples": [[0, 100, 200, 500, 1000], [0, 10, 50, 100]],
            "ui_component": "array_number",
            "ui_help": "Enter bin edges in ascending order. Example: [0, 100, 200, 500] creates 3 bins: 0-100, 100-200, 200-500",
        },
    )

    labels: Optional[List[str]] = Field(
        default=None,
        description="Optional labels for bins (must be len(bins)-1 if provided)",
        json_schema_extra={
            "examples": [["Low", "Medium", "High"], ["0-100m", "100-200m", "200m+"]],
            "ui_component": "array_text",
            "ui_help": "Optional: provide labels for each bin. Number of labels must equal number of bins minus 1.",
        },
    )

    include_percentages: bool = Field(
        default=False,
        description="Whether to include percentage calculations in the output",
        json_schema_extra={"ui_component": "checkbox"},
    )

    @field_validator("bins")
    @classmethod
    def validate_bins_ascending(cls, v: List[float]) -> List[float]:
        """Validate that bins are in strictly ascending order."""
        if len(v) < 2:
            raise ValueError("bins must have at least 2 values")

        for i in range(1, len(v)):
            if v[i] <= v[i - 1]:
                raise ValueError(
                    f"bins must be in strictly ascending order: {v[i - 1]} >= {v[i]} at positions {i - 1}, {i}"
                )

        return v

    @field_validator("labels")
    @classmethod
    def validate_labels_length(
        cls, v: Optional[List[str]], info: ValidationInfo
    ) -> Optional[List[str]]:
        """Validate that labels length matches bins-1 if provided."""
        if v is not None and "bins" in info.data:
            expected_length = len(info.data["bins"]) - 1
            if len(v) != expected_length:
                raise ValueError(
                    f"number of labels ({len(v)}) must equal number of bins minus 1 ({expected_length})"
                )
        return v


class BinnedDistributionConfig(PluginConfig):
    """Configuration for binned distribution plugin"""

    plugin: str = "binned_distribution"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "",
            "field": "",
            "bins": [],
            "labels": None,
            "include_percentages": False,
        },
        description="Parameters for binned distribution calculation",
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate params using the typed model."""
        # Convert to typed model for validation
        BinnedDistributionParams(**v)
        return v


@register("binned_distribution", PluginType.TRANSFORMER)
class BinnedDistribution(TransformerPlugin):
    """Plugin for creating binned distributions"""

    config_model = BinnedDistributionConfig

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
            logical_name: Entity name from config (e.g., "occurrences", "plots")

        Returns:
            Physical table name (e.g., "entity_occurrences", "entity_plots")
            Falls back to logical_name if not found in registry (backward compatibility)
        """
        try:
            metadata = self.registry.get(logical_name)
            return metadata.table_name
        except Exception:
            # Fallback: assume it's already a physical table name
            return logical_name

    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration."""
        try:
            # Validate using both the general config model and the typed params
            validated_config = self.config_model(**config)
            # Additional validation with typed params model
            BinnedDistributionParams(**validated_config.params)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")

    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        """Transform data according to configuration."""
        try:
            # Validate config and get typed parameters
            validated_config = self.config_model(**config)
            # Convert to typed params for easier access and type safety
            params = BinnedDistributionParams(**validated_config.params)

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
            field_data = data[params.field]

            # Remove any None or NaN values
            field_data = pd.to_numeric(field_data, errors="coerce").dropna()

            if field_data.empty:
                result = {
                    "bins": params.bins,
                    "counts": [0] * (len(params.bins) - 1),
                }
                if params.labels:
                    result["labels"] = params.labels
                return result

            # Calculate bin counts
            counts, _ = np.histogram(field_data, bins=params.bins)

            result = {
                "bins": params.bins,
                "counts": [int(x) for x in counts],
            }

            # Add labels if they exist
            if params.labels:
                result["labels"] = params.labels

            # Calculate percentages if requested
            if params.include_percentages:
                total = sum(counts)
                if total > 0:
                    percentages = [round((count / total) * 100, 2) for count in counts]
                else:
                    percentages = [0] * len(counts)
                result["percentages"] = percentages

            return result

        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}")
