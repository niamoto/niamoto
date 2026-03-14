"""Pydantic models for the canonical transform.yml format."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class TransformRelationConfig(BaseModel):
    """Relation configuration linking a source to the grouping entity."""

    plugin: str
    key: str
    ref_key: Optional[str] = None
    ref_field: Optional[str] = None
    fields: Optional[Dict[str, str]] = None

    model_config = ConfigDict(extra="allow")


class TransformSourceConfig(BaseModel):
    """Source configuration for a transform group."""

    name: str
    data: str
    grouping: str
    relation: TransformRelationConfig

    model_config = ConfigDict(extra="allow")


class TransformWidgetConfig(BaseModel):
    """Single widget transformation entry."""

    plugin: str
    source: Optional[str] = None
    field: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class TransformGroupConfig(BaseModel):
    """Canonical transform group."""

    group_by: str
    sources: List[TransformSourceConfig] = Field(default_factory=list)
    widgets_data: Dict[str, TransformWidgetConfig] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


TransformConfigAdapter = TypeAdapter(List[TransformGroupConfig])


def validate_transform_config(data: Any) -> List[Dict[str, Any]]:
    """Validate and normalize transform.yml content to canonical list form."""
    groups = TransformConfigAdapter.validate_python(data)
    return [group.model_dump(exclude_none=True) for group in groups]
