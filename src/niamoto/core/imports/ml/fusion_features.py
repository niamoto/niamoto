"""Shared fusion meta-feature helpers."""

from __future__ import annotations

import math
import re
from typing import Sequence

import numpy as np

_CODE_SUFFIXES = ("cd", "id", "nr", "no", "num", "code", "cod")


def is_code_like_header(raw_name: str, norm_name: str) -> float:
    """Detect short coded headers such as COUNTYCD, AGENTCD, PEUPNR."""
    raw_compact = re.sub(r"[^A-Za-z0-9]+", "", raw_name or "")
    norm_compact = re.sub(r"[^a-z0-9]+", "", norm_name or "")
    if not raw_compact and not norm_compact:
        return 0.0

    has_alpha = any(char.isalpha() for char in raw_compact)
    has_digit = any(char.isdigit() for char in raw_compact)
    is_upper_token = (
        bool(raw_compact) and raw_compact.upper() == raw_compact and has_alpha
    )
    short_token = 2 <= len(raw_compact) <= 10
    suffix_code = norm_compact.endswith(_CODE_SUFFIXES)

    return (
        1.0
        if suffix_code
        or (short_token and is_upper_token)
        or (short_token and has_alpha and has_digit)
        else 0.0
    )


def branch_confidence_stats(
    proba: Sequence[float] | None,
) -> tuple[float, float, float]:
    """Return max probability, top-1 margin and entropy-like uncertainty."""
    if proba is None:
        return 0.0, 0.0, 0.0
    arr = np.asarray(proba, dtype=float)
    if arr.size == 0 or float(arr.sum()) <= 0:
        return 0.0, 0.0, 0.0
    max_proba = float(arr.max())
    top_two = np.sort(arr)[-2:]
    margin = float(top_two[-1] - top_two[-2]) if len(top_two) == 2 else max_proba
    entropy = float(-np.sum([p * math.log(p) for p in arr if p > 0]))
    return max_proba, margin, entropy


def top_concept_flags(
    aligned_header: np.ndarray,
    aligned_value: np.ndarray,
    all_concepts: Sequence[str],
) -> tuple[float, float, float]:
    """Return branch agreement and `statistic.count`-focused flags."""
    if len(all_concepts) == 0:
        return 0.0, 0.0, 0.0

    header_top = (
        int(np.argmax(aligned_header)) if float(aligned_header.sum()) > 0 else -1
    )
    value_top = int(np.argmax(aligned_value)) if float(aligned_value.sum()) > 0 else -1
    agree = 1.0 if header_top >= 0 and header_top == value_top else 0.0

    stat_index = (
        all_concepts.index("statistic.count")
        if "statistic.count" in all_concepts
        else -1
    )
    value_stat = 1.0 if stat_index >= 0 and value_top == stat_index else 0.0
    header_stat = 1.0 if stat_index >= 0 and header_top == stat_index else 0.0
    return agree, value_stat, header_stat


def dampen_code_like_false_counts(
    aligned_header: np.ndarray,
    aligned_value: np.ndarray,
    all_concepts: Sequence[str],
    *,
    raw_name: str,
    norm_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce `statistic.count` dominance for obviously coded headers."""
    if "statistic.count" not in all_concepts:
        return aligned_header, aligned_value
    if is_code_like_header(raw_name, norm_name) == 0.0:
        return aligned_header, aligned_value

    stat_index = all_concepts.index("statistic.count")
    header = aligned_header.copy()
    value = aligned_value.copy()

    if stat_index < len(value) and value[stat_index] >= 0.55:
        value[stat_index] *= 0.35
    if stat_index < len(header) and header[stat_index] >= 0.55:
        header[stat_index] *= 0.5
    return header, value
