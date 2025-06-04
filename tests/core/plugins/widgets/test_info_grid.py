from unittest.mock import Mock

from niamoto.core.plugins.widgets.info_grid import (
    InfoGridWidget,
    InfoGridParams,
    InfoItem,
)
from tests.common.base_test import NiamotoTestCase


class TestInfoGridWidget(NiamotoTestCase):
    """Test cases for InfoGridWidget."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.widget = InfoGridWidget(self.mock_db)

    def test_init(self):
        """Test widget initialization."""
        self.assertEqual(self.widget.db, self.mock_db)
        self.assertEqual(self.widget.param_schema, InfoGridParams)

    def test_get_dependencies(self):
        """Test dependencies method."""
        dependencies = self.widget.get_dependencies()
        self.assertIsInstance(dependencies, set)
        self.assertEqual(len(dependencies), 0)

    def test_render_with_static_values(self):
        """Test rendering with static values only."""
        items = [
            InfoItem(label="Total Species", value=1250, unit="species"),
            InfoItem(label="Forest Coverage", value=68.5, unit="%"),
            InfoItem(label="Protected Areas", value=15, unit="km²"),
        ]

        params = InfoGridParams(
            title="Biodiversity Stats",
            description="Key biodiversity indicators",
            items=items,
            grid_columns=3,
        )

        result = self.widget.render(None, params)

        # Verify successful rendering
        self.assertIsInstance(result, str)
        self.assertIn("info-grid-widget", result)
        self.assertIn("Biodiversity Stats", result)
        self.assertIn("Key biodiversity indicators", result)
        self.assertIn("Total Species", result)
        self.assertIn("1250", result)
        self.assertIn("species", result)
        self.assertIn("Forest Coverage", result)
        self.assertIn("68.5", result)

    def test_render_with_data_sources(self):
        """Test rendering with data from sources."""
        data = {
            "stats": {
                "total_species": 1500,
                "forest_percent": 72.3,
                "areas": {"protected": 25},
            },
            "region": "New Caledonia",
        }

        items = [
            InfoItem(
                label="Species Count", source="stats.total_species", unit="species"
            ),
            InfoItem(label="Forest Cover", source="stats.forest_percent", unit="%"),
            InfoItem(label="Protected", source="stats.areas.protected", unit="km²"),
            InfoItem(label="Region", source="region"),
            InfoItem(label="Static", value="Test Value"),
        ]

        params = InfoGridParams(title="Dynamic Stats", items=items)

        result = self.widget.render(data, params)

        # Verify data was properly extracted
        self.assertIn("1500", result)
        self.assertIn("72.3", result)
        self.assertIn("25", result)
        self.assertIn("New Caledonia", result)
        self.assertIn("Test Value", result)

    def test_render_with_missing_sources(self):
        """Test rendering with missing data sources."""
        data = {"existing_key": 100}

        items = [
            InfoItem(label="Existing", source="existing_key", value="fallback1"),
            InfoItem(label="Missing", source="missing_key", value="fallback2"),
            InfoItem(label="No Fallback", source="another_missing"),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(data, params)

        # Should render existing and fallback values, skip items with no value
        self.assertIn("100", result)  # From source
        self.assertIn("fallback2", result)  # Fallback value used
        # "No Fallback" item should be skipped as it has no value

    def test_render_with_nested_value_extraction(self):
        """Test extraction from nested value dictionaries."""
        data = {
            "metric1": {"value": 250},
            "metric2": {"value": 42.7, "confidence": 0.95},
            "metric3": "direct_value",
        }

        items = [
            InfoItem(label="Metric 1", source="metric1"),
            InfoItem(label="Metric 2", source="metric2"),
            InfoItem(label="Metric 3", source="metric3"),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(data, params)

        # Should extract 'value' from nested dictionaries
        self.assertIn("250", result)
        self.assertIn("42.7", result)
        self.assertIn("direct_value", result)

    def test_render_with_format_mapping(self):
        """Test rendering with value mapping format."""
        data = {"status": "active", "level": "high", "category": "unknown_value"}

        items = [
            InfoItem(
                label="Status",
                source="status",
                format="map",
                mapping={"active": "✅ Active", "inactive": "❌ Inactive"},
            ),
            InfoItem(
                label="Priority",
                source="level",
                format="map",
                mapping={
                    "high": "🔴 High Priority",
                    "medium": "🟡 Medium Priority",
                    "low": "🟢 Low Priority",
                },
            ),
            InfoItem(
                label="Category",
                source="category",
                format="map",
                mapping={"known": "Known Value"},
            ),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(data, params)

        # Verify mapping worked
        self.assertIn("✅ Active", result)
        self.assertIn("🔴 High Priority", result)
        # Unknown value should fall back to original
        self.assertIn("unknown_value", result)

    def test_render_with_number_formatting(self):
        """Test rendering with number formatting."""
        data = {
            "count1": 1234567,
            "count2": 1234.56,
            "count3": {"value": 9876543},
            "count4": {"value": 123.789},
            "invalid": "not_a_number",
        }

        items = [
            InfoItem(label="Large Integer", source="count1", format="number"),
            InfoItem(label="Decimal", source="count2", format="number"),
            InfoItem(label="Nested Integer", source="count3", format="number"),
            InfoItem(label="Nested Decimal", source="count4", format="number"),
            InfoItem(label="Invalid Number", source="invalid", format="number"),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(data, params)

        # Verify French-style number formatting
        self.assertIn("1 234 567", result)  # Integer with space separators
        self.assertIn("1 234,56", result)  # Decimal with comma
        self.assertIn("9 876 543", result)  # Nested integer
        self.assertIn("123,79", result)  # Nested decimal (rounded to 2 places)
        self.assertIn("not_a_number", result)  # Invalid should remain as-is

    def test_render_with_icons(self):
        """Test rendering with various icon formats."""
        items = [
            InfoItem(label="Users", value=150, icon="fas fa-users"),
            InfoItem(label="Forest", value=75, icon="fa-tree"),
            InfoItem(label="Species", value=200, icon="fish"),  # Will become fa-fish
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(None, params)

        # Verify icon HTML generation
        self.assertIn("fas fa-users", result)
        self.assertIn("fa-tree", result)
        self.assertIn("fas fa-fish", result)

    def test_render_with_descriptions_tooltips(self):
        """Test rendering with descriptions as tooltips."""
        items = [
            InfoItem(
                label="Species Count",
                value=1500,
                description="Total number of documented species in the region",
            ),
            InfoItem(
                label="Coverage",
                value=68.5,
                unit="%",
                description="Percentage of forest coverage",
            ),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(None, params)

        # Verify tooltip attributes
        self.assertIn('title="Total number of documented species', result)
        self.assertIn('title="Percentage of forest coverage"', result)

    def test_render_with_different_grid_columns(self):
        """Test rendering with different grid column configurations."""
        items = [
            InfoItem(label="Item 1", value=1),
            InfoItem(label="Item 2", value=2),
            InfoItem(label="Item 3", value=3),
        ]

        # Test different grid configurations
        for columns in [1, 2, 3, 4, 5, 6]:
            params = InfoGridParams(items=items, grid_columns=columns)
            result = self.widget.render(None, params)

            # Should contain appropriate grid class
            self.assertIn("grid", result)
            self.assertIn("grid-cols", result)

    def test_render_with_invalid_grid_columns(self):
        """Test rendering with invalid grid column values."""
        items = [InfoItem(label="Test", value=1)]

        # Test invalid values
        params = InfoGridParams(items=items, grid_columns=0)
        result = self.widget.render(None, params)
        # Should use default responsive grid
        self.assertIn("md:grid-cols-2", result)

        params = InfoGridParams(items=items, grid_columns=10)
        result = self.widget.render(None, params)
        # Should use default responsive grid
        self.assertIn("lg:grid-cols-3", result)

    def test_render_no_items(self):
        """Test rendering with no items."""
        params = InfoGridParams(items=[])

        result = self.widget.render(None, params)

        self.assertIn("No information items configured", result)
        self.assertIn("text-gray-500", result)

    def test_render_none_data_with_sources(self):
        """Test rendering when data is None but sources are specified."""
        items = [
            InfoItem(label="From Source", source="some.key"),
            InfoItem(label="Static", value="test"),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(None, params)

        # Should render only static item since source data is None
        self.assertIn("Static", result)
        self.assertIn("test", result)

    def test_render_non_dict_data_with_sources(self):
        """Test rendering when data is not a dictionary but sources are specified."""
        items = [
            InfoItem(label="From Source", source="some.key"),
            InfoItem(label="Static", value="test"),
        ]

        params = InfoGridParams(items=items)

        # Use string data instead of dict
        result = self.widget.render("not_a_dict", params)

        # Should render only static item since data is not a dict
        self.assertIn("Static", result)
        self.assertIn("test", result)

    def test_render_all_items_skipped(self):
        """Test rendering when all items are skipped due to no values."""
        items = [
            InfoItem(label="No Value 1", source="missing.key"),
            InfoItem(label="No Value 2", source="another.missing"),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render({}, params)

        # Should return empty string when no items rendered
        self.assertEqual(result, "")

    def test_render_complex_scenario(self):
        """Test a complex scenario with multiple features."""
        data = {
            "biodiversity": {
                "species_count": {"value": 2847},
                "endemic_ratio": 0.73,
            },
            "conservation": {"status": "protected", "area_km2": 18590.5},
            "threats": {"level": "medium"},
        }

        items = [
            InfoItem(
                label="Total Species",
                source="biodiversity.species_count",
                format="number",
                icon="fas fa-leaf",
                description="Total documented species count",
            ),
            InfoItem(
                label="Endemism Rate",
                source="biodiversity.endemic_ratio",
                format="number",
                unit="%",
                icon="star",
            ),
            InfoItem(
                label="Protection Status",
                source="conservation.status",
                format="map",
                mapping={
                    "protected": "🛡️ Protected",
                    "threatened": "⚠️ Threatened",
                    "unprotected": "❌ Unprotected",
                },
                icon="fas fa-shield-alt",
            ),
            InfoItem(
                label="Protected Area",
                source="conservation.area_km2",
                format="number",
                unit="km²",
                description="Total protected area size",
            ),
            InfoItem(
                label="Threat Level",
                source="threats.level",
                format="map",
                mapping={"low": "🟢 Low", "medium": "🟡 Medium", "high": "🔴 High"},
            ),
        ]

        params = InfoGridParams(
            title="Conservation Dashboard",
            description="Key conservation metrics for the region",
            items=items,
            grid_columns=3,
        )

        result = self.widget.render(data, params)

        # Verify complex rendering
        self.assertIn("Conservation Dashboard", result)
        self.assertIn("Key conservation metrics", result)
        self.assertIn("2 847", result)  # Formatted number
        self.assertIn("0,73", result)  # Decimal formatting
        self.assertIn("🛡️ Protected", result)  # Mapped value
        self.assertIn("18 590,50", result)  # Large decimal formatted
        self.assertIn("🟡 Medium", result)  # Mapped threat level
        self.assertIn("fas fa-leaf", result)  # Icons
        self.assertIn("fas fa-shield-alt", result)
        self.assertIn('title="Total documented species', result)  # Tooltips

    def test_render_edge_cases_for_coverage(self):
        """Test edge cases to achieve full coverage."""
        data = {
            "nested_value_in_dict": {"value": 456},
            "null_after_extraction": {"value": None},
            "for_number_format": {"value": 789.123},
        }

        items = [
            # This will extract value from nested dict, then check if None (line 151 coverage)
            InfoItem(label="Null Value", source="null_after_extraction"),
            # This will hit the nested dict path in number formatting (line 165 coverage)
            InfoItem(
                label="Nested Number", source="for_number_format", format="number"
            ),
        ]

        params = InfoGridParams(items=items)

        result = self.widget.render(data, params)

        # Should skip the null value item and format the number correctly
        self.assertIn("789,12", result)  # Nested value formatted as number
        self.assertNotIn("Null Value", result)  # Null value item should be skipped


class TestInfoGridParams(NiamotoTestCase):
    """Test cases for InfoGridParams validation."""

    def test_params_minimal(self):
        """Test minimal InfoGridParams."""
        item = InfoItem(label="Test", value="test_value")
        params = InfoGridParams(items=[item])

        self.assertIsNone(params.title)
        self.assertIsNone(params.description)
        self.assertEqual(len(params.items), 1)
        self.assertIsNone(params.grid_columns)

    def test_params_full(self):
        """Test full InfoGridParams with all options."""
        items = [
            InfoItem(
                label="Test Item",
                value=123,
                source="data.source",
                unit="units",
                description="Test description",
                icon="fas fa-test",
                format="number",
                mapping={"key": "value"},
            )
        ]

        params = InfoGridParams(
            title="Test Title",
            description="Test description",
            items=items,
            grid_columns=4,
        )

        self.assertEqual(params.title, "Test Title")
        self.assertEqual(params.description, "Test description")
        self.assertEqual(len(params.items), 1)
        self.assertEqual(params.grid_columns, 4)

    def test_params_validation_empty_items(self):
        """Test validation with empty items list."""
        # Should be valid to have empty items list
        params = InfoGridParams(items=[])
        self.assertEqual(len(params.items), 0)


class TestInfoItem(NiamotoTestCase):
    """Test cases for InfoItem model."""

    def test_info_item_minimal(self):
        """Test minimal InfoItem with only required field."""
        item = InfoItem(label="Test Label")

        self.assertEqual(item.label, "Test Label")
        self.assertIsNone(item.value)
        self.assertIsNone(item.source)
        self.assertIsNone(item.unit)
        self.assertIsNone(item.description)
        self.assertIsNone(item.icon)
        self.assertIsNone(item.format)
        self.assertIsNone(item.mapping)

    def test_info_item_with_static_value(self):
        """Test InfoItem with static value."""
        item = InfoItem(
            label="Species Count",
            value=1250,
            unit="species",
            description="Total species in database",
        )

        self.assertEqual(item.label, "Species Count")
        self.assertEqual(item.value, 1250)
        self.assertEqual(item.unit, "species")
        self.assertEqual(item.description, "Total species in database")

    def test_info_item_with_source(self):
        """Test InfoItem with data source."""
        item = InfoItem(
            label="Forest Coverage",
            source="stats.forest.percentage",
            unit="%",
            format="number",
        )

        self.assertEqual(item.label, "Forest Coverage")
        self.assertEqual(item.source, "stats.forest.percentage")
        self.assertEqual(item.unit, "%")
        self.assertEqual(item.format, "number")

    def test_info_item_with_mapping(self):
        """Test InfoItem with value mapping."""
        mapping = {"active": "✅ Active", "inactive": "❌ Inactive"}

        item = InfoItem(
            label="Status", source="current_status", format="map", mapping=mapping
        )

        self.assertEqual(item.label, "Status")
        self.assertEqual(item.source, "current_status")
        self.assertEqual(item.format, "map")
        self.assertEqual(item.mapping, mapping)

    def test_info_item_full(self):
        """Test InfoItem with all fields."""
        item = InfoItem(
            label="Complex Item",
            value="default_value",
            source="data.complex.path",
            unit="units",
            description="A complex item with all features",
            icon="fas fa-complex",
            format="map",
            mapping={"key1": "value1", "key2": "value2"},
        )

        self.assertEqual(item.label, "Complex Item")
        self.assertEqual(item.value, "default_value")
        self.assertEqual(item.source, "data.complex.path")
        self.assertEqual(item.unit, "units")
        self.assertEqual(item.description, "A complex item with all features")
        self.assertEqual(item.icon, "fas fa-complex")
        self.assertEqual(item.format, "map")
        self.assertEqual(item.mapping, {"key1": "value1", "key2": "value2"})

    def test_info_item_different_value_types(self):
        """Test InfoItem with different value types."""
        # String value
        item1 = InfoItem(label="String", value="text_value")
        self.assertEqual(item1.value, "text_value")

        # Integer value
        item2 = InfoItem(label="Integer", value=42)
        self.assertEqual(item2.value, 42)

        # Float value
        item3 = InfoItem(label="Float", value=3.14159)
        self.assertEqual(item3.value, 3.14159)

        # None value (should be valid)
        item4 = InfoItem(label="None", value=None)
        self.assertIsNone(item4.value)
