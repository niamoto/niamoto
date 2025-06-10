from unittest.mock import Mock, patch

from niamoto.core.plugins.widgets.sunburst_chart import (
    SunburstChartWidget,
    SunburstChartWidgetParams,
)
from tests.common.base_test import NiamotoTestCase


class TestSunburstChartWidget(NiamotoTestCase):
    """Test cases for SunburstChartWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = SunburstChartWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, SunburstChartWidgetParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_render_basic_sunburst(self):
        """Test rendering with basic sunburst chart."""
        data = {
            "land_use": {"forest": 1500, "agriculture": 800, "urban": 200},
            "protection_status": {"protected": 1200, "unprotected": 1300},
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_custom_labels(self):
        """Test rendering with custom category and leaf labels."""
        data = {
            "emprise": {"forest": 2000, "non_forest": 500},
            "altitude": {"low": 800, "medium": 1200, "high": 500},
        }

        params = SunburstChartWidgetParams(
            title="Biodiversity Distribution",
            category_labels={"emprise": "Land Cover", "altitude": "Elevation Zones"},
            leaf_labels={
                "forest": "Forêt",
                "non_forest": "Hors-forêt",
                "low": "Basse altitude",
                "medium": "Moyenne altitude",
                "high": "Haute altitude",
            },
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_custom_colors(self):
        """Test rendering with custom leaf colors."""
        data = {
            "vegetation": {
                "primary_forest": 1000,
                "secondary_forest": 800,
                "grassland": 300,
            },
            "water": {"rivers": 150, "lakes": 100},
        }

        params = SunburstChartWidgetParams(
            leaf_colors={
                "Forêt primaire": "#228B22",  # Forest green
                "Forêt secondaire": "#90EE90",  # Light green
                "Prairie": "#FFD700",  # Gold
                "Rivières": "#4169E1",  # Royal blue
                "Lacs": "#1E90FF",  # Dodger blue
            },
            leaf_labels={
                "primary_forest": "Forêt primaire",
                "secondary_forest": "Forêt secondaire",
                "grassland": "Prairie",
                "rivers": "Rivières",
                "lakes": "Lacs",
            },
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_nested_colors(self):
        """Test rendering with nested color mapping (category-specific colors)."""
        data = {
            "conservation": {"protected": 1500, "unprotected": 1000},
            "tourism": {"protected": 200, "unprotected": 800},
        }

        params = SunburstChartWidgetParams(
            leaf_colors={
                "Protected": {
                    "conservation": "#2E8B57",  # Sea green for conservation protected
                    "tourism": "#FF6347",  # Tomato for tourism protected
                    "default": "#808080",  # Gray fallback
                },
                "Unprotected": "#CD853F",  # Peru for all unprotected
            },
            leaf_labels={"protected": "Protected", "unprotected": "Unprotected"},
            category_labels={
                "conservation": "Conservation Areas",
                "tourism": "Tourism Areas",
            },
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_with_different_text_info(self):
        """Test rendering with different text info options."""
        data = {"species": {"endemic": 45, "native": 120, "introduced": 25}}

        text_info_options = [
            "label",
            "text",
            "value",
            "percent root",
            "percent entry",
            "percent parent",
            "label+percent parent",
        ]

        for text_info in text_info_options:
            with self.subTest(text_info=text_info):
                params = SunburstChartWidgetParams(text_info=text_info)

                result = self.widget.render(data, params)

                # Verify successful rendering
                self.assertIsInstance(result, str)
                self.assertNotIn("<p class='error'>", result)
                self.assertIn("plotly-graph-div", result)

    def test_render_with_different_branchvalues(self):
        """Test rendering with different branchvalues options."""
        data = {"habitat": {"forest": 800, "savanna": 400, "wetland": 100}}

        for branchvalues in ["total", "remainder"]:
            with self.subTest(branchvalues=branchvalues):
                params = SunburstChartWidgetParams(branchvalues=branchvalues)

                result = self.widget.render(data, params)

                # Verify successful rendering
                self.assertIsInstance(result, str)
                self.assertNotIn("<p class='error'>", result)
                self.assertIn("plotly-graph-div", result)

    def test_render_with_opacity(self):
        """Test rendering with custom opacity."""
        data = {"category": {"item1": 50, "item2": 30}}

        for opacity in [0.5, 0.8, 1.0]:
            with self.subTest(opacity=opacity):
                params = SunburstChartWidgetParams(opacity=opacity)

                result = self.widget.render(data, params)

                # Verify successful rendering
                self.assertIsInstance(result, str)
                self.assertNotIn("<p class='error'>", result)
                self.assertIn("plotly-graph-div", result)

    def test_render_invalid_data_not_dict(self):
        """Test rendering with invalid data (not a dictionary)."""
        invalid_data = [1, 2, 3]

        params = SunburstChartWidgetParams()

        result = self.widget.render(invalid_data, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Invalid data format for Sunburst Chart", result)

    def test_render_invalid_data_not_nested_dict(self):
        """Test rendering with invalid data (not nested dictionary)."""
        invalid_data = {
            "category1": 100,  # Should be dict, not number
            "category2": {"item": 50},
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(invalid_data, params)

        self.assertIn("<p class='error'>", result)
        self.assertIn("Invalid data format for Sunburst Chart", result)

    def test_render_with_invalid_category_values(self):
        """Test rendering with invalid values in category (not dict)."""
        data = {
            "valid_category": {"item1": 50, "item2": 30},
            "invalid_category": "should_be_dict",  # Invalid
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Widget validates all values are dicts upfront, so this should error
        self.assertIn("<p class='error'>", result)
        self.assertIn("Invalid data format for Sunburst Chart", result)

    def test_render_with_invalid_leaf_values(self):
        """Test rendering with invalid leaf values (not numbers)."""
        data = {
            "category": {
                "valid_item": 50,
                "invalid_item": "not_a_number",  # Invalid
                "another_valid": 30,
            }
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should render successfully, skipping invalid values
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_empty_data(self):
        """Test rendering with empty data."""
        data = {}

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should return no data message for empty data
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("No data available", result)

    def test_render_zero_values(self):
        """Test rendering with zero values."""
        data = {
            "category1": {"zero_item": 0, "positive_item": 50},
            "category2": {"another_zero": 0, "another_positive": 30},
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should render successfully (including zero values)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_all_zero_values(self):
        """Test rendering with all values being zero."""
        data = {
            "category1": {"zero_item1": 0, "zero_item2": 0},
            "category2": {"zero_item3": 0, "zero_item4": 0},
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should return no data message when all values are zero
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("No data available", result)

    def test_render_negative_values(self):
        """Test rendering with negative values."""
        data = {"category": {"positive": 50, "negative": -20, "zero": 0}}

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should render successfully (Plotly handles negative values)
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_float_values(self):
        """Test rendering with float values."""
        data = {
            "measurements": {
                "precise_value": 123.456,
                "small_value": 0.789,
                "large_value": 9876.543,
            }
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should render successfully
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_single_category(self):
        """Test rendering with single category."""
        data = {"single_category": {"item1": 100, "item2": 200, "item3": 150}}

        params = SunburstChartWidgetParams(
            title="Single Category Sunburst",
            category_labels={"single_category": "The Category"},
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_large_dataset(self):
        """Test rendering with larger dataset."""
        # Create a larger dataset with multiple categories and items
        data = {}

        categories = [
            "habitat",
            "elevation",
            "protection",
            "accessibility",
            "vegetation",
        ]
        items_per_category = 8

        for i, category in enumerate(categories):
            data[category] = {}
            for j in range(items_per_category):
                item_name = f"item_{j + 1}"
                # Vary values based on category and item
                value = (i + 1) * 100 + (j + 1) * 10
                data[category][item_name] = value

        params = SunburstChartWidgetParams(
            title="Large Biodiversity Dataset",
            description="Distribution across multiple ecological dimensions",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_ecological_data_example(self):
        """Test rendering with realistic ecological data."""
        data = {
            "emprise": {"forest": 1850.5, "non_forest": 649.5},
            "elevation": {"low": 800.2, "medium": 1200.8, "high": 499.0},
            "protection_status": {
                "protected": 1250.0,
                "partially_protected": 750.5,
                "unprotected": 499.5,
            },
            "endemic_species": {
                "high_endemism": 350.0,
                "medium_endemism": 900.0,
                "low_endemism": 1250.0,
            },
        }

        params = SunburstChartWidgetParams(
            title="New Caledonia Biodiversity Distribution",
            description="Distribution of biodiversity across ecological gradients",
            category_labels={
                "emprise": "Land Cover",
                "elevation": "Elevation Zones",
                "protection_status": "Conservation Status",
                "endemic_species": "Endemism Level",
            },
            leaf_labels={
                "forest": "Forêt",
                "non_forest": "Hors-forêt",
                "low": "Basse altitude (0-200m)",
                "medium": "Moyenne altitude (200-800m)",
                "high": "Haute altitude (>800m)",
                "protected": "Aires protégées",
                "partially_protected": "Partiellement protégé",
                "unprotected": "Non protégé",
                "high_endemism": "Fort endémisme",
                "medium_endemism": "Endémisme moyen",
                "low_endemism": "Faible endémisme",
            },
            leaf_colors={
                "Forêt": "#228B22",
                "Hors-forêt": "#DEB887",
                "Basse altitude (0-200m)": "#87CEEB",
                "Moyenne altitude (200-800m)": "#98FB98",
                "Haute altitude (>800m)": "#F0E68C",
                "Aires protégées": "#32CD32",
                "Partiellement protégé": "#FFD700",
                "Non protégé": "#CD853F",
                "Fort endémisme": "#FF4500",
                "Endémisme moyen": "#FFA500",
                "Faible endémisme": "#FFFF00",
            },
            text_info="label+percent parent",
            branchvalues="total",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_plotly_exception(self):
        """Test handling of Plotly rendering exceptions."""
        data = {"category": {"item": 100}}

        params = SunburstChartWidgetParams()

        # Mock plotly Figure to raise an exception
        with patch(
            "plotly.graph_objects.Figure", side_effect=Exception("Plotly error")
        ):
            result = self.widget.render(data, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error generating Sunburst chart", result)
            self.assertIn("Plotly error", result)

    def test_render_sunburst_trace_exception(self):
        """Test handling of Sunburst trace creation exceptions."""
        data = {"category": {"item": 100}}

        params = SunburstChartWidgetParams()

        # Mock Sunburst trace to raise an exception
        with patch(
            "plotly.graph_objects.Sunburst",
            side_effect=Exception("Sunburst trace error"),
        ):
            result = self.widget.render(data, params)

            self.assertIn("<p class='error'>", result)
            self.assertIn("Error generating Sunburst chart", result)
            self.assertIn("Sunburst trace error", result)

    def test_render_invalid_color_format(self):
        """Test rendering with invalid color format."""
        data = {"category": {"item1": 50, "item2": 30}}

        params = SunburstChartWidgetParams(
            leaf_colors={
                "Item1": 123,  # Invalid: should be string or dict
                "Item2": "#FF0000",  # Valid
            },
            leaf_labels={"item1": "Item1", "item2": "Item2"},
        )

        result = self.widget.render(data, params)

        # Should render successfully using default color for invalid format
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_empty_categories(self):
        """Test rendering with empty categories."""
        data = {
            "category1": {"item1": 50},
            "empty_category": {},  # Empty category
            "category2": {"item2": 30},
        }

        params = SunburstChartWidgetParams()

        result = self.widget.render(data, params)

        # Should render successfully, handling empty categories
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

    def test_render_deterministic_order(self):
        """Test that rendering produces consistent structure (though IDs may vary)."""
        data = {
            "z_category": {"z_item": 100, "a_item": 50},
            "a_category": {"z_item": 30, "a_item": 70},
        }

        params = SunburstChartWidgetParams()

        # Render and verify consistent structure
        result1 = self.widget.render(data, params)
        result2 = self.widget.render(data, params)

        # Both should be successful (though IDs may differ due to Plotly)
        self.assertIsInstance(result1, str)
        self.assertNotIn("<p class='error'>", result1)
        self.assertIn("plotly-graph-div", result1)

        self.assertIsInstance(result2, str)
        self.assertNotIn("<p class='error'>", result2)
        self.assertIn("plotly-graph-div", result2)

        # Both should contain the same data elements (categories/items)
        # Note: Plotly generates unique IDs so exact equality isn't expected


class TestSunburstChartWidgetParams(NiamotoTestCase):
    """Test cases for SunburstChartWidgetParams validation."""

    def test_params_minimal_configuration(self):
        """Test parameters with minimal configuration."""
        params = SunburstChartWidgetParams()

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertEqual(params.category_labels, {})
        self.assertEqual(params.leaf_labels, {})
        self.assertEqual(params.leaf_colors, {})
        self.assertEqual(params.branchvalues, "total")
        self.assertEqual(params.text_info, "percent parent")
        self.assertEqual(params.opacity, 1.0)

    def test_params_all_fields(self):
        """Test parameters with all fields specified."""
        category_labels = {"cat1": "Category 1", "cat2": "Category 2"}
        leaf_labels = {"leaf1": "Leaf 1", "leaf2": "Leaf 2"}
        leaf_colors = {"Leaf 1": "#FF0000", "Leaf 2": "#00FF00"}

        params = SunburstChartWidgetParams(
            title="Test Sunburst",
            description="Test description",
            category_labels=category_labels,
            leaf_labels=leaf_labels,
            leaf_colors=leaf_colors,
            branchvalues="remainder",
            text_info="label+value",
            opacity=0.8,
        )

        self.assertEqual(params.title, "Test Sunburst")
        self.assertEqual(params.description, "Test description")
        self.assertEqual(params.category_labels, category_labels)
        self.assertEqual(params.leaf_labels, leaf_labels)
        self.assertEqual(params.leaf_colors, leaf_colors)
        self.assertEqual(params.branchvalues, "remainder")
        self.assertEqual(params.text_info, "label+value")
        self.assertEqual(params.opacity, 0.8)

    def test_params_branchvalues_options(self):
        """Test different branchvalues options."""
        for branchvalues in ["total", "remainder"]:
            params = SunburstChartWidgetParams(branchvalues=branchvalues)
            self.assertEqual(params.branchvalues, branchvalues)

    def test_params_text_info_options(self):
        """Test different text_info options."""
        text_info_options = [
            "label",
            "text",
            "value",
            "current path",
            "percent root",
            "percent entry",
            "percent parent",
            "label+value",
            "label+percent parent",
        ]

        for text_info in text_info_options:
            params = SunburstChartWidgetParams(text_info=text_info)
            self.assertEqual(params.text_info, text_info)

    def test_params_opacity_validation(self):
        """Test opacity parameter validation."""
        # Valid opacity values
        valid_opacities = [0.0, 0.5, 1.0]
        for opacity in valid_opacities:
            params = SunburstChartWidgetParams(opacity=opacity)
            self.assertEqual(params.opacity, opacity)

        # Invalid opacity values should raise validation error
        invalid_opacities = [-0.1, 1.1, 2.0]
        for opacity in invalid_opacities:
            with self.assertRaises(ValueError):
                SunburstChartWidgetParams(opacity=opacity)

    def test_params_nested_leaf_colors(self):
        """Test nested leaf colors structure."""
        nested_colors = {
            "Forest": {
                "category1": "#228B22",
                "category2": "#32CD32",
                "default": "#90EE90",
            },
            "Urban": "#808080",
        }

        params = SunburstChartWidgetParams(leaf_colors=nested_colors)
        self.assertEqual(params.leaf_colors, nested_colors)

    def test_params_empty_dictionaries(self):
        """Test parameters with empty dictionaries."""
        params = SunburstChartWidgetParams(
            category_labels={}, leaf_labels={}, leaf_colors={}
        )

        self.assertEqual(params.category_labels, {})
        self.assertEqual(params.leaf_labels, {})
        self.assertEqual(params.leaf_colors, {})

    def test_params_complex_labels(self):
        """Test parameters with complex label mappings."""
        category_labels = {
            "habitat_type": "Type d'habitat",
            "conservation_status": "Statut de conservation",
            "species_richness": "Richesse spécifique",
        }

        leaf_labels = {
            "primary_forest": "Forêt primaire",
            "secondary_forest": "Forêt secondaire",
            "grassland": "Prairie",
            "wetland": "Zone humide",
            "protected": "Protégé",
            "unprotected": "Non protégé",
            "high": "Élevé",
            "medium": "Moyen",
            "low": "Faible",
        }

        params = SunburstChartWidgetParams(
            category_labels=category_labels, leaf_labels=leaf_labels
        )

        self.assertEqual(params.category_labels, category_labels)
        self.assertEqual(params.leaf_labels, leaf_labels)

    def test_params_mixed_color_types(self):
        """Test leaf_colors with mixed string and dict values."""
        mixed_colors = {
            "Forest": "#228B22",  # Simple string color
            "Urban": {  # Nested dict with category-specific colors
                "residential": "#FFB6C1",
                "commercial": "#DDA0DD",
                "default": "#808080",
            },
            "Water": "#4169E1",  # Simple string color
        }

        params = SunburstChartWidgetParams(leaf_colors=mixed_colors)
        self.assertEqual(params.leaf_colors, mixed_colors)

    def test_params_string_values_in_dicts(self):
        """Test that dictionary values can be any type (for flexibility)."""
        flexible_params = {
            "category_labels": {"key1": "Label 1", "key2": "Label 2"},
            "leaf_labels": {"leaf_a": "Leaf A", "leaf_b": "Leaf B"},
            "leaf_colors": {
                "item1": "#FF0000",
                "item2": {"nested": "value"},
                "item3": 123,  # Non-string value - should be allowed by Pydantic
            },
        }

        # This should not raise an error due to Dict[str, Any] type
        params = SunburstChartWidgetParams(**flexible_params)
        self.assertEqual(params.leaf_colors["item1"], "#FF0000")
        self.assertEqual(params.leaf_colors["item2"], {"nested": "value"})
        self.assertEqual(params.leaf_colors["item3"], 123)
