"""Shared header text preprocessing for training and inference."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd


def _dtype_prefix(dtype: str) -> str:
    dtype = (dtype or "").lower()
    if dtype in {"float64", "float32"}:
        return "float"
    if dtype in {"int64", "int32"}:
        return "int"
    if dtype in {"object", "string"}:
        return "str"
    if dtype in {"bool", "boolean"}:
        return "bool"
    if "datetime" in dtype:
        return "date"
    return ""


def _finalize_header_text(
    norm_name: str,
    *,
    dtype: str,
    null_ratio: float,
    mean_length: float,
    n_rows: int,
) -> str:
    """Build the enriched header text used by the header model."""
    name = norm_name.replace("_", " ")
    prefix = _dtype_prefix(dtype)
    if prefix:
        name = f"{prefix} {name}"

    if null_ratio > 0.5:
        name = f"sparse {name}"

    if mean_length and mean_length < 3:
        name = f"short {name}"
    elif mean_length and mean_length > 50:
        name = f"long {name}"

    if n_rows and n_rows < 100:
        name = f"small {name}"

    return f"{name} {name} {name}"


def build_header_text_from_stats(norm_name: str, stats: Mapping[str, Any]) -> str:
    """Build enriched header text from serialized column stats."""
    return _finalize_header_text(
        norm_name,
        dtype=str(stats.get("dtype", "")),
        null_ratio=float(stats.get("null_ratio", 0.0) or 0.0),
        mean_length=float(stats.get("mean_length", 0.0) or 0.0),
        n_rows=int(stats.get("n", 0) or 0),
    )


def build_header_text_from_series(norm_name: str, series: pd.Series) -> str:
    """Build enriched header text from a runtime pandas series."""
    clean = series.dropna()
    mean_length = 0.0
    if len(clean) > 0:
        mean_length = float(clean.astype(str).str.len().mean())

    return _finalize_header_text(
        norm_name,
        dtype=str(series.dtype),
        null_ratio=float(series.isnull().mean()),
        mean_length=mean_length,
        n_rows=len(series),
    )
