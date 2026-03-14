#!/usr/bin/env python3
"""
Test script to demonstrate pattern matching in action.

This script shows how the pattern matching system automatically discovers
compatible widgets for transformers.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.core.plugins.matching.matcher import SmartMatcher
from niamoto.core.plugins.transformers.distribution.binned_distribution import (
    BinnedDistribution,
)
from niamoto.core.plugins.widgets.bar_plot import BarPlotWidget


def main():
    """Demonstrate pattern matching."""
    print("=" * 80)
    print("Pattern Matching System Demo")
    print("=" * 80)

    # Show transformer output structure
    print("\n1. Transformer Output Structure")
    print("-" * 80)
    print(
        f"BinnedDistribution.output_structure = {BinnedDistribution.output_structure}"
    )

    # Show widget compatible structures
    print("\n2. Widget Compatible Structures")
    print("-" * 80)
    print(
        f"BarPlotWidget.compatible_structures = {BarPlotWidget.compatible_structures}"
    )

    # Create matcher
    matcher = SmartMatcher()

    # Find compatible widgets
    print("\n3. Finding Compatible Widgets")
    print("-" * 80)
    suggestions = matcher.find_compatible_widgets(BinnedDistribution)

    if suggestions:
        print(f"Found {len(suggestions)} compatible widgets:\n")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.widget_name}")
            print(f"     Score: {suggestion.score}")
            print(f"     Reason: {suggestion.reason}")
            print(f"     Confidence: {suggestion.confidence}")
            print()
    else:
        print("No compatible widgets found.")

    # Test matching logic
    print("\n4. Testing Match Types")
    print("-" * 80)

    # Exact match test
    output = {"bins": "list", "counts": "list"}
    pattern = {"bins": "list", "counts": "list"}
    is_exact = matcher._exact_match(output, pattern)
    print(f"Exact match: {output} == {pattern} -> {is_exact}")

    # Superset match test
    output = {"bins": "list", "counts": "list", "percentages": "list"}
    pattern = {"bins": "list", "counts": "list"}
    is_superset = matcher._superset_match(output, pattern)
    print(f"Superset match: {output} ⊃ {pattern} -> {is_superset}")

    # Partial match test
    output = {"bins": "list", "counts": "list"}
    pattern = {
        "bins": "list",
        "counts": "list",
        "labels": "list",
        "percentages": "list",
    }
    is_partial = matcher._partial_match(output, pattern)
    print(f"Partial match: {output} ∩ {pattern} (50%+) -> {is_partial}")

    print("\n" + "=" * 80)
    print("Demo Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
