import pandas as pd
from unittest.mock import Mock, patch

from niamoto.core.plugins.widgets.diverging_bar_plot import (
    DivergingBarPlotWidget,
    DivergingBarPlotParams,
)
from tests.common.base_test import NiamotoTestCase


class TestDivergingBarPlotWidget(NiamotoTestCase):
    """Test cases for DivergingBarPlotWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = DivergingBarPlotWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, DivergingBarPlotParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_render_basic_horizontal(self):
        """Test rendering with basic horizontal diverging bar plot."""
        df = pd.DataFrame(
            {
                "region": ["North", "South", "East", "West", "Center"],
                "change": [15.5, -8.2, 22.1, -12.7, 3.4],
                "population": [1500, 800, 2200, 950, 1200],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="region", y_axis="change", title="Population Change by Region"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_basic_vertical(self):
        """Test rendering with basic vertical diverging bar plot."""
        df = pd.DataFrame({"category": ["A", "B", "C", "D"], "value": [10, -15, 8, -5]})

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="value", orientation="v"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_none_data(self):
        """Test rendering with None data."""
        params = DivergingBarPlotParams(x_axis="category", y_axis="value")

        result = self.widget.render(None, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the diverging bar plot", result)

    def test_render_empty_dataframe(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()

        params = DivergingBarPlotParams(x_axis="category", y_axis="value")

        result = self.widget.render(df, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the diverging bar plot", result)

    def test_render_invalid_data_type(self):
        """Test rendering with invalid data type."""
        data = "invalid string data"

        params = DivergingBarPlotParams(x_axis="category", y_axis="value")

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for the diverging bar plot", result)

    def test_render_missing_columns(self):
        """Test rendering with missing required columns."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "other_field": [1, 2, 3]})

        params = DivergingBarPlotParams(
            x_axis="category",
            y_axis="value",  # Missing column
        )

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Missing columns", result)

    def test_render_missing_hover_columns(self):
        """Test rendering with missing hover columns."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "value": [10, -5, 8]})

        params = DivergingBarPlotParams(
            x_axis="category",
            y_axis="value",
            hover_name="missing_hover",
            hover_data=["missing_data"],
        )

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Missing columns", result)

    def test_render_with_custom_colors(self):
        """Test rendering with custom positive and negative colors."""
        df = pd.DataFrame(
            {
                "metric": ["Increase", "Decrease", "Growth", "Loss"],
                "value": [25, -15, 30, -10],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="metric",
            y_axis="value",
            color_positive="#00ff00",
            color_negative="#ff0000",
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_custom_threshold(self):
        """Test rendering with custom threshold value."""
        df = pd.DataFrame(
            {"item": ["A", "B", "C", "D", "E"], "score": [5, 8, 2, 12, 7]}
        )

        params = DivergingBarPlotParams(
            x_axis="item",
            y_axis="score",
            threshold=7.0,  # Values >= 7 are positive (green), < 7 are negative (red)
            color_positive="#4CAF50",
            color_negative="#F44336",
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_sorting_enabled(self):
        """Test rendering with value sorting enabled."""
        df = pd.DataFrame(
            {
                "category": ["High", "Low", "Medium", "Very Low"],
                "value": [20, -15, 5, -25],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="value", sort_values=True
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_sorting_disabled(self):
        """Test rendering with value sorting disabled."""
        df = pd.DataFrame(
            {"category": ["First", "Second", "Third"], "value": [15, -10, 5]}
        )

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="value", sort_values=False
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_hover_name(self):
        """Test rendering with hover name field."""
        df = pd.DataFrame(
            {
                "region": ["North", "South", "East"],
                "change_pct": [12.5, -8.3, 4.7],
                "full_name": ["Northern Region", "Southern Region", "Eastern Region"],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="region", y_axis="change_pct", hover_name="full_name"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_hover_data(self):
        """Test rendering with additional hover data."""
        df = pd.DataFrame(
            {
                "country": ["USA", "Germany", "Japan", "Brazil"],
                "gdp_change": [2.3, -1.5, 0.8, -2.1],
                "population": [331, 83, 126, 213],
                "continent": ["North America", "Europe", "Asia", "South America"],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="country",
            y_axis="gdp_change",
            hover_name="country",
            hover_data=["population", "continent"],
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_custom_axis_titles(self):
        """Test rendering with custom axis titles."""
        df = pd.DataFrame(
            {
                "dept": ["Sales", "Marketing", "IT", "HR"],
                "budget_change": [15000, -5000, 8000, -2000],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="dept",
            y_axis="budget_change",
            xaxis_title="Department",
            yaxis_title="Budget Change ($)",
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_all_positive_values(self):
        """Test rendering with all positive values."""
        df = pd.DataFrame({"item": ["A", "B", "C", "D"], "value": [10, 15, 8, 20]})

        params = DivergingBarPlotParams(x_axis="item", y_axis="value", threshold=0.0)

        result = self.widget.render(df, params)

        # Verify successful rendering (all bars should be positive color)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_all_negative_values(self):
        """Test rendering with all negative values."""
        df = pd.DataFrame({"item": ["X", "Y", "Z"], "value": [-5, -12, -3]})

        params = DivergingBarPlotParams(x_axis="item", y_axis="value", threshold=0.0)

        result = self.widget.render(df, params)

        # Verify successful rendering (all bars should be negative color)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_zero_values(self):
        """Test rendering with zero values."""
        df = pd.DataFrame(
            {
                "category": ["Neutral", "Positive", "Negative", "Zero"],
                "change": [0, 10, -5, 0.0],
            }
        )

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="change", threshold=0.0
        )

        result = self.widget.render(df, params)

        # Verify successful rendering (zero values should be treated as positive >= threshold)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_sorting_key_error(self):
        """Test rendering when sorting column is missing."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "other_value": [1, 2, 3]})

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="other_value", sort_values=True
        )

        # Mock the y_axis to point to a missing column after data processing
        with patch.object(df, "sort_values", side_effect=KeyError("Column not found")):
            result = self.widget.render(df, params)

            # Should render successfully despite sorting error
            self.assertIsInstance(result, str)
            self.assertNotIn("<p class='error'>", result)
            self.assertIn("plotly-graph-div", result)

    def test_render_sorting_general_exception(self):
        """Test rendering when sorting raises a general exception."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "value": [10, -5, 8]})

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="value", sort_values=True
        )

        # Mock sort_values to raise a general exception
        with patch.object(df, "sort_values", side_effect=Exception("Sort error")):
            result = self.widget.render(df, params)

            # Should render successfully despite sorting error
            self.assertIsInstance(result, str)
            self.assertNotIn("<p class='error'>", result)
            self.assertIn("plotly-graph-div", result)

    def test_render_plotly_exception(self):
        """Test handling of Plotly rendering exceptions."""
        df = pd.DataFrame({"category": ["A", "B"], "value": [10, -5]})

        params = DivergingBarPlotParams(x_axis="category", y_axis="value")

        # Mock plotly Figure to raise an exception
        with patch(
            "plotly.graph_objects.Figure", side_effect=Exception("Plotly error")
        ):
            result = self.widget.render(df, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error generating diverging bar plot", result)
            self.assertIn("Plotly error", result)

    def test_render_complex_scenario_horizontal(self):
        """Test rendering with complex horizontal scenario."""
        df = pd.DataFrame(
            {
                "department": [
                    "Sales",
                    "Marketing",
                    "R&D",
                    "Operations",
                    "Finance",
                    "HR",
                ],
                "budget_change_pct": [12.5, -8.3, 15.7, -3.2, 4.1, -12.8],
                "full_department_name": [
                    "Sales Department",
                    "Marketing Department",
                    "Research & Development",
                    "Operations Department",
                    "Finance Department",
                    "Human Resources",
                ],
                "employee_count": [150, 45, 85, 120, 25, 35],
                "budget_2023": [2500000, 800000, 1200000, 1800000, 400000, 600000],
            }
        )

        params = DivergingBarPlotParams(
            title="Budget Change by Department",
            description="Percentage change in departmental budgets from 2022 to 2023",
            x_axis="department",
            y_axis="budget_change_pct",
            orientation="h",
            color_positive="#28a745",
            color_negative="#dc3545",
            threshold=0.0,
            hover_name="full_department_name",
            hover_data=["employee_count", "budget_2023"],
            xaxis_title="Budget Change (%)",
            yaxis_title="Department",
            sort_values=True,
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_complex_scenario_vertical(self):
        """Test rendering with complex vertical scenario."""
        df = pd.DataFrame(
            {
                "quarter": ["Q1", "Q2", "Q3", "Q4"],
                "revenue_change": [-2.1, 5.8, 8.3, -1.5],
                "quarter_full": [
                    "1st Quarter",
                    "2nd Quarter",
                    "3rd Quarter",
                    "4th Quarter",
                ],
                "revenue_millions": [45.2, 48.9, 52.7, 48.1],
                "expenses_millions": [42.1, 44.2, 46.8, 45.3],
            }
        )

        params = DivergingBarPlotParams(
            title="Quarterly Revenue Change",
            x_axis="quarter",
            y_axis="revenue_change",
            orientation="v",
            color_positive="#007bff",
            color_negative="#fd7e14",
            threshold=0.0,
            hover_name="quarter_full",
            hover_data=["revenue_millions", "expenses_millions"],
            xaxis_title="Quarter",
            yaxis_title="Revenue Change (%)",
            sort_values=False,  # Keep chronological order
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_nan_values(self):
        """Test rendering with NaN values in data."""
        import numpy as np

        df = pd.DataFrame(
            {"category": ["A", "B", "C", "D"], "value": [10, np.nan, -5, 8]}
        )

        params = DivergingBarPlotParams(x_axis="category", y_axis="value")

        result = self.widget.render(df, params)

        # Verify successful rendering (Plotly should handle NaN values)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_single_row(self):
        """Test rendering with single row DataFrame."""
        df = pd.DataFrame({"item": ["Single"], "value": [15.5]})

        params = DivergingBarPlotParams(x_axis="item", y_axis="value")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_large_dataset(self):
        """Test rendering with larger dataset."""
        import numpy as np

        # Create larger dataset
        np.random.seed(42)
        categories = [f"Cat_{i:02d}" for i in range(50)]
        values = np.random.normal(0, 10, 50)  # Random values around 0

        df = pd.DataFrame({"category": categories, "value": values})

        params = DivergingBarPlotParams(
            x_axis="category", y_axis="value", orientation="h"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_extreme_values(self):
        """Test rendering with extreme positive and negative values."""
        df = pd.DataFrame(
            {
                "scenario": ["Huge Loss", "Small Gain", "Massive Growth", "Tiny Loss"],
                "impact": [-1000000, 5, 2500000, -0.1],
            }
        )

        params = DivergingBarPlotParams(x_axis="scenario", y_axis="impact", threshold=0)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)


class TestDivergingBarPlotParams(NiamotoTestCase):
    """Test cases for DivergingBarPlotParams validation."""

    def test_params_minimal_required(self):
        """Test parameters with minimal required fields."""
        params = DivergingBarPlotParams(x_axis="category", y_axis="value")

        self.assertEqual(params.x_axis, "category")
        self.assertEqual(params.y_axis, "value")
        self.assertIsNone(params.title)
        self.assertIsNone(params.description)

    def test_params_all_fields(self):
        """Test parameters with all fields specified."""
        params = DivergingBarPlotParams(
            title="Test Plot",
            description="Test description",
            x_axis="x_field",
            y_axis="y_field",
            color_positive="#00ff00",
            color_negative="#ff0000",
            threshold=5.0,
            orientation="v",
            hover_name="hover_field",
            hover_data=["field1", "field2"],
            xaxis_title="X Axis",
            yaxis_title="Y Axis",
            sort_values=False,
        )

        self.assertEqual(params.title, "Test Plot")
        self.assertEqual(params.description, "Test description")
        self.assertEqual(params.x_axis, "x_field")
        self.assertEqual(params.y_axis, "y_field")
        self.assertEqual(params.color_positive, "#00ff00")
        self.assertEqual(params.color_negative, "#ff0000")
        self.assertEqual(params.threshold, 5.0)
        self.assertEqual(params.orientation, "v")
        self.assertEqual(params.hover_name, "hover_field")
        self.assertEqual(params.hover_data, ["field1", "field2"])
        self.assertEqual(params.xaxis_title, "X Axis")
        self.assertEqual(params.yaxis_title, "Y Axis")
        self.assertFalse(params.sort_values)

    def test_params_defaults(self):
        """Test parameter default values."""
        params = DivergingBarPlotParams(x_axis="x", y_axis="y")

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertEqual(params.color_positive, "#2ca02c")
        self.assertEqual(params.color_negative, "#d62728")
        self.assertEqual(params.threshold, 0.0)
        self.assertEqual(params.orientation, "h")
        self.assertIsNone(params.hover_name)
        self.assertIsNone(params.hover_data)
        self.assertIsNone(params.xaxis_title)
        self.assertIsNone(params.yaxis_title)
        self.assertTrue(params.sort_values)

    def test_params_orientation_options(self):
        """Test different orientation values."""
        orientations = ["h", "v"]

        for orientation in orientations:
            params = DivergingBarPlotParams(
                x_axis="x", y_axis="y", orientation=orientation
            )
            self.assertEqual(params.orientation, orientation)

    def test_params_color_validation(self):
        """Test color parameter values."""
        # Valid hex colors
        params = DivergingBarPlotParams(
            x_axis="x", y_axis="y", color_positive="#ff0000", color_negative="#0000ff"
        )

        self.assertEqual(params.color_positive, "#ff0000")
        self.assertEqual(params.color_negative, "#0000ff")

    def test_params_threshold_values(self):
        """Test different threshold values."""
        thresholds = [0.0, -5.5, 10.7, 100]

        for threshold in thresholds:
            params = DivergingBarPlotParams(x_axis="x", y_axis="y", threshold=threshold)
            self.assertEqual(params.threshold, threshold)

    def test_params_validation_required_fields(self):
        """Test validation of required fields."""
        # Missing x_axis should raise error
        with self.assertRaises(ValueError):
            DivergingBarPlotParams(y_axis="y")

        # Missing y_axis should raise error
        with self.assertRaises(ValueError):
            DivergingBarPlotParams(x_axis="x")

    def test_params_hover_data_types(self):
        """Test hover_data parameter with different types."""
        # List of strings
        params1 = DivergingBarPlotParams(
            x_axis="x", y_axis="y", hover_data=["field1", "field2", "field3"]
        )
        self.assertEqual(params1.hover_data, ["field1", "field2", "field3"])

        # Empty list
        params2 = DivergingBarPlotParams(x_axis="x", y_axis="y", hover_data=[])
        self.assertEqual(params2.hover_data, [])

        # None
        params3 = DivergingBarPlotParams(x_axis="x", y_axis="y", hover_data=None)
        self.assertIsNone(params3.hover_data)

    def test_params_boolean_values(self):
        """Test boolean parameter values."""
        # sort_values True
        params1 = DivergingBarPlotParams(x_axis="x", y_axis="y", sort_values=True)
        self.assertTrue(params1.sort_values)

        # sort_values False
        params2 = DivergingBarPlotParams(x_axis="x", y_axis="y", sort_values=False)
        self.assertFalse(params2.sort_values)
