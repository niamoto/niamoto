"""Tests for class object widget suggestion logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from niamoto.core.imports.class_object_analyzer import (
    ClassObjectAnalysis,
    ClassObjectStats,
)
from niamoto.core.imports.class_object_suggester import ClassObjectWidgetSuggester


def make_class_object(
    *,
    name: str = "cover_forest",
    cardinality: int = 4,
    class_names: list[str] | None = None,
    value_type: str = "categorical",
    sample_values: list[float] | None = None,
    suggested_plugin: str | None = "series_extractor",
    confidence: float = 0.85,
) -> ClassObjectStats:
    return ClassObjectStats(
        name=name,
        cardinality=cardinality,
        class_names=["Dense", "Open"] if class_names is None else class_names,
        value_type=value_type,
        sample_values=sample_values
        if sample_values is not None
        else [45.0, 35.0, 20.0],
        suggested_plugin=suggested_plugin,
        confidence=confidence,
    )


def test_numeric_series_distribution_uses_bar_plot_with_distribution_config():
    suggester = ClassObjectWidgetSuggester()
    class_object = make_class_object(
        name="dbh_bins",
        cardinality=8,
        value_type="numeric",
        sample_values=[40.0, 30.0, 20.0, 10.0],
        suggested_plugin="class_object_series_extractor",
        confidence=0.88,
    )

    suggestion = suggester.suggest_for_class_object(
        class_object,
        source_name="plot_stats",
        reference_name="plots",
    )

    assert suggestion is not None
    assert suggestion.template_id == "dbh_bins_series_extractor_bar_plot"
    assert suggestion.widget_plugin == "bar_plot"
    assert suggestion.category == "chart"
    assert suggestion.icon == "bar-chart"
    assert suggestion.config["source"] == "plot_stats"
    assert suggestion.config["class_object"] == "dbh_bins"
    assert suggestion.widget_params == {
        "orientation": "v",
        "x_axis": "tops",
        "y_axis": "counts",
        "sort_order": "descending",
        "gradient_color": "#8B4513",
        "gradient_mode": "luminance",
        "show_legend": False,
        "labels": {"tops": "DBH_BINS", "counts": "%"},
    }
    suggestion_dict = suggestion.to_dict()
    assert suggestion_dict["is_recommended"] is True
    assert suggestion_dict["widget_plugin"] == "bar_plot"
    assert suggestion_dict["widget_params"] == suggestion.widget_params


def test_small_categorical_series_prefers_donut_chart():
    suggester = ClassObjectWidgetSuggester()
    class_object = make_class_object(
        name="top10_family",
        cardinality=3,
        class_names=["Araucariaceae", "Podocarpaceae", "Myrtaceae"],
        sample_values=[12.0, 9.0, 4.0],
        suggested_plugin="series_extractor",
    )

    suggestion = suggester.suggest_for_class_object(
        class_object,
        source_name="plot_stats",
        reference_name="plots",
    )

    assert suggestion is not None
    assert suggestion.widget_plugin == "donut_chart"
    assert suggestion.category == "donut"
    assert suggestion.icon == "pie-chart"
    assert suggestion.config["class_object"] == "top10_family"
    assert suggestion.widget_params == {
        "labels_field": "tops",
        "values_field": "counts",
        "show_legend": False,
    }


def test_binary_class_object_preserves_detected_labels_in_config():
    suggester = ClassObjectWidgetSuggester()
    class_object = make_class_object(
        name="fertility",
        cardinality=2,
        class_names=["Fertile", "Sterile"],
        suggested_plugin="binary_aggregator",
        confidence=0.79,
    )

    suggestion = suggester.suggest_for_class_object(
        class_object,
        source_name="plot_stats",
        reference_name="plots",
    )

    assert suggestion is not None
    assert suggestion.widget_plugin == "donut_chart"
    assert suggestion.config == {
        "source": "plot_stats",
        "groups": [
            {
                "label": "fertility",
                "field": "fertility",
                "classes": ["Fertile", "Sterile"],
                "class_mapping": {
                    "Fertile": "Fertile",
                    "Sterile": "Sterile",
                },
            }
        ],
    }
    assert suggestion.widget_params == {
        "subplots": [{"name": "Fertility", "data_key": "fertility"}],
        "show_legend": False,
    }
    assert suggestion.to_dict()["is_recommended"] is False


def test_field_aggregator_uses_safe_default_when_samples_are_missing():
    suggester = ClassObjectWidgetSuggester()
    class_object = make_class_object(
        name="species_count",
        cardinality=1,
        class_names=[],
        sample_values=[],
        suggested_plugin="field_aggregator",
    )
    assert class_object.class_names == []
    assert class_object.sample_values == []

    suggestion = suggester.suggest_for_class_object(
        class_object,
        source_name="plot_stats",
        reference_name="plots",
    )

    assert suggestion is not None
    assert suggestion.widget_plugin == "radial_gauge"
    assert suggestion.config == {
        "source": "plot_stats",
        "fields": [{"class_object": "species_count", "target": "species_count"}],
    }
    assert suggestion.widget_params == {
        "value_field": "species_count.value",
        "max_value": 100,
    }


def test_field_aggregator_uses_positive_sample_headroom_for_gauge():
    suggester = ClassObjectWidgetSuggester()
    class_object = make_class_object(
        name="species_count",
        cardinality=1,
        class_names=[],
        sample_values=[150.0],
        suggested_plugin="field_aggregator",
    )

    suggestion = suggester.suggest_for_class_object(
        class_object,
        source_name="plot_stats",
        reference_name="plots",
    )

    assert suggestion is not None
    assert suggestion.widget_plugin == "radial_gauge"
    assert suggestion.widget_params["max_value"] == 200
    assert suggestion.widget_params["max_value"] >= 150.0


def test_suggest_from_source_returns_sorted_suggestions(monkeypatch):
    analysis = ClassObjectAnalysis(
        path="imports/plot_stats.csv",
        delimiter=",",
        row_count=12,
        entity_column="plot_id",
        entity_count=4,
        columns=["plot_id", "class_object", "class_name", "class_value"],
        class_objects=[
            make_class_object(
                name="top10_family",
                cardinality=3,
                suggested_plugin="series_extractor",
                confidence=0.72,
            ),
            make_class_object(
                name="dbh_bins",
                cardinality=8,
                value_type="numeric",
                sample_values=[50.0, 25.0, 15.0, 10.0],
                suggested_plugin="class_object_series_extractor",
                confidence=0.91,
            ),
            make_class_object(
                name="unknown_metric",
                suggested_plugin=None,
                confidence=0.99,
            ),
        ],
        is_valid=True,
        validation_errors=[],
    )
    analyzer = Mock()
    analyzer.analyze.return_value = analysis
    monkeypatch.setattr(
        "niamoto.core.imports.class_object_suggester.ClassObjectAnalyzer",
        lambda csv_path: analyzer,
    )

    suggestions = ClassObjectWidgetSuggester().suggest_from_source(
        Path("imports/plot_stats.csv"),
        source_name="plot_stats",
        reference_name="plots",
    )

    assert [suggestion.class_object for suggestion in suggestions] == [
        "dbh_bins",
        "top10_family",
    ]


def test_suggest_from_source_returns_empty_for_invalid_analysis(monkeypatch):
    analysis = ClassObjectAnalysis(
        path="imports/plot_stats.csv",
        delimiter=",",
        row_count=0,
        entity_column=None,
        entity_count=0,
        columns=[],
        class_objects=[],
        is_valid=False,
        validation_errors=["missing columns"],
    )
    analyzer = Mock()
    analyzer.analyze.return_value = analysis
    monkeypatch.setattr(
        "niamoto.core.imports.class_object_suggester.ClassObjectAnalyzer",
        lambda csv_path: analyzer,
    )

    suggestions = ClassObjectWidgetSuggester().suggest_from_source(
        Path("imports/plot_stats.csv"),
        source_name="plot_stats",
        reference_name="plots",
    )

    assert suggestions == []
