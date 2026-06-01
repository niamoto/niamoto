"""Tests for unified widget candidate projections."""

from __future__ import annotations

from niamoto.core.collections.widget_candidate_models import candidate_from_proposal
from niamoto.core.collections.widget_proposal_models import (
    ChartFitResult,
    MissingChartOpportunity,
    TransformedShape,
    TransformationCandidate,
    WidgetProposal,
)


def _proposal(status="recommended", applyability="applicable") -> WidgetProposal:
    shape = TransformedShape(kind="category_distribution", category_count=3)
    candidate = TransformationCandidate(
        id="candidate-1",
        collection="taxons",
        origin="raw_field",
        source_name="occurrences",
        field_names=["substrate"],
        intent="Count records by substrate",
        shape=shape,
        transformer_plugin="categorical_distribution",
    )
    return WidgetProposal(
        id="substrate_bar_plot",
        collection="taxons",
        title="Substrate distribution",
        status=status,
        candidate=candidate,
        shape=shape,
        primary_fit=ChartFitResult(
            widget="bar_plot",
            status="primary",
            score=0.9,
            reason="Readable ranking",
        ),
        applyability=applyability,
        recipe={
            "transformer": {
                "plugin": "categorical_distribution",
                "params": {"field": "substrate"},
            },
            "widget": {"plugin": "bar_plot", "params": {"orientation": "h"}},
        },
    )


def test_recommended_applicable_proposal_is_selected_by_default():
    candidate = candidate_from_proposal(_proposal())

    assert candidate.status == "recommended"
    assert candidate.applyability == "applicable"
    assert candidate.default_selected is True
    assert candidate.widget_plugin == "bar_plot"
    assert candidate.recipe_summary["widget"]["plugin"] == "bar_plot"


def test_review_only_proposal_is_inspectable_but_not_selected():
    candidate = candidate_from_proposal(
        _proposal(status="review_only", applyability="review_only")
    )

    assert candidate.status == "needs_review"
    assert candidate.applyability == "review_only"
    assert candidate.default_selected is False


def test_already_configured_proposal_uses_configured_status():
    candidate = candidate_from_proposal(
        _proposal(status="already_configured", applyability="not_applicable")
    )

    assert candidate.status == "configured"
    assert candidate.applyability == "not_applicable"
    assert candidate.default_selected is False
    assert candidate.recommendation is not None


def test_missing_chart_candidate_is_not_applicable():
    shape = TransformedShape(
        kind="unsupported",
        unsupported_reason="Needs a matrix widget",
    )
    proposal = WidgetProposal(
        id="matrix_candidate",
        collection="taxons",
        title="Matrix candidate",
        status="missing_chart",
        candidate=TransformationCandidate(
            id="matrix_candidate",
            collection="taxons",
            origin="combined_fields",
            intent="Compare two fields",
            shape=shape,
        ),
        shape=shape,
        missing_chart=MissingChartOpportunity(
            shape=shape,
            reason="No existing widget supports this shape.",
        ),
        applyability="not_applicable",
    )

    candidate = candidate_from_proposal(proposal)

    assert candidate.status == "missing_chart"
    assert candidate.category == "unsupported"
    assert candidate.default_selected is False
