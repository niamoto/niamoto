"""Tests for chart-fit readability rules."""

from __future__ import annotations

from niamoto.core.collections.chart_fit import evaluate_chart_fit
from niamoto.core.collections.widget_proposal_models import TransformedShape


def _widgets(results):
    return [fit.widget for fit in results]


def test_low_cardinality_categorical_distribution_gets_readable_primary_and_alternatives():
    shape = TransformedShape(
        kind="category_distribution",
        category_count=4,
        label_max_length=12,
        has_labels=True,
    )

    result = evaluate_chart_fit(shape)

    assert result.primary is not None
    assert result.primary.widget == "bar_plot"
    assert "donut_chart" in _widgets(result.alternatives)
    assert not result.missing_chart


def test_high_cardinality_categorical_distribution_suppresses_donut():
    shape = TransformedShape(
        kind="category_distribution",
        category_count=42,
        label_max_length=18,
        has_labels=True,
    )

    result = evaluate_chart_fit(shape)

    assert result.primary is not None
    assert result.primary.widget == "bar_plot"
    assert "donut_chart" in _widgets(result.suppressed)
    assert all(fit.widget != "donut_chart" for fit in result.alternatives)


def test_numeric_binned_distribution_prefers_bar_chart_not_donut():
    shape = TransformedShape(kind="binned_numeric_distribution", bin_count=8)

    result = evaluate_chart_fit(shape)

    assert result.primary is not None
    assert result.primary.widget == "bar_plot"
    assert result.primary.params["x_axis"] == "bin"
    assert result.primary.params["y_axis"] == "count"
    assert "donut_chart" in _widgets(result.suppressed)


def test_numeric_pair_maps_to_scatter_plot():
    shape = TransformedShape(kind="numeric_pair", columns=["height_m", "dbh_cm"])

    result = evaluate_chart_fit(shape)

    assert result.primary is not None
    assert result.primary.widget == "scatter_plot"
    assert result.primary.params == {"x_axis": "height_m", "y_axis": "dbh_cm"}


def test_boolean_split_prefers_donut_over_secondary_bar():
    shape = TransformedShape(kind="boolean_split", category_count=2)

    result = evaluate_chart_fit(shape)

    assert result.primary is not None
    assert result.primary.widget == "donut_chart"
    assert any(fit.widget == "bar_plot" for fit in result.alternatives)


def test_missing_labels_add_warning_without_blocking_fit():
    shape = TransformedShape(
        kind="category_distribution",
        category_count=5,
        has_labels=False,
    )

    result = evaluate_chart_fit(shape)

    assert result.primary is not None
    assert result.primary.widget == "bar_plot"
    assert any(warning.code == "missing_labels" for warning in result.warnings)


def test_unsupported_shape_returns_missing_chart_opportunity():
    shape = TransformedShape(
        kind="unsupported",
        unsupported_reason="Needs a calendar heatmap",
    )

    result = evaluate_chart_fit(shape)

    assert result.primary is None
    assert result.missing_chart is not None
    assert "calendar heatmap" in result.missing_chart.reason
