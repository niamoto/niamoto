"""Tests for transformation-first widget proposal models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from niamoto.core.collections.widget_proposal_models import (
    ChartFitResult,
    MissingChartOpportunity,
    ProposalScore,
    ProposalWarning,
    TransformedShape,
    TransformationCandidate,
    WidgetProposal,
)


def test_category_shape_requires_cardinality():
    with pytest.raises(ValidationError):
        TransformedShape(kind="category_distribution")


def test_numeric_pair_shape_requires_two_columns():
    with pytest.raises(ValidationError):
        TransformedShape(kind="numeric_pair", columns=["height_m"])


def test_unsupported_shape_requires_reason():
    with pytest.raises(ValidationError):
        TransformedShape(kind="unsupported")


def test_score_rejects_dimension_outside_confidence_range():
    with pytest.raises(ValidationError):
        ProposalScore(dimensions={"utility": 1.3})


def test_proposal_requires_missing_chart_record_for_missing_chart_status():
    shape = TransformedShape(
        kind="unsupported",
        unsupported_reason="Needs a matrix heatmap widget",
    )
    candidate = TransformationCandidate(
        id="candidate-1",
        collection="taxons",
        origin="combined_fields",
        intent="Compare two categorical axes",
        shape=shape,
    )

    with pytest.raises(ValidationError):
        WidgetProposal(
            id="proposal-1",
            collection="taxons",
            title="Relationship matrix",
            status="missing_chart",
            candidate=candidate,
            shape=shape,
            score=ProposalScore(dimensions={"utility": 0.8}),
        )


def test_review_only_proposal_can_explain_warning_and_non_applyability():
    shape = TransformedShape(
        kind="category_distribution",
        category_count=18,
        has_labels=False,
    )
    candidate = TransformationCandidate(
        id="candidate-2",
        collection="taxons",
        origin="raw_field",
        source_name="occurrences",
        field_names=["substrate"],
        intent="Count records by substrate",
        shape=shape,
        reconstructability="partial",
    )
    proposal = WidgetProposal(
        id="proposal-2",
        collection="taxons",
        title="Substrate distribution",
        status="warning",
        candidate=candidate,
        shape=shape,
        primary_fit=ChartFitResult(
            widget="bar_plot",
            status="warning",
            score=0.65,
            reason="Readable, but labels need review",
            warnings=[
                ProposalWarning(
                    code="missing_labels",
                    message="Labels are not available in the source evidence",
                )
            ],
        ),
        score=ProposalScore(dimensions={"utility": 0.7, "chart_fit": 0.65}),
        applyability="review_only",
    )

    assert proposal.status == "warning"
    assert proposal.applyability == "review_only"
    assert proposal.primary_fit is not None
    assert proposal.primary_fit.warnings[0].code == "missing_labels"


def test_missing_chart_proposal_is_valid_when_opportunity_is_attached():
    shape = TransformedShape(
        kind="unsupported",
        unsupported_reason="Needs a calendar heatmap",
    )
    candidate = TransformationCandidate(
        id="candidate-3",
        collection="taxons",
        origin="combined_fields",
        intent="Compare activity by month and category",
        shape=shape,
    )
    proposal = WidgetProposal(
        id="proposal-3",
        collection="taxons",
        title="Seasonal matrix",
        status="missing_chart",
        candidate=candidate,
        shape=shape,
        missing_chart=MissingChartOpportunity(
            shape=shape,
            reason="No existing widget supports a two-axis categorical heatmap",
            suggested_family="heatmap",
        ),
        score=ProposalScore(dimensions={"utility": 0.9}),
        applyability="not_applicable",
    )

    assert proposal.missing_chart is not None
    assert proposal.missing_chart.suggested_family == "heatmap"
