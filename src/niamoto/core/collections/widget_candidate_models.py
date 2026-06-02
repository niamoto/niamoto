"""Unified widget candidate models for collection add-widget flows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from niamoto.core.collections.widget_proposal_models import (
    ApplyabilityStatus,
    CandidateOrigin,
)

WidgetCandidateStatus = Literal[
    "recommended",
    "available",
    "needs_review",
    "missing_chart",
    "skipped",
    "configured",
]
WidgetCandidateCategory = Literal[
    "structure",
    "map",
    "metric",
    "chart",
    "table",
    "unsupported",
]


class WidgetCandidateRecommendation(BaseModel):
    """Recommendation metadata kept separate from candidate status."""

    reason: str
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class WidgetCandidateDetail(BaseModel):
    """Inspectable technical detail for a candidate."""

    shape: dict[str, Any] = Field(default_factory=dict)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    skip_reasons: list[dict[str, Any]] = Field(default_factory=list)
    score: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    recipe_summary: dict[str, Any] = Field(default_factory=dict)


class WidgetCandidate(BaseModel):
    """A user-facing widget candidate for a collection."""

    id: str
    collection: str
    title: str
    subtitle: str | None = None
    origin: CandidateOrigin
    category: WidgetCandidateCategory
    status: WidgetCandidateStatus
    applyability: ApplyabilityStatus
    default_selected: bool = False
    recommendation: WidgetCandidateRecommendation | None = None
    source_fields: list[str] = Field(default_factory=list)
    source_name: str | None = None
    transformer_plugin: str | None = None
    widget_plugin: str | None = None
    preview_descriptor: dict[str, Any] | None = None
    detail: WidgetCandidateDetail = Field(default_factory=WidgetCandidateDetail)
    recipe_summary: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str | None = None


class WidgetCandidateGroups(BaseModel):
    """Collection-scoped widget candidates grouped for the unified picker."""

    collection: str
    recommended: list[WidgetCandidate] = Field(default_factory=list)
    available: list[WidgetCandidate] = Field(default_factory=list)
    needs_review: list[WidgetCandidate] = Field(default_factory=list)
    missing_chart: list[WidgetCandidate] = Field(default_factory=list)
    skipped: list[WidgetCandidate] = Field(default_factory=list)
    configured: list[WidgetCandidate] = Field(default_factory=list)
    partial: bool = False
    messages: list[str] = Field(default_factory=list)

    def all_candidates(self) -> list[WidgetCandidate]:
        """Return every candidate in display order."""

        return [
            *self.recommended,
            *self.available,
            *self.needs_review,
            *self.missing_chart,
            *self.skipped,
            *self.configured,
        ]
