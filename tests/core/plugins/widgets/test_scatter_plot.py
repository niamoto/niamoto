import pandas as pd
from unittest.mock import Mock, patch
import numpy as np

from niamoto.core.plugins.widgets.scatter_plot import (
    ScatterPlotWidget,
    ScatterPlotParams,
)
from tests.common.base_test import NiamotoTestCase


class TestScatterPlotWidget(NiamotoTestCase):
    """Test cases for ScatterPlotWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = ScatterPlotWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, ScatterPlotParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_render_basic_scatter(self):
        """Test rendering with basic scatter plot."""
        df = pd.DataFrame(
            {
                "height": [10.5, 15.2, 8.9, 12.1, 14.6],
                "diameter": [2.1, 3.5, 1.8, 2.9, 3.2],
                "species": ["A", "B", "A", "C", "B"],
            }
        )

        params = ScatterPlotParams(x_axis="height", y_axis="diameter")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_color_field(self):
        """Test rendering with color field for point grouping."""
        df = pd.DataFrame(
            {
                "height": [10, 15, 8, 12, 14, 9, 16],
                "diameter": [2, 3, 1.5, 2.5, 3.2, 2.1, 3.8],
                "species": ["A", "B", "A", "C", "B", "A", "C"],
                "family": ["Fam1", "Fam2", "Fam1", "Fam3", "Fam2", "Fam1", "Fam3"],
            }
        )

        params = ScatterPlotParams(
            x_axis="height", y_axis="diameter", color_field="species"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_size_field(self):
        """Test rendering with size field for point sizing."""
        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 1, 5, 3],
                "population": [100, 500, 50, 1000, 200],
            }
        )

        params = ScatterPlotParams(x_axis="x", y_axis="y", size_field="population")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_symbol_field(self):
        """Test rendering with symbol field for different markers."""
        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5, 6],
                "y": [2, 4, 1, 5, 3, 6],
                "type": ["A", "B", "A", "C", "B", "C"],
            }
        )

        params = ScatterPlotParams(x_axis="x", y_axis="y", symbol_field="type")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_hover_data(self):
        """Test rendering with hover data."""
        df = pd.DataFrame(
            {
                "height": [10, 15, 8],
                "diameter": [2, 3, 1.5],
                "species": ["Araucaria", "Agathis", "Podocarpus"],
                "age": [50, 75, 30],
                "location": ["North", "South", "Center"],
            }
        )

        params = ScatterPlotParams(
            x_axis="height",
            y_axis="diameter",
            hover_name="species",
            hover_data=["age", "location"],
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_trendline(self):
        """Test rendering with trendline."""
        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "y": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],  # Linear relationship
            }
        )

        params = ScatterPlotParams(x_axis="x", y_axis="y", trendline="ols")

        result = self.widget.render(df, params)

        # Verify result - may fail if statsmodels not installed
        self.assertIsInstance(result, str)
        # Accept either successful rendering or statsmodels error
        if "<p class='error'>" in result:
            self.assertIn("No module named 'statsmodels'", result)
        else:
            self.assertIn("plotly-graph-div", result)

    def test_render_with_facets(self):
        """Test rendering with faceted plots."""
        df = pd.DataFrame(
            {
                "x": [1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 4],
                "y": [2, 4, 6, 8, 3, 5, 7, 9, 1, 3, 5, 7],
                "category": [
                    "A",
                    "A",
                    "A",
                    "A",
                    "B",
                    "B",
                    "B",
                    "B",
                    "C",
                    "C",
                    "C",
                    "C",
                ],
                "region": [
                    "North",
                    "North",
                    "South",
                    "South",
                    "North",
                    "North",
                    "South",
                    "South",
                    "North",
                    "North",
                    "South",
                    "South",
                ],
            }
        )

        params = ScatterPlotParams(
            x_axis="x", y_axis="y", facet_col="category", facet_row="region"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_log_scales(self):
        """Test rendering with logarithmic scales."""
        df = pd.DataFrame(
            {"x": [1, 10, 100, 1000, 10000], "y": [1, 100, 10000, 1000000, 100000000]}
        )

        params = ScatterPlotParams(x_axis="x", y_axis="y", log_x=True, log_y=True)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_custom_labels(self):
        """Test rendering with custom axis labels."""
        df = pd.DataFrame({"h": [10, 15, 8], "d": [2, 3, 1.5]})

        params = ScatterPlotParams(
            x_axis="h",
            y_axis="d",
            labels={"h": "Tree Height (m)", "d": "Diameter (cm)"},
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
                "x": [1, 2, 3, 4, 5, 6],
                "y": [2, 4, 1, 5, 3, 6],
                "species": ["A", "B", "A", "C", "B", "C"],
            }
        )

        color_map = {"A": "#ff6b35", "B": "#1fb99d", "C": "#6c5ce7"}

        params = ScatterPlotParams(
            x_axis="x", y_axis="y", color_field="species", color_discrete_map=color_map
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_size_max(self):
        """Test rendering with maximum size constraint."""
        df = pd.DataFrame(
            {"x": [1, 2, 3, 4], "y": [2, 4, 1, 5], "size": [10, 50, 100, 200]}
        )

        params = ScatterPlotParams(
            x_axis="x", y_axis="y", size_field="size", size_max=30
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_none_data(self):
        """Test rendering with None data."""
        params = ScatterPlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(None, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for scatter plot", result)

    def test_render_empty_dataframe(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()
        params = ScatterPlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available for scatter plot", result)

    def test_render_missing_columns(self):
        """Test rendering with missing required columns."""
        df = pd.DataFrame({"height": [10, 15, 8], "other_field": [1, 2, 3]})

        params = ScatterPlotParams(x_axis="height", y_axis="missing_diameter")

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("Missing columns", result)

    def test_render_missing_optional_columns(self):
        """Test rendering with missing optional columns."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 1]})

        params = ScatterPlotParams(
            x_axis="x",
            y_axis="y",
            color_field="missing_color",
            size_field="missing_size",
        )

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Missing columns", result)

    def test_render_non_numeric_axis(self):
        """Test rendering with non-numeric axis data."""
        df = pd.DataFrame({"x": ["a", "b", "c"], "y": [1, 2, 3]})

        params = ScatterPlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Data Error", result)
        self.assertIn("non-numeric values", result)

    def test_render_non_numeric_size_field(self):
        """Test rendering with non-numeric size field."""
        df = pd.DataFrame(
            {"x": [1, 2, 3], "y": [2, 4, 1], "size": ["small", "medium", "large"]}
        )

        params = ScatterPlotParams(x_axis="x", y_axis="y", size_field="size")

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Data Error", result)
        self.assertIn("non-numeric values", result)

    def test_render_numeric_conversion_with_nans(self):
        """Test rendering when numeric conversion produces NaNs."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": ["1", "not_a_number", "3"]})

        params = ScatterPlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Data Error", result)
        self.assertIn("non-numeric values", result)

    def test_render_numeric_conversion_exception(self):
        """Test rendering when numeric conversion raises exception."""
        # Use string data that would trigger numeric conversion
        df = pd.DataFrame(
            {
                "x": ["1", "2", "3"],  # String data that needs conversion
                "y": ["1", "2", "3"],
            }
        )

        params = ScatterPlotParams(x_axis="x", y_axis="y")

        # Mock pd.to_numeric to raise an exception - use the full module path
        with patch(
            "niamoto.core.plugins.widgets.scatter_plot.pd.to_numeric",
            side_effect=Exception("Conversion error"),
        ):
            result = self.widget.render(df, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Data Error", result)
            self.assertIn("Could not process numeric column", result)

    def test_render_plotly_exception(self):
        """Test handling of Plotly rendering exceptions."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 1]})

        params = ScatterPlotParams(x_axis="x", y_axis="y")

        # Mock plotly.express.scatter to raise an exception
        with patch("plotly.express.scatter", side_effect=Exception("Plotly error")):
            result = self.widget.render(df, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error generating scatter plot", result)
            self.assertIn("Plotly error", result)

    def test_render_with_nan_values(self):
        """Test rendering with NaN values in valid numeric data."""
        df = pd.DataFrame({"x": [1, 2, np.nan, 4, 5], "y": [2, np.nan, 1, 5, 3]})

        params = ScatterPlotParams(x_axis="x", y_axis="y")

        result = self.widget.render(df, params)

        # Verify successful rendering (Plotly should handle NaN values)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_hover_data_string_conversion(self):
        """Test rendering with hover_data as string (should be converted to list)."""
        df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 1], "info": ["A", "B", "C"]})

        # Note: hover_data expects List[str] in the Pydantic model
        # This test should use a list instead
        params = ScatterPlotParams(
            x_axis="x",
            y_axis="y",
            hover_data=["info"],  # List as expected by the model
        )

        result = self.widget.render(df, params)

        # Should render successfully
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_complex_scenario(self):
        """Test rendering with complex scenario combining multiple features."""
        np.random.seed(42)

        # Create synthetic ecological data
        species_list = [
            "Araucaria columnaris",
            "Agathis ovata",
            "Podocarpus novae-caledoniae",
            "Dacrydium guillauminii",
            "Retrophyllum minus",
        ]
        families = [
            "Araucariaceae",
            "Araucariaceae",
            "Podocarpaceae",
            "Cupressaceae",
            "Podocarpaceae",
        ]
        locations = ["North", "South", "Center", "East", "West"]

        n_points = 50
        df = pd.DataFrame(
            {
                "height": 5 + 15 * np.random.random(n_points),
                "diameter": 1 + 4 * np.random.random(n_points),
                "age": 10 + 90 * np.random.random(n_points),
                "species": np.random.choice(species_list, n_points),
                "family": [
                    families[species_list.index(s)]
                    for s in np.random.choice(species_list, n_points)
                ],
                "location": np.random.choice(locations, n_points),
                "conservation_status": np.random.choice(
                    ["LC", "NT", "VU", "EN"], n_points
                ),
                "plot_id": [f"Plot_{i:03d}" for i in range(n_points)],
            }
        )

        # Test without trendline to avoid statsmodels dependency
        params = ScatterPlotParams(
            title="Tree Allometry Analysis",
            x_axis="height",
            y_axis="diameter",
            color_field="family",
            size_field="age",
            symbol_field="conservation_status",
            hover_name="species",
            hover_data=["location", "plot_id"],
            labels={
                "height": "Tree Height (m)",
                "diameter": "Diameter at Breast Height (cm)",
                "family": "Taxonomic Family",
                "age": "Estimated Age (years)",
            },
            color_discrete_map={
                "Araucariaceae": "#2E8B57",
                "Podocarpaceae": "#4682B4",
                "Cupressaceae": "#CD853F",
            },
            size_max=25,
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_large_dataset(self):
        """Test rendering with larger dataset."""
        np.random.seed(42)

        # Create larger dataset
        n_points = 1000
        df = pd.DataFrame(
            {
                "x": np.random.normal(50, 15, n_points),
                "y": np.random.normal(30, 10, n_points),
                "category": np.random.choice(["A", "B", "C", "D"], n_points),
                "value": np.random.exponential(2, n_points),
            }
        )

        params = ScatterPlotParams(
            x_axis="x", y_axis="y", color_field="category", size_field="value"
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)


class TestScatterPlotParams(NiamotoTestCase):
    """Test cases for ScatterPlotParams validation."""

    def test_params_minimal_required(self):
        """Test parameters with minimal required fields."""
        params = ScatterPlotParams(x_axis="height", y_axis="diameter")

        self.assertEqual(params.x_axis, "height")
        self.assertEqual(params.y_axis, "diameter")
        self.assertIsNone(params.title)

    def test_params_all_fields(self):
        """Test parameters with all fields specified."""
        params = ScatterPlotParams(
            title="Test Scatter Plot",
            x_axis="x_field",
            y_axis="y_field",
            color_field="color_field",
            size_field="size_field",
            symbol_field="symbol_field",
            hover_name="hover_field",
            hover_data=["field1", "field2"],
            trendline="ols",
            facet_col="facet_col_field",
            facet_row="facet_row_field",
            log_x=True,
            log_y=True,
            labels={"x_field": "X Label", "y_field": "Y Label"},
            color_discrete_map={"A": "red", "B": "blue"},
            size_max=50,
        )

        self.assertEqual(params.title, "Test Scatter Plot")
        self.assertEqual(params.x_axis, "x_field")
        self.assertEqual(params.y_axis, "y_field")
        self.assertEqual(params.color_field, "color_field")
        self.assertEqual(params.size_field, "size_field")
        self.assertEqual(params.symbol_field, "symbol_field")
        self.assertEqual(params.hover_name, "hover_field")
        self.assertEqual(params.hover_data, ["field1", "field2"])
        self.assertEqual(params.trendline, "ols")
        self.assertEqual(params.facet_col, "facet_col_field")
        self.assertEqual(params.facet_row, "facet_row_field")
        self.assertTrue(params.log_x)
        self.assertTrue(params.log_y)
        self.assertEqual(params.labels, {"x_field": "X Label", "y_field": "Y Label"})
        self.assertEqual(params.color_discrete_map, {"A": "red", "B": "blue"})
        self.assertEqual(params.size_max, 50)

    def test_params_defaults(self):
        """Test parameter default values."""
        params = ScatterPlotParams(x_axis="x", y_axis="y")

        self.assertIsNone(params.title)
        self.assertIsNone(params.color_field)
        self.assertIsNone(params.size_field)
        self.assertIsNone(params.symbol_field)
        self.assertIsNone(params.hover_name)
        self.assertIsNone(params.hover_data)
        self.assertIsNone(params.trendline)
        self.assertIsNone(params.facet_col)
        self.assertIsNone(params.facet_row)
        self.assertFalse(params.log_x)
        self.assertFalse(params.log_y)
        self.assertIsNone(params.labels)
        self.assertIsNone(params.color_discrete_map)
        self.assertIsNone(params.size_max)

    def test_params_trendline_options(self):
        """Test different trendline values."""
        trendlines = ["ols", "lowess", None]

        for trendline in trendlines:
            params = ScatterPlotParams(x_axis="x", y_axis="y", trendline=trendline)
            self.assertEqual(params.trendline, trendline)

    def test_params_boolean_options(self):
        """Test boolean parameter options."""
        # log_x and log_y combinations
        params1 = ScatterPlotParams(x_axis="x", y_axis="y", log_x=True, log_y=False)
        self.assertTrue(params1.log_x)
        self.assertFalse(params1.log_y)

        params2 = ScatterPlotParams(x_axis="x", y_axis="y", log_x=False, log_y=True)
        self.assertFalse(params2.log_x)
        self.assertTrue(params2.log_y)

    def test_params_validation_required_fields(self):
        """Test validation of required fields."""
        # Missing x_axis should raise error
        with self.assertRaises(ValueError):
            ScatterPlotParams(y_axis="y")

        # Missing y_axis should raise error
        with self.assertRaises(ValueError):
            ScatterPlotParams(x_axis="x")

    def test_params_hover_data_types(self):
        """Test hover_data parameter with different types."""
        # List of strings
        params1 = ScatterPlotParams(
            x_axis="x", y_axis="y", hover_data=["field1", "field2"]
        )
        self.assertEqual(params1.hover_data, ["field1", "field2"])

        # Empty list
        params2 = ScatterPlotParams(x_axis="x", y_axis="y", hover_data=[])
        self.assertEqual(params2.hover_data, [])

        # None
        params3 = ScatterPlotParams(x_axis="x", y_axis="y", hover_data=None)
        self.assertIsNone(params3.hover_data)

    def test_params_size_max_validation(self):
        """Test size_max parameter validation."""
        # Valid positive integer
        params1 = ScatterPlotParams(x_axis="x", y_axis="y", size_max=30)
        self.assertEqual(params1.size_max, 30)

        # None
        params2 = ScatterPlotParams(x_axis="x", y_axis="y", size_max=None)
        self.assertIsNone(params2.size_max)

    def test_params_labels_dict(self):
        """Test labels parameter as dictionary."""
        labels_dict = {
            "x_field": "X-axis Label",
            "y_field": "Y-axis Label",
            "color_field": "Color Legend",
        }

        params = ScatterPlotParams(
            x_axis="x_field", y_axis="y_field", labels=labels_dict
        )

        self.assertEqual(params.labels, labels_dict)

    def test_params_color_discrete_map(self):
        """Test color_discrete_map parameter."""
        color_map = {
            "Category A": "#ff6b35",
            "Category B": "#1fb99d",
            "Category C": "#6c5ce7",
        }

        params = ScatterPlotParams(x_axis="x", y_axis="y", color_discrete_map=color_map)

        self.assertEqual(params.color_discrete_map, color_map)
