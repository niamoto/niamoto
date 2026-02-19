"""Shared table resolution and identifier quoting helpers."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlalchemy import inspect


def quote_identifier(db: Any, name: str) -> str:
    """Safely quote a SQL identifier (table/column name)."""
    preparer = inspect(db.engine).dialect.identifier_preparer
    return preparer.quote(name)


def resolve_existing_table_name(
    table_names: Iterable[str], logical_name: Optional[str], prefixes: Iterable[str]
) -> Optional[str]:
    """Resolve a logical name against an in-memory table list using prefixes."""
    if not logical_name:
        return None

    lookup = {name.lower(): name for name in table_names}
    for prefix in prefixes:
        candidate = f"{prefix}{logical_name}" if prefix else logical_name
        resolved = lookup.get(candidate.lower())
        if resolved:
            return resolved
    return None


def resolve_dataset_table_name(
    table_names: Iterable[str], dataset_name: Optional[str]
) -> Optional[str]:
    """Resolve a dataset logical name against an in-memory table list."""
    return resolve_existing_table_name(
        table_names, dataset_name, ("dataset_", "entity_", "")
    )


def resolve_reference_table_name(
    table_names: Iterable[str], reference_name: Optional[str]
) -> Optional[str]:
    """Resolve a reference logical name against an in-memory table list."""
    return resolve_existing_table_name(
        table_names, reference_name, ("entity_", "reference_", "")
    )


def resolve_entity_table_name(
    table_names: Iterable[str], entity_name: Optional[str]
) -> Optional[str]:
    """Resolve a generic entity logical name against an in-memory table list."""
    return resolve_existing_table_name(
        table_names, entity_name, ("entity_", "reference_", "dataset_", "")
    )


def resolve_existing_table(
    db: Any, logical_name: Optional[str], prefixes: Iterable[str]
) -> Optional[str]:
    """Resolve logical name against existing physical tables using prefixes."""
    if not logical_name:
        return None

    for prefix in prefixes:
        candidate = f"{prefix}{logical_name}" if prefix else logical_name
        if db.has_table(candidate):
            return candidate
    return None


def resolve_dataset_table(db: Any, dataset_name: Optional[str]) -> Optional[str]:
    """Resolve a dataset logical name to its physical table."""
    return resolve_existing_table(db, dataset_name, ("dataset_", "entity_", ""))


def resolve_reference_table(db: Any, reference_name: Optional[str]) -> Optional[str]:
    """Resolve a reference logical name to its physical table."""
    return resolve_existing_table(db, reference_name, ("entity_", "reference_", ""))


def resolve_entity_table(
    db: Any, entity_name: str, registry: Any = None, kind: Optional[str] = None
) -> Optional[str]:
    """Resolve entity table using registry first, then convention-based fallbacks."""
    if registry:
        try:
            entity_meta = registry.get(entity_name)
            meta_kind = getattr(getattr(entity_meta, "kind", None), "value", None)
            if kind is None or meta_kind == kind:
                table_name = getattr(entity_meta, "table_name", None)
                if table_name and db.has_table(table_name):
                    return table_name
        except Exception:
            pass

    if kind == "reference":
        return resolve_reference_table(db, entity_name)
    if kind == "dataset":
        return resolve_dataset_table(db, entity_name)

    return resolve_existing_table(
        db, entity_name, ("entity_", "reference_", "dataset_", "")
    )
