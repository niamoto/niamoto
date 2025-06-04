from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from niamoto.common.exceptions import ProcessError
from niamoto.core.plugins.exporters.index_generator import IndexGeneratorPlugin
from niamoto.core.plugins.models import (
    IndexGeneratorConfig,
    IndexGeneratorDisplayField,
    IndexGeneratorFilterConfig,
    IndexGeneratorPageConfig,
    IndexGeneratorViewConfig,
)
from tests.common.base_test import NiamotoTestCase


class TestIndexGeneratorPlugin(NiamotoTestCase):
    """Test cases for IndexGeneratorPlugin."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_db = Mock()
        self.plugin = IndexGeneratorPlugin(self.mock_db)
        self.test_output_dir = Path("/tmp/test_output")

    def test_init(self):
        """Test plugin initialization."""
        self.assertEqual(self.plugin.db, self.mock_db)

    def test_get_nested_value(self):
        """Test _get_nested_value method with various data structures."""
        data = {
            "level1": {
                "level2": {"value": "nested_value"},
                "array": ["item1", "item2"],
            },
            "simple": "simple_value",
        }

        # Test successful nested access
        result = self.plugin._get_nested_value(data, "level1.level2.value")
        self.assertEqual(result, "nested_value")

        # Test simple access
        result = self.plugin._get_nested_value(data, "simple")
        self.assertEqual(result, "simple_value")

        # Test array access
        result = self.plugin._get_nested_value(data, "level1.array")
        self.assertEqual(result, ["item1", "item2"])

        # Test missing path
        result = self.plugin._get_nested_value(data, "level1.missing.value")
        self.assertIsNone(result)

        # Test path through non-dict
        result = self.plugin._get_nested_value(data, "simple.extra")
        self.assertIsNone(result)

    def test_parse_json_field(self):
        """Test _parse_json_field method with various inputs."""
        # Test None
        result = self.plugin._parse_json_field(None)
        self.assertIsNone(result)

        # Test dict input
        dict_input = {"key": "value"}
        result = self.plugin._parse_json_field(dict_input)
        self.assertEqual(result, dict_input)

        # Test valid JSON string
        json_string = '{"key": "value", "number": 123}'
        result = self.plugin._parse_json_field(json_string)
        self.assertEqual(result, {"key": "value", "number": 123})

        # Test invalid JSON string
        invalid_json = "{invalid json}"
        result = self.plugin._parse_json_field(invalid_json)
        self.assertIsNone(result)

        # Test non-string, non-dict input
        result = self.plugin._parse_json_field(123)
        self.assertIsNone(result)

    def test_extract_field_value(self):
        """Test _extract_field_value method."""
        item = {
            "id": 1,
            "name": "Test Item",
            "general_info": {
                "name": {"value": "Nested Name"},
                "description": "Nested Description",
            },
            "array_field": '["item1", "item2"]',
            "fallback_value": "Fallback",
        }

        # Test simple field extraction
        field = IndexGeneratorDisplayField(
            name="item_name", source="name", label="Name", type="text"
        )
        result = self.plugin._extract_field_value(item, field)
        self.assertEqual(result, "Test Item")

        # Test nested field extraction
        field = IndexGeneratorDisplayField(
            name="nested_name",
            source="general_info.name.value",
            label="Nested Name",
            type="text",
        )
        result = self.plugin._extract_field_value(item, field)
        self.assertEqual(result, "Nested Name")

        # Test fallback
        field = IndexGeneratorDisplayField(
            name="missing_field",
            source="missing.path",
            label="Missing",
            type="text",
            fallback="fallback_value",
        )
        result = self.plugin._extract_field_value(item, field)
        self.assertEqual(result, "Fallback")

        # Test json_array type
        field = IndexGeneratorDisplayField(
            name="array", source="array_field", label="Array", type="json_array"
        )
        result = self.plugin._extract_field_value(item, field)
        self.assertEqual(result, ["item1", "item2"])

    def test_get_group_data_success(self):
        """Test successful data retrieval for a group."""
        # Mock database responses
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = [
            {
                "taxon_id": 1,
                "name": "Species 1",
                "general_info": '{"name": {"value": "Scientific Name 1"}}',
                "family": "Family 1",
            },
            {
                "taxon_id": 2,
                "name": "Species 2",
                "general_info": '{"name": {"value": "Scientific Name 2"}}',
                "family": "Family 2",
            },
        ]

        # Configure display fields
        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="name", source="name", label="Common Name", type="text"
                ),
                IndexGeneratorDisplayField(
                    name="scientific_name",
                    source="general_info.name.value",
                    label="Scientific Name",
                    type="text",
                ),
            ],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        result = self.plugin._get_group_data("taxon", config)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["taxon_id"], 1)
        self.assertEqual(result[0]["name"], "Species 1")
        self.assertEqual(result[0]["scientific_name"], "Scientific Name 1")

    def test_get_group_data_with_filters(self):
        """Test data retrieval with filters applied."""
        # Mock database responses
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = [
            {
                "taxon_id": 1,
                "name": "Species 1",
                "family": "Fabaceae",
                "status": "native",
            },
            {
                "taxon_id": 2,
                "name": "Species 2",
                "family": "Myrtaceae",
                "status": "endemic",
            },
            {
                "taxon_id": 3,
                "name": "Species 3",
                "family": "Fabaceae",
                "status": "introduced",
            },
        ]

        # Configure with filters
        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="name", source="name", label="Name", type="text"
                )
            ],
            filters=[
                IndexGeneratorFilterConfig(
                    field="family", operator="equals", values=["Fabaceae"]
                )
            ],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        result = self.plugin._get_group_data("taxon", config)

        # Should only include Fabaceae items
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["taxon_id"], 1)
        self.assertEqual(result[1]["taxon_id"], 3)

    def test_get_group_data_with_in_filter(self):
        """Test data retrieval with 'in' filter operator."""
        # Mock database responses
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = [
            {"shape_id": 1, "type": "forest", "name": "Forest 1"},
            {"shape_id": 2, "type": "urban", "name": "City 1"},
            {"shape_id": 3, "type": "forest", "name": "Forest 2"},
            {"shape_id": 4, "type": "agricultural", "name": "Farm 1"},
        ]

        # Configure with 'in' filter
        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="name", source="name", label="Name", type="text"
                )
            ],
            filters=[
                IndexGeneratorFilterConfig(
                    field="type", operator="in", values=["forest", "urban"]
                )
            ],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        result = self.plugin._get_group_data("shape", config)

        # Should include forest and urban items
        self.assertEqual(len(result), 3)
        shape_ids = [item["shape_id"] for item in result]
        self.assertEqual(shape_ids, [1, 2, 3])

    def test_get_group_data_table_not_exists(self):
        """Test error handling when table doesn't exist."""
        self.mock_db.has_table.return_value = False

        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        result = self.plugin._get_group_data("missing_table", config)

        self.assertEqual(result, [])

    def test_get_group_data_no_results(self):
        """Test handling of empty results."""
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = []

        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        result = self.plugin._get_group_data("taxon", config)

        self.assertEqual(result, [])

    def test_get_group_data_exception(self):
        """Test exception handling in data retrieval."""
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.side_effect = Exception("Database error")

        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        with self.assertRaises(ProcessError) as context:
            self.plugin._get_group_data("taxon", config)

        self.assertIn("Failed to fetch data for group 'taxon'", str(context.exception))

    @patch("builtins.open", create=True)
    def test_generate_index_success(self, mock_open):
        """Test successful index generation."""
        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock jinja environment
        mock_template = Mock()
        mock_template.render.return_value = "<html>Index Page</html>"
        mock_jinja_env = Mock()
        mock_jinja_env.get_template.return_value = mock_template

        # Mock HTML params
        mock_html_params = Mock()
        mock_html_params.site = Mock()
        mock_html_params.site.model_dump.return_value = {"title": "Test Site"}
        mock_html_params.navigation = [{"name": "Home", "url": "/"}]

        # Configure index
        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="name", source="name", label="Name", type="text"
                )
            ],
            page_config=IndexGeneratorPageConfig(title="Test Index", items_per_page=20),
        )

        # Mock _get_group_data
        with patch.object(self.plugin, "_get_group_data") as mock_get_data:
            mock_get_data.return_value = [
                {"taxon_id": 1, "name": "Species 1"},
                {"taxon_id": 2, "name": "Species 2"},
            ]

            # Create output directory mock
            with patch("pathlib.Path.mkdir"):
                self.plugin.generate_index(
                    "taxon",
                    config,
                    self.test_output_dir,
                    mock_jinja_env,
                    mock_html_params,
                )

        # Verify template was rendered with correct context
        mock_template.render.assert_called_once()
        context = mock_template.render.call_args[0][0]

        self.assertEqual(context["group_by"], "taxon")
        self.assertEqual(len(context["items_data"]), 2)
        self.assertEqual(context["depth"], 1)
        self.assertIn("index_config", context)

        # Verify file was written
        mock_file.write.assert_called_once_with("<html>Index Page</html>")

    @patch("builtins.open", create=True)
    def test_generate_index_no_data(self, mock_open):
        """Test index generation with no data."""
        # Mock jinja environment
        mock_jinja_env = Mock()
        mock_html_params = Mock()

        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        # Mock _get_group_data to return empty list
        with patch.object(self.plugin, "_get_group_data") as mock_get_data:
            mock_get_data.return_value = []

            self.plugin.generate_index(
                "taxon", config, self.test_output_dir, mock_jinja_env, mock_html_params
            )

        # Verify no file operations occurred
        mock_open.assert_not_called()

    def test_generate_index_exception(self):
        """Test exception handling in index generation."""
        mock_jinja_env = Mock()
        mock_html_params = Mock()

        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        # Mock _get_group_data to raise exception
        with patch.object(self.plugin, "_get_group_data") as mock_get_data:
            mock_get_data.side_effect = Exception("Data error")

            with self.assertRaises(ProcessError) as context:
                self.plugin.generate_index(
                    "taxon",
                    config,
                    self.test_output_dir,
                    mock_jinja_env,
                    mock_html_params,
                )

            self.assertIn(
                "Failed to generate index for group 'taxon'", str(context.exception)
            )

    def test_export_not_implemented(self):
        """Test that export method raises NotImplementedError."""
        with self.assertRaises(NotImplementedError) as context:
            self.plugin.export(None, None)

        self.assertIn("should be called directly", str(context.exception))

    def test_extract_field_value_json_array_with_quotes(self):
        """Test extraction of JSON array with single quotes."""
        item = {"array_field": "['item1', 'item2', 'item3']"}

        field = IndexGeneratorDisplayField(
            name="array", source="array_field", label="Array", type="json_array"
        )

        result = self.plugin._extract_field_value(item, field)
        self.assertEqual(result, ["item1", "item2", "item3"])

    def test_get_group_data_complex_json_parsing(self):
        """Test complex JSON field parsing in group data."""
        # Mock database responses with various JSON formats
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = [
            {
                "plot_id": 1,
                "name": "Plot 1",
                "metadata": '{"location": {"lat": -21.0, "lon": 165.0}}',  # JSON string
                "stats": {"count": 100, "area": 50.5},  # Already a dict
            }
        ]

        config = IndexGeneratorConfig(
            template="group_index.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="location",
                    source="metadata.location",
                    label="Location",
                    type="object",
                ),
                IndexGeneratorDisplayField(
                    name="count", source="stats.count", label="Count", type="number"
                ),
            ],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        result = self.plugin._get_group_data("plot", config)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["location"], {"lat": -21.0, "lon": 165.0})
        self.assertEqual(result[0]["count"], 100)


class TestIndexGeneratorModels(NiamotoTestCase):
    """Test cases for IndexGeneratorConfig and related models."""

    def test_index_generator_config_minimal(self):
        """Test minimal IndexGeneratorConfig."""
        config = IndexGeneratorConfig(
            template="test_template.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="name", source="name", label="Name", type="text"
                )
            ],
            page_config=IndexGeneratorPageConfig(title="Test Index"),
        )

        self.assertEqual(config.template, "test_template.html")
        self.assertEqual(len(config.display_fields), 1)
        self.assertIsNone(config.filters)
        self.assertIsNone(config.views)
        self.assertEqual(config.output_pattern, "{group_by}/{id}.html")

    def test_index_generator_config_full(self):
        """Test full IndexGeneratorConfig with all options."""
        config = IndexGeneratorConfig(
            template="custom_template.html",
            output_pattern="custom/{group_by}/{id}.html",
            display_fields=[
                IndexGeneratorDisplayField(
                    name="name",
                    source="general_info.name.value",
                    label="Scientific Name",
                    type="text",
                    sortable=True,
                    searchable=True,
                ),
                IndexGeneratorDisplayField(
                    name="status",
                    source="conservation_status",
                    label="Status",
                    type="badge",
                    fallback="status",
                ),
            ],
            filters=[
                IndexGeneratorFilterConfig(
                    field="family", operator="in", values=["Fabaceae", "Myrtaceae"]
                )
            ],
            page_config=IndexGeneratorPageConfig(
                title="Custom Index", description="Test description", items_per_page=50
            ),
            views=[
                IndexGeneratorViewConfig(
                    type="grid", template="grid_view.html", default=True
                ),
                IndexGeneratorViewConfig(type="list", template="list_view.html"),
            ],
        )

        self.assertEqual(config.template, "custom_template.html")
        self.assertEqual(config.output_pattern, "custom/{group_by}/{id}.html")
        self.assertEqual(len(config.display_fields), 2)
        self.assertEqual(len(config.filters), 1)
        self.assertEqual(config.page_config.items_per_page, 50)
        self.assertEqual(len(config.views), 2)
        self.assertTrue(config.views[0].default)
