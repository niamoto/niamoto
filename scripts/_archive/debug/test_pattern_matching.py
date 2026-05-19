#!/usr/bin/env python3
"""
Test script to demonstrate pattern matching in action.

This script shows how the pattern matching system automatically discovers
compatible widgets for transformers.
"""

import sys
from pathlib import Path

# Add src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
if not (REPO_ROOT / "src").is_dir():
    raise RuntimeError(f"Could not resolve repository root from {__file__}")
sys.path.insert(0, str(REPO_ROOT / "src"))

from niamoto.core.plugins.matching.matcher import SmartMatcher  # noqa: E402
from niamoto.core.plugins.transformers.distribution.binned_distribution import (  # noqa: E402
    BinnedDistribution,
)
from niamoto.core.plugins.widgets.bar_plot import BarPlotWidget  # noqa: E402


def test_binned_distribution_suggests_bar_plot():
    """Binned distribution output should match the bar plot widget."""
    matcher = SmartMatcher()
    suggestions = matcher.find_compatible_widgets(BinnedDistribution)

    assert suggestions, "Expected at least one compatible widget"
    top_suggestion = suggestions[0]
    assert top_suggestion.widget_name == BarPlotWidget.name
    assert top_suggestion.reason in {"exact_match", "superset_match", "partial_match"}
    assert top_suggestion.score > 0
    assert top_suggestion.confidence in {"high", "medium", "low"}


def test_pattern_matching_exact_superset_and_partial():
    """Pattern matching helpers should report exact, superset, and partial matches."""
    matcher = SmartMatcher()

    assert matcher._exact_match(
        {"bins": "list", "counts": "list"},
        {"bins": "list", "counts": "list"},
    )
    assert not matcher._exact_match(
        {"bins": "list", "counts": "list", "percentages": "list"},
        {"bins": "list", "counts": "list"},
    )

    assert matcher._superset_match(
        {"bins": "list", "counts": "list", "percentages": "list"},
        {"bins": "list", "counts": "list"},
    )
    assert not matcher._superset_match(
        {"bins": "list"},
        {"bins": "list", "counts": "list"},
    )

    assert matcher._partial_match(
        {"bins": "list", "counts": "list"},
        {
            "bins": "list",
            "counts": "list",
            "labels": "list",
            "percentages": "list",
        },
    )
    assert not matcher._partial_match(
        {"bins": "list"},
        {
            "bins": "list",
            "counts": "list",
            "labels": "list",
            "percentages": "list",
        },
    )


if __name__ == "__main__":
    raise SystemExit("Run this module with pytest.")
