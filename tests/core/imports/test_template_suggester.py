"""Tests for template suggestion orchestration."""

from __future__ import annotations

from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.imports.template_suggester import TemplateSuggester
from niamoto.core.imports.widget_generator import WidgetSuggestion


def make_profile(name: str = "dbh") -> EnrichedColumnProfile:
    return EnrichedColumnProfile(
        name=name,
        dtype="float64",
        semantic_type="measurement",
        unique_ratio=0.8,
        null_ratio=0.0,
        sample_values=[1.0, 2.0, 3.0],
        confidence=0.9,
        data_category=DataCategory.NUMERIC_CONTINUOUS,
        field_purpose=FieldPurpose.MEASUREMENT,
        cardinality=12,
        value_range=(0.0, 100.0),
    )


def make_widget_suggestion(
    *,
    suggestion_id: str,
    confidence: float,
    is_primary: bool,
    name: str,
    column: str = "dbh",
    alternatives: list[str] | None = None,
    widget_plugin: str = "bar_plot",
    widget_type: str = "distribution",
) -> WidgetSuggestion:
    return WidgetSuggestion(
        id=suggestion_id,
        name=name,
        description=f"Suggestion for {column}",
        transformer_plugin="binned_distribution",
        widget_plugin=widget_plugin,
        widget_type=widget_type,
        category="chart",
        icon="BarChart3",
        column=column,
        confidence=confidence,
        transformer_config={"source": "occurrences", "field": column},
        widget_params={"x_axis": "bin", "y_axis": "count"},
        source_name="occurrences",
        is_primary=is_primary,
        alternatives=alternatives or [],
    )


def test_suggest_for_entity_filters_low_confidence_and_sorts_results(monkeypatch):
    suggester = TemplateSuggester()
    widget_suggestions = [
        make_widget_suggestion(
            suggestion_id="dbh_secondary",
            confidence=0.9,
            is_primary=False,
            name="DBH Secondary",
        ),
        make_widget_suggestion(
            suggestion_id="dbh_primary",
            confidence=0.9,
            is_primary=True,
            name="DBH Primary",
        ),
        make_widget_suggestion(
            suggestion_id="dbh_low",
            confidence=0.39,
            is_primary=True,
            name="Filtered Out",
        ),
        make_widget_suggestion(
            suggestion_id="height_primary",
            confidence=0.65,
            is_primary=True,
            name="Height Primary",
            column="height",
        ),
    ]
    monkeypatch.setattr(
        suggester.generator,
        "generate_for_columns",
        lambda column_profiles, source_table: widget_suggestions,
    )

    suggestions = suggester.suggest_for_entity(
        [make_profile("dbh"), make_profile("height")],
        reference_name="plots",
        source_name="occurrences",
    )

    assert [suggestion.template_id for suggestion in suggestions] == [
        "dbh_primary",
        "dbh_secondary",
        "height_primary",
    ]
    assert suggestions[0].matched_column == "dbh"
    assert suggestions[0].match_reason == "Colonne 'dbh' (distribution)"
    assert suggestions[0].is_recommended is True


def test_suggest_for_entity_keeps_needed_alternatives_beyond_limit(monkeypatch):
    suggester = TemplateSuggester()
    widget_suggestions = [
        make_widget_suggestion(
            suggestion_id="dbh_histogram",
            confidence=0.95,
            is_primary=True,
            name="DBH Histogram",
            alternatives=["dbh_donut"],
        ),
        make_widget_suggestion(
            suggestion_id="species_bar",
            confidence=0.9,
            is_primary=True,
            name="Species Ranking",
            column="species",
        ),
        make_widget_suggestion(
            suggestion_id="dbh_donut",
            confidence=0.45,
            is_primary=False,
            name="DBH Donut",
        ),
    ]
    monkeypatch.setattr(
        suggester.generator,
        "generate_for_columns",
        lambda column_profiles, source_table: widget_suggestions,
    )

    suggestions = suggester.suggest_for_entity(
        [make_profile("dbh")],
        reference_name="plots",
        source_name="occurrences",
        max_suggestions=1,
    )

    assert [suggestion.template_id for suggestion in suggestions] == [
        "dbh_histogram",
        "dbh_donut",
    ]


def test_template_suggestion_to_dict_exposes_widget_metadata(monkeypatch):
    suggester = TemplateSuggester()
    monkeypatch.setattr(
        suggester.generator,
        "generate_for_columns",
        lambda column_profiles, source_table: [
            make_widget_suggestion(
                suggestion_id="dbh_histogram",
                confidence=0.876,
                is_primary=True,
                name="DBH Histogram",
            )
        ],
    )

    suggestion = suggester.suggest_for_entity(
        [make_profile("dbh")],
        reference_name="plots",
        source_name="occurrences",
    )[0]
    payload = suggestion.to_dict()

    assert payload["template_id"] == "dbh_histogram"
    assert payload["widget_plugin"] == "bar_plot"
    assert payload["widget_params"] == {"x_axis": "bin", "y_axis": "count"}
    assert payload["confidence"] == 0.88
    assert payload["config"] == {"source": "occurrences", "field": "dbh"}


def test_create_general_info_suggestion_builds_generic_reference_payload():
    suggestion = TemplateSuggester()._create_general_info_suggestion(
        reference_name="plots",
        source_name="occurrences",
    )

    assert suggestion.template_id == "general_info"
    assert suggestion.plugin == "field_aggregator"
    assert suggestion.source == "template"
    assert suggestion.matched_column == "plots"
    assert suggestion.config == {
        "fields": [
            {
                "source": "plots",
                "field": "name",
                "target": "name",
            },
            {
                "source": "occurrences",
                "field": "id",
                "target": "count",
                "transformation": "count",
            },
        ]
    }
