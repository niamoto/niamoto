import pandas as pd
from unittest.mock import Mock

from niamoto.core.plugins.widgets.donut_chart import (
    DonutChartWidget,
    DonutChartParams,
    SubplotConfig,
)
from tests.common.base_test import NiamotoTestCase


class TestDonutChartWidget(NiamotoTestCase):
    """Test cases for DonutChartWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = DonutChartWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, DonutChartParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_render_dataframe_input_success(self):
        """Test rendering with valid DataFrame input."""
        df = pd.DataFrame(
            {
                "category": ["A", "B", "C"],
                "value": [30, 40, 30],
                "description": ["Category A", "Category B", "Category C"],
            }
        )

        params = DonutChartParams(
            title="Test Donut Chart",
            labels_field="category",
            values_field="value",
            hover_name="description",
        )

        result = self.widget.render(df, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)
        self.assertIn("donut-chart-widget", result)

    def test_render_dataframe_missing_columns(self):
        """Test DataFrame with missing required columns."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "other_field": [30, 40, 30]})

        params = DonutChartParams(
            labels_field="category",
            values_field="value",  # This column doesn't exist
        )

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("DataFrame missing columns", result)

    def test_render_dataframe_missing_config(self):
        """Test DataFrame without required field configuration."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "value": [30, 40, 30]})

        params = DonutChartParams(
            title="Test Chart"
            # Missing labels_field and values_field
        )

        result = self.widget.render(df, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Missing fields for DataFrame", result)

    def test_render_dict_with_lists(self):
        """Test rendering with dictionary containing lists."""
        data = {
            "labels": ["Category A", "Category B", "Category C"],
            "values": [25.5, 35.2, 39.3],
        }

        params = DonutChartParams(
            title="Dict List Chart",
            labels_field="labels",
            values_field="values",
            hole_size=0.4,
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)

    def test_render_dict_lists_length_mismatch(self):
        """Test dictionary with mismatched list lengths."""
        data = {
            "labels": ["A", "B", "C"],
            "values": [30, 40],  # One less value
        }

        params = DonutChartParams(labels_field="labels", values_field="values")

        result = self.widget.render(data, params)

        # Should fall back to no data message since lists don't match
        self.assertIn("<p class='info'>", result)

    def test_render_dict_with_percent_keys(self):
        """Test rendering with dictionary using _percent keys."""
        data = {
            "forest_percent": 45.5,
            "urban_percent": 30.2,
            "agriculture_percent": 24.3,
        }

        params = DonutChartParams(
            title="Percent Keys Chart",
            label_mapping={
                "forest": "Forest Areas",
                "urban": "Urban Areas",
                "agriculture": "Agricultural Areas",
            },
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)

    def test_render_dict_percent_keys_non_numeric(self):
        """Test dictionary with non-numeric percent values."""
        data = {
            "forest_percent": "invalid",
            "urban_percent": 30.2,
            "agriculture_percent": None,
        }

        params = DonutChartParams(title="Mixed Data Types")

        result = self.widget.render(data, params)

        # Should still render with valid data only
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)

    def test_render_dict_no_percent_keys(self):
        """Test dictionary without _percent keys or field config."""
        data = {"some_field": 100, "other_field": "text"}

        params = DonutChartParams(title="No Valid Data")

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available", result)

    def test_render_subplots_success(self):
        """Test rendering with multiple subplots."""
        data = {
            "region_a": {"forest": 60, "urban": 40},
            "region_b": {"forest": 45, "urban": 30, "agriculture": 25},
            "region_c": {"forest": 70, "urban": 20, "water": 10},
        }

        subplots = [
            SubplotConfig(name="Region A", data_key="region_a"),
            SubplotConfig(name="Region B", data_key="region_b"),
            SubplotConfig(name="Region C", data_key="region_c"),
        ]

        params = DonutChartParams(
            title="Multi-Region Comparison", subplots=subplots, hole_size=0.3
        )

        result = self.widget.render(data, params)

        # Verify successful subplot rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)

    def test_render_subplots_with_custom_labels(self):
        """Test subplots with custom labels."""
        data = {"data1": {"cat1": 50, "cat2": 50}, "data2": {"cat1": 30, "cat2": 70}}

        subplots = [
            SubplotConfig(
                name="Dataset 1",
                data_key="data1",
                labels=["Category One", "Category Two"],
                colors=["#FF6B6B", "#4ECDC4"],
            ),
            SubplotConfig(
                name="Dataset 2",
                data_key="data2",
                labels=["Category One", "Category Two"],
            ),
        ]

        params = DonutChartParams(
            title="Custom Labels",
            subplots=subplots,
            common_labels=["Default 1", "Default 2"],
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)

    def test_render_subplots_missing_data(self):
        """Test subplots with missing data keys."""
        data = {"existing_data": {"a": 30, "b": 70}}

        subplots = [
            SubplotConfig(name="Missing", data_key="missing_key"),
            SubplotConfig(name="Existing", data_key="existing_data"),
        ]

        params = DonutChartParams(title="Partial Data", subplots=subplots)

        result = self.widget.render(data, params)

        # Should still render with available data
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)

    def test_render_subplots_no_valid_data(self):
        """Test subplots with no valid data."""
        data = {"invalid": "not a dict", "empty": {}}

        subplots = [
            SubplotConfig(name="Invalid", data_key="invalid"),
            SubplotConfig(name="Empty", data_key="empty"),
        ]

        params = DonutChartParams(title="No Valid Data", subplots=subplots)

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No valid data found", result)

    def test_render_subplots_label_value_mismatch(self):
        """Test subplots with label/value length mismatch."""
        data = {"data1": {"a": 30, "b": 40, "c": 30}}

        subplots = [
            SubplotConfig(
                name="Mismatch",
                data_key="data1",
                labels=["Label A", "Label B"],  # Only 2 labels for 3 values
            )
        ]

        params = DonutChartParams(title="Label Mismatch", subplots=subplots)

        result = self.widget.render(data, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No valid data found", result)

    def test_render_subplots_non_numeric_values(self):
        """Test subplots with non-numeric values."""
        data = {
            "data1": {"a": "invalid", "b": 40, "c": None},
            "data2": {"x": 50, "y": 50},
        }

        subplots = [
            SubplotConfig(name="Invalid", data_key="data1"),
            SubplotConfig(name="Valid", data_key="data2"),
        ]

        params = DonutChartParams(title="Mixed Validity", subplots=subplots)

        result = self.widget.render(data, params)

        # Should render with valid data only
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)

    def test_render_empty_subplots_config(self):
        """Test with empty subplots configuration."""
        data = {"some": "data"}

        params = DonutChartParams(title="Empty Subplots", subplots=[])

        result = self.widget.render(data, params)

        # Empty subplots list is treated as falsy, so falls back to normal dict processing
        # Since the data doesn't match expected format, it should show no data message
        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available", result)

    def test_render_none_data(self):
        """Test rendering with None data."""
        params = DonutChartParams(title="No Data")

        result = self.widget.render(None, params)

        self.assertIn("<p class='info'>", result)
        self.assertIn("No data available", result)

    def test_render_unsupported_data_type(self):
        """Test rendering with unsupported data type."""
        data = "unsupported string data"

        params = DonutChartParams(title="Invalid Type")

        result = self.widget.render(data, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Unsupported data type", result)

    def test_render_dataframe_empty_after_processing(self):
        """Test DataFrame that becomes empty after numeric conversion."""
        df = pd.DataFrame(
            {
                "category": ["A", "B", "C"],
                "value": ["invalid", "also_invalid", "still_invalid"],
            }
        )

        params = DonutChartParams(labels_field="category", values_field="value")

        result = self.widget.render(df, params)

        # Should result in no data message
        self.assertIn("<p class='info'>", result)

    def test_render_with_custom_parameters(self):
        """Test rendering with custom styling parameters."""
        data = {"category_percent": 60, "other_percent": 40}

        params = DonutChartParams(
            title="Custom Styling",
            hole_size=0.6,
            text_info="percent",
            legend_orientation="h",
            color_discrete_sequence=["#FF5733", "#33AFFF"],
            hovertemplate="<b>%{label}</b><br>Value: %{value}<br>Percent: %{percent}",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)

    def test_render_dataframe_processing_error(self):
        """Test DataFrame processing with conversion errors."""
        # Create a DataFrame that will cause processing issues
        df = pd.DataFrame({"category": ["A", "B", "C"], "value": [10, 20, 30]})

        params = DonutChartParams(labels_field="category", values_field="value")

        # Mock pandas operations to raise an exception
        from unittest.mock import patch

        with patch("pandas.to_numeric", side_effect=Exception("Processing error")):
            result = self.widget.render(df, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error preparing DataFrame data", result)

    def test_render_with_hover_data(self):
        """Test rendering with hover data configuration."""
        df = pd.DataFrame(
            {
                "category": ["A", "B", "C"],
                "value": [30, 40, 30],
                "description": ["Category A", "Category B", "Category C"],
                "extra_info": ["Info A", "Info B", "Info C"],
            }
        )

        params = DonutChartParams(
            title="Hover Data Test",
            labels_field="category",
            values_field="value",
            hover_name="description",
            hover_data=["extra_info"],
        )

        result = self.widget.render(df, params)

        # Verify successful rendering with hover data
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-chart-widget", result)


class TestDonutChartParams(NiamotoTestCase):
    """Test cases for DonutChartParams validation."""

    def test_params_defaults(self):
        """Test parameter defaults."""
        params = DonutChartParams()

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertIsNone(params.labels_field)
        self.assertIsNone(params.values_field)
        self.assertIsNone(params.label_mapping)
        self.assertIsNone(params.color_discrete_sequence)
        self.assertEqual(params.hole_size, 0.3)
        self.assertEqual(params.text_info, "percent+label")
        self.assertIsNone(params.legend_orientation)
        self.assertIsNone(params.subplots)
        self.assertIsNone(params.common_labels)

    def test_params_custom_values(self):
        """Test parameters with custom values."""
        subplot_config = SubplotConfig(
            name="Test Subplot",
            data_key="test_data",
            labels=["A", "B"],
            colors=["red", "blue"],
        )

        params = DonutChartParams(
            title="Custom Chart",
            description="Test description",
            labels_field="custom_labels",
            values_field="custom_values",
            label_mapping={"a": "Label A", "b": "Label B"},
            color_discrete_sequence=["#FF0000", "#00FF00"],
            hole_size=0.5,
            text_info="value",
            legend_orientation="v",
            subplots=[subplot_config],
            common_labels=["Common A", "Common B"],
            hover_name="hover_field",
            hover_data=["extra1", "extra2"],
            hovertemplate="Custom: %{label}",
        )

        self.assertEqual(params.title, "Custom Chart")
        self.assertEqual(params.description, "Test description")
        self.assertEqual(params.labels_field, "custom_labels")
        self.assertEqual(params.values_field, "custom_values")
        self.assertEqual(params.label_mapping, {"a": "Label A", "b": "Label B"})
        self.assertEqual(params.color_discrete_sequence, ["#FF0000", "#00FF00"])
        self.assertEqual(params.hole_size, 0.5)
        self.assertEqual(params.text_info, "value")
        self.assertEqual(params.legend_orientation, "v")
        self.assertEqual(len(params.subplots), 1)
        self.assertEqual(params.subplots[0].name, "Test Subplot")
        self.assertEqual(params.common_labels, ["Common A", "Common B"])
        self.assertEqual(params.hover_name, "hover_field")
        self.assertEqual(params.hover_data, ["extra1", "extra2"])
        self.assertEqual(params.hovertemplate, "Custom: %{label}")

    def test_params_hole_size_validation(self):
        """Test hole_size parameter validation."""
        # Valid hole sizes
        params1 = DonutChartParams(hole_size=0.0)
        self.assertEqual(params1.hole_size, 0.0)

        params2 = DonutChartParams(hole_size=0.9)
        self.assertEqual(params2.hole_size, 0.9)

        # Invalid hole sizes should raise validation error
        with self.assertRaises(ValueError):
            DonutChartParams(hole_size=-0.1)

        with self.assertRaises(ValueError):
            DonutChartParams(hole_size=1.0)

    def test_params_legend_orientation_validation(self):
        """Test legend_orientation parameter validation."""
        # Valid orientations
        params1 = DonutChartParams(legend_orientation="h")
        self.assertEqual(params1.legend_orientation, "h")

        params2 = DonutChartParams(legend_orientation="v")
        self.assertEqual(params2.legend_orientation, "v")

        # Invalid orientation should raise validation error
        with self.assertRaises(ValueError):
            DonutChartParams(legend_orientation="invalid")


class TestSubplotConfig(NiamotoTestCase):
    """Test cases for SubplotConfig model."""

    def test_subplot_config_minimal(self):
        """Test minimal SubplotConfig."""
        config = SubplotConfig(name="Test", data_key="test_key")

        self.assertEqual(config.name, "Test")
        self.assertEqual(config.data_key, "test_key")
        self.assertIsNone(config.labels)
        self.assertIsNone(config.colors)

    def test_subplot_config_full(self):
        """Test full SubplotConfig with all options."""
        config = SubplotConfig(
            name="Full Config",
            data_key="full_key",
            labels=["Label 1", "Label 2", "Label 3"],
            colors=["#FF0000", "#00FF00", "#0000FF"],
        )

        self.assertEqual(config.name, "Full Config")
        self.assertEqual(config.data_key, "full_key")
        self.assertEqual(config.labels, ["Label 1", "Label 2", "Label 3"])
        self.assertEqual(config.colors, ["#FF0000", "#00FF00", "#0000FF"])
