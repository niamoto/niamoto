"""
Tests for plugin discovery and loading.

This module tests the automatic discovery and loading of plugins from the filesystem.
"""

import importlib
import inspect
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from niamoto.core.plugins.base import (
    Plugin,
    PluginType,
    TransformerPlugin,
    ExporterPlugin,
    LoaderPlugin,
    WidgetPlugin,
    DeployerPlugin,
)
from niamoto.core.plugins.registry import PluginRegistry


BASE_PLUGIN_CLASSES = {
    Plugin,
    TransformerPlugin,
    ExporterPlugin,
    LoaderPlugin,
    WidgetPlugin,
    DeployerPlugin,
}


def load_discovered_plugin_class(plugin_info):
    """Load the concrete plugin class described by discovery metadata."""
    module = importlib.import_module(plugin_info["module"])
    plugin_type = PluginType(plugin_info["type"])

    candidates = [
        obj
        for _, obj in inspect.getmembers(module)
        if inspect.isclass(obj)
        and obj not in BASE_PLUGIN_CLASSES
        and issubclass(obj, Plugin)
        and getattr(obj, "type", None) == plugin_type
        and obj.__module__ == module.__name__
    ]

    assert candidates, (
        f"No concrete {plugin_type.value} plugin class found in {plugin_info['module']}"
    )
    assert len(candidates) == 1, (
        f"Expected one concrete plugin class in {plugin_info['module']}, "
        f"found {[candidate.__name__ for candidate in candidates]}"
    )
    return candidates[0]


class TestPluginDiscovery:
    """Tests for plugin discovery functionality."""

    def test_discover_core_plugins(
        self, plugin_loader, clear_registry, core_plugins_path
    ):
        """Test that core plugins can be discovered."""
        # Discover plugins
        discovered = plugin_loader.discover_plugins(core_plugins_path)

        # Verify that plugins were discovered
        assert len(discovered) > 0

        # Verify structure of discovered plugins
        for plugin_info in discovered:
            assert "path" in plugin_info
            assert "module" in plugin_info
            assert "name" in plugin_info
            assert "type" in plugin_info

            # Check that the path exists
            assert os.path.exists(plugin_info["path"])

            # Check that the type is valid
            assert plugin_info["type"] in [t.value for t in PluginType]

    def test_load_discovered_plugins(
        self, plugin_loader, clear_registry, core_plugins_path
    ):
        """Test that discovered plugins can be loaded."""
        # Discover plugins
        discovered = plugin_loader.discover_plugins(core_plugins_path)

        # Load the first few plugins (to avoid loading all of them)
        test_plugins = discovered[:3] if len(discovered) > 3 else discovered

        for plugin_info in test_plugins:
            plugin_class = load_discovered_plugin_class(plugin_info)

            # Verify that the plugin class was loaded
            assert plugin_class is not None

            # Create an instance (with a mock db)
            mock_db = MagicMock()
            plugin_instance = plugin_class(mock_db)

            # Check type-specific methods
            if plugin_info["type"] == PluginType.TRANSFORMER.value:
                assert hasattr(plugin_instance, "validate_config")
                assert hasattr(plugin_instance, "transform")
            elif plugin_info["type"] == PluginType.EXPORTER.value:
                assert hasattr(plugin_instance, "export")
            elif plugin_info["type"] == PluginType.LOADER.value:
                assert hasattr(plugin_instance, "validate_config")
                assert hasattr(plugin_instance, "load_data")
            elif plugin_info["type"] == PluginType.DEPLOYER.value:
                assert hasattr(plugin_instance, "deploy")

    def test_register_discovered_plugins(
        self, plugin_loader, clear_registry, core_plugins_path
    ):
        """Test that discovered plugins can be registered."""
        # Discover plugins
        discovered = plugin_loader.discover_plugins(core_plugins_path)

        # Register the plugins
        for plugin_info in discovered:
            plugin_class = load_discovered_plugin_class(plugin_info)
            PluginRegistry.register_plugin(
                plugin_info["name"], plugin_class, PluginType(plugin_info["type"])
            )

        # Check that plugins were registered
        registry = PluginRegistry.list_plugins()
        assert any(registry.values())

        # Check that plugins can be retrieved by type
        for plugin_type in PluginType:
            PluginRegistry.get_plugins_by_type(plugin_type)
            # Not all types may have plugins, so we don't assert length

    def test_plugin_discovery_with_custom_path(self, plugin_loader, clear_registry):
        """Test plugin discovery with a custom path."""
        with patch(
            "os.path.exists", return_value=True
        ):  # Mock Path.exists at the os level
            with patch("os.walk") as mock_walk:
                # Mock the os.walk function to return a fake directory structure
                mock_walk.return_value = [
                    ("/fake/path", ["dir1"], ["file1.py"]),
                    ("/fake/path/dir1", [], ["plugin1.py", "plugin2.py"]),
                ]

                # Create a fake plugin file path
                fake_file_path = Path("/fake/path/dir1/plugin1.py")

                # Mock all the necessary functions
                with patch("os.path.isfile", return_value=True):
                    with patch.object(Path, "exists", return_value=True):
                        with patch.object(
                            Path,
                            "relative_to",
                            return_value=Path("transformers/plugin1.py"),
                        ):
                            with patch(
                                "importlib.util.spec_from_file_location"
                            ) as mock_spec:
                                # Set up the mock spec
                                mock_spec.return_value = MagicMock()
                                mock_spec.return_value.loader = MagicMock()

                                # Mock module_from_spec
                                with patch(
                                    "importlib.util.module_from_spec"
                                ) as mock_module_from_spec:
                                    # Set up the mock module
                                    mock_module = MagicMock()
                                    mock_module.__name__ = "fake_module"
                                    mock_module_from_spec.return_value = mock_module

                                    # Mock the plugin class
                                    class FakePlugin:
                                        type = PluginType.TRANSFORMER

                                    FakePlugin.__module__ = "fake_module"

                                    # Mock inspect.getmembers to return our fake plugin
                                    with patch(
                                        "inspect.getmembers",
                                        return_value=[("FakePlugin", FakePlugin)],
                                    ):
                                        # Mock is_plugin_class
                                        with patch(
                                            "niamoto.core.plugins.plugin_loader.is_plugin_class",
                                            return_value=True,
                                        ):
                                            # Mock _get_module_name
                                            with patch.object(
                                                plugin_loader,
                                                "_get_module_name",
                                                return_value="fake_module",
                                            ):
                                                with patch(
                                                    "importlib.import_module",
                                                    return_value=mock_module,
                                                ):
                                                    discovered = (
                                                        plugin_loader.discover_plugins(
                                                            Path("/fake/path")
                                                        )
                                                    )

                                                assert any(
                                                    item["path"] == str(fake_file_path)
                                                    and item["module"] == "fake_module"
                                                    and item["type"] == "transformer"
                                                    for item in discovered
                                                )

    def test_plugin_discovery_error_handling(
        self, plugin_loader, clear_registry, tmp_path
    ):
        """Test error handling during plugin discovery."""
        # Test with a non-existent path
        non_existent_path = Path("/path/that/does/not/exist")

        # This should not raise an exception, but return an empty list
        discovered = plugin_loader.discover_plugins(non_existent_path)
        assert discovered == []

        # Test with a real plugin file that raises during speculative import.
        plugin_root = tmp_path / "plugins"
        plugin_root.mkdir()
        (plugin_root / "plugin_with_error.py").write_text("raise ImportError('boom')\n")

        discovered = plugin_loader.discover_plugins(plugin_root)

        assert discovered == []


# Add more test classes as needed for plugin discovery
