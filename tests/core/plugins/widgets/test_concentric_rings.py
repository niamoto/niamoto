from unittest.mock import Mock, patch

from niamoto.core.plugins.widgets.concentric_rings import (
    ConcentricRingsWidget,
    ConcentricRingsParams,
)
from tests.common.base_test import NiamotoTestCase


class TestConcentricRingsWidget(NiamotoTestCase):
    """Test cases for ConcentricRingsWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = ConcentricRingsWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, ConcentricRingsParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 1)
        # Should contain the Plotly CDN URL
        self.assertTrue(any("plotly" in dep for dep in dependencies))

    def test_render_invalid_data_type(self):
        """Test rendering with invalid data type."""
        params = ConcentricRingsParams()

        # Test with non-dict data
        result = self.widget.render("invalid", params)
        self.assertIn("Invalid data format", result)
        self.assertIn("error", result)

        result = self.widget.render([], params)
        self.assertIn("Invalid data format", result)

        result = self.widget.render(None, params)
        self.assertIn("Invalid data format", result)

    def test_render_valid_data(self):
        """Test rendering with valid concentric rings data."""
        # Test data with all three rings
        data = {
            "um": {"forest": 75.5, "non_forest": 24.5},
            "num": {"forest": 82.3, "non_forest": 17.7},
            "emprise": {"forest": 68.9, "non_forest": 31.1},
        }

        params = ConcentricRingsParams(
            title="Forest Cover Analysis",
            description="Concentric visualization of forest coverage",
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("Invalid data format", result)
        self.assertIn("plotly-graph-div", result)

        # Should contain data for all three rings
        self.assertIn('"values":[75.5,24.5]', result)  # UM ring data
        self.assertIn('"values":[82.3,17.7]', result)  # NUM ring data
        self.assertIn('"values":[68.9,31.1]', result)  # Emprise ring data

    def test_render_missing_rings(self):
        """Test rendering with missing rings."""
        # Data with only two rings
        data = {
            "um": {"forest": 80.0, "non_forest": 20.0},
            "emprise": {"forest": 70.0, "non_forest": 30.0},
        }

        params = ConcentricRingsParams()

        result = self.widget.render(data, params)

        # Verify successful rendering despite missing rings
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("Invalid data format", result)
        self.assertIn("plotly-graph-div", result)

        # Should contain data for available rings only
        self.assertIn('"values":[80.0,20.0]', result)  # UM ring data
        self.assertIn('"values":[70.0,30.0]', result)  # Emprise ring data

    def test_render_custom_colors(self):
        """Test rendering with custom category colors."""
        data = {
            "um": {"forest": 60.0, "non_forest": 40.0},
            "num": {"forest": 70.0, "non_forest": 30.0},
        }

        # Test with simple color mapping
        params = ConcentricRingsParams(
            category_colors={"forest": "#228B22", "non_forest": "#8B4513"}
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

        # Verify custom colors are applied in the JSON
        self.assertIn('"#228B22"', result)  # Forest color
        self.assertIn('"#8B4513"', result)  # Non-forest color

    def test_render_ring_specific_colors(self):
        """Test rendering with ring-specific colors."""
        data = {
            "um": {"forest": 55.0, "non_forest": 45.0},
            "num": {"forest": 65.0, "non_forest": 35.0},
        }

        # Test with ring-specific color mapping
        params = ConcentricRingsParams(
            category_colors={
                "forest": {"um": "#006400", "num": "#228B22", "default": "#32CD32"},
                "non_forest": "#D2691E",
            }
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

        # Verify ring-specific colors are applied
        self.assertIn('"#006400"', result)  # UM forest color
        self.assertIn('"#228B22"', result)  # NUM forest color
        self.assertIn('"#D2691E"', result)  # Non-forest color

    def test_render_zero_values(self):
        """Test rendering with zero values."""
        data = {
            "um": {"forest": 0, "non_forest": 0},  # All zeros
            "num": {"forest": 100.0, "non_forest": 0},  # One zero
            "emprise": {"forest": 50.0, "non_forest": 50.0},  # No zeros
        }

        params = ConcentricRingsParams()

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

        # Ring with all zeros should be skipped, so only 2 rings should be rendered
        self.assertIn('"values":[100.0,0]', result)  # NUM ring data
        self.assertIn('"values":[50.0,50.0]', result)  # Emprise ring data
        # UM ring should be skipped (all zeros)

    def test_render_custom_ring_order(self):
        """Test rendering with custom ring order."""
        data = {
            "inner": {"category1": 30.0, "category2": 70.0},
            "middle": {"category1": 40.0, "category2": 60.0},
            "outer": {"category1": 50.0, "category2": 50.0},
        }

        params = ConcentricRingsParams(
            ring_order=["inner", "middle", "outer"],
            ring_labels={
                "inner": "Inner Ring",
                "middle": "Middle Ring",
                "outer": "Outer Ring",
            },
        )

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

        # Should contain data for all custom rings
        self.assertIn('"values":[30.0,70.0]', result)  # Inner ring data
        self.assertIn('"values":[40.0,60.0]', result)  # Middle ring data
        self.assertIn('"values":[50.0,50.0]', result)  # Outer ring data

        # Should contain custom labels
        self.assertIn('"Inner Ring"', result)
        self.assertIn('"Middle Ring"', result)
        self.assertIn('"Outer Ring"', result)

    def test_render_invalid_ring_data(self):
        """Test rendering with invalid ring data."""
        data = {
            "um": "not a dict",  # Invalid data type
            "num": {"forest": 70.0, "non_forest": 30.0},
            "emprise": None,  # None value
        }

        params = ConcentricRingsParams()

        result = self.widget.render(data, params)

        # Verify successful rendering despite invalid data
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

        # Should only render the valid ring (NUM)
        self.assertIn('"values":[70.0,30.0]', result)  # NUM ring data

    def test_render_exception_handling(self):
        """Test exception handling during rendering."""
        # Create data that will cause an exception
        data = {"um": {"forest": 50.0, "non_forest": 50.0}}

        params = ConcentricRingsParams()

        # Mock Figure to raise an exception
        with patch("plotly.graph_objects.Figure", side_effect=Exception("Plot error")):
            result = self.widget.render(data, params)

            self.assertIn("Error generating concentric rings chart", result)
            self.assertIn("error", result)

    def test_render_multiple_categories(self):
        """Test rendering with more than two categories per ring."""
        data = {
            "um": {"forest": 40.0, "agriculture": 30.0, "urban": 20.0, "water": 10.0}
        }

        params = ConcentricRingsParams()

        result = self.widget.render(data, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertIn("plotly-graph-div", result)

        # Should contain all four categories
        self.assertIn('"values":[40.0,30.0,20.0,10.0]', result)  # All category values

    def test_render_custom_border_width(self):
        """Test rendering with custom border width."""
        data = {"um": {"forest": 80.0, "non_forest": 20.0}}

        params = ConcentricRingsParams(border_width=5.0)

        # Test the actual rendering without complex mocking to avoid interference
        result = self.widget.render(data, params)

        # Since this uses actual Plotly, the result should be HTML containing plotly content
        self.assertIsInstance(result, str)
        self.assertNotIn("<p class='error'>", result)
        self.assertNotIn("Invalid data format", result)

        # The result should contain HTML/JS content from Plotly
        self.assertTrue(len(result) > 100)  # Should be substantial HTML content
        self.assertIn("plotly-graph-div", result)  # Should contain Plotly elements

        # Verify the border width is actually applied in the JSON
        self.assertIn(
            '"width":5.0', result
        )  # Check that the border width parameter was applied


class TestConcentricRingsParams(NiamotoTestCase):
    """Test cases for ConcentricRingsParams validation."""

    def test_params_defaults(self):
        """Test parameter defaults."""
        params = ConcentricRingsParams()

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertEqual(params.ring_order, ["um", "num", "emprise"])
        self.assertEqual(
            params.ring_labels, {"um": "UM", "num": "NUM", "emprise": "Emprise"}
        )
        self.assertEqual(params.category_colors, {})
        self.assertEqual(
            params.default_colors, ["#6B8E23", "#8B7355", "#C5A98B", "#F4E4BC"]
        )
        self.assertEqual(params.border_width, 2.0)
        self.assertEqual(params.height, 500)

    def test_params_custom_values(self):
        """Test parameters with custom values."""
        params = ConcentricRingsParams(
            title="Custom Title",
            description="Custom Description",
            ring_order=["inner", "outer"],
            ring_labels={"inner": "Center", "outer": "Edge"},
            category_colors={"cat1": "#FF0000", "cat2": "#00FF00"},
            default_colors=["#111111", "#222222"],
            border_width=3.5,
            height=600,
        )

        self.assertEqual(params.title, "Custom Title")
        self.assertEqual(params.description, "Custom Description")
        self.assertEqual(params.ring_order, ["inner", "outer"])
        self.assertEqual(params.ring_labels, {"inner": "Center", "outer": "Edge"})
        self.assertEqual(params.category_colors, {"cat1": "#FF0000", "cat2": "#00FF00"})
        self.assertEqual(params.default_colors, ["#111111", "#222222"])
        self.assertEqual(params.border_width, 3.5)
        self.assertEqual(params.height, 600)

    def test_params_complex_category_colors(self):
        """Test complex category colors with ring-specific values."""
        category_colors = {
            "forest": {
                "um": "#006400",
                "num": "#228B22",
                "emprise": "#32CD32",
                "default": "#00FF00",
            },
            "non_forest": "#8B4513",
        }

        params = ConcentricRingsParams(category_colors=category_colors)

        self.assertEqual(params.category_colors["forest"]["um"], "#006400")
        self.assertEqual(params.category_colors["forest"]["default"], "#00FF00")
        self.assertEqual(params.category_colors["non_forest"], "#8B4513")
