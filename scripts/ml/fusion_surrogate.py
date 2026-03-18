#!/usr/bin/env python
"""Shared helpers for the fusion surrogate cache."""

from __future__ import annotations

import hashlib
from pathlib import Path


CACHE_VERSION = 1
DEFAULT_CACHE_ROOT = (
    Path(__file__).parent.parent.parent / "data" / "cache" / "ml" / "fusion_surrogate"
)


def compute_gold_set_sha256(path: Path) -> str:
    """Return a stable content hash for a gold-set JSON file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_cache_dir(gold_path: Path, splits: int) -> Path:
    """Return the default cache directory for a gold set / split count pair."""
    return DEFAULT_CACHE_ROOT / f"{gold_path.stem}_splits{splits}"
