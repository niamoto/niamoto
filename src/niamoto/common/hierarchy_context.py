"""Shared helpers for deriving ancestor context from hierarchical references."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class HierarchyMetadata:
    """Resolved hierarchy columns for an entity table."""

    id_field: str
    join_field: str
    parent_field: Optional[str]
    left_field: Optional[str]
    right_field: Optional[str]
    rank_field: str
    name_field: str


def normalize_hierarchy_key(value: Any) -> str:
    """Convert rank-like values into stable dictionary keys."""
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")
    return slug


def detect_hierarchy_metadata(
    columns: Iterable[str], join_field: Optional[str] = None
) -> Optional[HierarchyMetadata]:
    """Detect the main hierarchy columns on a table."""

    column_names = list(columns)
    if not column_names:
        return None

    by_lower = {column.lower(): column for column in column_names}

    def first_available(candidates: List[str]) -> Optional[str]:
        for candidate in candidates:
            if candidate in by_lower:
                return by_lower[candidate]
        return None

    id_field = first_available(["id"])
    rank_field = first_available(
        ["rank_name", "rank", "rank_value", "level_name", "category"]
    )
    name_field = first_available(["full_name", "name", "label", "title", "rank_value"])
    parent_field = first_available(["parent_id", "parent", "id_parent"])
    left_field = first_available(["lft", "left", "left_bound"])
    right_field = first_available(["rght", "right", "right_bound"])

    if not id_field or not rank_field or not name_field:
        return None
    if not parent_field and not (left_field and right_field):
        return None

    resolved_join_field = join_field if join_field in column_names else id_field

    return HierarchyMetadata(
        id_field=id_field,
        join_field=resolved_join_field,
        parent_field=parent_field,
        left_field=left_field,
        right_field=right_field,
        rank_field=rank_field,
        name_field=name_field,
    )


def _build_parent_map_from_nested_set(
    rows: List[Dict[str, Any]], metadata: HierarchyMetadata
) -> Dict[Any, Any]:
    """Derive parent IDs from nested-set boundaries when parent_id is missing."""

    if not metadata.left_field or not metadata.right_field:
        return {}

    sortable_rows = [
        row
        for row in rows
        if row.get(metadata.id_field) is not None
        and row.get(metadata.left_field) is not None
        and row.get(metadata.right_field) is not None
    ]
    sortable_rows.sort(
        key=lambda row: (row[metadata.left_field], -row[metadata.right_field])
    )

    parent_map: Dict[Any, Any] = {}
    stack: List[Dict[str, Any]] = []

    for row in sortable_rows:
        current_left = row[metadata.left_field]

        while stack and current_left > stack[-1][metadata.right_field]:
            stack.pop()

        if stack:
            parent_map[row[metadata.id_field]] = stack[-1][metadata.id_field]

        stack.append(row)

    return parent_map


def build_hierarchy_contexts(
    rows: Iterable[Dict[str, Any]], metadata: HierarchyMetadata
) -> Dict[Any, Dict[str, Dict[str, Any]]]:
    """Build ancestor context dictionaries keyed by the entity join field."""

    row_list = [dict(row) for row in rows]
    row_by_id = {
        row[metadata.id_field]: row
        for row in row_list
        if row.get(metadata.id_field) is not None
    }
    if not row_by_id:
        return {}

    if metadata.parent_field:
        parent_map = {
            row_id: row.get(metadata.parent_field)
            for row_id, row in row_by_id.items()
            if row.get(metadata.parent_field) is not None
        }
    else:
        parent_map = _build_parent_map_from_nested_set(row_list, metadata)

    cache: Dict[Any, Dict[str, Dict[str, Any]]] = {}

    def build_context(
        row_id: Any, lineage: Optional[set[Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        if row_id in cache:
            return cache[row_id]

        row = row_by_id.get(row_id)
        if not row:
            return {}

        visited = set() if lineage is None else set(lineage)
        if row_id in visited:
            return {}
        visited.add(row_id)

        parent_id = parent_map.get(row_id)
        context: Dict[str, Dict[str, Any]] = {}
        if parent_id is not None:
            for key, entry in build_context(parent_id, visited).items():
                context[key] = {
                    **entry,
                    "distance": int(entry.get("distance", 0)) + 1,
                }

        rank_value = row.get(metadata.rank_field)
        key = normalize_hierarchy_key(rank_value)
        name_value = row.get(metadata.name_field)
        if key and name_value not in (None, ""):
            context[key] = {
                "id": row.get(metadata.id_field),
                "name": name_value,
                "rank": rank_value,
                "distance": 0,
            }

        cache[row_id] = context
        return context

    return {
        row[metadata.join_field]: build_context(row[metadata.id_field])
        for row in row_list
        if row.get(metadata.join_field) is not None
        and row.get(metadata.id_field) is not None
    }
