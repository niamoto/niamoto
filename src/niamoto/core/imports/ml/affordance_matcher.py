"""
Affordance-based matching for column → transformer → widget suggestions.

Instead of matching on specific column concepts (diameter → binned_distribution),
this matches on what a column CAN DO (numeric_continuous + histogrammable → histogram).

This means a diameter and a height get the same widget suggestions, which is correct:
both should get a histogram, a statistical summary, and be available for scatter plots.

The AffordanceMatcher sits above SmartMatcher:
1. AffordanceMatcher: column affordances → candidate transformers
2. SmartMatcher: transformer output_structure → compatible widgets

Usage:
    from niamoto.core.plugins.matching.affordance_matcher import AffordanceMatcher

    matcher = AffordanceMatcher()
    suggestions = matcher.suggest(column_profile)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AffordanceSuggestion:
    """A transformer→widget suggestion based on affordance matching."""

    transformer: str
    widget: str
    score: float  # 0.0-1.0
    reason: str
    affordances_matched: list[str] = field(default_factory=list)


# ── Transformer affordance requirements ──────────────────────────
# Each transformer declares what affordances it needs from a column.
# If a column has >= 50% of the required affordances, it's a candidate.

TRANSFORMER_AFFORDANCES: dict[str, dict] = {
    "binned_distribution": {
        "required": {"numeric_continuous", "histogrammable"},
        "produced": {"binned_data", "distribution"},
        "preferred_widgets": ["bar_plot"],
    },
    "statistical_summary": {
        "required": {"numeric_continuous"},
        "produced": {"summary_stats"},
        "preferred_widgets": ["info_block", "gauge"],
    },
    "categorical_distribution": {
        "required": {"categorical"},
        "produced": {"category_counts"},
        "preferred_widgets": ["bar_plot", "donut_chart"],
    },
    "top_ranking": {
        "required": {"categorical", "rankable"},
        "produced": {"ranked_list"},
        "preferred_widgets": ["bar_plot"],
    },
    "scatter_analysis": {
        "required": {"numeric_continuous", "scatterable"},
        "produced": {"xy_data"},
        "preferred_widgets": ["scatter_plot"],
    },
    "geospatial_extractor": {
        "required": {"mappable", "coordinate"},
        "produced": {"geo_points"},
        "preferred_widgets": ["interactive_map"],
    },
    "temporal_aggregation": {
        "required": {"temporal"},
        "produced": {"time_series"},
        "preferred_widgets": ["line_plot"],
    },
    "hierarchy_distribution": {
        "required": {"categorical", "hierarchy_level"},
        "produced": {"hierarchy_data"},
        "preferred_widgets": ["sunburst", "donut_chart"],
    },
}


class AffordanceMatcher:
    """Match columns to transformers via affordances."""

    def __init__(
        self,
        transformer_affordances: Optional[dict] = None,
    ):
        self.transformers = transformer_affordances or TRANSFORMER_AFFORDANCES

    def suggest(
        self,
        affordances: set[str],
        *,
        max_suggestions: int = 5,
    ) -> list[AffordanceSuggestion]:
        """Find candidate transformer→widget pairs for a set of affordances.

        Args:
            affordances: Column affordances (from ColumnSemanticProfile)
            max_suggestions: Maximum number of suggestions to return

        Returns:
            Sorted list of suggestions (best first)
        """
        if not affordances:
            return []

        suggestions = []

        for transformer_name, spec in self.transformers.items():
            required = spec["required"]
            matched = affordances & required

            if not matched:
                continue

            # Score = proportion of required affordances present
            match_ratio = len(matched) / len(required)

            if match_ratio < 0.5:
                continue

            # Create a suggestion for each preferred widget
            for widget_name in spec.get("preferred_widgets", []):
                suggestions.append(
                    AffordanceSuggestion(
                        transformer=transformer_name,
                        widget=widget_name,
                        score=match_ratio,
                        reason=f"Matched {sorted(matched)}",
                        affordances_matched=sorted(matched),
                    )
                )

        # Sort by score descending
        suggestions.sort(key=lambda s: -s.score)
        return suggestions[:max_suggestions]

    def suggest_for_profile(
        self,
        profile,
        **kwargs,
    ) -> list[AffordanceSuggestion]:
        """Convenience: suggest from a ColumnSemanticProfile."""
        return self.suggest(profile.affordances, **kwargs)
