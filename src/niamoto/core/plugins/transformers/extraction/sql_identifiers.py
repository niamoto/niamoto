"""SQL identifier validation helpers for extraction transformers."""

from __future__ import annotations

import re
from typing import Any

from niamoto.common.table_resolver import quote_identifier

_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_validated_table(db: Any, table_name: str) -> str:
    """Validate and quote a table identifier for SQL text construction."""
    _validate_identifier_value(table_name, "table")
    exists = _table_exists(db, table_name)
    if exists is False:
        raise ValueError(f"Unknown table: {table_name}")
    if exists is None:
        _ensure_simple_identifier(table_name, "table")
    return _quote_identifier(db, table_name)


def quote_validated_column(db: Any, table_name: str, column_name: str) -> str:
    """Validate a column against known table metadata when available and quote it."""
    _validate_identifier_value(column_name, "column")
    known_columns = _known_columns(db, table_name)
    if known_columns is not None and column_name not in known_columns:
        raise ValueError(f"Unknown column '{column_name}' for table '{table_name}'")
    if known_columns is None:
        _ensure_simple_identifier(column_name, "column")
    return _quote_identifier(db, column_name)


def _validate_identifier_value(value: str, identifier_type: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid {identifier_type} identifier")
    if "\x00" in value:
        raise ValueError(f"Invalid {identifier_type} identifier")


def _ensure_simple_identifier(value: str, identifier_type: str) -> None:
    if not _SAFE_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"Invalid {identifier_type} identifier")


def _table_exists(db: Any, table_name: str) -> bool | None:
    has_table = getattr(db, "has_table", None)
    if not callable(has_table):
        return None
    try:
        result = has_table(table_name)
    except Exception:
        return None
    return result if isinstance(result, bool) else None


def _known_columns(db: Any, table_name: str) -> set[str] | None:
    get_table_columns = getattr(db, "get_table_columns", None)
    if callable(get_table_columns):
        try:
            columns = get_table_columns(table_name)
        except Exception:
            columns = None
        if isinstance(columns, list) and all(
            isinstance(column, str) for column in columns
        ):
            return set(columns)

    get_columns = getattr(db, "get_columns", None)
    if callable(get_columns):
        try:
            columns_info = get_columns(table_name)
        except Exception:
            columns_info = None
        if isinstance(columns_info, list) and all(
            isinstance(column, dict) and isinstance(column.get("name"), str)
            for column in columns_info
        ):
            return {column["name"] for column in columns_info}

    return None


def _quote_identifier(db: Any, name: str) -> str:
    try:
        quoted = quote_identifier(db, name)
        if isinstance(quoted, str):
            return quoted
    except Exception:
        pass
    escaped = name.replace('"', '""')
    return f'"{escaped}"'
