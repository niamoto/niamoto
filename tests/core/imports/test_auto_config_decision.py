from niamoto.core.imports.auto_config_decision import (
    build_entity_decision,
    build_heuristic_classification,
    build_semantic_evidence,
)
from niamoto.core.utils.column_detector import ColumnDetector


def _base_analysis() -> dict:
    return {
        "columns": ["plot_id", "label"],
        "hierarchy": {
            "detected": False,
            "hierarchy_type": "unknown",
            "levels": [],
            "column_mapping": {},
        },
        "id_columns": ["plot_id"],
        "geometry_columns": [],
        "name_columns": ["label"],
        "date_columns": [],
        "suggested_entity_type": "dataset",
        "suggested_connector_type": "file",
        "confidence": 0.55,
        "extract_hierarchy_as_reference": False,
        "row_count": 25,
        "ml_predictions": [
            {
                "column": "plot_id",
                "concept": "identifier.plot",
                "confidence": 0.91,
                "source": "semantic_classifier",
            },
            {
                "column": "label",
                "concept": "location.locality",
                "confidence": 0.84,
                "source": "semantic_classifier",
            },
        ],
    }


def test_build_entity_decision_uses_ml_to_override_to_reference():
    analysis = _base_analysis()

    decision = build_entity_decision(
        entity_name="plots",
        analysis=analysis,
        referenced_by={},
        all_analyses={"imports/plots.csv": analysis},
    )

    assert decision["heuristic_entity_type"] == "reference"
    assert decision["final_entity_type"] == "reference"
    assert decision["ml_entity_type"] == "reference"
    assert decision["alignment"] == "aligned"
    assert decision["ml_inference_reasons"]
    assert "review_required" not in decision


def test_build_entity_decision_keeps_enriched_plot_reference_despite_metrics():
    analysis = {
        "columns": ["id_plot", "plot", "elevation", "rainfall", "geo_pt"],
        "hierarchy": {
            "detected": False,
            "hierarchy_type": "unknown",
            "levels": [],
            "column_mapping": {},
        },
        "id_columns": ["id_plot"],
        "geometry_columns": ["geo_pt"],
        "name_columns": ["plot"],
        "date_columns": [],
        "suggested_entity_type": "dataset",
        "suggested_connector_type": "file",
        "confidence": 0.8,
        "extract_hierarchy_as_reference": False,
        "row_count": 22,
        "ml_predictions": [
            {
                "column": "id_plot",
                "concept": "identifier.plot",
                "confidence": 1.0,
                "source": "semantic_classifier",
            },
            {
                "column": "plot",
                "concept": "location.locality",
                "confidence": 1.0,
                "source": "semantic_classifier",
            },
            {
                "column": "species_level",
                "concept": "measurement.trait",
                "confidence": 1.0,
                "source": "semantic_classifier",
            },
            {
                "column": "rainfall",
                "concept": "environment.precipitation",
                "confidence": 1.0,
                "source": "semantic_classifier",
            },
        ],
    }

    decision = build_entity_decision(
        entity_name="plots",
        analysis=analysis,
        referenced_by={"plots": [{"from": "occurrences", "field": "plot_name"}]},
        all_analyses={
            "imports/plots.csv": analysis,
            "imports/occurrences.csv": {"row_count": 1000},
        },
    )

    assert decision["heuristic_entity_type"] == "reference"
    assert decision["final_entity_type"] == "reference"
    assert decision["ml_entity_type"] == "dataset"
    assert decision["alignment"] == "conflict"
    assert decision["heuristic_flags"]["is_enriched_reference_candidate"] is True


def test_build_semantic_evidence_summarizes_top_roles():
    analysis = _base_analysis()
    decision = {"ml_entity_type": "reference", "ml_confidence": 0.91}

    evidence = build_semantic_evidence(
        analysis=analysis,
        decision=decision,
        referenced_by=[],
    )

    assert evidence["top_predictions"][0]["concept"] == "identifier.plot"
    assert evidence["top_roles"][0]["role"] == "identifier"
    assert evidence["inferred_ml_entity_type"] == "reference"


def test_build_heuristic_classification_identifies_small_reference_table():
    analysis = _base_analysis()

    classification = build_heuristic_classification(analysis)

    assert classification["suggested_entity_type"] == "reference"
    assert classification["suggested_connector_type"] == "file"
    assert classification["extract_hierarchy_as_reference"] is False


def test_column_detector_uses_extracted_heuristic_classification():
    analysis = ColumnDetector.analyze_file_columns(
        columns=["plot_id", "label"],
        sample_data=[{"plot_id": "P1", "label": "North plot"}],
    )

    assert analysis["suggested_entity_type"] == "reference"
    assert analysis["suggested_connector_type"] == "file"
