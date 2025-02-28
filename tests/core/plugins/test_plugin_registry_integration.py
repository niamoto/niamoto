"""
Integration tests for plugin registry and loader.

This module tests the integration between the plugin registry and loader,
ensuring that plugins can be properly loaded, registered, and accessed.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.plugin_loader import PluginLoader


class TestPluginRegistryIntegration(unittest.TestCase):
    """Integration tests for plugin registry and loader."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear registry before each test
        PluginRegistry.clear()
        self.loader = PluginLoader()

        # Create a temporary directory for test plugins
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = Path(self.temp_dir) / "plugins"
        self.plugins_dir.mkdir()

        # Create plugin type directories
        for plugin_type in PluginType:
            (self.plugins_dir / f"{plugin_type.value}s").mkdir()

    def tearDown(self):
        """Clean up after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)

    def create_test_plugin(self, plugin_type, plugin_name, plugin_code):
        """Create a test plugin file."""
        type_dir = self.plugins_dir / f"{plugin_type.value}s"
        plugin_file = type_dir / f"{plugin_name}.py"

        with open(plugin_file, "w") as f:
            f.write(plugin_code)

        return plugin_file

    def test_load_and_register_transformer_plugin(self):
        """Test loading and registering a transformer plugin."""
        # Create a test transformer plugin
        plugin_code = """
from niamoto.core.plugins.base import TransformerPlugin, register
import pandas as pd

@register("test_transformer")
class TestTransformer(TransformerPlugin):
    def validate_config(self, config):
        return config

    def transform(self, data, config):
        return {"result": "transformed"}
"""
        self.create_test_plugin(PluginType.TRANSFORMER, "test_transformer", plugin_code)

        # Mock the _get_module_name method to return a predictable module name
        with patch.object(
            self.loader,
            "_get_module_name",
            return_value="plugins.transformers.test_transformer",
        ):
            # Load project plugins
            self.loader.load_project_plugins(str(self.plugins_dir))

            # Check if plugin was registered
            self.assertTrue(
                PluginRegistry.has_plugin("test_transformer", PluginType.TRANSFORMER),
                "Plugin was not registered",
            )

            # Get the plugin and check its type
            plugin_class = PluginRegistry.get_plugin(
                "test_transformer", PluginType.TRANSFORMER
            )
            self.assertEqual(plugin_class.__name__, "TestTransformer")
            self.assertEqual(plugin_class.type, PluginType.TRANSFORMER)

    def test_load_and_register_multiple_plugins(self):
        """Test loading and registering multiple plugins of different types."""
        # Create a test transformer plugin
        transformer_code = """
from niamoto.core.plugins.base import TransformerPlugin, register
import pandas as pd

@register("test_transformer")
class TestTransformer(TransformerPlugin):
    def validate_config(self, config):
        return config

    def transform(self, data, config):
        return {"result": "transformed"}
"""
        self.create_test_plugin(
            PluginType.TRANSFORMER, "test_transformer", transformer_code
        )

        # Create a test exporter plugin
        exporter_code = """
from niamoto.core.plugins.base import ExporterPlugin, register
import pandas as pd

@register("test_exporter")
class TestExporter(ExporterPlugin):
    def validate_config(self, config):
        return config

    def export(self, data, config):
        return "exported"
"""
        self.create_test_plugin(PluginType.EXPORTER, "test_exporter", exporter_code)

        # Mock the _get_module_name method to return predictable module names
        def mock_get_module_name(file, is_core):
            if "transformer" in str(file):
                return "plugins.transformers.test_transformer"
            elif "exporter" in str(file):
                return "plugins.exporters.test_exporter"
            return "unknown"

        with patch.object(
            self.loader, "_get_module_name", side_effect=mock_get_module_name
        ):
            # Load project plugins
            self.loader.load_project_plugins(str(self.plugins_dir))

            # Check if plugins were registered
            self.assertTrue(
                PluginRegistry.has_plugin("test_transformer", PluginType.TRANSFORMER),
                "Transformer plugin was not registered",
            )
            self.assertTrue(
                PluginRegistry.has_plugin("test_exporter", PluginType.EXPORTER),
                "Exporter plugin was not registered",
            )

            # Get plugin list by type
            transformer_plugins = PluginRegistry.get_plugins_by_type(
                PluginType.TRANSFORMER
            )
            exporter_plugins = PluginRegistry.get_plugins_by_type(PluginType.EXPORTER)

            self.assertIn("test_transformer", transformer_plugins)
            self.assertIn("test_exporter", exporter_plugins)

    def test_reload_plugin(self):
        """Test reloading a plugin."""
        # Create a test transformer plugin
        plugin_code = """
from niamoto.core.plugins.base import TransformerPlugin, register
import pandas as pd

@register("test_transformer")
class TestTransformer(TransformerPlugin):
    def validate_config(self, config):
        return config

    def transform(self, data, config):
        return {"result": "transformed"}
"""
        plugin_file = self.create_test_plugin(
            PluginType.TRANSFORMER, "test_transformer", plugin_code
        )

        # Mock the _get_module_name method to return a predictable module name
        module_name = "plugins.transformers.test_transformer"
        with patch.object(self.loader, "_get_module_name", return_value=module_name):
            # Load project plugins
            self.loader.load_project_plugins(str(self.plugins_dir))

            # Modify the plugin file
            new_plugin_code = """
from niamoto.core.plugins.base import TransformerPlugin, register
import pandas as pd

@register("test_transformer")
class TestTransformer(TransformerPlugin):
    def validate_config(self, config):
        return config

    def transform(self, data, config):
        return {"result": "transformed_v2"}
"""
            with open(plugin_file, "w") as f:
                f.write(new_plugin_code)

            # Mock sys.modules to simulate module already loaded
            mock_module = MagicMock()
            with patch.dict("sys.modules", {module_name: mock_module}):
                # Reload the plugin
                self.loader.reload_plugin(module_name)

                # Check if plugin was reloaded
                self.assertIn(module_name, self.loader.loaded_plugins)

    def test_unload_plugin(self):
        """Test unloading a plugin."""
        # Create a test transformer plugin
        plugin_code = """
from niamoto.core.plugins.base import TransformerPlugin, register
import pandas as pd

@register("test_transformer")
class TestTransformer(TransformerPlugin):
    def validate_config(self, config):
        return config

    def transform(self, data, config):
        return {"result": "transformed"}
"""
        self.create_test_plugin(PluginType.TRANSFORMER, "test_transformer", plugin_code)

        # Mock the _get_module_name method to return a predictable module name
        module_name = "plugins.transformers.test_transformer"
        with patch.object(self.loader, "_get_module_name", return_value=module_name):
            # Load project plugins
            self.loader.load_project_plugins(str(self.plugins_dir))

            # Unload the plugin
            self.loader.unload_plugin(module_name)

            # Check if plugin was unloaded
            self.assertNotIn(module_name, self.loader.loaded_plugins)
            self.assertNotIn(module_name, self.loader.plugin_paths)


if __name__ == "__main__":
    unittest.main()
