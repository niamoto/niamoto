"""Shared heuristic rules for auto-configuration decisions.

This module stays dependency-light so both low-level utilities and import
orchestration code can reuse the same heuristic classification logic.
"""

from __future__ import annotations

from typing import Any, Dict, List

from niamoto.core.domain_vocabulary import OBSERVATION_FIELD_MARKERS


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
        col.lower() in OBSERVATION_FIELD_MARKERS for col in columns
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


def is_enriched_reference_candidate(
    entity_name: str,
    analysis: Dict[str, Any],
    heuristics: Dict[str, Any],
) -> bool:
    """Detect stable entity tables that should stay references despite rich fields."""
    if not has_reference_identity(entity_name, analysis, heuristics):
        return False

    if heuristics["has_observations"] or analysis.get("date_columns"):
        return False

    return True


def has_reference_identity(
    entity_name: str,
    analysis: Dict[str, Any],
    heuristics: Dict[str, Any],
) -> bool:
    """Return True when a table has the identity shape of a reference entity."""
    if heuristics["has_taxonomic_hierarchy"]:
        return False

    row_count = int(analysis.get("row_count", 0) or 0)
    if row_count <= 0 or row_count > 5000:
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
    """Classify a file from heuristics only."""
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
