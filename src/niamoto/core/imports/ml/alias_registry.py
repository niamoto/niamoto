"""
Column alias registry for header-based semantic type detection.
Maps column names to semantic concepts via exact match, fuzzy matching, and alias lookup.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import yaml
from rapidfuzz import fuzz
from unidecode import unidecode

logger = logging.getLogger(__name__)

# Minimum fuzzy score (0-100) to accept a match
_FUZZY_THRESHOLD = 80

# Path to the alias YAML file (alongside this module)
_ALIAS_FILE = Path(__file__).parent / "column_aliases.yaml"


class AliasRegistry:
    """Registry mapping column names to semantic concepts via aliases."""

    def __init__(self, alias_path: Optional[Path] = None):
        self._aliases: dict[str, list[str]] = {}  # concept → [normalized aliases]
        self._raw: dict = {}  # original YAML structure
        self._load(alias_path or _ALIAS_FILE)

    def _load(self, path: Path) -> None:
        """Load and flatten the alias YAML into a normalized lookup."""
        with open(path) as f:
            self._raw = yaml.safe_load(f) or {}

        for concept, langs in self._raw.items():
            flat: list[str] = []
            for _lang, aliases in langs.items():
                for alias in aliases:
                    flat.append(_normalize(alias))
            self._aliases[concept] = flat

        total = sum(len(v) for v in self._aliases.values())
        logger.debug(
            "Loaded alias registry: %d concepts, %d aliases",
            len(self._aliases),
            total,
        )

    @property
    def concepts(self) -> list[str]:
        """List all registered concept names."""
        return list(self._aliases.keys())

    def match(self, column_name: str) -> Tuple[Optional[str], float]:
        """
        Match a column name to a semantic concept.

        Returns:
            (concept, score) where score is 0.0-1.0.
            Returns (None, 0.0) if no match found above threshold.
        """
        norm = _normalize(column_name)
        if not norm:
            return None, 0.0

        # 1. Exact match (fastest path)
        for concept, aliases in self._aliases.items():
            if norm in aliases:
                return concept, 1.0

        # 2. Fuzzy match (handles typos, slight variations)
        best_concept: Optional[str] = None
        best_score = 0.0

        for concept, aliases in self._aliases.items():
            for alias in aliases:
                score = fuzz.ratio(norm, alias)
                if score > best_score:
                    best_score = score
                    best_concept = concept

        if best_score >= _FUZZY_THRESHOLD:
            return best_concept, best_score / 100.0

        return None, 0.0

    def match_top_k(self, column_name: str, k: int = 3) -> list[Tuple[str, float]]:
        """
        Return top-k concept matches with scores.

        Useful for the fusion model which needs probability-like scores
        across multiple candidate concepts.
        """
        norm = _normalize(column_name)
        if not norm:
            return []

        scores: list[Tuple[str, float]] = []

        for concept, aliases in self._aliases.items():
            # Best alias score for this concept
            best = 0.0
            for alias in aliases:
                if norm == alias:
                    best = 100.0
                    break
                s = fuzz.ratio(norm, alias)
                if s > best:
                    best = s
            if best > 0:
                scores.append((concept, best / 100.0))

        scores.sort(key=lambda x: -x[1])
        return scores[:k]


def _normalize(name: str) -> str:
    """Normalize a column name for matching.

    - lowercase
    - ASCII transliteration (é→e, ü→u, ñ→n)
    - strip non-alphanumeric except underscore
    """
    name = unidecode(name).lower().strip()
    # Replace common separators with underscore
    for sep in [" ", "-", "."]:
        name = name.replace(sep, "_")
    # Remove anything that's not alphanumeric or underscore
    return "".join(c for c in name if c.isalnum() or c == "_")
