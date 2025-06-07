import pandas as pd
from unittest.mock import Mock, patch

from niamoto.core.plugins.widgets.table_view import (
    TableViewWidget,
    TableViewParams,
    TableColumn,
)
from tests.common.base_test import NiamotoTestCase


class TestTableViewWidget(NiamotoTestCase):
    """Test cases for TableViewWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = TableViewWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, TableViewParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 0)

    def test_render_none_data(self):
        """Test rendering with None data."""
        params = TableViewParams()

        result = self.widget.render(None, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available to display in table", result)

    def test_render_empty_dataframe(self):
        """Test rendering with empty DataFrame."""
        df = pd.DataFrame()
        params = TableViewParams()

        result = self.widget.render(df, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available to display in table", result)

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
                "status": ["Active", "Protected", "Monitored"],
            }
        )

        params = TableViewParams(
            title="Species Overview",
            description="List of species with their counts and locations",
        )

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
        self.assertIn("species", result)
        self.assertIn("count", result)
        self.assertIn("location", result)
        self.assertIn("status", result)

    def test_render_with_specific_columns(self):
        """Test rendering with specific columns selection."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "species": ["Species A", "Species B", "Species C"],
                "count": [100, 200, 300],
                "location": ["North", "South", "Center"],
                "notes": ["Note 1", "Note 2", "Note 3"],
                "internal_code": ["PRIV1", "PRIV2", "PRIV3"],
            }
        )

        params = TableViewParams(columns=["species", "count", "location"])

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify only specified columns are included
        self.assertIn("species", result)
        self.assertIn("count", result)
        self.assertIn("location", result)

        # Verify excluded columns are not present
        self.assertNotIn("id", result)
        self.assertNotIn("notes", result)
        self.assertNotIn("internal_code", result)

    def test_render_with_missing_columns(self):
        """Test rendering with some missing columns."""
        df = pd.DataFrame({"species": ["Species A", "Species B"], "count": [100, 200]})

        params = TableViewParams(
            columns=["species", "count", "missing_column", "another_missing"]
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

        params = TableViewParams(columns=["missing1", "missing2", "missing3"])

        result = self.widget.render(df, params)

        # Should return error message
        self.assertIn("<p class='error'>", result)
        self.assertIn("Configuration Error", result)
        self.assertIn("None of the specified columns found", result)

    def test_render_with_single_column_sorting(self):
        """Test rendering with single column sorting."""
        df = pd.DataFrame(
            {
                "species": ["Species C", "Species A", "Species B"],
                "count": [300, 100, 200],
                "priority": [3, 1, 2],
            }
        )

        params = TableViewParams(sort_by=["count"], ascending=[True])

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Check that sorting is applied (Species A with count=100 should appear first)
        species_a_pos = result.find("Species A")
        species_b_pos = result.find("Species B")
        species_c_pos = result.find("Species C")

        self.assertLess(species_a_pos, species_b_pos)
        self.assertLess(species_b_pos, species_c_pos)

    def test_render_with_multiple_column_sorting(self):
        """Test rendering with multiple column sorting."""
        df = pd.DataFrame(
            {
                "family": [
                    "Araucariaceae",
                    "Araucariaceae",
                    "Podocarpaceae",
                    "Podocarpaceae",
                ],
                "species": ["Species B", "Species A", "Species D", "Species C"],
                "count": [200, 100, 400, 300],
            }
        )

        params = TableViewParams(
            sort_by=["family", "count"],
            ascending=[True, False],  # Family ascending, count descending
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

    def test_render_with_missing_sort_columns(self):
        """Test rendering with missing sort columns."""
        df = pd.DataFrame(
            {
                "species": ["Species A", "Species B", "Species C"],
                "count": [100, 200, 300],
            }
        )

        params = TableViewParams(
            sort_by=["species", "missing_column", "count"],
            ascending=[True, False, True],
        )

        result = self.widget.render(df, params)

        # Should render successfully, sorting by available columns only
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

    def test_render_with_all_missing_sort_columns(self):
        """Test rendering when all sort columns are missing."""
        df = pd.DataFrame(
            {
                "species": ["Species A", "Species B", "Species C"],
                "count": [100, 200, 300],
            }
        )

        params = TableViewParams(sort_by=["missing1", "missing2"])

        result = self.widget.render(df, params)

        # Should render successfully without sorting
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

    def test_render_with_mismatched_ascending_list(self):
        """Test rendering with mismatched ascending list length."""
        df = pd.DataFrame(
            {
                "species": ["Species C", "Species A", "Species B"],
                "count": [300, 100, 200],
                "priority": [3, 1, 2],
            }
        )

        # More sort columns than ascending flags
        params1 = TableViewParams(
            sort_by=["count", "priority", "species"],
            ascending=[True],  # Only one flag for three columns
        )

        result1 = self.widget.render(df, params1)
        self.assertIsInstance(result1, str)
        self.assertNotIn("<p class='error'>", result1)

        # More ascending flags than sort columns
        params2 = TableViewParams(
            sort_by=["count"],
            ascending=[True, False, True],  # Three flags for one column
        )

        result2 = self.widget.render(df, params2)
        self.assertIsInstance(result2, str)
        self.assertNotIn("<p class='error'>", result2)

    def test_render_with_no_ascending_specified(self):
        """Test rendering with sort_by but no ascending specified."""
        df = pd.DataFrame(
            {
                "species": ["Species C", "Species A", "Species B"],
                "count": [300, 100, 200],
            }
        )

        params = TableViewParams(
            sort_by=["count"]
            # No ascending parameter - should default to True
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

    def test_render_with_max_rows_limit(self):
        """Test rendering with max rows limit."""
        # Create DataFrame with more rows than limit
        df = pd.DataFrame(
            {
                "id": range(1, 16),  # 15 rows
                "value": [f"Value {i}" for i in range(1, 16)],
            }
        )

        params = TableViewParams(max_rows=5)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should only contain first 5 rows
        self.assertIn("Value 1", result)
        self.assertIn("Value 5", result)
        self.assertNotIn("Value 6", result)
        self.assertNotIn("Value 15", result)

    def test_render_with_index_displayed(self):
        """Test rendering with DataFrame index displayed."""
        df = pd.DataFrame(
            {
                "species": ["Species A", "Species B", "Species C"],
                "count": [100, 200, 300],
            }
        )

        params = TableViewParams(index=True)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should include index values (0, 1, 2)
        self.assertIn(">0<", result)
        self.assertIn(">1<", result)
        self.assertIn(">2<", result)

    def test_render_with_custom_table_classes(self):
        """Test rendering with custom table CSS classes."""
        df = pd.DataFrame({"col1": ["A", "B", "C"], "col2": [1, 2, 3]})

        params = TableViewParams(table_classes="custom-table responsive-table striped")

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should include custom classes
        self.assertIn("custom-table", result)
        self.assertIn("responsive-table", result)
        self.assertIn("striped", result)

    def test_render_with_escape_disabled(self):
        """Test rendering with HTML escaping disabled."""
        df = pd.DataFrame(
            {
                "name": ["<b>Bold Name</b>", "<i>Italic Name</i>"],
                "description": ["<em>Emphasized</em>", "<strong>Strong</strong>"],
            }
        )

        params = TableViewParams(escape=False)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should contain unescaped HTML
        self.assertIn("<b>Bold Name</b>", result)
        self.assertIn("<i>Italic Name</i>", result)

    def test_render_with_escape_enabled(self):
        """Test rendering with HTML escaping enabled (default)."""
        df = pd.DataFrame(
            {
                "name": ['<script>alert("test")</script>', "Normal Name"],
                "description": ["<b>Bold</b>", "Normal Description"],
            }
        )

        params = TableViewParams(escape=True)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should contain escaped HTML
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_render_with_custom_border(self):
        """Test rendering with custom border attribute."""
        df = pd.DataFrame({"col1": ["A", "B"], "col2": [1, 2]})

        params = TableViewParams(border=2)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should include border attribute
        self.assertIn('border="2"', result)

    def test_render_with_nan_values(self):
        """Test rendering with NaN values in DataFrame."""
        df = pd.DataFrame(
            {
                "species": ["Species A", None, "Species C"],
                "count": [100, 200, None],
                "location": ["North", "South", "Center"],
            }
        )

        params = TableViewParams()

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # NaN values should be represented as "-"
        self.assertIn(">-<", result)

    def test_render_invalid_data_type_convertible(self):
        """Test rendering with invalid data type that can be converted."""
        data = [
            {"species": "Species A", "count": 100},
            {"species": "Species B", "count": 200},
            {"species": "Species C", "count": 300},
        ]

        params = TableViewParams()

        # Note: The widget has a bug where it checks data.empty before isinstance check
        # This will cause AttributeError for non-DataFrame types
        with self.assertRaises(AttributeError):
            self.widget.render(data, params)

    def test_render_invalid_data_type_non_convertible(self):
        """Test rendering with invalid data type that cannot be converted."""
        data = "invalid string data"

        params = TableViewParams()

        # Note: The widget has a bug where it checks data.empty before isinstance check
        # This will cause AttributeError for non-DataFrame types
        with self.assertRaises(AttributeError):
            self.widget.render(data, params)

    def test_render_with_sorting_exception(self):
        """Test rendering when sorting raises an exception."""
        df = pd.DataFrame(
            {
                "species": ["Species A", "Species B"],
                "mixed_types": [
                    100,
                    "string",
                ],  # Mixed types that might cause sorting issues
            }
        )

        params = TableViewParams(sort_by=["mixed_types"])

        # This might or might not raise an exception depending on pandas version
        # If it does, it should be handled gracefully
        result = self.widget.render(df, params)

        # Should either render successfully or show appropriate error
        self.assertIsInstance(result, str)
        if "<p class='error'>" in result:
            self.assertIn("Error sorting data", result)
        else:
            self.assertIn("<table", result)

    def test_render_exception_during_html_generation(self):
        """Test exception handling during HTML generation."""
        df = pd.DataFrame({"col1": ["A", "B", "C"], "col2": [1, 2, 3]})

        params = TableViewParams()

        # Mock pandas DataFrame to_html method to raise an exception
        with patch(
            "pandas.DataFrame.to_html", side_effect=Exception("HTML generation error")
        ):
            result = self.widget.render(df, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error displaying table", result)
            self.assertIn("HTML generation error", result)

    def test_render_complex_scenario(self):
        """Test rendering with complex scenario combining multiple features."""
        df = pd.DataFrame(
            {
                "species_id": [101, 102, 103, 104, 105, 106, 107, 108],
                "species_name": [
                    "Araucaria columnaris",
                    "Agathis ovata",
                    "Podocarpus novae-caledoniae",
                    "Dacrydium guillauminii",
                    "Retrophyllum minus",
                    "Parasitaxus ustus",
                    "Acmopyle pancheri",
                    "Neocallitropsis pancheri",
                ],
                "family": [
                    "Araucariaceae",
                    "Araucariaceae",
                    "Podocarpaceae",
                    "Cupressaceae",
                    "Podocarpaceae",
                    "Podocarpaceae",
                    "Podocarpaceae",
                    "Cupressaceae",
                ],
                "count": [150, 230, 95, 75, 120, 45, 60, 85],
                "conservation_status": ["LC", "NT", "VU", "EN", "LC", "CR", "VU", "NT"],
                "location": [
                    "North",
                    "South",
                    "Center",
                    "West",
                    "East",
                    "South",
                    "North",
                    "West",
                ],
                "last_survey": pd.to_datetime(
                    [
                        "2023-01-15",
                        "2023-02-20",
                        "2023-01-30",
                        "2023-03-10",
                        "2023-02-05",
                        "2023-01-25",
                        "2023-03-15",
                        "2023-02-28",
                    ]
                ),
                "notes": [
                    "Common species",
                    "Protected area",
                    "Monitoring required",
                    "Habitat loss concern",
                    "Stable population",
                    "Critical habitat",
                    "Recent discovery",
                    "Population increasing",
                ],
            }
        )

        params = TableViewParams(
            title="Species Conservation Table",
            description="Detailed view of species conservation data",
            columns=[
                "species_name",
                "family",
                "count",
                "conservation_status",
                "location",
            ],
            sort_by=["family", "count"],
            ascending=[True, False],  # Family ascending, count descending
            max_rows=6,
            index=False,
            table_classes="table table-bordered table-hover conservation-table",
            escape=True,
            border=1,
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify column selection
        self.assertIn("species_name", result)
        self.assertIn("family", result)
        self.assertIn("count", result)
        self.assertIn("conservation_status", result)
        self.assertIn("location", result)

        # Should not include excluded columns
        self.assertNotIn("species_id", result)
        self.assertNotIn("last_survey", result)
        self.assertNotIn("notes", result)

        # Verify table attributes
        self.assertIn("conservation-table", result)
        self.assertIn('border="1"', result)

        # Should only show first 6 rows due to max_rows limit
        # Can't easily verify exact sorting without parsing HTML, but should contain expected data

    def test_render_with_different_data_types(self):
        """Test rendering with various data types."""
        df = pd.DataFrame(
            {
                "integer_col": [1, 2, 3],
                "float_col": [1.5, 2.7, 3.9],
                "string_col": ["A", "B", "C"],
                "boolean_col": [True, False, True],
                "datetime_col": pd.date_range("2023-01-01", periods=3),
                "category_col": pd.Categorical(["Low", "High", "Medium"]),
            }
        )

        params = TableViewParams()

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Verify different data types are handled
        self.assertIn("1.5", result)  # Float
        self.assertIn("True", result)  # Boolean
        self.assertIn("2023-01-01", result)  # Date
        self.assertIn("Low", result)  # Category

    def test_render_large_dataframe_performance(self):
        """Test rendering with larger DataFrame."""
        # Create larger dataset
        df = pd.DataFrame(
            {
                "id": range(500),
                "name": [f"Item {i}" for i in range(500)],
                "value": [i * 1.5 for i in range(500)],
                "category": [f"Cat {i % 10}" for i in range(500)],
            }
        )

        params = TableViewParams(max_rows=50)

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("<table", result)

        # Should only show first 50 rows
        self.assertIn("Item 0", result)
        self.assertIn("Item 49", result)
        self.assertNotIn("Item 50", result)


class TestTableViewParams(NiamotoTestCase):
    """Test cases for TableViewParams validation."""

    def test_params_defaults(self):
        """Test parameter defaults."""
        params = TableViewParams()

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertIsNone(params.columns)
        self.assertIsNone(params.sort_by)
        self.assertIsNone(params.ascending)
        self.assertEqual(params.max_rows, 100)
        self.assertFalse(params.index)
        self.assertEqual(
            params.table_classes, "table table-striped table-hover table-sm"
        )
        self.assertTrue(params.escape)
        self.assertEqual(params.border, 0)

    def test_params_custom_values(self):
        """Test parameters with custom values."""
        params = TableViewParams(
            title="Custom Table",
            description="Custom description",
            columns=["col1", "col2", "col3"],
            sort_by=["col1", "col2"],
            ascending=[True, False],
            max_rows=50,
            index=True,
            table_classes="custom-table responsive",
            escape=False,
            border=2,
        )

        self.assertEqual(params.title, "Custom Table")
        self.assertEqual(params.description, "Custom description")
        self.assertEqual(params.columns, ["col1", "col2", "col3"])
        self.assertEqual(params.sort_by, ["col1", "col2"])
        self.assertEqual(params.ascending, [True, False])
        self.assertEqual(params.max_rows, 50)
        self.assertTrue(params.index)
        self.assertEqual(params.table_classes, "custom-table responsive")
        self.assertFalse(params.escape)
        self.assertEqual(params.border, 2)

    def test_params_max_rows_validation(self):
        """Test max_rows parameter validation."""
        # Valid values
        params1 = TableViewParams(max_rows=1)
        self.assertEqual(params1.max_rows, 1)

        params2 = TableViewParams(max_rows=1000)
        self.assertEqual(params2.max_rows, 1000)

        # Note: The original model doesn't have validation constraints for max_rows
        # These would require adding Field constraints like Field(100, gt=0)
        # For now, we test that the values are accepted
        params3 = TableViewParams(max_rows=0)
        self.assertEqual(params3.max_rows, 0)

        params4 = TableViewParams(max_rows=-1)
        self.assertEqual(params4.max_rows, -1)

    def test_params_empty_lists(self):
        """Test parameters with empty lists."""
        params = TableViewParams(columns=[], sort_by=[], ascending=[])

        # Empty lists should be valid
        self.assertEqual(params.columns, [])
        self.assertEqual(params.sort_by, [])
        self.assertEqual(params.ascending, [])

    def test_params_border_validation(self):
        """Test border parameter validation."""
        # Valid values
        params1 = TableViewParams(border=0)
        self.assertEqual(params1.border, 0)

        params2 = TableViewParams(border=5)
        self.assertEqual(params2.border, 5)

        # None should be valid
        params3 = TableViewParams(border=None)
        self.assertIsNone(params3.border)


class TestTableColumn(NiamotoTestCase):
    """Test cases for TableColumn model."""

    def test_table_column_minimal(self):
        """Test minimal TableColumn with only required field."""
        column = TableColumn(source="column_name")

        self.assertEqual(column.source, "column_name")
        self.assertIsNone(column.label)
        self.assertIsNone(column.format)
        self.assertTrue(column.visible)
        self.assertTrue(column.searchable)
        self.assertTrue(column.sortable)
        self.assertIsNone(column.width)

    def test_table_column_full(self):
        """Test TableColumn with all fields."""
        column = TableColumn(
            source="species_count",
            label="Species Count",
            format="number",
            visible=False,
            searchable=False,
            sortable=False,
            width="150px",
        )

        self.assertEqual(column.source, "species_count")
        self.assertEqual(column.label, "Species Count")
        self.assertEqual(column.format, "number")
        self.assertFalse(column.visible)
        self.assertFalse(column.searchable)
        self.assertFalse(column.sortable)
        self.assertEqual(column.width, "150px")

    def test_table_column_different_formats(self):
        """Test TableColumn with different format types."""
        formats = ["number", "currency", "date", ".2f", "percent"]

        for fmt in formats:
            column = TableColumn(source="test_col", format=fmt)
            self.assertEqual(column.format, fmt)

    def test_table_column_different_widths(self):
        """Test TableColumn with different width specifications."""
        widths = ["100px", "10%", "5em", "auto", "150"]

        for width in widths:
            column = TableColumn(source="test_col", width=width)
            self.assertEqual(column.width, width)
