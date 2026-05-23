"""Tests for collection widget proposal generation."""

from __future__ import annotations

from niamoto.core.collections.widget_proposal_service import WidgetProposalService
from niamoto.core.imports.class_object_analyzer import (
    ClassObjectCategory,
    ClassObjectStats,
)
from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)


def make_profile(
    name: str,
    category: DataCategory,
    *,
    cardinality: int = 0,
    null_ratio: float = 0.0,
    labels: list[str] | None = None,
    purpose: FieldPurpose = FieldPurpose.METADATA,
    suggested_bins: list[float] | None = None,
    value_range: tuple[float, float] | None = None,
) -> EnrichedColumnProfile:
    is_numeric = category.value.startswith("numeric")
    return EnrichedColumnProfile(
        name=name,
        dtype="float64" if is_numeric else "object",
        semantic_type=None,
        unique_ratio=0.2,
        null_ratio=null_ratio,
        sample_values=[],
        confidence=0.88,
        data_category=category,
        field_purpose=purpose,
        suggested_bins=suggested_bins
        if suggested_bins is not None
        else ([0, 10, 20] if is_numeric else None),
        suggested_labels=labels,
        cardinality=cardinality,
        value_range=value_range
        if value_range is not None
        else ((0.0, 20.0) if is_numeric else None),
    )


def test_raw_numeric_field_becomes_binned_distribution_proposal():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile(
                "dbh_cm",
                DataCategory.NUMERIC_CONTINUOUS,
                purpose=FieldPurpose.MEASUREMENT,
            )
        ],
    )

    proposal = result.all_proposals()[0]
    assert proposal.shape.kind == "binned_numeric_distribution"
    assert proposal.primary_fit is not None
    assert proposal.primary_fit.widget == "bar_plot"
    assert proposal.candidate.transformer_plugin == "binned_distribution"
    assert proposal.candidate.transformer_config["bins"] == [0.0, 10.0, 20.0]
    assert proposal.recipe["widget"]["params"]["x_axis"] == "bin"
    assert proposal.candidate.field_names == ["dbh_cm"]


def test_numeric_field_without_suggested_bins_uses_value_range_edges():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile(
                "height_m",
                DataCategory.NUMERIC_CONTINUOUS,
                purpose=FieldPurpose.MEASUREMENT,
                suggested_bins=[],
                value_range=(0.0, 50.0),
            )
        ],
    )

    proposal = result.recommended[0]
    assert proposal.candidate.transformer_config["bins"] == [
        0.0,
        10.0,
        20.0,
        30.0,
        40.0,
        50.0,
    ]


def test_numeric_identifier_is_skipped_before_histogram_generation():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile(
                "taxon_id",
                DataCategory.NUMERIC_DISCRETE,
                purpose=FieldPurpose.FOREIGN_KEY,
            )
        ],
    )

    proposal = result.skipped[0]
    assert proposal.candidate.transformer_plugin is None
    assert proposal.skip_reasons[0].code == "low_utility_identifier"


def test_boolean_raw_field_enables_percentages_for_donut_recipe():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile(
                "is_endemic",
                DataCategory.BOOLEAN,
                cardinality=2,
                purpose=FieldPurpose.CLASSIFICATION,
            )
        ],
    )

    proposal = result.recommended[0]
    assert proposal.candidate.transformer_plugin == "binary_counter"
    assert proposal.primary_fit is not None
    assert proposal.primary_fit.widget == "donut_chart"
    assert proposal.recipe["transformer"]["params"]["include_percentages"] is True


def test_high_cardinality_categorical_prefers_ranking_and_suppresses_donut():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile(
                "family",
                DataCategory.CATEGORICAL_HIGH_CARD,
                cardinality=80,
                labels=["A", "B"],
                purpose=FieldPurpose.CLASSIFICATION,
            )
        ],
    )

    proposal = result.all_proposals()[0]
    assert proposal.shape.kind == "category_ranking"
    assert proposal.primary_fit is not None
    assert proposal.primary_fit.widget == "bar_plot"
    assert proposal.candidate.transformer_plugin == "top_ranking"
    assert "donut_chart" in [fit.widget for fit in proposal.suppressed_fits]
    assert proposal.recipe["widget"]["params"]["x_axis"] == "counts"
    assert proposal.recipe["widget"]["params"]["y_axis"] == "tops"
    assert proposal.recipe["widget"]["params"]["orientation"] == "h"


def test_text_and_identifier_profiles_are_returned_as_skipped_candidates():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile("id", DataCategory.IDENTIFIER),
            make_profile("notes", DataCategory.TEXT),
        ],
    )

    assert not result.recommended
    assert [proposal.status for proposal in result.skipped] == ["skipped", "skipped"]
    assert {proposal.candidate.field_names[0] for proposal in result.skipped} == {
        "id",
        "notes",
    }


def test_class_object_scalar_metrics_are_grouped_into_info_grid_candidate():
    service = WidgetProposalService()
    class_objects = [
        ClassObjectStats(
            name=f"metric_{index}",
            cardinality=0,
            suggested_plugin="class_object_field_aggregator",
            confidence=0.9,
            category=ClassObjectCategory.SCALAR,
        )
        for index in range(5)
    ]

    result = service.generate_for_collection(
        collection="plots",
        source_name="plot_stats",
        profiles=[],
        class_objects=class_objects,
    )

    proposal = result.recommended[0]
    assert proposal.shape.kind == "metric_group"
    assert proposal.shape.metric_count == 5
    assert proposal.primary_fit is not None
    assert proposal.primary_fit.widget == "info_grid"
    assert proposal.recipe["widget"]["params"]["items"][0]["source"] == "metric_0.value"
    assert proposal.candidate.field_names == [
        "metric_0",
        "metric_1",
        "metric_2",
        "metric_3",
        "metric_4",
    ]


def test_class_object_binary_candidate_uses_valid_binary_recipe():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="plots",
        source_name="shape_stats",
        class_objects=[
            ClassObjectStats(
                name="cover_forest",
                cardinality=2,
                class_names=["Forest", "Outside"],
                suggested_plugin="class_object_binary_aggregator",
                confidence=0.95,
                category=ClassObjectCategory.BINARY,
                mapping_hints={"Forest": "forest", "Outside": "outside"},
            )
        ],
    )

    proposal = result.recommended[0]
    assert proposal.primary_fit is not None
    assert proposal.primary_fit.widget == "donut_chart"
    assert proposal.candidate.transformer_config["groups"][0]["field"] == "cover_forest"
    assert (
        proposal.recipe["widget"]["params"]["subplots"][0]["data_key"] == "cover_forest"
    )


def test_class_object_binary_auto_config_is_normalized_with_required_label():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="plots",
        source_name="shape_stats",
        class_objects=[
            ClassObjectStats(
                name="cover_forest",
                cardinality=2,
                class_names=["Forest", "Outside"],
                suggested_plugin="class_object_binary_aggregator",
                confidence=0.95,
                category=ClassObjectCategory.BINARY,
                auto_config={
                    "source": "shape_stats",
                    "groups": [
                        {
                            "field": "cover_forest",
                            "classes": ["forest", "outside"],
                            "class_mapping": {
                                "Forest": "forest",
                                "Outside": "outside",
                            },
                        }
                    ],
                },
            )
        ],
    )

    group_config = result.recommended[0].candidate.transformer_config["groups"][0]
    assert group_config["label"] == "cover_forest"
    assert group_config["field"] == "cover_forest"


def test_class_object_large_category_ranking_uses_horizontal_count_axis():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="plots",
        source_name="shape_stats",
        class_objects=[
            ClassObjectStats(
                name="dominant_species",
                cardinality=24,
                class_names=["species_a", "species_b"],
                suggested_plugin="class_object_series_extractor",
                confidence=0.85,
                category=ClassObjectCategory.LARGE_CATEGORY,
            )
        ],
    )

    proposal = result.recommended[0]
    assert proposal.shape.kind == "category_ranking"
    assert proposal.recipe["widget"]["params"]["x_axis"] == "counts"
    assert proposal.recipe["widget"]["params"]["y_axis"] == "tops"
    assert proposal.recipe["widget"]["params"]["orientation"] == "h"


def test_duplicate_candidates_keep_distinct_recipe_intents():
    service = WidgetProposalService()

    result = service.generate_for_collection(
        collection="taxons",
        source_name="occurrences",
        profiles=[
            make_profile(
                "family",
                DataCategory.CATEGORICAL,
                cardinality=5,
                purpose=FieldPurpose.CLASSIFICATION,
            ),
            make_profile(
                "life_form",
                DataCategory.CATEGORICAL,
                cardinality=5,
                purpose=FieldPurpose.CLASSIFICATION,
            ),
        ],
    )

    proposals = result.all_proposals()
    fingerprints = {proposal.fingerprint for proposal in proposals}
    assert len(proposals) == 2
    assert len(fingerprints) == 2
    assert {proposal.candidate.field_names[0] for proposal in proposals} == {
        "family",
        "life_form",
    }
