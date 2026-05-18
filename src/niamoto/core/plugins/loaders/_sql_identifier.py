"""SQL identifier helpers for loader-generated queries."""

from __future__ import annotations

import re

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(value: str, label: str = "SQL identifier") -> str:
    """Validate and quote a SQL identifier, allowing dotted qualified names."""

    if not value:
        raise ValueError(f"{label} cannot be empty")

    parts = value.split(".")
    if any(not _IDENTIFIER_RE.fullmatch(part) for part in parts):
        raise ValueError(f"Invalid {label}: {value}")

    return ".".join(f'"{part}"' for part in parts)
