import pandas as pd
from unittest.mock import Mock, patch
import numpy as np

from niamoto.core.plugins.widgets.line_plot import (
    LinePlotWidget,
    LinePlotParams,
)
from tests.common.base_test import NiamotoTestCase


class TestLinePlotWidget(NiamotoTestCase):
    """Test cases for LinePlotWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = LinePlotWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, LinePlotParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_get_nested_data_simple_key(self):
        """Test _get_nested_data with simple key."""
        data = {"temperature": [20, 25, 30], "humidity": [60, 65, 70]}

        result = self.widget._get_nested_data(data, "temperature")
        self.assertEqual(result, [20, 25, 30])

    def test_get_nested_data_nested_key(self):
        """Test _get_nested_data with nested keys."""
        data = {
            "sensors": {
                "outdoor": {"temperature": [18, 22, 25], "humidity": [55, 60, 65]}
            }
        }

        result = self.widget._get_nested_data(data, "sensors.outdoor.temperature")
        self.assertEqual(result, [18, 22, 25])

    def test_get_nested_data_missing_key(self):
        """Test _get_nested_data with missing keys."""
        data = {"temperature": [20, 25]}

        result = self.widget._get_nested_data(data, "pressure")
        self.assertIsNone(result)

    def test_render_basic_dataframe(self):
        """Test rendering with basic DataFrame."""
        df = pd.DataFrame(
            {
                "time": pd.date_range("2023-01-01", periods=5, freq="D"),
                "temperature": [20, 22, 25, 23, 21],
                "humidity": [60, 65, 70, 68, 62],
            }
        )

        params = LinePlotParams(x_axis="time", y_axis="temperature")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_multiple_y_axis(self):
        """Test rendering with multiple Y-axis fields."""
        df = pd.DataFrame(
            {
                "time": pd.date_range("2023-01-01", periods=4, freq="D"),
                "temp_indoor": [22, 23, 24, 23],
                "temp_outdoor": [18, 20, 22, 19],
                "humidity": [60, 65, 70, 68],
            }
        )

        params = LinePlotParams(x_axis="time", y_axis=["temp_indoor", "temp_outdoor"])

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_color_field(self):
        """Test rendering with color grouping field."""
        df = pd.DataFrame(
            {
                "month": ["Jan", "Feb", "Mar", "Apr", "Jan", "Feb", "Mar", "Apr"],
                "temperature": [20, 22, 25, 28, 18, 20, 23, 26],
                "location": [
                    "North",
                    "North",
                    "North",
                    "North",
                    "South",
                    "South",
                    "South",
                    "South",
                ],
            }
        )

        params = LinePlotParams(
            x_axis="month", y_axis="temperature", color_field="location"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_markers(self):
        """Test rendering with markers enabled."""
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 15, 13, 17, 20]})

        params = LinePlotParams(x_axis="x", y_axis="y", markers=True)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_line_shapes(self):
        """Test rendering with different line shapes."""
        df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 15, 13, 17]})

        line_shapes = ["linear", "spline", "hv", "vh"]

        for shape in line_shapes:
            with self.subTest(line_shape=shape):
                params = LinePlotParams(x_axis="x", y_axis="y", line_shape=shape)

                result = self.widget.render(df, params)

                # Verify successful rendering
                self.assertIsInstance(result, str)
                self.assertNotIn("<p class='error'>", result)
                self.assertIn("plotly-graph-div", result)

    def test_render_with_hover_data(self):
        """Test rendering with hover data."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2023-01-01", periods=3, freq="D"),
                "price": [100, 105, 102],
                "volume": [1000, 1200, 950],
                "company": ["CompanyA", "CompanyA", "CompanyA"],
            }
        )

        params = LinePlotParams(
            x_axis="date", y_axis="price", hover_name="company", hover_data=["volume"]
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_log_y(self):
        """Test rendering with logarithmic Y-axis."""
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, 100, 1000, 10000, 100000]})

        params = LinePlotParams(x_axis="x", y_axis="y", log_y=True)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_custom_labels(self):
        """Test rendering with custom axis labels."""
        df = pd.DataFrame(
            {"time_period": [1, 2, 3, 4], "measurement": [20, 25, 22, 28]}
        )

        params = LinePlotParams(
            x_axis="time_period",
            y_axis="measurement",
            labels={"time_period": "Time (hours)", "measurement": "Temperature (°C)"},
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_color_discrete_map(self):
        """Test rendering with custom color mapping."""
        df = pd.DataFrame(
            {
                "month": ["Jan", "Feb", "Mar", "Jan", "Feb", "Mar"],
                "temp": [20, 22, 25, 18, 20, 23],
                "region": ["North", "North", "North", "South", "South", "South"],
            }
        )

        color_map = {"North": "#ff6b35", "South": "#1fb99d"}

        params = LinePlotParams(
            x_axis="month",
            y_axis="temp",
            color_field="region",
            color_discrete_map=color_map,
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_direct_keys(self):
        """Test rendering with dictionary containing direct keys."""
        data = {"time": [1, 2, 3, 4, 5], "values": [10, 15, 13, 17, 20]}

        params = LinePlotParams(x_axis="time", y_axis="values")

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_fragmentation_structure(self):
        """Test rendering with fragmentation distribution structure."""
        data = {"sizes": [1, 2, 3, 4, 5], "areas": [100, 150, 130, 170, 200]}

        params = LinePlotParams(x_axis="sizes", y_axis="areas")

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_cumulative_structure(self):
        """Test rendering with cumulative data structure."""
        data = {"sizes": [1, 2, 3, 4], "cumulative": [25, 50, 75, 100]}

        params = LinePlotParams(x_axis="sizes", y_axis="cumulative")

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_nested_data(self):
        """Test rendering with nested dictionary data."""
        data = {
            "elevation": {
                "classes": [0, 100, 200, 300],
                "distribution": [30, 25, 20, 25],
            }
        }

        params = LinePlotParams(
            x_axis="elevation.classes", y_axis="elevation.distribution"
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_none_data(self):
        """Test rendering with None data."""
        params = LinePlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(None, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the line plot", result)

    def test_render_empty_dataframe(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()
        params = LinePlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the line plot", result)

    def test_render_invalid_data_type(self):
        """Test rendering with invalid data type."""
        data = "invalid string data"
        params = LinePlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the line plot", result)

    def test_render_missing_columns(self):
        """Test rendering with missing required columns."""
        df = pd.DataFrame({"time": [1, 2, 3], "other_field": [10, 20, 30]})

        params = LinePlotParams(x_axis="time", y_axis="missing_field")

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Missing columns", result)

    def test_render_missing_color_field(self):
        """Test rendering with missing color field."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})

        params = LinePlotParams(x_axis="x", y_axis="y", color_field="missing_color")

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Missing columns", result)

    def test_render_datetime_conversion(self):
        """Test rendering with automatic datetime conversion."""
        df = pd.DataFrame(
            {
                "date_str": ["2023-01-01", "2023-01-02", "2023-01-03"],
                "value": [10, 15, 12],
            }
        )

        params = LinePlotParams(x_axis="date_str", y_axis="value")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_datetime_conversion_failure(self):
        """Test rendering when datetime conversion fails."""
        df = pd.DataFrame(
            {
                "text_field": ["not_a_date", "also_not_date", "nope"],
                "value": [10, 15, 12],
            }
        )

        params = LinePlotParams(x_axis="text_field", y_axis="value")

        # Should still render successfully even if datetime conversion fails
        result = self.widget.render(df, params)

        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_sorting_numeric_x(self):
        """Test rendering with automatic sorting for numeric X-axis."""
        df = pd.DataFrame(
            {
                "x": [3, 1, 4, 2],  # Unsorted
                "y": [30, 10, 40, 20],
            }
        )

        params = LinePlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_sorting_exception(self):
        """Test rendering when sorting raises an exception."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})

        params = LinePlotParams(x_axis="x", y_axis="y")

        # Mock sort_values to raise an exception
        with patch.object(
            pd.DataFrame, "sort_values", side_effect=Exception("Sort error")
        ):
            result = self.widget.render(df, params)

            # Should still render successfully despite sorting error
            self.assertIsInstance(result, str)
            self.assertNotIn("<p class='error'>", result)
            self.assertIn("plotly-graph-div", result)

    def test_render_plotly_exception(self):
        """Test handling of Plotly rendering exceptions."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})

        params = LinePlotParams(x_axis="x", y_axis="y")

        # Mock plotly.express.line to raise an exception
        with patch("plotly.express.line", side_effect=Exception("Plotly error")):
            result = self.widget.render(df, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error generating line plot", result)
            self.assertIn("Plotly error", result)

    def test_render_with_nan_values(self):
        """Test rendering with NaN values in data."""
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [10, np.nan, 30, np.nan, 50]})

        params = LinePlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        # Verify successful rendering (Plotly should handle NaN values)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_complex_time_series(self):
        """Test rendering with complex time series scenario."""
        dates = pd.date_range("2023-01-01", periods=30, freq="D")

        df = pd.DataFrame(
            {
                "date": dates,
                "temperature_north": 20
                + 5 * np.sin(np.arange(30) * 0.2)
                + np.random.normal(0, 1, 30),
                "temperature_south": 25
                + 3 * np.cos(np.arange(30) * 0.15)
                + np.random.normal(0, 0.8, 30),
                "humidity": 60
                + 10 * np.sin(np.arange(30) * 0.1)
                + np.random.normal(0, 2, 30),
                "region": ["North"] * 15 + ["South"] * 15,
            }
        )

        # Reshape data for multiple lines
        df_melted = pd.melt(
            df,
            id_vars=["date", "region", "humidity"],
            value_vars=["temperature_north", "temperature_south"],
            var_name="sensor_type",
            value_name="temperature",
        )

        params = LinePlotParams(
            title="Temperature Monitoring",
            description="Multi-region temperature trends over time",
            x_axis="date",
            y_axis="temperature",
            color_field="sensor_type",
            markers=True,
            line_shape="spline",
            hover_name="sensor_type",
            hover_data=["humidity"],
            labels={
                "date": "Date",
                "temperature": "Temperature (°C)",
                "sensor_type": "Sensor",
            },
            color_discrete_map={
                "temperature_north": "#1f77b4",
                "temperature_south": "#ff7f0e",
            },
        )

        result = self.widget.render(df_melted, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_dict_processing_failure(self):
        """Test rendering when dictionary processing fails."""
        data = {"some_key": "some_value", "another_key": [1, 2, 3]}

        params = LinePlotParams(x_axis="missing_x", y_axis="missing_y")

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the line plot", result)


class TestLinePlotParams(NiamotoTestCase):
    """Test cases for LinePlotParams validation."""

    def test_params_minimal_required(self):
        """Test parameters with minimal required fields."""
        params = LinePlotParams(x_axis="time", y_axis="value")

        self.assertEqual(params.x_axis, "time")
        self.assertEqual(params.y_axis, "value")
        self.assertIsNone(params.title)
        self.assertIsNone(params.description)

    def test_params_y_axis_string(self):
        """Test parameters with string Y-axis."""
        params = LinePlotParams(x_axis="time", y_axis="temperature")

        self.assertEqual(params.y_axis, "temperature")
        self.assertIsInstance(params.y_axis, str)

    def test_params_y_axis_list(self):
        """Test parameters with list of Y-axis fields."""
        params = LinePlotParams(x_axis="time", y_axis=["temp1", "temp2", "temp3"])

        self.assertEqual(params.y_axis, ["temp1", "temp2", "temp3"])
        self.assertIsInstance(params.y_axis, list)

    def test_params_all_fields(self):
        """Test parameters with all fields specified."""
        params = LinePlotParams(
            title="Test Plot",
            description="Test description",
            x_axis="time",
            y_axis=["value1", "value2"],
            color_field="category",
            line_group="group_field",
            markers=True,
            line_shape="spline",
            hover_name="hover_field",
            hover_data=["field1", "field2"],
            color_discrete_map={"A": "red", "B": "blue"},
            color_continuous_scale="viridis",
            range_y=[0, 100],
            labels={"time": "Time", "value1": "Value 1"},
            log_y=True,
        )

        self.assertEqual(params.title, "Test Plot")
        self.assertEqual(params.description, "Test description")
        self.assertEqual(params.x_axis, "time")
        self.assertEqual(params.y_axis, ["value1", "value2"])
        self.assertEqual(params.color_field, "category")
        self.assertEqual(params.line_group, "group_field")
        self.assertTrue(params.markers)
        self.assertEqual(params.line_shape, "spline")
        self.assertEqual(params.hover_name, "hover_field")
        self.assertEqual(params.hover_data, ["field1", "field2"])
        self.assertEqual(params.color_discrete_map, {"A": "red", "B": "blue"})
        self.assertEqual(params.color_continuous_scale, "viridis")
        self.assertEqual(params.range_y, [0, 100])
        self.assertEqual(params.labels, {"time": "Time", "value1": "Value 1"})
        self.assertTrue(params.log_y)

    def test_params_defaults(self):
        """Test parameter default values."""
        params = LinePlotParams(x_axis="x", y_axis="y")

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertIsNone(params.color_field)
        self.assertIsNone(params.line_group)
        self.assertFalse(params.markers)
        self.assertEqual(params.line_shape, "linear")
        self.assertIsNone(params.hover_name)
        self.assertIsNone(params.hover_data)
        self.assertIsNone(params.color_discrete_map)
        self.assertIsNone(params.color_continuous_scale)
        self.assertIsNone(params.range_y)
        self.assertIsNone(params.labels)
        self.assertFalse(params.log_y)

    def test_params_markers_options(self):
        """Test different markers parameter values."""
        # Boolean markers
        params1 = LinePlotParams(x_axis="x", y_axis="y", markers=True)
        self.assertTrue(params1.markers)

        params2 = LinePlotParams(x_axis="x", y_axis="y", markers=False)
        self.assertFalse(params2.markers)

        # String markers (field name)
        params3 = LinePlotParams(x_axis="x", y_axis="y", markers="symbol_field")
        self.assertEqual(params3.markers, "symbol_field")

    def test_params_line_shape_options(self):
        """Test different line shape values."""
        line_shapes = ["linear", "spline", "hv", "vh", "hvh", "vhv"]

        for shape in line_shapes:
            params = LinePlotParams(x_axis="x", y_axis="y", line_shape=shape)
            self.assertEqual(params.line_shape, shape)

    def test_params_validation_required_fields(self):
        """Test validation of required fields."""
        # Missing x_axis should raise error
        with self.assertRaises(ValueError):
            LinePlotParams(y_axis="y")

        # Missing y_axis should raise error
        with self.assertRaises(ValueError):
            LinePlotParams(x_axis="x")

    def test_params_range_y_validation(self):
        """Test range_y parameter validation."""
        # Valid range
        params1 = LinePlotParams(x_axis="x", y_axis="y", range_y=[0, 100])
        self.assertEqual(params1.range_y, [0, 100])

        # Negative values
        params2 = LinePlotParams(x_axis="x", y_axis="y", range_y=[-50, 50])
        self.assertEqual(params2.range_y, [-50, 50])

        # None
        params3 = LinePlotParams(x_axis="x", y_axis="y", range_y=None)
        self.assertIsNone(params3.range_y)

    def test_params_hover_data_types(self):
        """Test hover_data parameter with different types."""
        # List of strings
        params1 = LinePlotParams(
            x_axis="x", y_axis="y", hover_data=["field1", "field2"]
        )
        self.assertEqual(params1.hover_data, ["field1", "field2"])

        # Empty list
        params2 = LinePlotParams(x_axis="x", y_axis="y", hover_data=[])
        self.assertEqual(params2.hover_data, [])

        # None
        params3 = LinePlotParams(x_axis="x", y_axis="y", hover_data=None)
        self.assertIsNone(params3.hover_data)

    def test_params_boolean_fields(self):
        """Test boolean parameter fields."""
        # log_y True
        params1 = LinePlotParams(x_axis="x", y_axis="y", log_y=True)
        self.assertTrue(params1.log_y)

        # log_y False (default)
        params2 = LinePlotParams(x_axis="x", y_axis="y", log_y=False)
        self.assertFalse(params2.log_y)
