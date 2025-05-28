"""Tests for the ExporterService class."""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from niamoto.common.config import Config
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.core.services.exporter import ExporterService
from niamoto.core.plugins.base import ExporterPlugin
from tests.common.base_test import NiamotoTestCase


class MockExporterPlugin(ExporterPlugin):
    """Mock exporter plugin for testing."""

    def export(self, target_config, repository, group_filter=None):
        """Mock export method."""
        pass


class TestExporterService(NiamotoTestCase):
    """Test cases for ExporterService."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")

        # Create mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.plugins_dir = os.path.join(self.test_dir, "plugins")

        # Default valid export config
        self.valid_export_config = {
            "exports": [
                {
                    "name": "test_export",
                    "enabled": True,
                    "exporter": "mock_exporter",
                    "params": {"output_dir": "/tmp/export"},
                    "groups": [],
                }
            ]
        }

    def tearDown(self):
        """Tear down test fixtures."""
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        super().tearDown()

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_init_valid_config(self, mock_registry, mock_loader, mock_db):
        """Test initialization with valid configuration."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        service = ExporterService(self.db_path, self.mock_config)

        # Verify initialization
        mock_db.assert_called_once_with(self.db_path)
        mock_loader.return_value.load_core_plugins.assert_called_once()
        mock_loader.return_value.load_project_plugins.assert_called_once_with(
            self.mock_config.plugins_dir
        )
        self.assertIsNotNone(service.validated_config)
        self.assertEqual(len(service.validated_config.exports), 1)

    @patch("niamoto.core.services.exporter.Database")
    def test_init_invalid_config_structure(self, mock_db):
        """Test initialization with invalid configuration structure."""
        # Missing required 'exports' key
        self.mock_config.get_exports_config.return_value = {}

        with self.assertRaises(ConfigurationError) as context:
            ExporterService(self.db_path, self.mock_config)

        self.assertIn("Invalid configuration", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    def test_init_config_exception(self, mock_db):
        """Test initialization when config raises exception."""
        self.mock_config.get_exports_config.side_effect = Exception("Config error")

        with self.assertRaises(ProcessError) as context:
            ExporterService(self.db_path, self.mock_config)

        self.assertIn("Failed to validate export configuration", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_no_targets(self, mock_registry, mock_loader, mock_db):
        """Test run_export with no export targets."""
        self.mock_config.get_exports_config.return_value = {"exports": []}

        service = ExporterService(self.db_path, self.mock_config)

        # Should not raise, just log warning
        service.run_export()

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_target_not_found(self, mock_registry, mock_loader, mock_db):
        """Test run_export with non-existent target name."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        service = ExporterService(self.db_path, self.mock_config)

        with self.assertRaises(ConfigurationError) as context:
            service.run_export(target_name="non_existent")

        self.assertIn("Target 'non_existent' not found", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_disabled_target(self, mock_registry, mock_loader, mock_db):
        """Test run_export skips disabled targets."""
        self.valid_export_config["exports"][0]["enabled"] = False
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        service = ExporterService(self.db_path, self.mock_config)

        # Should not raise, just skip disabled target
        service.run_export()

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_plugin_not_found(self, mock_registry, mock_loader, mock_db):
        """Test run_export when exporter plugin is not found."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock registry returns None for plugin
        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = None
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)

        with self.assertRaises(ConfigurationError) as context:
            service.run_export()

        self.assertIn(
            "Exporter plugin 'mock_exporter' not found", str(context.exception)
        )

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_plugin_instantiation_error(
        self, mock_registry, mock_loader, mock_db
    ):
        """Test run_export when plugin instantiation fails."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock registry returns plugin class that fails on instantiation
        mock_plugin_class = Mock(side_effect=Exception("Init error"))
        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)

        with self.assertRaises(ProcessError) as context:
            service.run_export()

        self.assertIn("Plugin instantiation failed", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_plugin_execution_error(
        self, mock_registry, mock_loader, mock_db
    ):
        """Test run_export when plugin execution fails."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock plugin that fails during export
        mock_plugin_instance = Mock(spec=MockExporterPlugin)
        mock_plugin_instance.export.side_effect = Exception("Export error")
        mock_plugin_class = Mock(return_value=mock_plugin_instance)

        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)

        with self.assertRaises(ProcessError) as context:
            service.run_export()

        self.assertIn("Export failed for target 'test_export'", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_success(self, mock_registry, mock_loader, mock_db):
        """Test successful export execution."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock successful plugin execution
        mock_plugin_instance = Mock(spec=MockExporterPlugin)
        mock_plugin_class = Mock(return_value=mock_plugin_instance)

        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)
        service.run_export()

        # Verify plugin was called correctly
        mock_plugin_instance.export.assert_called_once()
        call_args = mock_plugin_instance.export.call_args
        self.assertEqual(call_args.kwargs["target_config"].name, "test_export")
        self.assertIsNone(call_args.kwargs["group_filter"])

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_with_target_name(self, mock_registry, mock_loader, mock_db):
        """Test export with specific target name."""
        # Add multiple targets
        self.valid_export_config["exports"].append(
            {
                "name": "second_export",
                "enabled": True,
                "exporter": "mock_exporter2",
                "params": {},
                "groups": [],
            }
        )
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock successful plugin execution
        mock_plugin_instance = Mock(spec=MockExporterPlugin)
        mock_plugin_class = Mock(return_value=mock_plugin_instance)

        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)
        service.run_export(target_name="second_export")

        # Verify only the specified target was processed
        mock_plugin_instance.export.assert_called_once()
        call_args = mock_plugin_instance.export.call_args
        self.assertEqual(call_args.kwargs["target_config"].name, "second_export")

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_with_group_filter(self, mock_registry, mock_loader, mock_db):
        """Test export with group filter."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock successful plugin execution
        mock_plugin_instance = Mock(spec=MockExporterPlugin)
        mock_plugin_class = Mock(return_value=mock_plugin_instance)

        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)
        service.run_export(group_filter="test_group")

        # Verify group_filter was passed to plugin
        mock_plugin_instance.export.assert_called_once()
        call_args = mock_plugin_instance.export.call_args
        self.assertEqual(call_args.kwargs["group_filter"], "test_group")

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_multiple_targets(self, mock_registry, mock_loader, mock_db):
        """Test export with multiple enabled targets."""
        # Add multiple enabled targets
        self.valid_export_config["exports"].extend(
            [
                {
                    "name": "second_export",
                    "enabled": True,
                    "exporter": "mock_exporter",
                    "params": {},
                    "groups": [],
                },
                {
                    "name": "third_export",
                    "enabled": False,  # Disabled
                    "exporter": "mock_exporter",
                    "params": {},
                    "groups": [],
                },
            ]
        )
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock successful plugin execution
        mock_plugin_instance = Mock(spec=MockExporterPlugin)
        mock_plugin_class = Mock(return_value=mock_plugin_instance)

        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)
        service.run_export()

        # Verify only enabled targets were processed (2 out of 3)
        self.assertEqual(mock_plugin_instance.export.call_count, 2)

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_complex_export_config(self, mock_registry, mock_loader, mock_db):
        """Test with complex export configuration including groups and static pages."""
        complex_config = {
            "exports": [
                {
                    "name": "web_export",
                    "enabled": True,
                    "exporter": "html_page_exporter",
                    "params": {"template_dir": "templates", "output_dir": "exports"},
                    "static_pages": [
                        {
                            "name": "index",
                            "output_file": "index.html",
                            "template": "index.html",
                            "data": {"title": "Home"},
                        }
                    ],
                    "groups": [
                        {
                            "group_by": "taxon",
                            "data_source": "db",
                            "template": "taxon_detail.html",
                            "output_pattern": "taxons/{id}.html",
                            "index_output_pattern": "taxons/index.html",
                            "widgets": [],
                        }
                    ],
                }
            ]
        }
        self.mock_config.get_exports_config.return_value = complex_config

        # Create service - should validate complex config successfully
        service = ExporterService(self.db_path, self.mock_config)

        self.assertEqual(len(service.validated_config.exports), 1)
        export_target = service.validated_config.exports[0]
        self.assertEqual(export_target.name, "web_export")
        self.assertEqual(len(export_target.static_pages), 1)
        self.assertEqual(len(export_target.groups), 1)

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_run_export_all_targets_disabled(self, mock_registry, mock_loader, mock_db):
        """Test run_export when all targets are disabled."""
        # Create multiple disabled targets
        self.valid_export_config["exports"] = [
            {
                "name": "disabled1",
                "enabled": False,
                "exporter": "mock_exporter",
                "params": {},
                "groups": [],
            },
            {
                "name": "disabled2",
                "enabled": False,
                "exporter": "mock_exporter",
                "params": {},
                "groups": [],
            },
        ]
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        service = ExporterService(self.db_path, self.mock_config)

        # Should complete without error but log warning about no enabled targets
        service.run_export()

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_invalid_export_config_details(self, mock_registry, mock_loader, mock_db):
        """Test detailed validation errors in export configuration."""
        # Invalid exporter type - missing required fields
        invalid_config = {
            "exports": [
                {
                    "name": "invalid_export",
                    "enabled": True,
                    "exporter": "json_api_exporter",
                    "params": {
                        # Missing required 'output_dir' for json_api_exporter
                    },
                    "groups": [
                        {
                            "group_by": "taxon",
                            # Missing required fields for API group
                        }
                    ],
                }
            ]
        }
        self.mock_config.get_exports_config.return_value = invalid_config

        with self.assertRaises(ConfigurationError) as context:
            ExporterService(self.db_path, self.mock_config)

        self.assertIn("Invalid configuration", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    def test_plugin_loader_error(self, mock_loader, mock_db):
        """Test when plugin loader fails."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Make plugin loader fail
        mock_loader.return_value.load_core_plugins.side_effect = Exception(
            "Plugin load error"
        )

        with self.assertRaises(Exception) as context:
            ExporterService(self.db_path, self.mock_config)

        self.assertIn("Plugin load error", str(context.exception))

    @patch("niamoto.core.services.exporter.Database")
    @patch("niamoto.core.services.exporter.PluginLoader")
    @patch("niamoto.core.services.exporter.PluginRegistry")
    def test_database_passed_to_plugin(self, mock_registry, mock_loader, mock_db):
        """Test that database instance is correctly passed to plugin."""
        self.mock_config.get_exports_config.return_value = self.valid_export_config

        # Mock database instance
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance

        # Mock plugin
        mock_plugin_instance = Mock(spec=MockExporterPlugin)
        mock_plugin_class = Mock(return_value=mock_plugin_instance)

        mock_registry_instance = Mock()
        mock_registry_instance.get_plugin.return_value = mock_plugin_class
        mock_registry.return_value = mock_registry_instance

        service = ExporterService(self.db_path, self.mock_config)
        service.run_export()

        # Verify database was passed to plugin constructor
        mock_plugin_class.assert_called_once_with(db=mock_db_instance)

        # Verify repository parameter in export call is the same db instance
        call_args = mock_plugin_instance.export.call_args
        self.assertEqual(call_args.kwargs["repository"], mock_db_instance)


if __name__ == "__main__":
    unittest.main()
