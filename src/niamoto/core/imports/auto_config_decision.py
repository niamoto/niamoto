"""Decision helpers for import auto-configuration.

This module isolates heuristic and hybrid ML decision rules from evidence
collection so they can be reused by ColumnDetector and AutoConfigService.
"""

from __future__ import annotations

from collections import defaultdict
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from niamoto.core.auto_config_rules import (
    build_heuristic_classification,
    collect_heuristic_flags,
    has_reference_identity,
    is_enriched_reference_candidate,
)

ML_REVIEW_THRESHOLD = 0.7
ML_OVERRIDE_THRESHOLD = 0.82
logger = logging.getLogger(__name__)


def is_strong_reference_target(
    entity_name: str,
    analysis: Dict[str, Any],
    heuristics: Dict[str, Any],
    referenced_by: Dict[str, List[Dict[str, Any]]],
    analyses_by_entity: Dict[str, Dict[str, Any]],
) -> bool:
    """Detect rich references that are identified by incoming dataset relations."""
    if not has_reference_identity(entity_name, analysis, heuristics):
        return False

    target_rows = int(analysis.get("row_count", 0) or 0)
    if target_rows <= 0:
        return False

    for relation in referenced_by.get(entity_name, []):
        if float(relation.get("confidence", 0.0) or 0.0) < 0.75:
            continue
        source_analysis = analyses_by_entity.get(str(relation.get("from", "")))
        if not source_analysis:
            continue
        source_rows = int(source_analysis.get("row_count", 0) or 0)
        if source_rows > 0 and (source_rows / target_rows) >= 10:
            return True

    return False


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
    heuristic_result = analysis.get("heuristic_classification") or (
        build_heuristic_classification(analysis)
    )
    heuristic_entity_type = analysis.get(
        "suggested_entity_type", heuristic_result["suggested_entity_type"]
    )
    heuristic_confidence = analysis.get("confidence", heuristic_result["confidence"])
    final_entity_type = heuristic_entity_type
    ml_entity_type, ml_confidence, ml_reasons = infer_ml_entity_type(analysis)
    heuristics = analysis.get("heuristic_flags") or collect_heuristic_flags(analysis)
    heuristics["is_enriched_reference_candidate"] = is_enriched_reference_candidate(
        entity_name=entity_name,
        analysis=analysis,
        heuristics=heuristics,
    )
    alignment = "heuristic_only"
    analyses_by_entity = {
        Path(filepath).stem: item for filepath, item in all_analyses.items()
    }
    heuristics["is_strong_reference_target"] = is_strong_reference_target(
        entity_name=entity_name,
        analysis=analysis,
        heuristics=heuristics,
        referenced_by=referenced_by,
        analyses_by_entity=analyses_by_entity,
    )

    if final_entity_type == "dataset" and (
        heuristics["is_enriched_reference_candidate"]
        or heuristics["is_strong_reference_target"]
    ):
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
                source_analysis = analyses_by_entity.get(source_name)
                if not source_analysis:
                    continue
                source_rows = source_analysis.get("row_count", 0)
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
        and not heuristics["is_strong_reference_target"]
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

    logger.debug(
        "Auto-config decision for %s: heuristic=%s final=%s ml=%s alignment=%s",
        entity_name,
        heuristic_entity_type,
        final_entity_type,
        ml_entity_type,
        alignment,
    )

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
