"""Decision helpers for import auto-configuration.

This module isolates heuristic and hybrid ML decision rules from evidence
collection so they can be reused by ColumnDetector and AutoConfigService.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


ML_REVIEW_THRESHOLD = 0.7
ML_OVERRIDE_THRESHOLD = 0.82
GENERIC_ENTITY_TOKENS = {
    "data",
    "dataset",
    "datasets",
    "entity",
    "entities",
    "file",
    "files",
    "import",
    "imports",
    "raw",
    "sample",
    "samples",
    "source",
    "sources",
    "stat",
    "stats",
    "table",
    "tables",
}


def collect_heuristic_flags(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Extract heuristic flags from a file analysis."""
    columns = analysis.get("columns", [])
    hierarchy = analysis.get("hierarchy", {})
    has_observations = len(analysis.get("date_columns", [])) > 0 or any(
        col.lower()
        in {
            "dbh",
            "height",
            "diameter",
            "measurement",
            "value",
            "stem_diameter",
        }
        for col in columns
    )

    return {
        "has_geometry": len(analysis.get("geometry_columns", [])) > 0,
        "has_observations": has_observations,
        "has_taxonomic_hierarchy": bool(
            hierarchy.get("detected") and hierarchy.get("hierarchy_type") == "taxonomic"
        ),
        "has_hierarchy": bool(hierarchy.get("detected")),
        "column_count": len(columns),
    }


def _normalize_entity_tokens(entity_name: str) -> List[str]:
    tokens = []
    for part in entity_name.lower().replace("-", "_").split("_"):
        if not part or part in GENERIC_ENTITY_TOKENS:
            continue
        tokens.append(part)
        if part.endswith("ies") and len(part) > 3:
            tokens.append(part[:-3] + "y")
        elif part.endswith("s") and len(part) > 3:
            tokens.append(part[:-1])
    return list(dict.fromkeys(tokens))


def _is_enriched_reference_candidate(
    entity_name: str,
    analysis: Dict[str, Any],
    heuristics: Dict[str, Any],
) -> bool:
    """Detect stable entity tables that should stay references despite rich fields."""
    if heuristics["has_taxonomic_hierarchy"]:
        return False

    row_count = int(analysis.get("row_count", 0) or 0)
    if row_count <= 0 or row_count > 5000:
        return False

    if heuristics["has_observations"] or analysis.get("date_columns"):
        return False

    id_columns = [column.lower() for column in analysis.get("id_columns", [])]
    name_columns = [column.lower() for column in analysis.get("name_columns", [])]
    all_columns = [column.lower() for column in analysis.get("columns", [])]
    entity_tokens = _normalize_entity_tokens(entity_name)

    has_non_generic_id = any(column not in {"id", "uuid"} for column in id_columns)
    has_distinct_name = any(column not in set(id_columns) for column in name_columns)
    if not has_non_generic_id or not has_distinct_name or not entity_tokens:
        return False

    anchored_identifier = any(
        token in column
        for token in entity_tokens
        for column in id_columns + name_columns + all_columns
    )
    if not anchored_identifier:
        return False

    return heuristics["has_geometry"] or bool(name_columns)


def build_heuristic_classification(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a file from heuristics only.

    This is the previous first-pass decision used by ColumnDetector, extracted
    so the rule set can evolve independently from evidence collection.
    """
    columns = analysis.get("columns", [])
    hierarchy = analysis.get("hierarchy", {})
    flags = collect_heuristic_flags(analysis)
    level_count = hierarchy.get("level_count", len(hierarchy.get("levels", [])))
    has_hierarchy = hierarchy.get("detected") and level_count >= 2
    has_many_columns = len(columns) > 10

    if (
        has_hierarchy
        and flags["has_geometry"]
        and (has_many_columns or flags["has_observations"])
    ):
        return {
            "suggested_entity_type": "dataset",
            "suggested_connector_type": "file",
            "confidence": 0.9,
            "extract_hierarchy_as_reference": True,
        }
    if has_hierarchy and not flags["has_geometry"] and not has_many_columns:
        return {
            "suggested_entity_type": "hierarchical_reference",
            "suggested_connector_type": "file",
            "confidence": hierarchy.get("confidence", 0.8),
            "extract_hierarchy_as_reference": False,
        }
    if flags["has_geometry"]:
        return {
            "suggested_entity_type": "dataset",
            "suggested_connector_type": "file",
            "confidence": 0.8,
            "extract_hierarchy_as_reference": False,
        }
    if len(analysis.get("id_columns", [])) > 0 and len(columns) < 10:
        return {
            "suggested_entity_type": "reference",
            "suggested_connector_type": "file",
            "confidence": 0.7,
            "extract_hierarchy_as_reference": False,
        }
    return {
        "suggested_entity_type": "dataset",
        "suggested_connector_type": "file",
        "confidence": 0.5,
        "extract_hierarchy_as_reference": False,
    }


def infer_ml_entity_type(
    analysis: Dict[str, Any],
) -> Tuple[Optional[str], float, List[str]]:
    """Infer an entity type from semantic ML predictions."""
    predictions = analysis.get("ml_predictions", [])
    if not predictions:
        return None, 0.0, []

    role_scores: Dict[str, float] = defaultdict(float)
    taxonomy_level_count = 0
    join_key_count = 0
    for prediction in predictions:
        concept = prediction.get("concept") or ""
        confidence = float(prediction.get("confidence", 0.0))
        role = concept.split(".")[0]
        role_scores[role] += confidence

        if concept.startswith("taxonomy."):
            taxonomy_level_count += 1
        if concept.startswith("identifier."):
            join_key_count += 1

    measurement_score = role_scores.get("measurement", 0.0)
    time_score = role_scores.get("time", 0.0)
    taxonomy_score = role_scores.get("taxonomy", 0.0)
    geometry_score = role_scores.get("geometry", 0.0)
    location_score = role_scores.get("location", 0.0)
    identifier_score = role_scores.get("identifier", 0.0)
    max_confidence = max(float(pred.get("confidence", 0.0)) for pred in predictions)
    reasons = []

    if (
        taxonomy_level_count >= 2
        and measurement_score < 0.8
        and time_score < 0.6
        and geometry_score == 0.0
        and len(analysis.get("columns", [])) < 12
    ):
        reasons.append(
            "ML sees multiple taxonomy levels with little observational evidence."
        )
        return "hierarchical_reference", max_confidence, reasons

    if (
        (measurement_score >= 0.7 or time_score >= 0.7)
        or len(analysis.get("date_columns", [])) > 0
        or geometry_score >= 0.7
    ):
        reasons.append(
            "ML found observation-oriented signals such as measurements, time, or geometry."
        )
        return "dataset", max_confidence, reasons

    if identifier_score >= 0.7 or (join_key_count >= 1 and location_score >= 0.4):
        reasons.append(
            "ML mostly found identifier/location join signals typical of lookup tables."
        )
        return "reference", max_confidence, reasons

    if taxonomy_score >= 0.7:
        reasons.append(
            "ML found taxonomy concepts but not enough evidence for a factual dataset."
        )
        return "reference", max_confidence, reasons

    return None, max_confidence, []


def build_entity_decision(
    entity_name: str,
    analysis: Dict[str, Any],
    referenced_by: Dict[str, List[Dict[str, Any]]],
    all_analyses: Dict[str, Dict[str, Any]],
    ml_review_threshold: float = ML_REVIEW_THRESHOLD,
    ml_override_threshold: float = ML_OVERRIDE_THRESHOLD,
) -> Dict[str, Any]:
    """Combine heuristics, ML, and relationship context into a final decision."""
    heuristic_result = build_heuristic_classification(analysis)
    heuristic_entity_type = analysis.get(
        "suggested_entity_type", heuristic_result["suggested_entity_type"]
    )
    heuristic_confidence = analysis.get("confidence", heuristic_result["confidence"])
    final_entity_type = heuristic_entity_type
    ml_entity_type, ml_confidence, ml_reasons = infer_ml_entity_type(analysis)
    heuristics = collect_heuristic_flags(analysis)
    heuristics["is_enriched_reference_candidate"] = _is_enriched_reference_candidate(
        entity_name=entity_name,
        analysis=analysis,
        heuristics=heuristics,
    )
    alignment = "heuristic_only"

    if final_entity_type == "dataset" and heuristics["is_enriched_reference_candidate"]:
        heuristic_entity_type = "reference"
        heuristic_confidence = max(heuristic_confidence, 0.78)
        final_entity_type = "reference"

    if final_entity_type == "dataset" and entity_name in referenced_by:
        if (
            not heuristics["has_observations"]
            and not heuristics["has_taxonomic_hierarchy"]
        ):
            for ref_info in referenced_by[entity_name]:
                source_name = ref_info["from"]
                source_filepath = f"imports/{source_name}.csv"
                if source_filepath not in all_analyses:
                    continue
                source_rows = all_analyses[source_filepath].get("row_count", 0)
                target_rows = analysis.get("row_count", 0)
                if target_rows > 0 and (source_rows / target_rows) >= 10:
                    final_entity_type = "reference"
                    break

    if (
        ml_entity_type in {"reference", "hierarchical_reference"}
        and final_entity_type == "dataset"
        and ml_confidence >= ml_override_threshold
        and not heuristics["has_observations"]
        and not heuristics["has_geometry"]
    ):
        final_entity_type = ml_entity_type
        alignment = "ml_override"
    elif (
        ml_entity_type == "dataset"
        and final_entity_type in {"reference", "hierarchical_reference"}
        and ml_confidence >= ml_override_threshold
        and not heuristics["is_enriched_reference_candidate"]
        and (
            heuristics["has_observations"]
            or heuristics["has_geometry"]
            or analysis.get("row_count", 0) >= 1000
        )
    ):
        final_entity_type = "dataset"
        alignment = "ml_override"
    elif ml_entity_type:
        if heuristic_entity_type == ml_entity_type == final_entity_type:
            alignment = "aligned"
        elif final_entity_type == heuristic_entity_type != ml_entity_type:
            alignment = "conflict"
        elif final_entity_type == ml_entity_type != heuristic_entity_type:
            alignment = "ml_override"
        else:
            alignment = "mixed"

    return {
        "final_entity_type": final_entity_type,
        "heuristic_entity_type": heuristic_entity_type,
        "heuristic_confidence": heuristic_confidence,
        "ml_entity_type": ml_entity_type,
        "ml_confidence": ml_confidence,
        "ml_review_threshold": ml_review_threshold,
        "alignment": alignment,
        "ml_inference_reasons": ml_reasons,
        "referenced_by": referenced_by.get(entity_name, []),
        "row_count": analysis.get("row_count", 0),
        "heuristic_flags": heuristics,
    }


def build_semantic_evidence(
    analysis: Dict[str, Any],
    decision: Dict[str, Any],
    referenced_by: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Summarize semantic evidence for the UI."""
    role_scores: Dict[str, float] = defaultdict(float)
    concept_scores: Dict[str, float] = defaultdict(float)
    for prediction in analysis.get("ml_predictions", []):
        concept = prediction.get("concept", "")
        if not concept:
            continue
        role = concept.split(".")[0]
        confidence = float(prediction.get("confidence", 0.0))
        role_scores[role] += confidence
        concept_scores[concept] += confidence

    top_roles = [
        {"role": role, "score": round(score, 4)}
        for role, score in sorted(
            role_scores.items(), key=lambda item: item[1], reverse=True
        )[:3]
    ]
    top_concepts = [
        {"concept": concept, "score": round(score, 4)}
        for concept, score in sorted(
            concept_scores.items(), key=lambda item: item[1], reverse=True
        )[:3]
    ]

    return {
        "top_predictions": analysis.get("ml_predictions", [])[:3],
        "top_roles": top_roles,
        "top_concepts": top_concepts,
        "date_columns": analysis.get("date_columns", []),
        "geometry_columns": analysis.get("geometry_columns", []),
        "hierarchy": analysis.get("hierarchy", {}),
        "relationship_candidates": referenced_by,
        "inferred_ml_entity_type": decision.get("ml_entity_type"),
        "inferred_ml_confidence": decision.get("ml_confidence", 0.0),
    }
