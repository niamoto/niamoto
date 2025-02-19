# core/plugins/validation.py
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from pathlib import Path


class SourceType(str, Enum):
    """Types of data sources"""

    TAXONOMY = "taxonomy"
    OCCURRENCES = "occurrences"
    PLOTS = "plots"
    SHAPES = "shapes"
    RAW_DATA = "raw_data"


class SourceConfig(BaseModel):
    """Configuration for a data source"""

    main: str = Field(..., description="Main data source table")
    reference: Optional[Dict[str, Any]] = Field(
        None, description="Reference configuration"
    )


class LoaderConfig(BaseModel):
    """Configuration for data loaders"""

    plugin: str = Field(..., description="Loader plugin identifier")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Loader parameters"
    )


class PluginConfig(BaseModel):
    """Base configuration for all plugins"""

    plugin: str = Field(..., description="Plugin identifier")
    source: Optional[str] = Field(None, description="Data source for plugin")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Plugin parameters"
    )


class TransformerConfig(PluginConfig):
    """Configuration for transformer plugins"""

    field: Optional[str] = Field(None, description="Field to transform")
    output_field: Optional[str] = Field(None, description="Output field name")


class WidgetConfig(PluginConfig):
    """Configuration for widget plugins"""

    width: Optional[str] = Field(None, description="Widget width")
    height: Optional[str] = Field(None, description="Widget height")
    title: Optional[str] = Field(None, description="Widget title")
    description: Optional[str] = Field(None, description="Widget description")


class ExporterConfig(PluginConfig):
    """Configuration for exporter plugins"""

    output_path: Path = Field(..., description="Output path")
    template: Optional[str] = Field(None, description="Template path")

    @field_validator("output_path")
    def validate_output_path(cls, v):
        """Validate output path"""
        return v.resolve()


# Specific plugin configurations
class BinnedDistributionConfig(TransformerConfig):
    """Configuration for binned distribution transformer"""

    bins: List[float] = Field(..., description="Bin boundaries")
    labels: Optional[List[str]] = Field(None, description="Bin labels")

    @field_validator("bins")
    def validate_bins(cls, v):
        """Validate bins are ascending"""
        if not all(a < b for a, b in zip(v, v[1:])):
            raise ValueError("Bins must be in ascending order")
        return v


class NestedSetLoaderConfig(LoaderConfig):
    """Configuration for nested set loader"""

    fields: Dict[str, str] = Field(..., description="Hierarchy fields")

    @field_validator("fields")
    def validate_fields(cls, v):
        """Validate required fields are present"""
        required = {"left", "right"}
        if not all(f in v for f in required):
            raise ValueError(f"Missing required fields: {required - v.keys()}")
        return v


class StatisticalSummaryConfig(TransformerConfig):
    """Configuration for statistical summary transformer"""

    stats: List[Literal["min", "mean", "max"]] = Field(
        ..., description="Statistics to compute"
    )
    units: Optional[str] = Field(None, description="Units for values")
    max_value: Optional[float] = Field(None, description="Maximum value for scaling")


class GeospatialConfig(TransformerConfig):
    """Configuration for geospatial transformer"""

    geometry_field: str = Field(..., description="Field containing geometry")
    format: Literal["geojson", "wkt", "wkb"] = Field(
        "geojson", description="Output format"
    )


class GroupConfig(BaseModel):
    """Configuration for a group"""

    group_by: str = Field(..., description="Grouping field")
    source: SourceConfig
    loader: LoaderConfig
    widgets_data: Dict[str, WidgetConfig] = Field(
        ..., description="Widget configurations"
    )

    @field_validator("group_by")
    def validate_group_by(cls, v):
        """Validate group_by field"""
        valid_groups = {"taxon", "plot", "shape"}
        if v not in valid_groups:
            raise ValueError(f"Invalid group: {v}. Must be one of {valid_groups}")
        return v

    @model_validator
    def validate_source_loader_compatibility(cls, values):
        """Validate that source and loader configurations are compatible"""
        source = values.get("source")
        loader = values.get("loader")

        if not source or not loader:
            return values

        # Add compatibility checks here
        # Example:
        # if source.main == 'taxonomy' and loader.plugin != 'nested_set':
        #     raise ValueError("Taxonomy source requires nested_set loader")

        return values


# Helper functions
def validate_config(config: Dict[str, Any], config_class: type) -> Any:
    """
    Validate configuration using the specified Pydantic model.

    Args:
        config: Configuration dictionary
        config_class: Pydantic model class to use for validation

    Returns:
        Validated configuration object

    Raises:
        ValidationError: If configuration is invalid
    """
    return config_class(**config)


def validate_transform_config(config: Dict[str, Any]) -> List[GroupConfig]:
    """
    Validate complete transform.yml configuration.

    Args:
        config: Configuration loaded from transform.yml

    Returns:
        List of validated GroupConfig objects

    Raises:
        ValidationError: If configuration is invalid
    """
    return [GroupConfig(**group_config) for group_config in config]
