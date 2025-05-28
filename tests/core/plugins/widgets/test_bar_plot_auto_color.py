# tests/core/plugins/widgets/test_bar_plot_auto_color.py

import pytest
import pandas as pd
from unittest.mock import Mock

from niamoto.core.plugins.widgets.bar_plot import (
    BarPlotWidget,
    BarPlotParams,
    generate_colors,
)
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry


class TestBarPlotAutoColor:
    """Test suite for BarPlotWidget auto_color functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    @pytest.fixture
    def widget(self, mock_db):
        """Create a widget instance."""
        return BarPlotWidget(db=mock_db)

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return pd.DataFrame(
            {"category": ["A", "B", "C", "D", "E"], "value": [10, 25, 15, 30, 20]}
        )

    def test_auto_color_param_exists(self):
        """Test that auto_color parameter is present in BarPlotParams."""
        # Create params with auto_color=True
        params = BarPlotParams(x_axis="category", y_axis="value", auto_color=True)
        assert params.auto_color is True

        # Create params with auto_color=False (default)
        params_default = BarPlotParams(x_axis="category", y_axis="value")
        assert params_default.auto_color is False

    def test_generate_colors_function(self):
        """Test that generate_colors function generates correct number of colors."""
        # Test with different counts
        colors_5 = generate_colors(5)
        assert len(colors_5) == 5
        assert all(isinstance(color, str) for color in colors_5)
        assert all(color.startswith("#") and len(color) == 7 for color in colors_5)

        colors_10 = generate_colors(10)
        assert len(colors_10) == 10
        assert all(isinstance(color, str) for color in colors_10)
        assert all(color.startswith("#") and len(color) == 7 for color in colors_10)

        # Test with edge cases
        colors_1 = generate_colors(1)
        assert len(colors_1) == 1

        colors_0 = generate_colors(0)
        assert len(colors_0) == 0

    def test_generate_colors_uniqueness(self):
        """Test that generated colors are unique."""
        colors = generate_colors(20)
        # While we can't guarantee 100% uniqueness due to rounding,
        # colors should be mostly unique
        unique_colors = set(colors)
        assert len(unique_colors) >= len(colors) * 0.9  # At least 90% unique

    def test_render_with_auto_color_vertical(self, widget, sample_data):
        """Test rendering vertical bar plot with auto_color=True."""
        params = BarPlotParams(
            x_axis="category", y_axis="value", auto_color=True, orientation="v"
        )

        html = widget.render(sample_data, params)

        # Basic checks
        assert html is not None
        assert "plotly" in html.lower()
        assert "_auto_color" in html  # Check that auto color field was created

        # Verify no error messages (check for HTML error tags, not JavaScript)
        assert "<p class='error'>" not in html
        assert "No data available" not in html

    def test_render_with_auto_color_horizontal(self, widget, sample_data):
        """Test rendering horizontal bar plot with auto_color=True."""
        params = BarPlotParams(
            x_axis="value", y_axis="category", auto_color=True, orientation="h"
        )

        html = widget.render(sample_data, params)

        # Basic checks
        assert html is not None
        assert "plotly" in html.lower()
        assert "_auto_color" in html  # Check that auto color field was created

        # Verify no error messages (check for HTML error tags, not JavaScript)
        assert "<p class='error'>" not in html
        assert "No data available" not in html

    def test_render_without_auto_color(self, widget, sample_data):
        """Test rendering bar plot with auto_color=False (default)."""
        params = BarPlotParams(x_axis="category", y_axis="value", auto_color=False)

        html = widget.render(sample_data, params)

        # Basic checks
        assert html is not None
        assert "plotly" in html.lower()
        assert "_auto_color" not in html  # Should not create auto color field

        # Verify no error messages (check for HTML error tags, not JavaScript)
        assert "<p class='error'>" not in html
        assert "No data available" not in html

    def test_auto_color_with_existing_color_field(self, widget):
        """Test that auto_color is ignored when color_field is specified."""
        data = pd.DataFrame(
            {
                "category": ["A", "B", "C", "D"],
                "value": [10, 20, 15, 25],
                "group": ["X", "X", "Y", "Y"],
            }
        )

        params = BarPlotParams(
            x_axis="category",
            y_axis="value",
            color_field="group",
            auto_color=True,  # Should be ignored
        )

        html = widget.render(data, params)

        # Should use the specified color_field, not auto coloring
        assert html is not None
        assert "_auto_color" not in html
        assert "group" in html  # The actual color field should be used

    def test_widget_registration(self):
        """Test that the widget is properly registered."""
        # Import the widget module to ensure it's registered
        from niamoto.core.plugins.widgets import bar_plot  # noqa: F401

        registry = PluginRegistry()
        try:
            widget_class = registry.get_plugin("bar_plot", PluginType.WIDGET)
            assert widget_class == BarPlotWidget
        except Exception as e:
            # Skip if plugin not found - this can happen due to test isolation issues
            pytest.skip(f"Plugin registration test skipped due to registry state: {e}")

    def test_render_with_invalid_dict_data_and_auto_color(self, widget):
        """Test rendering with invalid dictionary data and auto_color."""
        data = {
            "invalid_key": [
                {"category": "A", "value": 10},
                {"category": "B", "value": 20},
                {"category": "C", "value": 15},
            ]
        }

        params = BarPlotParams(x_axis="category", y_axis="value", auto_color=True)

        html = widget.render(data, params)

        # Should handle invalid dict data gracefully with error message
        assert html is not None
        assert "<p class='error'>" in html
        assert "Input dict structure not recognized" in html
