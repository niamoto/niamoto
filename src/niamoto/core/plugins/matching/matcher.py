"""
SmartMatcher for automatic transformer-widget discovery.

This module implements the core matching logic that finds compatible widgets
for transformers based on their output/input structure patterns.
"""

import logging
from typing import List, Type, Optional, Dict
from pydantic import BaseModel, Field

from niamoto.core.plugins.base import TransformerPlugin, WidgetPlugin, PluginType
from niamoto.core.plugins.registry import PluginRegistry

logger = logging.getLogger(__name__)


class WidgetSuggestion(BaseModel):
    """
    Suggestion for a compatible widget.

    Attributes:
        widget_name: Name of the widget plugin
        score: Compatibility score (0.0 to 1.0)
        confidence: Confidence level ("high", "medium", "low")
        reason: Explanation of why this widget was matched
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "widget_name": "bar_plot",
                    "score": 1.0,
                    "confidence": "high",
                    "reason": "exact_match",
                }
            ]
        }
    }

    widget_name: str = Field(..., description="Name of the widget plugin")
    score: float = Field(..., ge=0.0, le=1.0, description="Compatibility score")
    confidence: str = Field(
        ..., description="Confidence level", pattern="^(high|medium|low)$"
    )
    reason: str = Field(..., description="Explanation of matching reason")


class TransformerSuggestion(BaseModel):
    """
    Suggestion for a compatible transformer.

    Attributes:
        transformer_name: Name of the transformer plugin
        score: Compatibility score (0.0 to 1.0)
        confidence: Confidence level ("high", "medium", "low")
        reason: Explanation of why this transformer was matched
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transformer_name": "binned_distribution",
                    "score": 1.0,
                    "confidence": "high",
                    "reason": "exact_match",
                }
            ]
        }
    }

    transformer_name: str = Field(..., description="Name of the transformer plugin")
    score: float = Field(..., ge=0.0, le=1.0, description="Compatibility score")
    confidence: str = Field(
        ..., description="Confidence level", pattern="^(high|medium|low)$"
    )
    reason: str = Field(..., description="Explanation of matching reason")


class SmartMatcher:
    """
    Matches transformers with compatible widgets based on output/input structure patterns.

    The matcher uses a structure-based scoring system:
    - 1.0: Exact structure match (all required keys present)
    - 0.8: Superset match (transformer provides more than widget requires)
    - 0.6: Partial match (at least 50% of required keys present)
    - 0.0: Incompatible

    When multiple widgets have the same score, priority_rank is used as tie-breaker.
    """

    def __init__(self, registry: Optional[PluginRegistry] = None):
        """
        Initialize SmartMatcher.

        Args:
            registry: PluginRegistry instance (uses global if None)
        """
        self.registry = registry or PluginRegistry

    def find_compatible_widgets(
        self, transformer_class: Type[TransformerPlugin]
    ) -> List[WidgetSuggestion]:
        """
        Find all widgets compatible with a transformer via pattern matching.

        Args:
            transformer_class: The transformer class to find widgets for

        Returns:
            List of WidgetSuggestion sorted by score (descending) then priority_rank (ascending)

        Example:
            ```python
            from niamoto.core.plugins.transformers.distribution.binned_distribution import BinnedDistribution
            from niamoto.core.plugins.matching import SmartMatcher

            matcher = SmartMatcher()
            suggestions = matcher.find_compatible_widgets(BinnedDistribution)

            for suggestion in suggestions:
                print(f"{suggestion.widget_name}: {suggestion.score} ({suggestion.reason})")
            # Output:
            # bar_plot: 1.0 (exact_match)
            ```
        """
        suggestions = []

        # Check if transformer has output_structure
        if (
            not hasattr(transformer_class, "output_structure")
            or transformer_class.output_structure is None
        ):
            logger.debug(
                f"Transformer {transformer_class.__name__} has no output_structure, "
                "using legacy fallback"
            )
            return self._legacy_matching(transformer_class)

        output_structure = transformer_class.output_structure

        # Scan all registered widgets
        widget_plugins = self.registry.get_plugins_by_type(PluginType.WIDGET)

        for widget_name, widget_class in widget_plugins.items():
            score = self._structure_match_score(output_structure, widget_class)

            if score > 0:
                confidence = self._calculate_confidence(score)
                reason = self._match_reason(score)

                suggestions.append(
                    WidgetSuggestion(
                        widget_name=widget_name,
                        score=score,
                        confidence=confidence,
                        reason=reason,
                    )
                )

                logger.debug(
                    f"Match found: {widget_name} - score={score:.2f}, reason={reason}"
                )

        # Sort by score (desc) then priority_rank (asc)
        suggestions.sort(
            key=lambda x: (
                -x.score,  # Higher score first
                getattr(
                    self.registry.get_plugin(x.widget_name, PluginType.WIDGET),
                    "priority_rank",
                    50,
                ),  # Lower priority_rank first (tie-breaker)
            )
        )

        logger.info(
            f"Found {len(suggestions)} compatible widgets for "
            f"{transformer_class.__name__}"
        )

        return suggestions

    def _structure_match_score(
        self, output_structure: Dict[str, str], widget_class: Type[WidgetPlugin]
    ) -> float:
        """
        Calculate structure compatibility score (0-1).

        Args:
            output_structure: Transformer's output structure dict
            widget_class: Widget class to check compatibility with

        Returns:
            - 1.0: Exact structure match
            - 0.8: Superset match (widget accepts more than transformer provides)
            - 0.6: Partial match (some required fields present)
            - 0.0: Incompatible
        """
        if (
            not hasattr(widget_class, "compatible_structures")
            or widget_class.compatible_structures is None
        ):
            return 0.0

        compatible_structures = widget_class.compatible_structures
        if not compatible_structures:
            return 0.0

        # Check each compatible pattern
        best_score = 0.0

        for pattern in compatible_structures:
            # Exact match
            if self._exact_match(output_structure, pattern):
                best_score = max(best_score, 1.0)
            # Superset match
            elif self._superset_match(output_structure, pattern):
                best_score = max(best_score, 0.8)
            # Partial match
            elif self._partial_match(output_structure, pattern):
                best_score = max(best_score, 0.6)

        return best_score

    def _exact_match(self, output: Dict[str, str], pattern: Dict[str, str]) -> bool:
        """
        Check if output exactly matches pattern.

        Args:
            output: Output structure from transformer
            pattern: Required structure pattern from widget

        Returns:
            True if output has all required keys (and no extras)
        """
        output_keys = set(output.keys())
        pattern_keys = set(pattern.keys())
        return output_keys == pattern_keys

    def _superset_match(self, output: Dict[str, str], pattern: Dict[str, str]) -> bool:
        """
        Check if output is a superset of pattern (has all required + more).

        Args:
            output: Output structure from transformer
            pattern: Required structure pattern from widget

        Returns:
            True if output has all pattern keys plus additional ones
        """
        output_keys = set(output.keys())
        pattern_keys = set(pattern.keys())
        return pattern_keys.issubset(output_keys) and len(output_keys) > len(
            pattern_keys
        )

    def _partial_match(self, output: Dict[str, str], pattern: Dict[str, str]) -> bool:
        """
        Check if output has at least some required keys.

        Args:
            output: Output structure from transformer
            pattern: Required structure pattern from widget

        Returns:
            True if at least 50% of pattern keys are in output
        """
        output_keys = set(output.keys())
        pattern_keys = set(pattern.keys())
        overlap = pattern_keys.intersection(output_keys)
        return len(overlap) >= len(pattern_keys) * 0.5

    def _match_reason(self, score: float) -> str:
        """
        Get reason string from score.

        Args:
            score: Compatibility score (0.0 to 1.0)

        Returns:
            Reason string describing the match type
        """
        if score == 1.0:
            return "exact_match"
        elif score == 0.8:
            return "superset_match"
        elif score == 0.6:
            return "partial_match"
        else:
            return "incompatible"

    def _calculate_confidence(self, score: float) -> str:
        """
        Calculate confidence level from score.

        Args:
            score: Compatibility score (0.0 to 1.0)

        Returns:
            "high", "medium", or "low"
        """
        if score >= 0.9:
            return "high"
        elif score >= 0.7:
            return "medium"
        else:
            return "low"

    def _legacy_matching(
        self, transformer_class: Type[TransformerPlugin]
    ) -> List[WidgetSuggestion]:
        """
        Fallback matching for transformers without output_schema.

        This uses a small hardcoded mapping for critical plugins during migration.

        Args:
            transformer_class: Transformer class without output_schema

        Returns:
            List of widget suggestions based on legacy mapping
        """
        # Small legacy mapping for critical plugins
        LEGACY_MAPPINGS = {
            "binneddistribution": ["bar_plot"],
            "statisticalsummary": ["radial_gauge"],
            "geospatialextractor": ["interactive_map"],
            "topranking": ["bar_plot"],
        }

        # FIX: Normalize class name to match mapping keys
        # Remove all underscores and convert to lowercase
        transformer_name = (
            getattr(transformer_class, "__name__", "").replace("_", "").lower()
        )

        # Direct lookup instead of substring matching for precision
        widgets = LEGACY_MAPPINGS.get(transformer_name)

        if widgets:
            return [
                WidgetSuggestion(
                    widget_name=widget,
                    score=0.5,  # Lower score for legacy matches
                    confidence="medium",
                    reason="legacy_fallback",
                )
                for widget in widgets
            ]

        logger.warning(f"No legacy mapping found for {transformer_class.__name__}")
        return []

    def find_compatible_transformers(
        self, widget_class: Type[WidgetPlugin]
    ) -> List[TransformerSuggestion]:
        """
        Find all transformers compatible with a widget via pattern matching.

        Args:
            widget_class: The widget class to find transformers for

        Returns:
            List of TransformerSuggestion sorted by score (descending)

        Example:
            ```python
            from niamoto.core.plugins.widgets.bar_plot import BarPlotWidget
            from niamoto.core.plugins.matching import SmartMatcher

            matcher = SmartMatcher()
            suggestions = matcher.find_compatible_transformers(BarPlotWidget)

            for suggestion in suggestions:
                print(f"{suggestion.transformer_name}: {suggestion.score} ({suggestion.reason})")
            # Output:
            # binned_distribution: 1.0 (exact_match)
            # categorical_distribution: 1.0 (exact_match)
            # top_ranking: 1.0 (exact_match)
            ```
        """
        suggestions = []

        # Check if widget has compatible_structures
        if (
            not hasattr(widget_class, "compatible_structures")
            or widget_class.compatible_structures is None
        ):
            logger.debug(f"Widget {widget_class.__name__} has no compatible_structures")
            return suggestions

        compatible_structures = widget_class.compatible_structures
        if not compatible_structures:
            return suggestions

        # Scan all registered transformers
        transformer_plugins = self.registry.get_plugins_by_type(PluginType.TRANSFORMER)

        for transformer_name, transformer_class in transformer_plugins.items():
            # Skip transformers without output_structure
            if (
                not hasattr(transformer_class, "output_structure")
                or transformer_class.output_structure is None
            ):
                continue

            output_structure = transformer_class.output_structure

            # Calculate best match score across all compatible patterns
            best_score = 0.0
            for pattern in compatible_structures:
                # Exact match
                if self._exact_match(output_structure, pattern):
                    best_score = max(best_score, 1.0)
                # Superset match (transformer provides more than pattern requires)
                elif self._superset_match(output_structure, pattern):
                    best_score = max(best_score, 0.8)
                # Partial match
                elif self._partial_match(output_structure, pattern):
                    best_score = max(best_score, 0.6)

            if best_score > 0:
                confidence = self._calculate_confidence(best_score)
                reason = self._match_reason(best_score)

                suggestions.append(
                    TransformerSuggestion(
                        transformer_name=transformer_name,
                        score=best_score,
                        confidence=confidence,
                        reason=reason,
                    )
                )

                logger.debug(
                    f"Match found: {transformer_name} - score={best_score:.2f}, reason={reason}"
                )

        # Sort by score (descending)
        suggestions.sort(key=lambda x: -x.score)

        logger.info(
            f"Found {len(suggestions)} compatible transformers for "
            f"{widget_class.__name__}"
        )

        return suggestions
