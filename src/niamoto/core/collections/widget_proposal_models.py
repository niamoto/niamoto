"""Models for transformation-first widget proposals."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

CandidateOrigin = Literal[
    "transformed_output",
    "transform_config",
    "export_config",
    "raw_field",
    "class_object",
    "combined_fields",
    "template_suggestion",
    "unknown",
]
FreshnessStatus = Literal["current", "stale", "unknown"]
ReconstructabilityStatus = Literal["full", "partial", "evidence_only", "unknown"]
TransformedShapeKind = Literal[
    "scalar_metric",
    "metric_group",
    "category_distribution",
    "category_ranking",
    "binned_numeric_distribution",
    "boolean_split",
    "time_series",
    "numeric_pair",
    "map_layer",
    "table",
    "unsupported",
]
ChartFitStatus = Literal["primary", "secondary", "warning", "suppressed"]
ProposalStatus = Literal[
    "recommended",
    "warning",
    "missing_chart",
    "skipped",
    "already_configured",
    "review_only",
]
ApplyabilityStatus = Literal[
    "applicable",
    "review_only",
    "not_applicable",
    "stale",
    "conflict",
]
WarningSeverity = Literal["info", "warning", "error"]


class ProposalWarning(BaseModel):
    """Warning attached to a proposal, candidate, or chart fit."""

    code: str
    message: str
    severity: WarningSeverity = "warning"
    details: dict[str, Any] = Field(default_factory=dict)


class ProposalSkipReason(BaseModel):
    """Reason explaining why a candidate was skipped or downgraded."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ProposalProvenance(BaseModel):
    """Evidence explaining where a candidate came from."""

    source: CandidateOrigin
    source_name: str | None = None
    source_path: str | None = None
    config_path: str | None = None
    recipe_key: str | None = None
    field_names: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class TransformedShape(BaseModel):
    """Renderer-oriented description of transformed data."""

    kind: TransformedShapeKind
    category_count: int | None = Field(default=None, ge=0)
    bin_count: int | None = Field(default=None, ge=0)
    point_count: int | None = Field(default=None, ge=0)
    series_count: int | None = Field(default=None, ge=0)
    metric_count: int | None = Field(default=None, ge=0)
    label_max_length: int | None = Field(default=None, ge=0)
    has_labels: bool = True
    columns: list[str] = Field(default_factory=list)
    value_field: str | None = None
    label_field: str | None = None
    count_field: str | None = None
    unit: str | None = None
    unsupported_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shape_contract(self) -> Self:
        """Reject shape descriptors that are too vague to score safely."""

        if self.kind in {"category_distribution", "category_ranking"}:
            if self.category_count is None:
                raise ValueError(f"{self.kind} requires category_count")

        if self.kind == "boolean_split" and self.category_count not in {None, 2}:
            raise ValueError("boolean_split category_count must be 2 when provided")

        if self.kind == "binned_numeric_distribution" and self.bin_count is None:
            raise ValueError("binned_numeric_distribution requires bin_count")

        if self.kind == "numeric_pair" and len(self.columns) < 2:
            raise ValueError("numeric_pair requires at least two columns")

        if self.kind == "metric_group" and self.metric_count == 0:
            raise ValueError("metric_group metric_count must be positive when provided")

        if self.kind == "unsupported" and not self.unsupported_reason:
            raise ValueError("unsupported shape requires unsupported_reason")

        return self


class ChartFitResult(BaseModel):
    """Fit result for one widget against a transformed shape."""

    widget: str
    status: ChartFitStatus
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    warnings: list[ProposalWarning] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    rank: int = Field(default=0, ge=0)


class MissingChartOpportunity(BaseModel):
    """Useful transformed shape with no readable widget yet."""

    shape: TransformedShape
    reason: str
    suggested_family: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProposalScore(BaseModel):
    """Inspectable score dimensions for a proposal."""

    dimensions: dict[str, float] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dimension_ranges(self) -> Self:
        for name, value in self.dimensions.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"score dimension '{name}' must be between 0 and 1")
        for name, value in self.weights.items():
            if value < 0.0:
                raise ValueError(f"score weight '{name}' must be positive")
        return self

    def weighted_total(self) -> float:
        """Return a deterministic weighted average for sorting."""

        if not self.dimensions:
            return 0.0

        total_weight = 0.0
        total = 0.0
        for name, value in sorted(self.dimensions.items()):
            weight = self.weights.get(name, 1.0)
            total += value * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0
        return total / total_weight


class TransformationCandidate(BaseModel):
    """A reusable data product that could back one or more widgets."""

    id: str
    collection: str
    origin: CandidateOrigin
    intent: str
    shape: TransformedShape
    source_name: str | None = None
    field_names: list[str] = Field(default_factory=list)
    transformer_plugin: str | None = None
    transformer_config: dict[str, Any] = Field(default_factory=dict)
    output_name: str | None = None
    provenance: ProposalProvenance | None = None
    freshness: FreshnessStatus = "unknown"
    reconstructability: ReconstructabilityStatus = "unknown"
    warnings: list[ProposalWarning] = Field(default_factory=list)
    skip_reasons: list[ProposalSkipReason] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WidgetProposal(BaseModel):
    """Reviewable widget proposal for a collection Blocks surface."""

    id: str
    collection: str
    title: str
    status: ProposalStatus
    candidate: TransformationCandidate
    shape: TransformedShape
    primary_fit: ChartFitResult | None = None
    alternatives: list[ChartFitResult] = Field(default_factory=list)
    suppressed_fits: list[ChartFitResult] = Field(default_factory=list)
    missing_chart: MissingChartOpportunity | None = None
    score: ProposalScore = Field(default_factory=ProposalScore)
    warnings: list[ProposalWarning] = Field(default_factory=list)
    skip_reasons: list[ProposalSkipReason] = Field(default_factory=list)
    applyability: ApplyabilityStatus = "review_only"
    fingerprint: str | None = None
    recipe: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_contract(self) -> Self:
        if self.status == "missing_chart" and self.missing_chart is None:
            raise ValueError("missing_chart proposals require missing_chart details")

        if self.status == "recommended" and self.primary_fit is None:
            raise ValueError("recommended proposals require a primary chart fit")

        if self.applyability == "applicable" and self.primary_fit is None:
            raise ValueError("applicable proposals require a primary chart fit")

        if (
            self.status in {"skipped", "missing_chart"}
            and self.applyability == "applicable"
        ):
            raise ValueError(f"{self.status} proposals cannot be directly applicable")

        return self


class WidgetProposalGroups(BaseModel):
    """Collection-scoped proposals grouped for review surfaces."""

    collection: str
    recommended: list[WidgetProposal] = Field(default_factory=list)
    warnings: list[WidgetProposal] = Field(default_factory=list)
    missing_chart: list[WidgetProposal] = Field(default_factory=list)
    skipped: list[WidgetProposal] = Field(default_factory=list)
    already_configured: list[WidgetProposal] = Field(default_factory=list)
    review_only: list[WidgetProposal] = Field(default_factory=list)
    partial: bool = False
    messages: list[str] = Field(default_factory=list)

    def all_proposals(self) -> list[WidgetProposal]:
        """Return every proposal in display order."""

        return [
            *self.recommended,
            *self.warnings,
            *self.review_only,
            *self.missing_chart,
            *self.already_configured,
            *self.skipped,
        ]
