"""
Column alias registry for header-based semantic type detection.
Maps column names to semantic concepts via exact match, fuzzy matching, and alias lookup.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import fuzz, process
from unidecode import unidecode

logger = logging.getLogger(__name__)

# Minimum fuzzy score (0-100) to accept a match
_FUZZY_THRESHOLD = 80

# Path to the alias YAML file (alongside this module)
_ALIAS_FILE = Path(__file__).parent / "column_aliases.yaml"


class AliasRegistry:
    """Registry mapping column names to semantic concepts via aliases."""

    def __init__(self, alias_path: Optional[Path] = None):
        self._raw: dict = {}
        self._exact_index: dict[
            str, str
        ] = {}  # normalized_alias → concept (O(1) lookup)
        self._all_aliases: list[str] = []  # flat list for extractOne
        self._alias_to_concept: dict[
            str, str
        ] = {}  # alias → concept (for fuzzy result mapping)
        self._load(alias_path or _ALIAS_FILE)

    def _load(self, path: Path) -> None:
        """Load and flatten the alias YAML into optimized lookup structures."""
        with open(path) as f:
            self._raw = yaml.safe_load(f) or {}

        for concept, langs in self._raw.items():
            for _lang, aliases in langs.items():
                for alias in aliases:
                    norm = _normalize(alias)
                    if not norm:
                        continue
                    self._exact_index[norm] = concept
                    if norm not in self._alias_to_concept:
                        self._all_aliases.append(norm)
                        self._alias_to_concept[norm] = concept

        logger.debug(
            "Loaded alias registry: %d concepts, %d aliases",
            len(self._raw),
            len(self._all_aliases),
        )

    @property
    def concepts(self) -> list[str]:
        """List all registered concept names."""
        return list(self._raw.keys())

    def match(self, column_name: str) -> tuple[Optional[str], float]:
        """
        Match a column name to a semantic concept.

        Returns:
            (concept, score) where score is 0.0-1.0.
            Returns (None, 0.0) if no match found above threshold.
        """
        norm = _normalize(column_name)
        if not norm:
            return None, 0.0

        # 1. Exact match via reverse index — O(1)
        concept = self._exact_index.get(norm)
        if concept:
            return concept, 1.0

        # 2. Fuzzy match via rapidfuzz extractOne — C-optimized with early termination
        result = process.extractOne(
            norm,
            self._all_aliases,
            scorer=fuzz.ratio,
            score_cutoff=_FUZZY_THRESHOLD,
        )
        if result:
            matched_alias, score, _idx = result
            return self._alias_to_concept[matched_alias], score / 100.0

        return None, 0.0

    def match_top_k(self, column_name: str, k: int = 3) -> list[tuple[str, float]]:
        """
        Return top-k concept matches with scores.

        Useful for the fusion model which needs probability-like scores
        across multiple candidate concepts.
        """
        norm = _normalize(column_name)
        if not norm:
            return []

        # Use extractOne for exact first
        exact = self._exact_index.get(norm)
        if exact:
            return [(exact, 1.0)]

        # Fuzzy top-k via rapidfuzz.process.extract
        results = process.extract(
            norm,
            self._all_aliases,
            scorer=fuzz.ratio,
            limit=k * 2,  # over-fetch to deduplicate by concept
        )

        # Deduplicate by concept (keep best score per concept)
        concept_scores: dict[str, float] = {}
        for matched_alias, score, _idx in results:
            concept = self._alias_to_concept[matched_alias]
            if concept not in concept_scores or score > concept_scores[concept]:
                concept_scores[concept] = score

        ranked = sorted(concept_scores.items(), key=lambda x: -x[1])
        return [(c, s / 100.0) for c, s in ranked[:k]]


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
