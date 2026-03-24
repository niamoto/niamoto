from niamoto.core.imports.auto_config_review import (
    build_auto_config_warnings,
    build_entity_review,
)


def test_build_entity_review_flags_ml_conflict():
    decision = {
        "final_entity_type": "dataset",
        "heuristic_entity_type": "dataset",
        "heuristic_confidence": 0.55,
        "ml_entity_type": "reference",
        "ml_confidence": 0.91,
        "alignment": "conflict",
        "ml_inference_reasons": [
            "ML mostly found identifier/location join signals typical of lookup tables."
        ],
        "referenced_by": [],
        "heuristic_flags": {
            "has_geometry": False,
            "has_observations": False,
            "has_taxonomic_hierarchy": False,
        },
    }
    analysis = {
        "row_count": 25,
        "date_columns": [],
        "geometry_columns": [],
    }

    review = build_entity_review(decision=decision, analysis=analysis)

    assert review["review_required"] is True
    assert review["review_level"] == "review"
    assert review["review_priority"] == "high"
    assert review["analysis_snapshot"]["row_count"] == 25
    assert any("ML suggests reference" in reason for reason in review["review_reasons"])


def test_build_entity_review_marks_referenced_dataset_as_info():
    decision = {
        "final_entity_type": "dataset",
        "heuristic_entity_type": "dataset",
        "heuristic_confidence": 0.9,
        "ml_entity_type": "dataset",
        "ml_confidence": 0.99,
        "alignment": "aligned",
        "ml_inference_reasons": [],
        "referenced_by": [{"from": "plots", "field": "plot_id"}],
        "heuristic_flags": {
            "has_geometry": False,
            "has_observations": True,
            "has_taxonomic_hierarchy": False,
            "is_enriched_reference_candidate": False,
        },
    }

    review = build_entity_review(decision=decision, analysis={})

    assert review["review_required"] is False
    assert review["review_level"] == "info"
    assert review["review_reasons"] == [
        "Referenced by another entity and kept as a dataset."
    ]


def test_build_entity_review_marks_enriched_reference_as_notice():
    decision = {
        "final_entity_type": "reference",
        "heuristic_entity_type": "reference",
        "heuristic_confidence": 0.82,
        "ml_entity_type": "dataset",
        "ml_confidence": 1.0,
        "alignment": "conflict",
        "ml_inference_reasons": [
            "ML found observation-oriented signals such as measurements, time, or geometry."
        ],
        "referenced_by": [],
        "heuristic_flags": {
            "has_geometry": True,
            "has_observations": True,
            "has_taxonomic_hierarchy": False,
            "is_enriched_reference_candidate": True,
        },
    }

    review = build_entity_review(decision=decision, analysis={})

    assert review["review_required"] is False
    assert review["review_level"] == "notice"
    assert any("Reference enriched" in reason for reason in review["review_reasons"])


def test_build_auto_config_warnings_deduplicates_review_and_global_messages():
    warnings = build_auto_config_warnings(
        decision_summary={
            "plots": {
                "review_required": True,
                "review_level": "review",
                "review_reasons": [
                    "ML suggests reference (91%) while final decision is dataset."
                ],
            },
            "taxonomy": {
                "review_required": True,
                "review_level": "review",
                "review_reasons": [
                    "ML suggests reference (91%) while final decision is dataset."
                ],
            },
        },
        overall_confidence=0.55,
        has_references=False,
    )

    assert any(warning.startswith('Review "plots"') for warning in warnings)
    assert any(warning.startswith('Review "taxonomy"') for warning in warnings)
    assert "Low confidence in auto-configuration. Please review carefully." in warnings
    assert "No references detected. Add taxonomy or lookup tables." in warnings
