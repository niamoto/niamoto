"""Unified widget candidate models for collection add-widget flows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from niamoto.core.collections.widget_proposal_models import (
    ApplyabilityStatus,
    CandidateOrigin,
    ProposalStatus,
    WidgetProposal,
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
    source_status: ProposalStatus | None = None


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
    proposal_status: ProposalStatus | None = None
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
    proposal: WidgetProposal | None = None


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


def candidate_from_proposal(proposal: WidgetProposal) -> WidgetCandidate:
    """Project a transformation-first proposal into the unified candidate contract."""

    status = _candidate_status(proposal)
    widget_plugin = proposal.primary_fit.widget if proposal.primary_fit else None
    recipe_summary = {
        "transformer": _plugin_summary(proposal.recipe.get("transformer")),
        "widget": _plugin_summary(proposal.recipe.get("widget")),
    }
    recommendation = None
    if proposal.status == "recommended":
        recommendation = WidgetCandidateRecommendation(
            reason=proposal.primary_fit.reason
            if proposal.primary_fit
            else proposal.candidate.intent,
            score=proposal.primary_fit.score if proposal.primary_fit else None,
            source_status=proposal.status,
        )
    elif proposal.status == "already_configured":
        recommendation = WidgetCandidateRecommendation(
            reason="This candidate is already configured for the collection.",
            score=proposal.primary_fit.score if proposal.primary_fit else None,
            source_status=proposal.status,
        )

    return WidgetCandidate(
        id=proposal.id,
        collection=proposal.collection,
        title=proposal.title,
        subtitle=proposal.candidate.intent,
        origin=proposal.candidate.origin,
        category=_candidate_category(proposal),
        status=status,
        proposal_status=proposal.status,
        applyability=proposal.applyability,
        default_selected=(
            proposal.status == "recommended" and proposal.applyability == "applicable"
        ),
        recommendation=recommendation,
        source_fields=list(proposal.candidate.field_names),
        source_name=proposal.candidate.source_name,
        transformer_plugin=proposal.candidate.transformer_plugin,
        widget_plugin=widget_plugin,
        detail=WidgetCandidateDetail(
            shape=proposal.shape.model_dump(),
            warnings=[warning.model_dump() for warning in proposal.warnings],
            skip_reasons=[
                skip_reason.model_dump() for skip_reason in proposal.skip_reasons
            ],
            score=proposal.score.model_dump(),
            provenance=proposal.candidate.provenance.model_dump()
            if proposal.candidate.provenance
            else {},
            recipe_summary=recipe_summary,
        ),
        recipe_summary=recipe_summary,
        fingerprint=proposal.fingerprint,
        proposal=proposal,
    )


def _candidate_status(proposal: WidgetProposal) -> WidgetCandidateStatus:
    if proposal.status == "recommended":
        return "recommended"
    if proposal.status == "warning":
        return "needs_review"
    if proposal.status == "review_only":
        return "needs_review"
    if proposal.status == "missing_chart":
        return "missing_chart"
    if proposal.status == "skipped":
        return "skipped"
    return "configured"


def _candidate_category(proposal: WidgetProposal) -> WidgetCandidateCategory:
    if proposal.primary_fit and proposal.primary_fit.widget in {
        "hierarchical_nav_widget",
        "info_grid",
    }:
        return "structure"

    shape_kind = proposal.shape.kind
    if shape_kind == "map_layer":
        return "map"
    if shape_kind in {"scalar_metric", "metric_group"}:
        return "metric"
    if shape_kind in {
        "category_distribution",
        "category_ranking",
        "binned_numeric_distribution",
        "boolean_split",
        "time_series",
        "numeric_pair",
    }:
        return "chart"
    if shape_kind == "table":
        return "table"
    return "unsupported"


def _plugin_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "plugin": value.get("plugin"),
        "params": value.get("params") or {},
    }
