"""
Column alias registry for header-based semantic type detection.

At runtime: exact match only (O(1) via reverse index). No fuzzy matching —
that's handled by the ML classifier.

The YAML file also serves as the source of truth for training data generation
(ml/scripts/data/build_gold_set.py).
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
from unidecode import unidecode

logger = logging.getLogger(__name__)

# Path to the alias YAML file (alongside this module)
_ALIAS_FILE = Path(__file__).parent / "column_aliases.yaml"


class AliasRegistry:
    """Registry mapping column names to semantic concepts via exact match."""

    def __init__(self, alias_path: Optional[Path] = None):
        self._raw: dict = {}
        self._exact_index: dict[str, str] = {}  # normalized_alias → concept
        self._load(alias_path or _ALIAS_FILE)

    def _load(self, path: Path) -> None:
        """Load and flatten the alias YAML into a reverse index.

        Two-pass loading: first collect all concepts per normalized alias,
        then only index aliases that map to exactly one concept. Ambiguous
        aliases (same normalized form → multiple concepts) are excluded and
        left for the ML classifier to resolve.
        """
        with open(path, encoding="utf-8") as f:
            self._raw = yaml.safe_load(f) or {}

        # First pass: collect all concepts for each normalized alias
        alias_to_concepts: dict[str, set[str]] = {}
        for concept, langs in self._raw.items():
            for _lang, aliases in langs.items():
                for alias in aliases:
                    norm = _normalize(alias)
                    if norm:
                        alias_to_concepts.setdefault(norm, set()).add(concept)

        # Second pass: only index unambiguous aliases
        self._ambiguous: dict[str, frozenset[str]] = {}
        for norm, concepts in alias_to_concepts.items():
            if len(concepts) == 1:
                self._exact_index[norm] = next(iter(concepts))
            else:
                self._ambiguous[norm] = frozenset(concepts)
                logger.debug(
                    "Ambiguous alias '%s' maps to %d concepts (%s) — "
                    "excluded from exact matching, deferred to ML",
                    norm,
                    len(concepts),
                    ", ".join(sorted(concepts)),
                )

        logger.debug(
            "Loaded alias registry: %d concepts, %d unambiguous aliases, "
            "%d ambiguous aliases excluded",
            len(self._raw),
            len(self._exact_index),
            len(self._ambiguous),
        )

    @property
    def concepts(self) -> list[str]:
        """List all registered concept names."""
        return list(self._raw.keys())

    @property
    def ambiguous(self) -> dict[str, frozenset[str]]:
        """Aliases excluded from exact match due to multi-concept mapping."""
        return dict(self._ambiguous)

    def match(self, column_name: str) -> tuple[Optional[str], float]:
        """Exact match a column name to a semantic concept.

        Returns:
            (concept, 1.0) if found, (None, 0.0) otherwise.
        """
        norm = _normalize(column_name)
        if not norm:
            return None, 0.0

        concept = self._exact_index.get(norm)
        if concept:
            return concept, 1.0

        return None, 0.0


def _normalize(name: str) -> str:
    """Normalize a column name for matching.

    - lowercase
    - ASCII transliteration (é→e, ü→u, ñ→n)
    - strip non-alphanumeric except underscore
    """
    name = unidecode(name).lower().strip()
    for sep in [" ", "-", "."]:
        name = name.replace(sep, "_")
    return "".join(c for c in name if c.isalnum() or c == "_")
