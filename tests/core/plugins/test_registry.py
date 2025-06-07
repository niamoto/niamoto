"""
Tests for the plugin registry.

This module contains tests for the plugin registry in the core.plugins.registry module.
"""

import unittest
from unittest.mock import MagicMock, patch
from niamoto.core.plugins.base import Plugin, PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.exceptions import PluginRegistrationError, PluginNotFoundError
from tests.common.base_test import NiamotoTestCase


class MockPlugin(Plugin):
    """Mock plugin for testing."""

    type = PluginType.TRANSFORMER

    def validate_config(self, config):
        """Validate plugin configuration."""
        pass


class MockLoaderPlugin(Plugin):
    """Mock loader plugin for testing."""

    type = PluginType.LOADER

    def validate_config(self, config):
        """Validate plugin configuration."""
        pass


class TestPluginRegistry(NiamotoTestCase):
    """Tests for the PluginRegistry class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Clear the registry before each test
        PluginRegistry.clear()

    def tearDown(self):
        """Tear down test fixtures."""
        # Clear the registry after each test
        PluginRegistry.clear()
        super().tearDown()

    def test_register_plugin(self):
        """Test registering a plugin."""
        # Register a plugin
        PluginRegistry.register_plugin("test_plugin", MockPlugin)

        # Verify it was registered correctly
        self.assertTrue(
            PluginRegistry.has_plugin("test_plugin", PluginType.TRANSFORMER)
        )
        plugin_class = PluginRegistry.get_plugin("test_plugin", PluginType.TRANSFORMER)
        self.assertEqual(plugin_class, MockPlugin)

    def test_register_plugin_with_explicit_type(self):
        """Test registering a plugin with explicit type."""
        # Register a plugin with explicit type
        PluginRegistry.register_plugin(
            "test_plugin", MockPlugin, PluginType.TRANSFORMER
        )

        # Verify it was registered correctly
        self.assertTrue(
            PluginRegistry.has_plugin("test_plugin", PluginType.TRANSFORMER)
        )
        plugin_class = PluginRegistry.get_plugin("test_plugin", PluginType.TRANSFORMER)
        self.assertEqual(plugin_class, MockPlugin)

    def test_register_plugin_with_metadata(self):
        """Test registering a plugin with metadata."""
        # Register a plugin with metadata
        metadata = {"author": "Test Author", "version": "1.0.0"}
        PluginRegistry.register_plugin("test_plugin", MockPlugin, metadata=metadata)

        # Verify metadata was stored correctly
        stored_metadata = PluginRegistry.get_plugin_metadata("test_plugin")
        self.assertEqual(stored_metadata, metadata)

    def test_register_plugin_invalid_type(self):
        """Test registering a plugin with invalid type."""
        # Try to register a plugin with invalid type
        with self.assertRaises(PluginRegistrationError):
            PluginRegistry.register_plugin("test_plugin", MockPlugin, "invalid_type")

    def test_register_plugin_duplicate(self):
        """Test registering a duplicate plugin."""
        # Register a plugin
        PluginRegistry.register_plugin("test_plugin", MockPlugin)

        # Try to register the same plugin class again - should succeed (allow re-registration)
        PluginRegistry.register_plugin("test_plugin", MockPlugin)  # Should not raise

        # Verify plugin is still registered
        plugin = PluginRegistry.get_plugin("test_plugin", PluginType.TRANSFORMER)
        self.assertEqual(plugin, MockPlugin)

    def test_register_plugin_different_class_same_name(self):
        """Test registering different plugin classes with the same name should fail."""
        # Register a plugin
        PluginRegistry.register_plugin("test_plugin", MockPlugin)

        # Create a different plugin class
        class DifferentMockPlugin(Plugin):
            type = PluginType.TRANSFORMER

        # Try to register a different plugin class with the same name - should fail
        with self.assertRaises(PluginRegistrationError):
            PluginRegistry.register_plugin("test_plugin", DifferentMockPlugin)

    def test_register_plugin_generic_exception(self):
        """Test registering a plugin with a generic exception."""
        # Create a mock that raises an exception when accessed
        mock_plugin_type = MagicMock()
        mock_plugin_type.__getitem__ = MagicMock(side_effect=ValueError("Test error"))

        # Patch the _plugins dictionary to use our mock
        with patch.object(PluginRegistry, "_plugins", mock_plugin_type):
            # Try to register a plugin, which should raise a PluginRegistrationError
            with self.assertRaises(PluginRegistrationError) as context:
                PluginRegistry.register_plugin("test_plugin", MockPlugin)

            # Verify the error details
            self.assertIn(
                "Failed to register plugin test_plugin", str(context.exception)
            )
            self.assertIn("error", context.exception.details)
            self.assertIn("Test error", context.exception.details["error"])

    def test_get_plugin(self):
        """Test getting a plugin."""
        # Register a plugin
        PluginRegistry.register_plugin("test_plugin", MockPlugin)

        # Get the plugin
        plugin_class = PluginRegistry.get_plugin("test_plugin", PluginType.TRANSFORMER)
        self.assertEqual(plugin_class, MockPlugin)

    def test_get_plugin_not_found(self):
        """Test getting a non-existent plugin."""
        # Try to get a non-existent plugin
        with self.assertRaises(PluginNotFoundError):
            PluginRegistry.get_plugin("non_existent", PluginType.TRANSFORMER)

    def test_get_plugins_by_type(self):
        """Test getting all plugins of a type."""
        # Register multiple plugins
        PluginRegistry.register_plugin("test_plugin1", MockPlugin)
        PluginRegistry.register_plugin("test_plugin2", MockPlugin)
        PluginRegistry.register_plugin("test_loader", MockLoaderPlugin)

        # Get all transformer plugins
        transformer_plugins = PluginRegistry.get_plugins_by_type(PluginType.TRANSFORMER)
        self.assertEqual(len(transformer_plugins), 2)
        self.assertIn("test_plugin1", transformer_plugins)
        self.assertIn("test_plugin2", transformer_plugins)

        # Get all loader plugins
        loader_plugins = PluginRegistry.get_plugins_by_type(PluginType.LOADER)
        self.assertEqual(len(loader_plugins), 1)
        self.assertIn("test_loader", loader_plugins)

    def test_list_plugins(self):
        """Test listing all plugins."""
        # Register multiple plugins
        PluginRegistry.register_plugin("test_plugin1", MockPlugin)
        PluginRegistry.register_plugin("test_plugin2", MockPlugin)
        PluginRegistry.register_plugin("test_loader", MockLoaderPlugin)

        # List all plugins
        plugins = PluginRegistry.list_plugins()
        self.assertIn(PluginType.TRANSFORMER, plugins)
        self.assertIn(PluginType.LOADER, plugins)
        self.assertEqual(
            set(plugins[PluginType.TRANSFORMER]), {"test_plugin1", "test_plugin2"}
        )
        self.assertEqual(set(plugins[PluginType.LOADER]), {"test_loader"})

    def test_clear(self):
        """Test clearing the registry."""
        # Register a plugin
        PluginRegistry.register_plugin("test_plugin", MockPlugin)
        PluginRegistry.register_plugin(
            "test_loader", MockLoaderPlugin, metadata={"version": "1.0.0"}
        )

        # Clear the registry
        PluginRegistry.clear()

        # Verify registry is empty
        self.assertEqual(
            len(PluginRegistry.get_plugins_by_type(PluginType.TRANSFORMER)), 0
        )
        self.assertEqual(len(PluginRegistry.get_plugins_by_type(PluginType.LOADER)), 0)
        self.assertEqual(PluginRegistry.get_plugin_metadata("test_plugin"), {})

    def test_has_plugin(self):
        """Test checking if a plugin exists."""
        # Register a plugin
        PluginRegistry.register_plugin("test_plugin", MockPlugin)

        # Check if plugin exists
        self.assertTrue(
            PluginRegistry.has_plugin("test_plugin", PluginType.TRANSFORMER)
        )
        self.assertFalse(
            PluginRegistry.has_plugin("non_existent", PluginType.TRANSFORMER)
        )
        self.assertFalse(PluginRegistry.has_plugin("test_plugin", PluginType.LOADER))

    def test_remove_plugin(self):
        """Test removing a plugin."""
        # Register a plugin
        PluginRegistry.register_plugin(
            "test_plugin", MockPlugin, metadata={"version": "1.0.0"}
        )

        # Remove the plugin
        PluginRegistry.remove_plugin("test_plugin", PluginType.TRANSFORMER)

        # Verify plugin was removed
        self.assertFalse(
            PluginRegistry.has_plugin("test_plugin", PluginType.TRANSFORMER)
        )
        self.assertEqual(PluginRegistry.get_plugin_metadata("test_plugin"), {})

    def test_remove_plugin_not_found(self):
        """Test removing a non-existent plugin."""
        # Try to remove a non-existent plugin
        with self.assertRaises(PluginNotFoundError):
            PluginRegistry.remove_plugin("non_existent", PluginType.TRANSFORMER)


if __name__ == "__main__":
    unittest.main()
