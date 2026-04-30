"""Typed models for reviewable Niamoto collections."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CollectionSourceType = Literal["reference", "dataset", "transform_group"]
CollectionRole = Literal["site", "api", "standard", "technical"]
CollectionReviewStatus = Literal["pending", "accepted", "deferred", "rejected"]


class CollectionEvidence(BaseModel):
    """Evidence explaining why a collection candidate exists."""

    kind: str
    message: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class CollectionCatalogEntry(BaseModel):
    """A reviewable collection candidate or explicit collection."""

    name: str
    label: str
    source_type: CollectionSourceType
    source_name: str
    grain: str = "unknown"
    roles: list[CollectionRole] = Field(default_factory=list)
    visible: bool = True
    review_status: CollectionReviewStatus = "pending"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    description: str | None = None
    evidence: list[CollectionEvidence] = Field(default_factory=list)


class CollectionSourceOption(BaseModel):
    """Source data option that can back a manual collection."""

    type: CollectionSourceType
    name: str
    label: str


class CollectionCatalog(BaseModel):
    """Catalog payload for GUI collection review."""

    collections: list[CollectionCatalogEntry]
    sources: list[CollectionSourceOption]
    total: int
