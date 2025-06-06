import pandas as pd
from unittest.mock import Mock, patch

from niamoto.core.plugins.widgets.radial_gauge import (
    RadialGaugeWidget,
    RadialGaugeParams,
)
from tests.common.base_test import NiamotoTestCase


class TestRadialGaugeWidget(NiamotoTestCase):
    """Test cases for RadialGaugeWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = RadialGaugeWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, RadialGaugeParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_get_nested_data_simple_key(self):
        """Test _get_nested_data with simple key."""
        data = {"temperature": 25.5, "humidity": 60}

        result = self.widget._get_nested_data(data, "temperature")
        self.assertEqual(result, 25.5)

        result = self.widget._get_nested_data(data, "humidity")
        self.assertEqual(result, 60)

    def test_get_nested_data_nested_key(self):
        """Test _get_nested_data with nested keys."""
        data = {
            "sensors": {
                "indoor": {"temperature": 22.5, "humidity": 45},
                "outdoor": {"temperature": 18.0, "humidity": 70},
            },
            "status": "active",
        }

        result = self.widget._get_nested_data(data, "sensors.indoor.temperature")
        self.assertEqual(result, 22.5)

        result = self.widget._get_nested_data(data, "sensors.outdoor.humidity")
        self.assertEqual(result, 70)

        result = self.widget._get_nested_data(data, "status")
        self.assertEqual(result, "active")

    def test_get_nested_data_missing_key(self):
        """Test _get_nested_data with missing keys."""
        data = {"temperature": 25.5}

        result = self.widget._get_nested_data(data, "pressure")
        self.assertIsNone(result)

        result = self.widget._get_nested_data(data, "sensors.temperature")
        self.assertIsNone(result)

    def test_get_nested_data_invalid_input(self):
        """Test _get_nested_data with invalid input."""
        result = self.widget._get_nested_data(None, "temperature")
        self.assertIsNone(result)

        result = self.widget._get_nested_data("invalid", "temperature")
        self.assertIsNone(result)

        result = self.widget._get_nested_data({"temp": 25}, "")
        self.assertIsNone(result)

    def test_render_dataframe_basic(self):
        """Test rendering with basic DataFrame."""
        df = pd.DataFrame({"temperature": [25.5, 22.0, 28.3], "humidity": [60, 55, 65]})

        params = RadialGaugeParams(
            value_field="temperature", max_value=50.0, title="Temperature Gauge"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dataframe_empty(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()

        params = RadialGaugeParams(value_field="temperature", max_value=50.0)

        result = self.widget.render(df, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data for gauge", result)

    def test_render_dataframe_missing_field(self):
        """Test rendering with missing value field in DataFrame."""
        df = pd.DataFrame({"humidity": [60, 55, 65], "pressure": [1013, 1015, 1010]})

        params = RadialGaugeParams(value_field="temperature", max_value=50.0)

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Value field 'temperature' missing", result)

    def test_render_series_basic(self):
        """Test rendering with pandas Series."""
        series = pd.Series([25.5, 22.0, 28.3])

        params = RadialGaugeParams(
            value_field="value",  # Not used for Series
            max_value=50.0,
        )

        result = self.widget.render(series, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_series_empty(self):
        """Test rendering with empty Series."""
        series = pd.Series([])

        params = RadialGaugeParams(value_field="value", max_value=50.0)

        result = self.widget.render(series, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data for gauge", result)

    def test_render_dict_simple(self):
        """Test rendering with simple dictionary."""
        data = {"temperature": 25.5, "humidity": 60, "status": "active"}

        params = RadialGaugeParams(value_field="temperature", max_value=50.0)

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_nested(self):
        """Test rendering with nested dictionary using dot notation."""
        data = {
            "sensors": {
                "indoor": {"temperature": 22.5, "humidity": 45},
                "outdoor": {"temperature": 18.0, "humidity": 70},
            }
        }

        params = RadialGaugeParams(
            value_field="sensors.indoor.temperature", max_value=50.0
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_missing_field(self):
        """Test rendering with missing field in dictionary."""
        data = {"humidity": 60, "pressure": 1013}

        params = RadialGaugeParams(value_field="temperature", max_value=50.0)

        result = self.widget.render(data, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Value field 'temperature' missing", result)

    def test_render_dict_missing_nested_field(self):
        """Test rendering with missing nested field in dictionary."""
        data = {"sensors": {"indoor": {"humidity": 45}}}

        params = RadialGaugeParams(
            value_field="sensors.indoor.temperature", max_value=50.0
        )

        result = self.widget.render(data, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Nested value field 'sensors.indoor.temperature' missing", result)

    def test_render_numeric_value_int(self):
        """Test rendering with integer value."""
        data = 25

        params = RadialGaugeParams(
            value_field="value",  # Not used for numeric
            max_value=100,
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_numeric_value_float(self):
        """Test rendering with float value."""
        data = 25.7

        params = RadialGaugeParams(value_field="value", max_value=100.0)

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_invalid_data_type(self):
        """Test rendering with invalid data type."""
        data = "invalid data"

        params = RadialGaugeParams(value_field="value", max_value=100)

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("Invalid data type for gauge", result)

    def test_render_none_value(self):
        """Test rendering when value extraction returns None."""
        data = {"other_field": 25}

        params = RadialGaugeParams(value_field="missing_field", max_value=100)

        result = self.widget.render(data, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Value field 'missing_field' missing", result)

    def test_render_non_numeric_value(self):
        """Test rendering with non-numeric value."""
        data = {"temperature": "invalid_temp"}

        params = RadialGaugeParams(value_field="temperature", max_value=100)

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("Gauge value is not numeric", result)

    def test_render_with_unit(self):
        """Test rendering with unit specification."""
        data = {"temperature": 25.5}

        params = RadialGaugeParams(value_field="temperature", max_value=50.0, unit="°C")

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_deprecated_units(self):
        """Test rendering with deprecated units parameter."""
        data = {"temperature": 25.5}

        params = RadialGaugeParams(
            value_field="temperature",
            max_value=50.0,
            units="°C",  # Deprecated parameter
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_value_format_decimal(self):
        """Test rendering with decimal value formatting."""
        data = {"temperature": 25.567}

        params = RadialGaugeParams(
            value_field="temperature", max_value=50.0, value_format=".1f"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_value_format_percentage(self):
        """Test rendering with percentage value formatting."""
        data = {"completion": 0.85}

        params = RadialGaugeParams(
            value_field="completion", max_value=1.0, value_format=".0%"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_style_classic_with_steps(self):
        """Test rendering with classic style and color steps."""
        data = {"score": 75}

        steps = [
            {"range": [0, 50], "color": "#ff4444"},
            {"range": [50, 80], "color": "#ffaa00"},
            {"range": [80, 100], "color": "#44ff44"},
        ]

        params = RadialGaugeParams(
            value_field="score", max_value=100, style_mode="classic", steps=steps
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_style_minimal(self):
        """Test rendering with minimal style."""
        data = {"value": 42}

        params = RadialGaugeParams(
            value_field="value", max_value=100, style_mode="minimal"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_style_gradient(self):
        """Test rendering with gradient style."""
        data = {"value": 65}

        params = RadialGaugeParams(
            value_field="value",
            max_value=100,
            style_mode="gradient",
            bar_color="#1fb99d",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_style_contextual_low_value(self):
        """Test rendering with contextual style for low value."""
        data = {"value": 20}  # Low value (20% of range)

        params = RadialGaugeParams(
            value_field="value", min_value=0, max_value=100, style_mode="contextual"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_style_contextual_medium_value(self):
        """Test rendering with contextual style for medium value."""
        data = {"value": 50}  # Medium value (50% of range)

        params = RadialGaugeParams(
            value_field="value", min_value=0, max_value=100, style_mode="contextual"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_style_contextual_high_value(self):
        """Test rendering with contextual style for high value."""
        data = {"value": 85}  # High value (85% of range)

        params = RadialGaugeParams(
            value_field="value", min_value=0, max_value=100, style_mode="contextual"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_threshold(self):
        """Test rendering with threshold line."""
        data = {"cpu_usage": 78}

        threshold = {
            "line": {"color": "red", "width": 4},
            "thickness": 0.75,
            "value": 80,
        }

        params = RadialGaugeParams(
            value_field="cpu_usage", max_value=100, threshold=threshold
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_bullet_shape(self):
        """Test rendering with bullet gauge shape."""
        data = {"progress": 65}

        params = RadialGaugeParams(
            value_field="progress", max_value=100, gauge_shape="bullet"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_hide_axis(self):
        """Test rendering with hidden axis."""
        data = {"value": 42}

        params = RadialGaugeParams(value_field="value", max_value=100, show_axis=False)

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_custom_colors(self):
        """Test rendering with custom colors."""
        data = {"value": 55}

        params = RadialGaugeParams(
            value_field="value",
            max_value=100,
            bar_color="#ff6b35",
            background_color="#f0f0f0",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_title_description(self):
        """Test rendering with title and description."""
        data = {"temperature": 23.5}

        params = RadialGaugeParams(
            value_field="temperature",
            max_value=50.0,
            title="Temperature Monitor",
            description="Current Room Temperature",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_custom_range(self):
        """Test rendering with custom min/max range."""
        data = {"temperature": -5.2}

        params = RadialGaugeParams(
            value_field="temperature", min_value=-20.0, max_value=40.0, unit="°C"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_plotly_exception(self):
        """Test handling of Plotly rendering exceptions."""
        data = {"value": 50}

        params = RadialGaugeParams(value_field="value", max_value=100)

        # Mock plotly Figure to raise an exception
        with patch(
            "plotly.graph_objects.Figure", side_effect=Exception("Plotly error")
        ):
            result = self.widget.render(data, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error generating gauge", result)
            self.assertIn("Plotly error", result)

    def test_render_numeric_conversion_exception(self):
        """Test handling of numeric conversion exceptions."""
        data = {"value": "complex_invalid_value"}

        params = RadialGaugeParams(value_field="value", max_value=100)

        # Mock pd.to_numeric to raise an exception
        with patch("pandas.to_numeric", side_effect=ValueError("Invalid conversion")):
            result = self.widget.render(data, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error processing gauge value", result)

    def test_render_complex_scenario(self):
        """Test rendering with complex scenario combining multiple features."""
        data = {
            "metrics": {
                "performance": {
                    "cpu_usage": 73.5,
                    "memory_usage": 58.2,
                    "disk_usage": 45.8,
                },
                "health": {"score": 0.82, "status": "good"},
            },
            "timestamp": "2023-12-01T10:30:00Z",
        }

        steps = [
            {"range": [0, 30], "color": "#28a745"},  # Green for good
            {"range": [30, 70], "color": "#ffc107"},  # Yellow for warning
            {"range": [70, 100], "color": "#dc3545"},  # Red for critical
        ]

        threshold = {
            "line": {"color": "#ff0000", "width": 3},
            "thickness": 0.8,
            "value": 80,
        }

        params = RadialGaugeParams(
            title="CPU Usage Monitor",
            description="Current CPU Usage",
            value_field="metrics.performance.cpu_usage",
            min_value=0,
            max_value=100,
            unit="%",
            steps=steps,
            threshold=threshold,
            bar_color="#007bff",
            background_color="#f8f9fa",
            gauge_shape="angular",
            style_mode="classic",
            show_axis=True,
            value_format=".1f",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_edge_cases_zero_value(self):
        """Test rendering with zero value."""
        data = {"value": 0}

        params = RadialGaugeParams(value_field="value", min_value=-10, max_value=10)

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_edge_cases_negative_value(self):
        """Test rendering with negative value."""
        data = {"value": -7.5}

        params = RadialGaugeParams(value_field="value", min_value=-10, max_value=10)

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_edge_cases_boundary_values(self):
        """Test rendering with boundary values."""
        # Test minimum value
        data = {"value": 0}
        params = RadialGaugeParams(value_field="value", min_value=0, max_value=100)
        result = self.widget.render(data, params)
        self.assertIn("plotly-graph-div", result)

        # Test maximum value
        data = {"value": 100}
        result = self.widget.render(data, params)
        self.assertIn("plotly-graph-div", result)

        # Test value exceeding range
        data = {"value": 150}
        result = self.widget.render(data, params)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_nan_value(self):
        """Test rendering with NaN value."""
        import numpy as np

        data = {"value": np.nan}

        params = RadialGaugeParams(value_field="value", max_value=100)

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("Gauge value is not numeric", result)


class TestRadialGaugeParams(NiamotoTestCase):
    """Test cases for RadialGaugeParams validation."""

    def test_params_minimal_required(self):
        """Test parameters with minimal required fields."""
        params = RadialGaugeParams(value_field="temperature", max_value=100)

        self.assertEqual(params.value_field, "temperature")
        self.assertEqual(params.max_value, 100)
        self.assertEqual(params.min_value, 0)  # Default
        self.assertIsNone(params.title)
        self.assertIsNone(params.description)

    def test_params_all_fields(self):
        """Test parameters with all fields specified."""
        steps = [{"range": [0, 50], "color": "red"}]
        threshold = {"line": {"color": "red", "width": 4}, "value": 80}

        params = RadialGaugeParams(
            title="Test Gauge",
            description="Test description",
            value_field="test_field",
            min_value=10,
            max_value=200,
            unit="units",
            steps=steps,
            threshold=threshold,
            bar_color="blue",
            background_color="gray",
            gauge_shape="bullet",
            style_mode="minimal",
            show_axis=False,
            value_format=".2f",
        )

        self.assertEqual(params.title, "Test Gauge")
        self.assertEqual(params.description, "Test description")
        self.assertEqual(params.value_field, "test_field")
        self.assertEqual(params.min_value, 10)
        self.assertEqual(params.max_value, 200)
        self.assertEqual(params.unit, "units")
        self.assertEqual(params.steps, steps)
        self.assertEqual(params.threshold, threshold)
        self.assertEqual(params.bar_color, "blue")
        self.assertEqual(params.background_color, "gray")
        self.assertEqual(params.gauge_shape, "bullet")
        self.assertEqual(params.style_mode, "minimal")
        self.assertFalse(params.show_axis)
        self.assertEqual(params.value_format, ".2f")

    def test_params_defaults(self):
        """Test parameter default values."""
        params = RadialGaugeParams(value_field="test", max_value=100)

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertEqual(params.min_value, 0)
        self.assertIsNone(params.unit)
        self.assertIsNone(params.steps)
        self.assertIsNone(params.threshold)
        self.assertEqual(params.bar_color, "cornflowerblue")
        self.assertEqual(params.background_color, "white")
        self.assertEqual(params.gauge_shape, "angular")
        self.assertEqual(params.style_mode, "classic")
        self.assertTrue(params.show_axis)
        self.assertIsNone(params.value_format)

    def test_params_gauge_shapes(self):
        """Test different gauge shape values."""
        # Angular shape
        params1 = RadialGaugeParams(
            value_field="test", max_value=100, gauge_shape="angular"
        )
        self.assertEqual(params1.gauge_shape, "angular")

        # Bullet shape
        params2 = RadialGaugeParams(
            value_field="test", max_value=100, gauge_shape="bullet"
        )
        self.assertEqual(params2.gauge_shape, "bullet")

    def test_params_style_modes(self):
        """Test different style mode values."""
        style_modes = ["classic", "minimal", "gradient", "contextual"]

        for mode in style_modes:
            params = RadialGaugeParams(
                value_field="test", max_value=100, style_mode=mode
            )
            self.assertEqual(params.style_mode, mode)

    def test_params_value_formats(self):
        """Test different value format strings."""
        formats = [".0f", ".1f", ".2f", ".0%", ".1%", "d"]

        for fmt in formats:
            params = RadialGaugeParams(
                value_field="test", max_value=100, value_format=fmt
            )
            self.assertEqual(params.value_format, fmt)

    def test_params_complex_steps(self):
        """Test parameters with complex color steps."""
        steps = [
            {"range": [0, 25], "color": "#ff0000"},
            {"range": [25, 50], "color": "#ff8800"},
            {"range": [50, 75], "color": "#ffff00"},
            {"range": [75, 100], "color": "#00ff00"},
        ]

        params = RadialGaugeParams(value_field="test", max_value=100, steps=steps)

        self.assertEqual(params.steps, steps)
        self.assertEqual(len(params.steps), 4)

    def test_params_complex_threshold(self):
        """Test parameters with complex threshold configuration."""
        threshold = {
            "line": {"color": "#dc3545", "width": 5},
            "thickness": 0.9,
            "value": 85,
            "fillcolor": "rgba(220, 53, 69, 0.2)",
        }

        params = RadialGaugeParams(
            value_field="test", max_value=100, threshold=threshold
        )

        self.assertEqual(params.threshold, threshold)

    def test_params_validation_required_fields(self):
        """Test validation of required fields."""
        # Missing value_field should raise error
        with self.assertRaises(ValueError):
            RadialGaugeParams(max_value=100)

        # Missing max_value should raise error
        with self.assertRaises(ValueError):
            RadialGaugeParams(value_field="test")

    def test_params_deprecated_units(self):
        """Test deprecated units parameter."""
        params = RadialGaugeParams(
            value_field="test", max_value=100, units="deprecated_unit"
        )

        self.assertEqual(params.units, "deprecated_unit")
        self.assertIsNone(params.unit)  # Should be None since unit takes precedence
