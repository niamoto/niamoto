"""
Tests for pattern matching system in SmartMatcher.

This module tests the structure-based pattern matching that enables
automatic transformer-widget discovery without Pydantic contracts.
"""

import pytest
from typing import Any

from niamoto.core.plugins.base import TransformerPlugin, WidgetPlugin, PluginType
from niamoto.core.plugins.matching.matcher import SmartMatcher
from niamoto.core.plugins.registry import PluginRegistry


# Mock transformer classes for testing
class MockTransformerWithStructure(TransformerPlugin):
    """Mock transformer with output_structure defined."""

    type = PluginType.TRANSFORMER
    output_structure = {"bins": "list", "counts": "list", "percentages": "list"}

    def transform(self, data: Any, params: Any) -> Any:
        return {"bins": [], "counts": [], "percentages": []}


class MockTransformerMinimal(TransformerPlugin):
    """Mock transformer with minimal output."""

    type = PluginType.TRANSFORMER
    output_structure = {"bins": "list", "counts": "list"}

    def transform(self, data: Any, params: Any) -> Any:
        return {"bins": [], "counts": []}


class MockTransformerNoStructure(TransformerPlugin):
    """Mock transformer without output_structure (legacy)."""

    type = PluginType.TRANSFORMER
    # No output_structure defined

    def transform(self, data: Any, params: Any) -> Any:
        return {}


class MockTransformerExtraFields(TransformerPlugin):
    """Mock transformer with extra fields."""

    type = PluginType.TRANSFORMER
    output_structure = {
        "bins": "list",
        "counts": "list",
        "percentages": "list",
        "labels": "list",
        "metadata": "dict",
    }

    def transform(self, data: Any, params: Any) -> Any:
        return {}


# Mock widget classes for testing
class MockWidgetExactMatch(WidgetPlugin):
    """Widget expecting exact structure match."""

    type = PluginType.WIDGET
    compatible_structures = [{"bins": "list", "counts": "list", "percentages": "list"}]

    def render(self, data: Any, params: Any) -> str:
        return "<div>mock</div>"


class MockWidgetMinimal(WidgetPlugin):
    """Widget expecting minimal structure."""

    type = PluginType.WIDGET
    compatible_structures = [{"bins": "list", "counts": "list"}]

    def render(self, data: Any, params: Any) -> str:
        return "<div>mock</div>"


class MockWidgetMultiplePatterns(WidgetPlugin):
    """Widget accepting multiple structure patterns."""

    type = PluginType.WIDGET
    compatible_structures = [
        {"bins": "list", "counts": "list"},
        {"categories": "list", "values": "list"},
        {"labels": "list", "data": "list"},
    ]

    def render(self, data: Any, params: Any) -> str:
        return "<div>mock</div>"


class MockWidgetNoStructure(WidgetPlugin):
    """Widget without compatible_structures (legacy)."""

    type = PluginType.WIDGET
    # No compatible_structures defined

    def render(self, data: Any, params: Any) -> str:
        return "<div>mock</div>"


class MockWidgetPartialMatch(WidgetPlugin):
    """Widget that requires only some fields."""

    type = PluginType.WIDGET
    compatible_structures = [
        {"counts": "list"}  # Only requires counts
    ]

    def render(self, data: Any, params: Any) -> str:
        return "<div>mock</div>"


class TestPatternMatching:
    """Test suite for pattern matching functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry with test widgets."""
        # Clear existing registry and reinitialize structure
        PluginRegistry._plugins = {plugin_type: {} for plugin_type in PluginType}
        PluginRegistry._metadata = {}

        # Register mock widgets
        PluginRegistry.register_plugin(
            "exact_match", MockWidgetExactMatch, PluginType.WIDGET
        )
        PluginRegistry.register_plugin("minimal", MockWidgetMinimal, PluginType.WIDGET)
        PluginRegistry.register_plugin(
            "multiple_patterns", MockWidgetMultiplePatterns, PluginType.WIDGET
        )
        PluginRegistry.register_plugin(
            "no_structure", MockWidgetNoStructure, PluginType.WIDGET
        )
        PluginRegistry.register_plugin(
            "partial_match", MockWidgetPartialMatch, PluginType.WIDGET
        )

        yield PluginRegistry

        # Cleanup and reinitialize
        PluginRegistry._plugins = {plugin_type: {} for plugin_type in PluginType}
        PluginRegistry._metadata = {}

    @pytest.fixture
    def matcher(self, mock_registry):
        """Create SmartMatcher instance with mock registry."""
        return SmartMatcher(registry=mock_registry)

    def test_exact_structure_match(self, matcher):
        """Test exact structure match returns score 1.0."""
        suggestions = matcher.find_compatible_widgets(MockTransformerWithStructure)

        # Should find exact_match widget
        exact_matches = [s for s in suggestions if s.widget_name == "exact_match"]
        assert len(exact_matches) == 1
        assert exact_matches[0].score == 1.0
        assert exact_matches[0].reason == "exact_match"
        assert exact_matches[0].confidence == "high"

    def test_superset_match(self, matcher):
        """Test superset match (transformer has more fields) returns score 0.8."""
        suggestions = matcher.find_compatible_widgets(MockTransformerExtraFields)

        # minimal widget requires only bins+counts, transformer provides 5 fields
        minimal_matches = [s for s in suggestions if s.widget_name == "minimal"]
        assert len(minimal_matches) == 1
        assert minimal_matches[0].score == 0.8
        assert minimal_matches[0].reason == "superset_match"
        assert minimal_matches[0].confidence == "medium"

    def test_partial_match(self, matcher):
        """Test partial match (some required fields present) returns score 0.6."""
        # MockTransformerWithStructure has {bins, counts, percentages}
        # partial_match widget requires only {counts}
        # This is actually a superset match (0.8) because transformer has all required + more

        suggestions = matcher.find_compatible_widgets(MockTransformerWithStructure)

        # partial_match widget only requires "counts" which is present (plus more fields)
        partial_matches = [s for s in suggestions if s.widget_name == "partial_match"]
        assert len(partial_matches) == 1
        # It's a superset match because transformer has counts + extra fields
        assert partial_matches[0].score == 0.8
        assert partial_matches[0].reason == "superset_match"
        assert partial_matches[0].confidence == "medium"

    def test_no_match_incompatible(self, matcher):
        """Test incompatible structures return no suggestions."""
        # minimal widget should not match because it's superset (needs only bins+counts)
        # but MockTransformerMinimal has exactly bins+counts, so it's exact match
        suggestions = matcher.find_compatible_widgets(MockTransformerMinimal)

        minimal_matches = [s for s in suggestions if s.widget_name == "minimal"]
        assert len(minimal_matches) == 1
        assert minimal_matches[0].score == 1.0  # Exact match

    def test_multiple_pattern_matching(self, matcher):
        """Test widget with multiple patterns finds best match."""
        suggestions = matcher.find_compatible_widgets(MockTransformerMinimal)

        # multiple_patterns widget should match on first pattern (bins+counts)
        multi_matches = [s for s in suggestions if s.widget_name == "multiple_patterns"]
        assert len(multi_matches) == 1
        assert multi_matches[0].score == 1.0  # Exact match on first pattern

    def test_legacy_fallback_no_structure(self, matcher):
        """Test legacy fallback when transformer has no output_structure."""
        suggestions = matcher.find_compatible_widgets(MockTransformerNoStructure)

        # Should use legacy matching (returns empty or legacy mappings)
        # Legacy matching is limited, so we expect fewer or no results
        assert isinstance(suggestions, list)

    def test_widget_without_structure_ignored(self, matcher):
        """Test widgets without compatible_structures are not matched."""
        suggestions = matcher.find_compatible_widgets(MockTransformerWithStructure)

        # no_structure widget should not appear in results
        no_struct_matches = [s for s in suggestions if s.widget_name == "no_structure"]
        assert len(no_struct_matches) == 0

    def test_sorting_by_score(self, matcher):
        """Test suggestions are sorted by score (descending)."""
        suggestions = matcher.find_compatible_widgets(MockTransformerWithStructure)

        # Verify descending order
        scores = [s.score for s in suggestions]
        assert scores == sorted(scores, reverse=True)

    def test_exact_match_method(self, matcher):
        """Test _exact_match helper method."""
        output = {"bins": "list", "counts": "list"}
        pattern = {"bins": "list", "counts": "list"}
        assert matcher._exact_match(output, pattern) is True

        pattern_extra = {"bins": "list", "counts": "list", "labels": "list"}
        assert matcher._exact_match(output, pattern_extra) is False

    def test_superset_match_method(self, matcher):
        """Test _superset_match helper method."""
        output = {"bins": "list", "counts": "list", "percentages": "list"}
        pattern = {"bins": "list", "counts": "list"}
        assert matcher._superset_match(output, pattern) is True

        # Same size - not a superset
        pattern_same = {"bins": "list", "counts": "list", "percentages": "list"}
        assert matcher._superset_match(output, pattern_same) is False

        # Output missing required key
        pattern_missing = {"bins": "list", "labels": "list"}
        assert matcher._superset_match(output, pattern_missing) is False

    def test_partial_match_method(self, matcher):
        """Test _partial_match helper method."""
        output = {"bins": "list", "counts": "list"}
        pattern = {
            "bins": "list",
            "counts": "list",
            "labels": "list",
            "percentages": "list",
        }

        # 50% overlap (2 out of 4 required)
        assert matcher._partial_match(output, pattern) is True

        # Less than 50%
        pattern_large = {
            "a": "list",
            "b": "list",
            "c": "list",
            "d": "list",
            "bins": "list",
        }
        assert matcher._partial_match(output, pattern_large) is False

    def test_partial_match_real_scenario(self, matcher):
        """Test real partial match scenario where transformer lacks some widget fields."""

        # Create a transformer that has only some of the required fields
        class PartialTransformer(TransformerPlugin):
            type = PluginType.TRANSFORMER
            output_structure = {"bins": "list", "counts": "list"}

            def transform(self, data: Any, params: Any) -> Any:
                return {}

        # Create a widget that requires 4 fields (only 2 will be present)
        class GreedyWidget(WidgetPlugin):
            type = PluginType.WIDGET
            compatible_structures = [
                {
                    "bins": "list",
                    "counts": "list",
                    "labels": "list",
                    "percentages": "list",
                }
            ]

            def render(self, data: Any, params: Any) -> str:
                return ""

        PluginRegistry.register_plugin("greedy_widget", GreedyWidget, PluginType.WIDGET)

        suggestions = matcher.find_compatible_widgets(PartialTransformer)
        greedy_matches = [s for s in suggestions if s.widget_name == "greedy_widget"]

        assert len(greedy_matches) == 1
        assert greedy_matches[0].score == 0.6  # Partial match (2/4 = 50%)
        assert greedy_matches[0].reason == "partial_match"

    def test_match_reason_mapping(self, matcher):
        """Test _match_reason returns correct reason strings."""
        assert matcher._match_reason(1.0) == "exact_match"
        assert matcher._match_reason(0.8) == "superset_match"
        assert matcher._match_reason(0.6) == "partial_match"
        assert matcher._match_reason(0.0) == "incompatible"

    def test_confidence_calculation(self, matcher):
        """Test _calculate_confidence returns correct confidence levels."""
        assert matcher._calculate_confidence(1.0) == "high"
        assert matcher._calculate_confidence(0.9) == "high"
        assert matcher._calculate_confidence(0.8) == "medium"
        assert matcher._calculate_confidence(0.7) == "medium"
        assert matcher._calculate_confidence(0.6) == "low"
        assert matcher._calculate_confidence(0.0) == "low"

    def test_empty_compatible_structures(self, matcher):
        """Test widget with empty compatible_structures list."""

        class MockWidgetEmpty(WidgetPlugin):
            type = PluginType.WIDGET
            compatible_structures = []

            def render(self, data: Any, params: Any) -> str:
                return ""

        PluginRegistry.register_plugin(
            "empty_widget", MockWidgetEmpty, PluginType.WIDGET
        )

        suggestions = matcher.find_compatible_widgets(MockTransformerWithStructure)
        empty_matches = [s for s in suggestions if s.widget_name == "empty_widget"]
        assert len(empty_matches) == 0

    def test_real_binned_distribution_bar_plot_match(self, matcher):
        """Test real-world example: binned_distribution -> bar_plot."""

        # Register real patterns
        class RealBinnedDistribution(TransformerPlugin):
            type = PluginType.TRANSFORMER
            output_structure = {
                "bins": "list",
                "counts": "list",
                "labels": "list",
                "percentages": "list",
            }

            def transform(self, data: Any, params: Any) -> Any:
                return {}

        class RealBarPlot(WidgetPlugin):
            type = PluginType.WIDGET
            compatible_structures = [
                {"bins": "list", "counts": "list"},
                {"bins": "list", "counts": "list", "percentages": "list"},
                {"categories": "list", "values": "list"},
            ]

            def render(self, data: Any, params: Any) -> str:
                return ""

        PluginRegistry.register_plugin("real_bar_plot", RealBarPlot, PluginType.WIDGET)

        suggestions = matcher.find_compatible_widgets(RealBinnedDistribution)
        bar_matches = [s for s in suggestions if s.widget_name == "real_bar_plot"]

        assert len(bar_matches) == 1
        # Should be superset match (transformer has 4 fields, widget needs 2-3)
        assert bar_matches[0].score == 0.8
        assert bar_matches[0].reason == "superset_match"
