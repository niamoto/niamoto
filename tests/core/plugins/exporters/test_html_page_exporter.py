"""Tests for the HtmlPageExporter plugin."""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List
from unittest.mock import Mock, MagicMock, patch

from niamoto.core.plugins.exporters.html_page_exporter import HtmlPageExporter
from niamoto.core.plugins.models import (
    TargetConfig,
    HtmlExporterParams,
    StaticPageConfig,
    GroupConfigWeb,
    WidgetConfig,
    StaticPageContext,
    SiteConfig,
    IndexGeneratorConfig,
    IndexGeneratorPageConfig,
    IndexGeneratorDisplayField,
)
from niamoto.common.database import Database
from niamoto.common.exceptions import ConfigurationError, ProcessError
from tests.common.base_test import NiamotoTestCase


class MockWidgetPlugin:
    """Mock widget plugin for testing."""

    def __init__(self, db=None):
        self.db = db
        self.param_schema = None

    def get_dependencies(self):
        return ["chart.js"]

    def render(self, data, params):
        return f"<div>Widget rendered with data: {data}</div>"

    def get_container_html(self, widget_id, content, config):
        return f'<div id="{widget_id}" class="widget">{content}</div>'


class TestHtmlPageExporter(NiamotoTestCase):
    """Test cases for HtmlPageExporter."""

    @classmethod
    def setUpClass(cls):
        """Clear registry before class tests start."""
        from niamoto.core.plugins.registry import PluginRegistry

        PluginRegistry.clear()
        super().setUpClass()

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.test_dir) / "output"
        self.template_dir = Path(self.test_dir) / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Clear the plugin registry to ensure test isolation
        from niamoto.core.plugins.registry import PluginRegistry

        PluginRegistry.clear()

        # Create mock database
        self.mock_db = Mock(spec=Database)
        self.mock_db.get_table_columns.return_value = [
            "id",
            "name",
            "full_name",
            "parent_id",
            "lft",
            "rght",
        ]

        # Create test templates
        self._create_test_templates()

        # Default target config
        self.target_config = TargetConfig(
            name="test_export",
            enabled=True,
            exporter="html_page_exporter",
            params={
                "output_dir": str(self.output_dir),
                "template_dir": str(self.template_dir),
                "include_default_assets": False,
                "site": {"title": "Test Site", "base_url": "https://example.com"},
            },
            static_pages=[],
            groups=[],
        )

    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # Clear the plugin registry after test
        from niamoto.core.plugins.registry import PluginRegistry

        PluginRegistry.clear()

        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        """Clear registry after class tests end."""
        from niamoto.core.plugins.registry import PluginRegistry

        PluginRegistry.clear()
        super().tearDownClass()

    def _create_test_templates(self):
        """Create test templates."""
        # Base template
        base_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ site.title }}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
"""
        (self.template_dir / "_base.html").write_text(base_template)

        # Static page template
        static_template = """
{% extends "_base.html" %}
{% block content %}
<h1>{{ page.title }}</h1>
{{ page_content_html|safe }}
{% endblock %}
"""
        (self.template_dir / "_layouts" / "static_page.html").parent.mkdir(
            exist_ok=True
        )
        (self.template_dir / "_layouts" / "static_page.html").write_text(
            static_template
        )

        # Group index template
        index_template = """
{% extends "_base.html" %}
{% block content %}
<h1>{{ group_by }} Index</h1>
<ul>
{% for item in items %}
    <li>{{ item.name }}</li>
{% endfor %}
</ul>
{% endblock %}
"""
        (self.template_dir / "_layouts" / "group_index.html").write_text(index_template)

        # Group detail template
        detail_template = """
{% extends "_base.html" %}
{% block content %}
<h1>{{ item.name }}</h1>
{% for widget_key, widget_html in widgets.items() %}
    {{ widget_html|safe }}
{% endfor %}
{% endblock %}
"""
        (self.template_dir / "_layouts" / "group_detail_with_sidebar.html").write_text(
            detail_template
        )

        # Also create templates at root level for new template structure
        (self.template_dir / "group_index.html").write_text(index_template)
        (self.template_dir / "group_detail.html").write_text(detail_template)

        # Create _group_index.html for traditional index generation
        (self.template_dir / "_group_index.html").write_text(index_template)
        (self.template_dir / "_group_detail.html").write_text(detail_template)

    def test_init(self):
        """Test exporter initialization."""
        exporter = HtmlPageExporter(self.mock_db)
        self.assertEqual(exporter.db, self.mock_db)
        self.assertEqual(exporter._navigation_cache, {})
        self.assertEqual(exporter._navigation_js_generated, set())
        self.assertEqual(exporter._reference_table_cache, {})
        self.assertEqual(exporter._table_columns_cache, {})

    def test_get_nested_data(self):
        """Test _get_nested_data method."""
        exporter = HtmlPageExporter(self.mock_db)

        data = {"level1": {"level2": {"value": "test"}}}

        # Test successful retrieval
        result = exporter._get_nested_data(data, "level1.level2.value")
        self.assertEqual(result, "test")

        # Test missing key
        result = exporter._get_nested_data(data, "level1.missing")
        self.assertIsNone(result)

        # Test accessing non-dict
        result = exporter._get_nested_data(data, "level1.level2.value.extra")
        self.assertIsNone(result)

    def test_navigation_data_orders_by_lft_for_nested_sets(self):
        """
        Navigation data should be ordered by nested-set boundaries to preserve hierarchy.

        The exporter currently chooses the ORDER BY column from an unordered set of fields,
        which can select the wrong column (e.g. taxonomy_id) and scramble the resulting tree.
        """
        exporter = HtmlPageExporter(self.mock_db)

        self.mock_db.has_table.return_value = True
        self.mock_db.get_table_columns.return_value = [
            "taxonomy_id",
            "full_name",
            "lft",
            "rght",
            "level",
        ]

        group_config = GroupConfigWeb(
            group_by="taxonomy",
            data_source="db",
            navigation_entity="taxonomy",
            output_pattern="taxonomy/{id}.html",
            index_output_pattern="taxonomy/index.html",
            widgets=[
                WidgetConfig(
                    plugin="hierarchical_nav_widget",
                    data_source="unused",
                    params={
                        "referential_data": "entity_taxonomy",
                        "id_field": "id",
                        "name_field": "full_name",
                        "lft_field": "lft",
                        "rght_field": "rght",
                        "level_field": "level",
                        "base_url": "{{ depth }}taxon/",
                    },
                )
            ],
        )

        captured_queries: List[str] = []

        def fake_fetch_all(query: str):
            captured_queries.append(query)
            return [
                {
                    "taxonomy_id": 10,
                    "full_name": "Family A",
                    "lft": 1,
                    "rght": 6,
                    "level": 0,
                },
                {
                    "taxonomy_id": 11,
                    "full_name": "Genus A",
                    "lft": 2,
                    "rght": 5,
                    "level": 1,
                },
                {
                    "taxonomy_id": 12,
                    "full_name": "Species A",
                    "lft": 3,
                    "rght": 4,
                    "level": 2,
                },
            ]

        self.mock_db.fetch_all.side_effect = fake_fetch_all

        with patch.object(
            exporter,
            "_extract_navigation_fields",
            return_value=["taxonomy_id", "full_name", "lft", "rght", "level"],
        ):
            exporter._generate_navigation_js(group_config, self.output_dir)

        self.assertGreater(
            len(captured_queries), 0, "navigation query was not executed"
        )
        navigation_query = captured_queries[0]
        self.assertIn('ORDER BY "lft"', navigation_query)

        # Ensure identifier values are serialised as strings in the JS payload
        js_path = self.output_dir / "assets/js/taxonomy_navigation.js"
        if not js_path.exists():
            js_path = self.output_dir / "assets/js/taxons_navigation.js"
        self.assertTrue(js_path.exists())
        js_content = js_path.read_text()
        self.assertIn('"taxonomy_id":"10"', js_content)

    def test_export_basic(self):
        """Test basic export functionality."""
        exporter = HtmlPageExporter(self.mock_db)

        # Add a static page
        self.target_config.static_pages = [
            StaticPageConfig(
                name="index",
                output_file="index.html",
                template="_layouts/static_page.html",
                context=StaticPageContext(title="Home", content_markdown="# Welcome"),
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        # Check output file was created
        index_file = self.output_dir / "index.html"
        self.assertTrue(index_file.exists())

        # Check content
        content = index_file.read_text()
        self.assertIn("Test Site", content)
        self.assertIn("<h1>Welcome</h1>", content)

    def test_export_calls_process_groups_without_parallel_options(self):
        """Export should use the sequential group-processing call shape."""
        exporter = HtmlPageExporter(self.mock_db)
        self.target_config.groups = [
            GroupConfigWeb(
                group_by="taxons",
                data_source="db",
                output_pattern="taxons/{id}.html",
                index_output_pattern="taxons/index.html",
                widgets=[],
            )
        ]

        with (
            patch.object(exporter, "_copy_static_assets"),
            patch.object(exporter, "_process_static_pages"),
            patch.object(exporter, "_process_groups") as mock_process_groups,
        ):
            exporter.export(self.target_config, self.mock_db)

        mock_process_groups.assert_called_once()
        self.assertNotIn("workers", mock_process_groups.call_args.kwargs)

    @patch(
        "niamoto.core.plugins.exporters.html_page_exporter.importlib.resources.files"
    )
    def test_copy_default_assets(self, mock_resources):
        """Test copying default assets."""
        # Create mock asset structure
        # The structure should be: parent_dir/assets/[css, js, etc]
        parent_path = Path(self.test_dir) / "niamoto_publish"
        mock_assets_path = parent_path / "assets"
        mock_assets_path.mkdir(parents=True, exist_ok=True)
        (mock_assets_path / "css").mkdir()
        (mock_assets_path / "css" / "style.css").write_text("body { color: red; }")
        (mock_assets_path / "js").mkdir()
        (mock_assets_path / "js" / "script.js").write_text("console.log('test');")

        # Mock importlib.resources to return a traversable object
        # The code converts it to Path, so we need to mock it properly
        mock_traversable = MagicMock()
        mock_traversable.__str__.return_value = str(parent_path)
        mock_traversable.__fspath__.return_value = str(parent_path)
        mock_resources.return_value = mock_traversable

        exporter = HtmlPageExporter(self.mock_db)
        params = HtmlExporterParams(
            output_dir=str(self.output_dir),
            template_dir=str(self.template_dir),
            include_default_assets=True,
        )

        exporter._copy_static_assets(params, self.output_dir)

        # Check assets were copied
        self.assertTrue((self.output_dir / "assets" / "css" / "style.css").exists())
        self.assertTrue((self.output_dir / "assets" / "js" / "script.js").exists())

    @patch("niamoto.core.plugins.exporters.html_page_exporter.Config.get_niamoto_home")
    def test_copy_user_assets(self, mock_get_home):
        """Test copying user-specified assets."""
        mock_get_home.return_value = self.test_dir

        # Create user assets
        user_assets_dir = Path(self.test_dir) / "my_assets"
        user_assets_dir.mkdir()
        (user_assets_dir / "custom.css").write_text("body { background: blue; }")

        exporter = HtmlPageExporter(self.mock_db)
        params = HtmlExporterParams(
            output_dir=str(self.output_dir),
            template_dir=str(self.template_dir),
            include_default_assets=False,
            copy_assets_from=["my_assets"],
        )

        exporter._copy_static_assets(params, self.output_dir)

        # Check user assets were copied
        self.assertTrue((self.output_dir / "my_assets" / "custom.css").exists())

    def test_process_static_pages_with_markdown(self):
        """Test processing static pages with markdown content."""
        exporter = HtmlPageExporter(self.mock_db)

        static_pages = [
            StaticPageConfig(
                name="about",
                output_file="about.html",
                template="_layouts/static_page.html",
                context=StaticPageContext(
                    title="About", content_markdown="## About Us\n\nWe are *awesome*!"
                ),
            )
        ]

        from jinja2 import Environment, FileSystemLoader

        jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        from markdown_it import MarkdownIt

        md = MarkdownIt()

        params = HtmlExporterParams(
            output_dir=str(self.output_dir),
            template_dir=str(self.template_dir),
            site=SiteConfig(title="Test Site"),
        )

        exporter._process_static_pages(
            static_pages, jinja_env, params, self.output_dir, md
        )

        # Check output
        about_file = self.output_dir / "about.html"
        self.assertTrue(about_file.exists())
        content = about_file.read_text()
        self.assertIn("<h2>About Us</h2>", content)
        self.assertIn("<em>awesome</em>", content)

    def test_process_static_pages_with_content_source(self):
        """Test processing static pages with external content source."""
        # Create content file
        content_file = Path(self.test_dir) / "content.md"
        content_file.write_text("# External Content\n\nLoaded from file.")

        exporter = HtmlPageExporter(self.mock_db)

        static_pages = [
            StaticPageConfig(
                name="external",
                output_file="external.html",
                template="_layouts/static_page.html",
                context=StaticPageContext(
                    title="External", content_source=str(content_file)
                ),
            )
        ]

        from jinja2 import Environment, FileSystemLoader

        jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        from markdown_it import MarkdownIt

        md = MarkdownIt()

        params = HtmlExporterParams(
            output_dir=str(self.output_dir), template_dir=str(self.template_dir)
        )

        exporter._process_static_pages(
            static_pages, jinja_env, params, self.output_dir, md
        )

        # Check output
        external_file = self.output_dir / "external.html"
        self.assertTrue(external_file.exists())
        content = external_file.read_text()
        self.assertIn("<h1>External Content</h1>", content)

    @patch("niamoto.core.plugins.registry.PluginRegistry")
    def test_process_groups_basic(self, mock_registry_class):
        """Test basic group processing."""
        # Mock registry
        mock_registry_instance = Mock()
        mock_registry_class.return_value = mock_registry_instance

        # Mock database responses
        self.mock_db.has_table.return_value = True
        self.mock_db.get_table_columns.return_value = ["taxon_id", "name"]

        # Use a callable that returns the appropriate data based on the query
        def fetch_all_side_effect(query, *args, **kwargs):
            if "taxon_ref" in query:
                # Navigation data
                return [{"taxon_id": 1, "name": "Species 1", "rank": "species"}]
            else:
                # Index data
                return [
                    {"taxon_id": 1, "name": "Species 1"},
                    {"taxon_id": 2, "name": "Species 2"},
                ]

        self.mock_db.fetch_all.side_effect = fetch_all_side_effect
        self.mock_db.fetch_one.side_effect = [
            {"taxon_id": 1, "name": "Species 1", "data": '{"test": "value"}'},
            {"taxon_id": 2, "name": "Species 2", "data": '{"test": "value2"}'},
        ]

        exporter = HtmlPageExporter(self.mock_db)

        groups = [
            GroupConfigWeb(
                group_by="taxon",
                data_source="db",
                template="group_detail.html",
                output_pattern="{group_by}/{id}.html",
                index_output_pattern="{group_by}/index.html",
                widgets=[],
            )
        ]

        from jinja2 import Environment, FileSystemLoader

        jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        params = HtmlExporterParams(
            output_dir=str(self.output_dir), template_dir=str(self.template_dir)
        )

        exporter._process_groups(
            groups, jinja_env, params, self.output_dir, self.mock_db
        )

        # Check index file
        index_file = self.output_dir / "taxon" / "index.html"
        self.assertTrue(index_file.exists())

        # Check detail files
        detail1 = self.output_dir / "taxon" / "1.html"
        detail2 = self.output_dir / "taxon" / "2.html"
        self.assertTrue(detail1.exists())
        self.assertTrue(detail2.exists())

    def test_process_groups_with_widgets(self):
        """Test group processing with widgets."""
        from niamoto.core.plugins.registry import PluginRegistry
        from niamoto.core.plugins.base import PluginType

        # Create a real widget class that implements the required interface
        class MockTestWidget:
            type = PluginType.WIDGET

            def __init__(self, db=None):
                self.db = db

            def get_dependencies(self):
                return ["chart.js"]

            def render(self, data, config):
                return "<div>Widget rendered with data: [{'x': 1, 'y': 2}]</div>"

            def get_container_html(self, widget_id, content, config):
                return f"<div id=\"{widget_id}\" class=\"widget\"><div>Widget rendered with data: [{{'x': 1, 'y': 2}}]</div></div>"

        # Register the mock widget
        PluginRegistry.register_plugin("test_widget", MockTestWidget, PluginType.WIDGET)

        # Mock database
        self.mock_db.has_table.return_value = True
        self.mock_db.get_table_columns.return_value = ["taxon_id", "name", "chart_data"]

        # Use a callable for consistent behavior
        def fetch_all_side_effect(query, *args, **kwargs):
            if "taxon_ref" in query:
                return []  # No navigation data
            else:
                return [{"taxon_id": 1, "name": "Species 1"}]

        self.mock_db.fetch_all.side_effect = fetch_all_side_effect
        self.mock_db.fetch_one.return_value = {
            "taxon_id": 1,
            "name": "Species 1",
            "chart_data": '[{"x": 1, "y": 2}]',
        }

        exporter = HtmlPageExporter(self.mock_db)

        groups = [
            GroupConfigWeb(
                group_by="taxon",
                data_source="db",
                template="_layouts/group_detail_with_sidebar.html",
                output_pattern="{group_by}/{id}.html",
                index_output_pattern="{group_by}/index.html",
                widgets=[
                    WidgetConfig(
                        plugin="test_widget", data_source="chart_data", params={}
                    )
                ],
            )
        ]

        from jinja2 import Environment, FileSystemLoader

        jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        params = HtmlExporterParams(
            output_dir=str(self.output_dir), template_dir=str(self.template_dir)
        )

        exporter._process_groups(
            groups, jinja_env, params, self.output_dir, self.mock_db
        )

        # Check widget was rendered
        detail_file = self.output_dir / "taxon" / "1.html"
        self.assertTrue(detail_file.exists())

        # Read the content and verify the widget was rendered
        content = detail_file.read_text()
        self.assertIn("Widget rendered with data:", content)

    def test_resolve_registry_entity_uses_instance_cache(self):
        """Registry lookups should be memoized during one exporter run."""
        mock_registry = Mock()
        mock_registry.get.return_value = Mock(
            table_name="entity_taxons",
            config={"schema": {"id_field": "taxon_id"}},
        )
        self.mock_db.has_table.return_value = True

        exporter = HtmlPageExporter(self.mock_db, registry=mock_registry)

        first = exporter._resolve_registry_entity("taxons")
        second = exporter._resolve_registry_entity("taxons")

        self.assertEqual(first, second)
        mock_registry.get.assert_called_once_with("taxons")

    def test_process_groups_with_filter(self):
        """Test group processing with filter."""
        exporter = HtmlPageExporter(self.mock_db)

        # Mock database
        self.mock_db.has_table.return_value = True
        self.mock_db.get_table_columns.return_value = ["plot_id", "name"]

        def fetch_all_side_effect(query, *args, **kwargs):
            if "plot_ref" in query or "taxon_ref" in query:
                return []  # Navigation data
            elif "plot" in query:
                return [{"plot_id": 1, "name": "Plot 1"}]
            else:
                return []

        self.mock_db.fetch_all.side_effect = fetch_all_side_effect
        self.mock_db.fetch_one.return_value = {"plot_id": 1, "name": "Plot 1"}

        groups = [
            GroupConfigWeb(
                group_by="taxon",
                data_source="db",
                template="_layouts/group_detail_with_sidebar.html",
                output_pattern="{group_by}/{id}.html",
                index_output_pattern="{group_by}/index.html",
                widgets=[],
            ),
            GroupConfigWeb(
                group_by="plot",
                data_source="db",
                template="_layouts/group_detail_with_sidebar.html",
                output_pattern="{group_by}/{id}.html",
                index_output_pattern="{group_by}/index.html",
                widgets=[],
            ),
        ]

        from jinja2 import Environment, FileSystemLoader

        jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        params = HtmlExporterParams(
            output_dir=str(self.output_dir), template_dir=str(self.template_dir)
        )

        # Process with filter for "plot" only
        exporter._process_groups(
            groups,
            jinja_env,
            params,
            self.output_dir,
            self.mock_db,
            group_filter="plot",
        )

        # Check only plot files were created
        self.assertTrue((self.output_dir / "plot" / "index.html").exists())
        self.assertFalse((self.output_dir / "taxon").exists())

    def test_get_group_index_data(self):
        """Test _get_group_index_data method."""
        # Test successful fetch
        exporter = HtmlPageExporter(self.mock_db)
        self.mock_db.get_table_columns.return_value = ["taxon_id", "name", "rank"]
        self.mock_db.fetch_all.return_value = [
            {"taxon_id": 1, "name": "Species A"},
            {"taxon_id": 2, "name": "Species B"},
        ]

        result = exporter._get_group_index_data(self.mock_db, "taxon", "taxon_id")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Species A")

        # Test missing table columns
        exporter = HtmlPageExporter(self.mock_db)
        self.mock_db.get_table_columns.return_value = None
        result = exporter._get_group_index_data(self.mock_db, "invalid_table", "id")
        self.assertIsNone(result)

        # Test missing id column
        exporter = HtmlPageExporter(self.mock_db)
        self.mock_db.get_table_columns.return_value = ["name", "rank"]
        result = exporter._get_group_index_data(self.mock_db, "taxon", "taxon_id")
        self.assertIsNone(result)

        # Test database error
        exporter = HtmlPageExporter(self.mock_db)
        self.mock_db.get_table_columns.return_value = ["taxon_id", "name"]
        self.mock_db.fetch_all.side_effect = Exception("DB Error")
        result = exporter._get_group_index_data(self.mock_db, "taxon", "taxon_id")
        self.assertIsNone(result)

    def test_get_item_detail_data(self):
        """Test _get_item_detail_data method."""
        exporter = HtmlPageExporter(self.mock_db)

        # Test successful fetch
        self.mock_db.fetch_one.return_value = {
            "taxon_id": 1,
            "name": "Species A",
            "data": '{"key": "value"}',
        }

        result = exporter._get_item_detail_data(self.mock_db, "taxon", "taxon_id", 1)
        self.assertEqual(result["taxon_id"], 1)
        self.assertEqual(result["name"], "Species A")

        # Test not found
        self.mock_db.fetch_one.return_value = None
        result = exporter._get_item_detail_data(self.mock_db, "taxon", "taxon_id", 999)
        self.assertIsNone(result)

        # Test database error
        self.mock_db.fetch_one.side_effect = Exception("DB Error")
        result = exporter._get_item_detail_data(self.mock_db, "taxon", "taxon_id", 1)
        self.assertIsNone(result)

    def test_generate_navigation_js(self):
        """Test _generate_navigation_js method."""
        exporter = HtmlPageExporter(self.mock_db)

        # Mock navigation data
        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = [
            {"taxon_id": 1, "name": "Root", "parent_id": None},
            {"taxon_id": 2, "name": "Child", "parent_id": 1},
        ]

        group_config = GroupConfigWeb(
            group_by="taxon",
            navigation_entity="taxonomy",
            data_source="db",
            template="_layouts/group_detail.html",
            output_pattern="{group_by}/{id}.html",
            index_output_pattern="{group_by}/index.html",
            widgets=[],
        )

        exporter._generate_navigation_js(group_config, self.output_dir)

        self.mock_db.get_table_columns.assert_called_with("entity_taxonomy")

        # Check JS file was created
        js_file = self.output_dir / "assets" / "js" / "taxon_navigation.js"
        self.assertTrue(js_file.exists())

        # Check content
        content = js_file.read_text()
        self.assertIn("const taxonNavigationData =", content)
        self.assertIn('"taxon_id":1', content)

        # Test caching - should not regenerate
        self.mock_db.fetch_all.reset_mock()
        exporter._generate_navigation_js(group_config, self.output_dir)
        self.mock_db.fetch_all.assert_not_called()

    def test_generate_navigation_js_reuses_cached_payload_across_outputs(self):
        """Navigation payload and table metadata should be cached across outputs."""
        exporter = HtmlPageExporter(self.mock_db)

        self.mock_db.has_table.return_value = True
        self.mock_db.fetch_all.return_value = [
            {"taxon_id": 1, "name": "Root", "parent_id": None},
            {"taxon_id": 2, "name": "Child", "parent_id": 1},
        ]

        group_config = GroupConfigWeb(
            group_by="taxon",
            navigation_entity="taxonomy",
            data_source="db",
            template="_layouts/group_detail.html",
            output_pattern="{group_by}/{id}.html",
            index_output_pattern="{group_by}/index.html",
            widgets=[],
        )

        second_output_dir = Path(self.test_dir) / "output-second"

        exporter._generate_navigation_js(group_config, self.output_dir)
        exporter._navigation_js_generated.clear()
        self.mock_db.fetch_all.reset_mock()
        self.mock_db.get_table_columns.reset_mock()

        exporter._generate_navigation_js(group_config, second_output_dir)

        self.mock_db.fetch_all.assert_not_called()
        self.mock_db.get_table_columns.assert_not_called()
        js_file = second_output_dir / "assets" / "js" / "taxon_navigation.js"
        self.assertTrue(js_file.exists())

    def test_export_validation_error(self):
        """Test export with validation error."""
        exporter = HtmlPageExporter(self.mock_db)

        # Invalid params
        self.target_config.params = {"invalid": "params"}

        with self.assertRaises(ConfigurationError) as context:
            exporter.export(self.target_config, self.mock_db)

        self.assertIn("Invalid params", str(context.exception))

    def test_export_process_error(self):
        """Test export with process error."""
        exporter = HtmlPageExporter(self.mock_db)

        # Make output dir a file to cause error
        self.output_dir.parent.mkdir(parents=True, exist_ok=True)
        self.output_dir.write_text("not a directory")

        with self.assertRaises(ProcessError):
            exporter.export(self.target_config, self.mock_db)

    def test_relative_url_filter(self):
        """Test the relative_url Jinja filter."""
        exporter = HtmlPageExporter(self.mock_db)

        # Create a test template using the filter
        test_template = """
<a href="{{ '/about.html' | relative_url(0) }}">Root level</a>
<a href="{{ '/about.html' | relative_url(1) }}">One level deep</a>
<a href="{{ '/about.html' | relative_url(2) }}">Two levels deep</a>
<a href="{{ 'https://example.com' | relative_url(1) }}">Absolute URL</a>
<a href="{{ '#section' | relative_url(1) }}">Anchor</a>
"""
        (self.template_dir / "test_filter.html").write_text(test_template)

        self.target_config.static_pages = [
            StaticPageConfig(
                name="test", output_file="test.html", template="test_filter.html"
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        # Check output
        test_file = self.output_dir / "test.html"
        content = test_file.read_text()
        self.assertIn('href="about.html"', content)  # Root level
        self.assertIn('href="../about.html"', content)  # One level deep
        self.assertIn('href="../../about.html"', content)  # Two levels deep
        self.assertIn('href="https://example.com"', content)  # Absolute URL unchanged
        self.assertIn('href="#section"', content)  # Anchor unchanged

    def test_group_index_uses_index_output_depth_for_assets(self):
        """Group index pages must resolve assets from index_output_pattern depth."""
        exporter = HtmlPageExporter(self.mock_db)

        group_index_template = """
{% extends "_base.html" %}
{% block content %}
<link rel="stylesheet" href="{{ '/assets/css/niamoto.css' | relative_url(depth|default(0)) }}">
<img src="{{ site.logo_header | relative_url(depth|default(0)) }}" alt="Logo">
{% endblock %}
"""
        (self.template_dir / "_group_index.html").write_text(group_index_template)

        self.mock_db.fetch_all.return_value = [
            {"plots_id": 1, "name": "Plot 1"},
            {"plots_id": 2, "name": "Plot 2"},
        ]
        self.mock_db.get_table_columns.return_value = ["plots_id", "name"]

        self.target_config.params = {
            "output_dir": str(self.output_dir),
            "template_dir": str(self.template_dir),
            "include_default_assets": False,
            "site": {
                "title": "Test Site",
                "logo_header": "files/niamoto_logo.png",
                "languages": ["fr", "en"],
            },
        }
        self.target_config.groups = [
            GroupConfigWeb(
                group_by="plots",
                data_source="db",
                template="_group_detail.html",
                output_pattern="plots/{id}.html",
                index_output_pattern="plots/index.html",
                widgets=[],
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        index_file = self.output_dir / "fr" / "plots" / "index.html"
        self.assertTrue(index_file.exists())
        content = index_file.read_text()
        self.assertIn('href="../../assets/css/niamoto.css"', content)
        self.assertIn('src="../../assets/files/niamoto_logo.png"', content)

    def test_group_index_uses_real_output_path_when_pattern_is_local_index(self):
        """Group index depth must be computed from the actual output path."""
        exporter = HtmlPageExporter(self.mock_db)

        group_index_template = """
{% extends "_base.html" %}
{% block content %}
<link rel="stylesheet" href="{{ '/assets/css/niamoto.css' | relative_url(depth|default(0)) }}">
<img src="{{ site.logo_header | relative_url(depth|default(0)) }}" alt="Logo">
{% endblock %}
"""
        (self.template_dir / "_group_index.html").write_text(group_index_template)

        self.mock_db.fetch_all.return_value = [{"plots_id": 1, "name": "Plot 1"}]
        self.mock_db.get_table_columns.return_value = ["plots_id", "name"]

        self.target_config.params = {
            "output_dir": str(self.output_dir),
            "template_dir": str(self.template_dir),
            "include_default_assets": False,
            "site": {
                "title": "Test Site",
                "logo_header": "files/niamoto_logo.png",
                "languages": ["fr", "en"],
            },
        }
        self.target_config.groups = [
            GroupConfigWeb(
                group_by="plots",
                data_source="db",
                template="_group_detail.html",
                output_pattern="{id}.html",
                index_output_pattern="index.html",
                widgets=[],
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        index_file = self.output_dir / "fr" / "plots" / "index.html"
        self.assertTrue(index_file.exists())
        content = index_file.read_text()
        self.assertIn('href="../../assets/css/niamoto.css"', content)
        self.assertIn('src="../../assets/files/niamoto_logo.png"', content)

    def test_index_generator_uses_export_root_depth_for_multilang_assets(self):
        """Index generator pages must resolve shared assets from the export root."""
        exporter = HtmlPageExporter(self.mock_db)

        group_index_template = """
{% extends "_base.html" %}
{% block content %}
<link rel="stylesheet" href="{{ '/assets/css/niamoto.css' | relative_url(depth|default(0)) }}">
<img src="{{ site.logo_header | relative_url(depth|default(0)) }}" alt="Logo">
{% endblock %}
"""
        (self.template_dir / "_group_index.html").write_text(group_index_template)

        self.mock_db.fetch_all.return_value = [{"plots_id": 1, "name": "Plot 1"}]
        self.mock_db.get_table_columns.return_value = ["plots_id", "name"]
        self.mock_db.has_table.return_value = True

        self.target_config.params = {
            "output_dir": str(self.output_dir),
            "template_dir": str(self.template_dir),
            "include_default_assets": False,
            "site": {
                "title": "Test Site",
                "logo_header": "files/niamoto_logo.png",
                "languages": ["fr", "en"],
            },
        }
        self.target_config.groups = [
            GroupConfigWeb(
                group_by="plots",
                data_source="db",
                template="_group_detail.html",
                output_pattern="plots/{id}.html",
                index_output_pattern="plots/index.html",
                index_generator=IndexGeneratorConfig(
                    enabled=True,
                    template="group_index.html",
                    page_config=IndexGeneratorPageConfig(title="Plots"),
                    display_fields=[
                        IndexGeneratorDisplayField(
                            name="name",
                            source="name",
                            type="text",
                            label="Name",
                        )
                    ],
                    views=[],
                ),
                widgets=[],
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        index_file = self.output_dir / "fr" / "plots" / "index.html"
        self.assertTrue(index_file.exists())
        content = index_file.read_text()
        self.assertIn('href="../../assets/css/niamoto.css"', content)
        self.assertIn('src="../../assets/files/niamoto_logo.png"', content)

    def test_index_generator_resolves_localized_navigation_strings(self):
        """Index generator pages must receive localized site and navigation labels."""
        exporter = HtmlPageExporter(self.mock_db)

        localized_base_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ site.title }}</title>
</head>
<body>
    <nav>{{ navigation[0].text }}</nav>
    {% block content %}{% endblock %}
</body>
</html>
"""
        (self.template_dir / "_base.html").write_text(localized_base_template)

        group_index_template = """
{% extends "_base.html" %}
{% block content %}
<div>Index</div>
{% endblock %}
"""
        (self.template_dir / "_group_index.html").write_text(group_index_template)

        self.mock_db.fetch_all.return_value = [{"taxons_id": 1, "name": "Taxon 1"}]
        self.mock_db.get_table_columns.return_value = ["taxons_id", "name"]
        self.mock_db.has_table.return_value = True

        self.target_config.params = {
            "output_dir": str(self.output_dir),
            "template_dir": str(self.template_dir),
            "include_default_assets": False,
            "site": {
                "title": {"fr": "Niamoto FR", "en": "Niamoto EN"},
                "logo_header": "files/niamoto_logo.png",
                "languages": ["fr", "en"],
            },
            "navigation": [
                {"text": {"fr": "Accueil", "en": "Home"}, "url": "/index.html"}
            ],
        }
        self.target_config.groups = [
            GroupConfigWeb(
                group_by="taxons",
                data_source="db",
                template="_group_detail.html",
                output_pattern="taxons/{id}.html",
                index_output_pattern="taxons/index.html",
                index_generator=IndexGeneratorConfig(
                    enabled=True,
                    template="group_index.html",
                    page_config=IndexGeneratorPageConfig(title="Taxons"),
                    display_fields=[
                        IndexGeneratorDisplayField(
                            name="name",
                            source="name",
                            type="text",
                            label="Name",
                        )
                    ],
                    views=[],
                ),
                widgets=[],
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        index_file = self.output_dir / "fr" / "taxons" / "index.html"
        content = index_file.read_text()
        self.assertIn("Accueil", content)
        self.assertNotIn("{'fr': 'Accueil', 'en': 'Home'}", content)
        self.assertIn("Niamoto FR", content)
        self.assertNotIn("{'fr': 'Niamoto FR', 'en': 'Niamoto EN'}", content)

    @patch("niamoto.core.plugins.exporters.html_page_exporter.Config.get_niamoto_home")
    def test_project_files_are_copied_even_without_user_assets(self, mock_home):
        """Project files must still be copied when copy_assets_from is empty."""
        exporter = HtmlPageExporter(self.mock_db)

        project_home = Path(self.test_dir) / "project-home"
        files_dir = project_home / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        (files_dir / "niamoto_logo.png").write_bytes(b"fake-image")
        mock_home.return_value = str(project_home)

        params = HtmlExporterParams(
            output_dir=str(self.output_dir),
            template_dir=str(self.template_dir),
            include_default_assets=False,
            copy_assets_from=[],
        )

        exporter._copy_static_assets(params, self.output_dir)

        copied_file = self.output_dir / "assets" / "files" / "niamoto_logo.png"
        self.assertTrue(copied_file.exists())
        self.assertEqual(copied_file.read_bytes(), b"fake-image")

    def test_language_redirect_targets_index_html(self):
        """Root redirect page should work when opened via file://."""
        exporter = HtmlPageExporter(self.mock_db)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        exporter._generate_language_redirect(self.output_dir, "fr", ["fr", "en"])

        content = (self.output_dir / "index.html").read_text()
        self.assertIn('content="0; url=fr/index.html"', content)
        self.assertIn("window.location.href = shortLang + '/index.html';", content)
        self.assertIn("window.location.href = 'fr/index.html';", content)
        self.assertIn('href="fr/index.html"', content)

    def test_bibliography_page_embeds_bibtex_download_payload(self):
        """Bibliography pages should download BibTeX without relying on file:// download."""
        exporter = HtmlPageExporter(self.mock_db)
        self.target_config.params = {
            "output_dir": str(self.output_dir),
            "template_dir": "src/niamoto/publish/templates",
            "include_default_assets": False,
            "site": {"title": "Test Site", "lang": "fr"},
        }
        self.target_config.static_pages = [
            StaticPageConfig(
                name="bibliography",
                template="bibliography.html",
                output_file="references.html",
                context=StaticPageContext(
                    title="Références",
                    references=[
                        {
                            "authors": "Doe, J.",
                            "year": "2024",
                            "title": "Example Reference",
                            "journal": "Niamoto Journal",
                            "type": "article",
                        }
                    ],
                ),
            )
        ]

        exporter.export(self.target_config, self.mock_db)

        html = (self.output_dir / "references.html").read_text(encoding="utf-8")
        bib = (self.output_dir / "references.bib").read_text(encoding="utf-8")

        self.assertIn('id="download-bibtex"', html)
        self.assertIn("const bibliographyBibtex =", html)
        self.assertIn("link.download = 'references.bib';", html)
        self.assertIn("@article", bib)
        self.assertIn("Example Reference", bib)

    @patch("niamoto.core.plugins.exporters.html_page_exporter.Config.get_niamoto_home")
    def test_export_paths_resolve_against_project_root(self, mock_home):
        """Relative output_dir and template_dir must resolve against NIAMOTO_HOME."""
        project_home = Path(self.test_dir) / "project-home"
        project_home.mkdir(parents=True, exist_ok=True)
        output_dir = project_home / "exports" / "web"
        template_dir = project_home / "templates"
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "_base.html").write_text(
            "<html><body>{% block content %}{% endblock %}</body></html>"
        )
        (template_dir / "_layouts").mkdir(exist_ok=True)
        (template_dir / "_layouts" / "static_page.html").write_text(
            '{% extends "_base.html" %}{% block content %}<h1>{{ page.title }}</h1>{% endblock %}'
        )

        mock_home.return_value = str(project_home)

        exporter = HtmlPageExporter(self.mock_db)
        target_config = TargetConfig(
            name="test_export",
            enabled=True,
            exporter="html_page_exporter",
            params={
                "output_dir": "exports/web",
                "template_dir": "templates",
                "include_default_assets": False,
                "site": {"title": "Test Site", "lang": "fr"},
            },
            static_pages=[
                StaticPageConfig(
                    name="home",
                    output_file="index.html",
                    template="_layouts/static_page.html",
                    context=StaticPageContext(title="Home"),
                )
            ],
            groups=[],
        )

        exporter.export(target_config, self.mock_db)

        self.assertTrue((output_dir / "index.html").exists())

    def test_hierarchical_nav_widget_special_handling(self):
        """Test special handling for hierarchical navigation widget."""
        from niamoto.core.plugins.registry import PluginRegistry
        from niamoto.core.plugins.base import PluginType

        # Create a widget class for hierarchical navigation
        class MockHierarchicalNavWidget:
            type = PluginType.WIDGET

            def __init__(self, db=None):
                self.db = db

            def get_dependencies(self):
                return []

            def render(self, data, config):
                return "<div>Nav widget</div>"

            def get_container_html(self, widget_id, content, config):
                return f'<div id="{widget_id}">Nav widget</div>'

        # Register the hierarchical nav widget
        PluginRegistry.register_plugin(
            "hierarchical_nav_widget", MockHierarchicalNavWidget, PluginType.WIDGET
        )

        # Mock database
        self.mock_db.has_table.return_value = True
        self.mock_db.get_table_columns.return_value = ["taxon_id", "name"]

        def fetch_all_side_effect(query, *args, **kwargs):
            if "taxon_ref" in query:
                return []  # No navigation data
            else:
                return [{"taxon_id": 1, "name": "Species 1"}]

        self.mock_db.fetch_all.side_effect = fetch_all_side_effect
        self.mock_db.fetch_one.return_value = {"taxon_id": 1, "name": "Species 1"}

        exporter = HtmlPageExporter(self.mock_db)

        groups = [
            GroupConfigWeb(
                group_by="taxon",
                data_source="db",
                template="_layouts/group_detail_with_sidebar.html",
                output_pattern="{group_by}/{id}.html",
                index_output_pattern="{group_by}/index.html",
                widgets=[
                    WidgetConfig(
                        plugin="hierarchical_nav_widget",
                        data_source="nav_data",
                        params={},
                    )
                ],
            )
        ]

        from jinja2 import Environment, FileSystemLoader

        jinja_env = Environment(loader=FileSystemLoader(str(self.template_dir)))

        params = HtmlExporterParams(
            output_dir=str(self.output_dir), template_dir=str(self.template_dir)
        )

        exporter._process_groups(
            groups, jinja_env, params, self.output_dir, self.mock_db
        )

        # Verify the widget was rendered
        detail_file = self.output_dir / "taxon" / "1.html"
        self.assertTrue(detail_file.exists())

        # Read the content and verify the nav widget was rendered
        content = detail_file.read_text()
        self.assertIn("Nav widget", content)

    def test_export_with_group_filter_no_clear(self):
        """Test that export with group filter doesn't clear entire output directory."""
        exporter = HtmlPageExporter(self.mock_db)

        # Create existing files
        self.output_dir.mkdir(parents=True, exist_ok=True)
        existing_file = self.output_dir / "existing.html"
        existing_file.write_text("Should not be deleted")

        # Mock database
        self.mock_db.has_table.return_value = True
        self.mock_db.get_table_columns.return_value = ["plot_id", "name"]
        self.mock_db.fetch_all.return_value = []

        # Export with group filter
        exporter.export(self.target_config, self.mock_db, group_filter="plot")

        # Check existing file was not deleted
        self.assertTrue(existing_file.exists())
        self.assertEqual(existing_file.read_text(), "Should not be deleted")

    def test_validate_template_availability(self):
        """Test template availability validation."""
        exporter = HtmlPageExporter(self.mock_db)

        # Mock Jinja environment
        mock_jinja_env = Mock()

        # Test successful template loading
        mock_jinja_env.get_template.return_value = Mock()
        result = exporter._validate_template_availability(
            mock_jinja_env, "test_template.html"
        )
        self.assertTrue(result)

        # Test template not found
        mock_jinja_env.get_template.side_effect = Exception("Template not found")
        result = exporter._validate_template_availability(
            mock_jinja_env, "missing_template.html"
        )
        self.assertFalse(result)


if __name__ == "__main__":
    import unittest

    unittest.main()
