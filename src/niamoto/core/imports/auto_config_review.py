"""Review and warning policy for auto-config decisions."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def build_entity_review(
    decision: Dict[str, Any],
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Build UI-facing review state from a decision and its evidence."""
    review_reasons: List[str] = []
    ml_entity_type = decision.get("ml_entity_type")
    ml_confidence = float(decision.get("ml_confidence", 0.0) or 0.0)
    ml_review_threshold = float(decision.get("ml_review_threshold", 0.7) or 0.7)
    final_entity_type = decision.get("final_entity_type")
    heuristics = decision.get("heuristic_flags", {})
    review_level = "stable"

    def elevate(level: str) -> None:
        nonlocal review_level
        order = {"stable": 0, "info": 1, "notice": 2, "review": 3}
        if order[level] > order[review_level]:
            review_level = level

    if (
        ml_entity_type
        and ml_confidence >= ml_review_threshold
        and ml_entity_type != final_entity_type
    ):
        if (
            final_entity_type in {"reference", "hierarchical_reference"}
            and ml_entity_type == "dataset"
            and heuristics.get("is_enriched_reference_candidate")
        ):
            elevate("notice")
            review_reasons.append(
                f"Reference enriched with measurements or geometry; ML also saw dataset-like signals ({ml_confidence:.0%})."
            )
        else:
            elevate("review")
            review_reasons.append(
                f"ML suggests {ml_entity_type} ({ml_confidence:.0%}) while final decision is {final_entity_type}."
            )

    if float(decision.get("heuristic_confidence", 0.0) or 0.0) < 0.6:
        elevate("review")
        review_reasons.append("Heuristic confidence is low for this file.")

    if final_entity_type in {"reference", "hierarchical_reference"} and heuristics.get(
        "has_observations"
    ):
        if heuristics.get("is_enriched_reference_candidate"):
            elevate("notice")
            review_reasons.append(
                "Observation-like signals were detected, but the file still behaves like an enriched reference."
            )
        else:
            elevate("review")
            review_reasons.append(
                "Observation-like signals were detected in a file classified as reference."
            )

    if (
        final_entity_type == "dataset"
        and heuristics.get("has_taxonomic_hierarchy")
        and not heuristics.get("has_geometry")
        and not heuristics.get("has_observations")
    ):
        elevate("review")
        review_reasons.append(
            "The file looks hierarchy-heavy for a dataset; taxonomy extraction should be checked."
        )

    if decision.get("referenced_by") and final_entity_type == "dataset":
        elevate("info")
        review_reasons.append("Referenced by another entity and kept as a dataset.")

    for reason in decision.get("ml_inference_reasons", []):
        if reason in review_reasons:
            continue
        if decision.get("alignment") in {"conflict", "mixed"}:
            if review_level == "notice" and final_entity_type in {
                "reference",
                "hierarchical_reference",
            }:
                review_reasons.append(reason)
            elif review_level == "review":
                review_reasons.append(reason)

    logger.debug(
        "Auto-config review for %s: level=%s reasons=%d",
        decision.get("final_entity_type"),
        review_level,
        len(review_reasons),
    )

    return {
        "review_required": review_level == "review",
        "review_level": review_level,
        "review_reasons": review_reasons,
        "review_priority": "high"
        if review_level == "review" and len(review_reasons) >= 2
        else "normal",
        "analysis_snapshot": {
            "row_count": analysis.get("row_count", 0),
            "date_columns": analysis.get("date_columns", []),
            "geometry_columns": analysis.get("geometry_columns", []),
        },
    }


def build_auto_config_warnings(
    decision_summary: Dict[str, Dict[str, Any]],
    overall_confidence: float,
    has_references: bool,
) -> List[str]:
    """Build global warning messages for the auto-config response."""
    warnings: List[str] = []

    for entity_name, summary in decision_summary.items():
        if summary.get("final_entity_type") == "auxiliary_source":
            continue
        if summary.get("review_required"):
            joined = "; ".join(summary.get("review_reasons", [])[:2])
            warnings.append(f'Review "{entity_name}": {joined}')

    if overall_confidence < 0.6:
        warnings.append(
            "Low confidence in auto-configuration. Please review carefully."
        )

    if not has_references:
        warnings.append("No references detected. Add taxonomy or lookup tables.")

    return list(dict.fromkeys(warnings))
