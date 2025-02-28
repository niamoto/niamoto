"""
Tests for plugin categories.

This module contains parameterized tests that can be applied to all plugins
of a specific category (transformer, exporter, loader, widget).
"""

import unittest
import importlib
import inspect
import sys
from pathlib import Path
from typing import List, Type, Tuple

from niamoto.core.plugins.base import (
    Plugin,
    PluginType,
    TransformerPlugin,
    ExporterPlugin,
    LoaderPlugin,
    WidgetPlugin,
)
from niamoto.core.plugins.plugin_loader import PluginLoader


def discover_plugins(plugin_type: PluginType) -> List[Tuple[str, Type[Plugin]]]:
    """
    Discover all plugins of a specific type in the core plugins directory.

    Args:
        plugin_type: Type of plugins to discover

    Returns:
        List of tuples containing (module_name, plugin_class)
    """
    plugins = []

    # Get the plugins directory
    plugins_dir = (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "niamoto"
        / "core"
        / "plugins"
    )

    # Get the specific plugin type directory
    type_dir = plugins_dir / f"{plugin_type.value}s"

    if not type_dir.exists():
        return []

    # Add the src directory to path if not already there
    src_dir = str(plugins_dir.parent.parent.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Load the plugin loader to use its functionality
    loader = PluginLoader()

    # Find all Python files in the directory (recursively)
    for file in type_dir.rglob("*.py"):
        if file.name.startswith("_"):
            continue

        # Get module name
        module_name = loader._get_module_name(file, is_core=True)

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Plugin)
                    and obj != Plugin
                    and obj != TransformerPlugin
                    and obj != ExporterPlugin
                    and obj != LoaderPlugin
                    and obj != WidgetPlugin
                    and hasattr(obj, "type")
                    and obj.type == plugin_type
                ):
                    plugins.append((module_name, obj))
        except Exception as e:
            print(f"Error loading module {module_name}: {str(e)}")

    return plugins


class TestTransformerPlugins(unittest.TestCase):
    """Tests that apply to all transformer plugins."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are reused for all tests."""
        cls.plugins = discover_plugins(PluginType.TRANSFORMER)

    def test_all_transformers_have_transform_method(self):
        """Test that all transformer plugins have a transform method."""
        for module_name, plugin_class in self.plugins:
            with self.subTest(f"Testing {module_name}.{plugin_class.__name__}"):
                # Check if transform method is implemented
                self.assertTrue(
                    hasattr(plugin_class, "transform"),
                    f"{plugin_class.__name__} does not implement transform method",
                )

                # Check if transform method has the correct signature
                signature = inspect.signature(plugin_class.transform)
                params = list(signature.parameters.keys())
                self.assertGreaterEqual(
                    len(params),
                    3,
                    f"{plugin_class.__name__}.transform has incorrect signature",
                )
                self.assertEqual(
                    params[0],
                    "self",
                    f"{plugin_class.__name__}.transform has incorrect first parameter",
                )

    def test_all_transformers_have_validate_config(self):
        """Test that all transformer plugins have a validate_config method."""
        for module_name, plugin_class in self.plugins:
            with self.subTest(f"Testing {module_name}.{plugin_class.__name__}"):
                # Check if validate_config method is implemented
                self.assertTrue(
                    hasattr(plugin_class, "validate_config"),
                    f"{plugin_class.__name__} does not implement validate_config method",
                )


class TestExporterPlugins(unittest.TestCase):
    """Tests that apply to all exporter plugins."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are reused for all tests."""
        cls.plugins = discover_plugins(PluginType.EXPORTER)

    def test_all_exporters_have_export_method(self):
        """Test that all exporter plugins have an export method."""
        for module_name, plugin_class in self.plugins:
            with self.subTest(f"Testing {module_name}.{plugin_class.__name__}"):
                # Check if export method is implemented
                self.assertTrue(
                    hasattr(plugin_class, "export"),
                    f"{plugin_class.__name__} does not implement export method",
                )

                # Check if export method has the correct signature
                signature = inspect.signature(plugin_class.export)
                params = list(signature.parameters.keys())
                self.assertGreaterEqual(
                    len(params),
                    3,
                    f"{plugin_class.__name__}.export has incorrect signature",
                )
                self.assertEqual(
                    params[0],
                    "self",
                    f"{plugin_class.__name__}.export has incorrect first parameter",
                )


class TestLoaderPlugins(unittest.TestCase):
    """Tests that apply to all loader plugins."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are reused for all tests."""
        cls.plugins = discover_plugins(PluginType.LOADER)

    def test_all_loaders_have_load_data_method(self):
        """Test that all loader plugins have a load_data method."""
        for module_name, plugin_class in self.plugins:
            with self.subTest(f"Testing {module_name}.{plugin_class.__name__}"):
                # Check if load_data method is implemented
                self.assertTrue(
                    hasattr(plugin_class, "load_data"),
                    f"{plugin_class.__name__} does not implement load_data method",
                )

                # Check if load_data method has the correct signature
                signature = inspect.signature(plugin_class.load_data)
                params = list(signature.parameters.keys())
                self.assertGreaterEqual(
                    len(params),
                    3,
                    f"{plugin_class.__name__}.load_data has incorrect signature",
                )
                self.assertEqual(
                    params[0],
                    "self",
                    f"{plugin_class.__name__}.load_data has incorrect first parameter",
                )


class TestWidgetPlugins(unittest.TestCase):
    """Tests that apply to all widget plugins."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are reused for all tests."""
        cls.plugins = discover_plugins(PluginType.WIDGET)

    def test_all_widgets_have_render_method(self):
        """Test that all widget plugins have a render method."""
        for module_name, plugin_class in self.plugins:
            with self.subTest(f"Testing {module_name}.{plugin_class.__name__}"):
                # Check if render method is implemented
                self.assertTrue(
                    hasattr(plugin_class, "render"),
                    f"{plugin_class.__name__} does not implement render method",
                )

                # Check if render method has the correct signature
                signature = inspect.signature(plugin_class.render)
                params = list(signature.parameters.keys())
                self.assertGreaterEqual(
                    len(params),
                    3,
                    f"{plugin_class.__name__}.render has incorrect signature",
                )
                self.assertEqual(
                    params[0],
                    "self",
                    f"{plugin_class.__name__}.render has incorrect first parameter",
                )


if __name__ == "__main__":
    unittest.main()
