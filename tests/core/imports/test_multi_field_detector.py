"""Tests for multi-field widget pattern detection."""

from __future__ import annotations

from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.imports.multi_field_detector import (
    MultiFieldPattern,
    MultiFieldPatternDetector,
    MultiFieldPatternType,
)


def make_profile(
    *,
    name: str,
    data_category: DataCategory,
    field_purpose: FieldPurpose,
    dtype: str = "object",
    semantic_type: str | None = None,
    sample_values: list[object] | None = None,
    cardinality: int = 12,
) -> EnrichedColumnProfile:
    return EnrichedColumnProfile(
        name=name,
        dtype=dtype,
        semantic_type=semantic_type,
        unique_ratio=0.4,
        null_ratio=0.0,
        sample_values=sample_values or [],
        confidence=0.9,
        data_category=data_category,
        field_purpose=field_purpose,
        cardinality=cardinality,
        value_range=(0.0, 100.0)
        if data_category
        in (DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE)
        else None,
    )


def test_selection_requires_at_least_two_profiles():
    detector = MultiFieldPatternDetector()
    single_profile = make_profile(
        name="flower",
        data_category=DataCategory.BOOLEAN,
        field_purpose=FieldPurpose.CLASSIFICATION,
        dtype="bool",
        sample_values=[True, False],
    )

    assert detector.suggest_for_selection([single_profile]) == []


def test_selection_detects_phenology_and_marks_it_recommended():
    detector = MultiFieldPatternDetector()
    profiles = [
        make_profile(
            name="month_obs",
            data_category=DataCategory.TEMPORAL,
            field_purpose=FieldPurpose.METADATA,
            dtype="int64",
            sample_values=[1, 2, 3],
        ),
        make_profile(
            name="flower",
            data_category=DataCategory.BOOLEAN,
            field_purpose=FieldPurpose.CLASSIFICATION,
            dtype="bool",
            sample_values=[True, False],
        ),
        make_profile(
            name="fruit",
            data_category=DataCategory.BOOLEAN,
            field_purpose=FieldPurpose.CLASSIFICATION,
            dtype="bool",
            sample_values=[True, False],
        ),
    ]

    suggestions = detector.suggest_for_selection(profiles, source_name="occurrences")

    assert suggestions
    assert suggestions[0].pattern_type is MultiFieldPatternType.PHENOLOGY
    assert suggestions[0].is_recommended is True
    assert suggestions[0].transformer_plugin == "time_series_analysis"
    assert suggestions[0].transformer_params["time_field"] == "month_obs"
    assert suggestions[0].fields == ["month_obs", "flower", "fruit"]
    assert set(suggestions[0].widget_params["color_discrete_map"]) == {
        "flower",
        "fruit",
    }
    assert any(
        suggestion.pattern_type is MultiFieldPatternType.BOOLEAN_COMPARISON
        for suggestion in suggestions
    )


def test_trait_detection_falls_back_to_other_numeric_measurements():
    detector = MultiFieldPatternDetector()
    profiles = [
        make_profile(
            name="leaf_area",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
            sample_values=[12.5, 14.3],
        ),
        make_profile(
            name="stem_density",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
            sample_values=[0.5, 0.6],
        ),
    ]

    suggestions = detector.suggest_for_selection(profiles, source_name="traits")
    trait_pattern = next(
        suggestion
        for suggestion in suggestions
        if suggestion.pattern_type is MultiFieldPatternType.TRAIT_COMPARISON
    )

    assert trait_pattern.transformer_plugin == "field_aggregator"
    assert trait_pattern.fields == ["leaf_area", "stem_density"]
    assert trait_pattern.widget_plugin == "info_grid"


def test_detect_semantic_groups_finds_phenology_dimensions_and_traits():
    detector = MultiFieldPatternDetector()
    profiles = [
        make_profile(
            name="month_obs",
            data_category=DataCategory.TEMPORAL,
            field_purpose=FieldPurpose.METADATA,
        ),
        make_profile(
            name="flower",
            data_category=DataCategory.BOOLEAN,
            field_purpose=FieldPurpose.CLASSIFICATION,
        ),
        make_profile(
            name="fruit",
            data_category=DataCategory.BOOLEAN,
            field_purpose=FieldPurpose.CLASSIFICATION,
        ),
        make_profile(
            name="dbh",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
        ),
        make_profile(
            name="height",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
        ),
        make_profile(
            name="leaf_area",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
        ),
        make_profile(
            name="wood_density",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
        ),
    ]

    groups = detector.detect_semantic_groups(profiles)

    assert {group["group_name"] for group in groups} == {
        "phenology",
        "dimensions",
        "functional_traits",
    }


def test_detector_continues_when_one_pattern_detector_raises():
    detector = MultiFieldPatternDetector()

    def broken_detector(profiles, source_name):
        raise RuntimeError("boom")

    def working_detector(profiles, source_name):
        return MultiFieldPattern(
            pattern_type=MultiFieldPatternType.NUMERIC_CORRELATION,
            name="Corrélation",
            description="Corrélation entre deux mesures",
            fields=["dbh", "height"],
            field_roles={"dbh": "x_axis", "height": "y_axis"},
            confidence=0.7,
            transformer_plugin="scatter_analysis",
            transformer_params={"source": source_name},
            widget_plugin="scatter_plot",
            widget_params={"x_axis": "dbh", "y_axis": "height"},
        )

    detector.pattern_detectors = [broken_detector, working_detector]
    profiles = [
        make_profile(
            name="dbh",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
        ),
        make_profile(
            name="height",
            data_category=DataCategory.NUMERIC_CONTINUOUS,
            field_purpose=FieldPurpose.MEASUREMENT,
            dtype="float64",
        ),
    ]

    suggestions = detector.suggest_for_selection(profiles, source_name="occurrences")

    assert len(suggestions) == 1
    assert suggestions[0].pattern_type is MultiFieldPatternType.NUMERIC_CORRELATION
    assert suggestions[0].is_recommended is True
