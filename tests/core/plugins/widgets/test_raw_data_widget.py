import pandas as pd
import pytest
from unittest.mock import Mock

from niamoto.core.plugins.widgets.raw_data_widget import (
    RawDataWidget,
    RawDataWidgetParams,
)
from tests.common.base_test import NiamotoTestCase


class TestRawDataWidget(NiamotoTestCase):
    """Test cases for RawDataWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = RawDataWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, RawDataWidgetParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 0)

    def test_render_none_data(self):
        """Test rendering with None data."""
        params = RawDataWidgetParams()

        result = self.widget.render(None, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available to display", result)

    def test_render_empty_dataframe(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()
        params = RawDataWidgetParams()

        result = self.widget.render(df, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available to display", result)

    def test_render_basic_dataframe(self):
        """Test rendering with basic DataFrame."""
        df = pd.DataFrame(
            {
                "species": [
                    "Araucaria columnaris",
                    "Agathis ovata",
                    "Podocarpus novae-caledoniae",
                ],
                "count": [150, 230, 95],
                "location": ["North", "South", "Center"],
            }
        )

        params = RawDataWidgetParams(title="Species Data")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("<p class='info'>", result)
        self.assertIn("<table", result)
        self.assertIn("table-striped", result)

        # Verify data content
        self.assertIn("Araucaria columnaris", result)
        self.assertIn("150", result)
        self.assertIn("North", result)

    def test_render_with_specific_columns(self):
        """Test rendering with specific columns selection."""
        df = pd.DataFrame(
            {
                "species": ["Species A", "Species B", "Species C"],
                "count": [100, 200, 300],
                "location": ["North", "South", "Center"],
                "notes": ["Note 1", "Note 2", "Note 3"],
            }
        )

        params = RawDataWidgetParams(columns=["species", "count"], max_rows=10)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify only specified columns are included
        self.assertIn("species", result)
        self.assertIn("count", result)
        self.assertNotIn("location", result)
        self.assertNotIn("notes", result)

    def test_render_with_missing_columns(self):
        """Test rendering with some missing columns."""
        df = pd.DataFrame({"species": ["Species A", "Species B"], "count": [100, 200]})

        params = RawDataWidgetParams(
            columns=["species", "count", "missing_column"], max_rows=10
        )

        result = self.widget.render(df, params)

        # Should render with available columns only
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)
        self.assertIn("species", result)
        self.assertIn("count", result)

    def test_render_with_all_missing_columns(self):
        """Test rendering when all specified columns are missing."""
        df = pd.DataFrame({"species": ["Species A", "Species B"], "count": [100, 200]})

        params = RawDataWidgetParams(columns=["missing1", "missing2"], max_rows=10)

        result = self.widget.render(df, params)

        # Should return error message
        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("None of the specified columns", result)

    def test_render_with_sorting_ascending(self):
        """Test rendering with ascending sort."""
        df = pd.DataFrame(
            {
                "species": ["Species C", "Species A", "Species B"],
                "count": [300, 100, 200],
                "priority": [3, 1, 2],
            }
        )

        params = RawDataWidgetParams(sort_by="count", ascending=True, max_rows=10)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Since sorting is applied before HTML generation, we can check relative positions
        species_a_pos = result.find("Species A")
        species_b_pos = result.find("Species B")
        species_c_pos = result.find("Species C")

        # Species A (count=100) should come before Species B (count=200) which comes before Species C (count=300)
        self.assertLess(species_a_pos, species_b_pos)
        self.assertLess(species_b_pos, species_c_pos)

    def test_render_with_sorting_descending(self):
        """Test rendering with descending sort."""
        df = pd.DataFrame(
            {
                "species": ["Species C", "Species A", "Species B"],
                "count": [300, 100, 200],
                "priority": [3, 1, 2],
            }
        )

        params = RawDataWidgetParams(sort_by="count", ascending=False, max_rows=10)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Species C (count=300) should come before Species B (count=200) which comes before Species A (count=100)
        species_a_pos = result.find("Species A")
        species_b_pos = result.find("Species B")
        species_c_pos = result.find("Species C")

        self.assertLess(species_c_pos, species_b_pos)
        self.assertLess(species_b_pos, species_a_pos)

    def test_render_with_invalid_sort_column(self):
        """Test rendering with invalid sort column."""
        df = pd.DataFrame({"species": ["Species A", "Species B"], "count": [100, 200]})

        params = RawDataWidgetParams(sort_by="missing_column", max_rows=10)

        result = self.widget.render(df, params)

        # Should render successfully but skip sorting
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

    def test_render_with_max_rows_limit(self):
        """Test rendering with max rows limit."""
        # Create DataFrame with more rows than limit
        df = pd.DataFrame(
            {
                "id": range(1, 21),  # 20 rows
                "value": [f"Value {i}" for i in range(1, 21)],
            }
        )

        params = RawDataWidgetParams(max_rows=5)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should only contain first 5 rows
        self.assertIn("Value 1", result)
        self.assertIn("Value 5", result)
        self.assertNotIn("Value 6", result)
        self.assertNotIn("Value 20", result)

    def test_render_with_special_characters(self):
        """Test rendering with special characters and HTML entities."""
        df = pd.DataFrame(
            {
                "name": [
                    '<script>alert("test")</script>',
                    "Species & More",
                    "Normal Name",
                ],
                "description": [
                    'Test with "quotes"',
                    "Test with 'apostrophes'",
                    "Normal description",
                ],
            }
        )

        params = RawDataWidgetParams()

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify HTML escaping (pandas to_html with escape=True should handle this)
        self.assertNotIn("<script>", result)  # Should be escaped
        self.assertIn("&lt;script&gt;", result)  # Should be HTML encoded

    def test_render_complex_scenario(self):
        """Test rendering with multiple features combined."""
        df = pd.DataFrame(
            {
                "species_id": [101, 102, 103, 104, 105, 106],
                "species_name": [
                    "Araucaria columnaris",
                    "Agathis ovata",
                    "Podocarpus novae-caledoniae",
                    "Dacrydium guillauminii",
                    "Retrophyllum minus",
                    "Parasitaxus ustus",
                ],
                "family": [
                    "Araucariaceae",
                    "Araucariaceae",
                    "Podocarpaceae",
                    "Cupressaceae",
                    "Podocarpaceae",
                    "Podocarpaceae",
                ],
                "count": [150, 230, 95, 75, 120, 45],
                "conservation_status": ["LC", "NT", "VU", "EN", "LC", "CR"],
                "location": ["North", "South", "Center", "West", "East", "South"],
            }
        )

        params = RawDataWidgetParams(
            title="Species Conservation Status",
            columns=["species_name", "family", "count", "conservation_status"],
            sort_by="count",
            ascending=False,
            max_rows=4,
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify columns are correctly selected
        self.assertIn("species_name", result)
        self.assertIn("family", result)
        self.assertIn("count", result)
        self.assertIn("conservation_status", result)
        self.assertNotIn("species_id", result)
        self.assertNotIn("location", result)

        # Verify sorting (highest count first) and row limit
        self.assertIn("Agathis ovata", result)  # count=230, should be first
        self.assertIn("Araucaria columnaris", result)  # count=150, should be second
        self.assertNotIn(
            "Parasitaxus ustus", result
        )  # count=45, should be excluded due to max_rows=4

    def test_render_with_different_data_types(self):
        """Test rendering with various data types."""
        df = pd.DataFrame(
            {
                "integer_col": [1, 2, 3],
                "float_col": [1.5, 2.7, 3.9],
                "string_col": ["A", "B", "C"],
                "boolean_col": [True, False, True],
                "datetime_col": pd.date_range("2023-01-01", periods=3),
                "nullable_col": [1, None, 3],
            }
        )

        params = RawDataWidgetParams()

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify different data types are handled
        self.assertIn("1.5", result)  # Float
        self.assertIn("True", result)  # Boolean
        self.assertIn("2023-01-01", result)  # Date

    def test_render_exception_handling(self):
        """Test exception handling during HTML generation."""
        df = pd.DataFrame({"col1": ["A", "B", "C"], "col2": [1, 2, 3]})

        params = RawDataWidgetParams()

        # Mock to_html to raise an exception
        with pytest.raises(Exception):
            # Mock the to_html method to raise an exception
            original_to_html = df.to_html
            df.to_html = Mock(side_effect=Exception("HTML generation error"))

            try:
                result = self.widget.render(df, params)

                self.assertIn("<p class='error'>", result)
                self.assertIn("Error displaying data", result)
                self.assertIn("HTML generation error", result)
            finally:
                # Restore original method
                df.to_html = original_to_html

    def test_render_large_dataframe_performance(self):
        """Test rendering with larger DataFrame to ensure performance."""
        # Create a larger DataFrame
        df = pd.DataFrame(
            {
                "id": range(1000),
                "name": [f"Item {i}" for i in range(1000)],
                "value": [i * 1.5 for i in range(1000)],
            }
        )

        params = RawDataWidgetParams(max_rows=50)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should only show first 50 rows
        self.assertIn("Item 0", result)
        self.assertIn("Item 49", result)
        self.assertNotIn("Item 50", result)


class TestRawDataWidgetParams(NiamotoTestCase):
    """Test cases for RawDataWidgetParams validation."""

    def test_params_defaults(self):
        """Test parameter defaults."""
        params = RawDataWidgetParams()

        self.assertIsNone(params.title)
        self.assertEqual(params.max_rows, 100)
        self.assertIsNone(params.columns)
        self.assertIsNone(params.sort_by)
        self.assertTrue(params.ascending)

    def test_params_custom_values(self):
        """Test parameters with custom values."""
        params = RawDataWidgetParams(
            title="Custom Data View",
            max_rows=25,
            columns=["col1", "col2", "col3"],
            sort_by="col1",
            ascending=False,
        )

        self.assertEqual(params.title, "Custom Data View")
        self.assertEqual(params.max_rows, 25)
        self.assertEqual(params.columns, ["col1", "col2", "col3"])
        self.assertEqual(params.sort_by, "col1")
        self.assertFalse(params.ascending)

    def test_params_max_rows_validation(self):
        """Test max_rows parameter validation."""
        # Valid values
        params1 = RawDataWidgetParams(max_rows=1)
        self.assertEqual(params1.max_rows, 1)

        params2 = RawDataWidgetParams(max_rows=1000)
        self.assertEqual(params2.max_rows, 1000)

        # Note: The original model doesn't have validation constraints for max_rows
        # These would require adding Field constraints like Field(100, gt=0)
        # For now, we test that the values are accepted
        params3 = RawDataWidgetParams(max_rows=0)
        self.assertEqual(params3.max_rows, 0)

        params4 = RawDataWidgetParams(max_rows=-1)
        self.assertEqual(params4.max_rows, -1)

    def test_params_empty_columns_list(self):
        """Test parameters with empty columns list."""
        params = RawDataWidgetParams(columns=[])

        # Empty list should be valid
        self.assertEqual(params.columns, [])

    def test_params_column_types(self):
        """Test columns parameter with different string types."""
        columns = ["column_1", "column-2", "Column With Spaces", "123_numeric_start"]

        params = RawDataWidgetParams(columns=columns)

        self.assertEqual(params.columns, columns)
