"""
Tests for the base plugin classes.

This module contains tests for the base plugin classes in the core.plugins.base module.
"""

import unittest
import pandas as pd
from unittest.mock import MagicMock
from pydantic import ValidationError

from niamoto.core.plugins.base import (
    Plugin,
    PluginType,
    PluginConfig,
    LoaderPlugin,
    TransformerPlugin,
    ExporterPlugin,
    WidgetPlugin,
    register,
)
from tests.common.base_test import NiamotoTestCase


class TestPluginConfig(NiamotoTestCase):
    """Tests for the PluginConfig class."""

    def test_valid_config(self):
        """Test creating a valid plugin configuration."""
        config = PluginConfig(plugin="test_plugin")
        self.assertEqual(config.plugin, "test_plugin")
        self.assertEqual(config.source, None)
        self.assertEqual(config.params, {})

    def test_valid_config_with_params(self):
        """Test creating a valid plugin configuration with parameters."""
        config = PluginConfig(
            plugin="test_plugin",
            source="test_source",
            params={"param1": "value1", "param2": 2},
        )
        self.assertEqual(config.plugin, "test_plugin")
        self.assertEqual(config.source, "test_source")
        self.assertEqual(config.params, {"param1": "value1", "param2": 2})

    def test_invalid_config(self):
        """Test creating an invalid plugin configuration."""
        with self.assertRaises(ValidationError):
            PluginConfig()  # Missing required plugin field


class ConcretePlugin(Plugin):
    """Concrete implementation of Plugin for testing."""

    type = PluginType.TRANSFORMER

    def validate_config(self, config):
        """Validate plugin configuration."""
        return self.config_model(**config)


class TestPlugin(NiamotoTestCase):
    """Tests for the Plugin base class."""

    def test_initialization(self):
        """Test plugin initialization."""
        mock_db = MagicMock()
        plugin = ConcretePlugin(mock_db)
        self.assertEqual(plugin.db, mock_db)
        self.assertEqual(plugin.type, PluginType.TRANSFORMER)

    def test_validate_config(self):
        """Test config validation."""
        plugin = ConcretePlugin(MagicMock())
        config = {"plugin": "test_plugin"}
        result = plugin.validate_config(config)
        self.assertIsInstance(result, PluginConfig)
        self.assertEqual(result.plugin, "test_plugin")

    def test_validate_config_invalid(self):
        """Test validation with invalid config."""
        plugin = ConcretePlugin(MagicMock())
        with self.assertRaises(ValidationError):
            plugin.validate_config({})  # Missing required plugin field


class ConcreteLoaderPlugin(LoaderPlugin):
    """Concrete implementation of LoaderPlugin for testing."""

    def validate_config(self, config):
        """Validate plugin configuration."""
        return self.config_model(**config)

    def load_data(self, group_id, config):
        """Load data according to configuration."""
        return pd.DataFrame({"data": [1, 2, 3]})


class TestLoaderPlugin(NiamotoTestCase):
    """Tests for the LoaderPlugin class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteLoaderPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.LOADER)

    def test_load_data(self):
        """Test loading data."""
        plugin = ConcreteLoaderPlugin(MagicMock())
        result = plugin.load_data(1, {"plugin": "test_plugin"})
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.shape, (3, 1))


class ConcreteTransformerPlugin(TransformerPlugin):
    """Concrete implementation of TransformerPlugin for testing."""

    def validate_config(self, config):
        """Validate plugin configuration."""
        return self.config_model(**config)

    def transform(self, data, config):
        """Transform input data according to configuration."""
        return {"transformed": data.sum().to_dict()}


class TestTransformerPlugin(NiamotoTestCase):
    """Tests for the TransformerPlugin class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteTransformerPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.TRANSFORMER)

    def test_transform(self):
        """Test transforming data."""
        plugin = ConcreteTransformerPlugin(MagicMock())
        data = pd.DataFrame({"data": [1, 2, 3]})
        result = plugin.transform(data, {"plugin": "test_plugin"})
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"transformed": {"data": 6}})


class ConcreteExporterPlugin(ExporterPlugin):
    """Concrete implementation of ExporterPlugin for testing."""

    def validate_config(self, config):
        """Validate plugin configuration."""
        return self.config_model(**config)

    def export(self, data, config):
        """Export data according to configuration."""
        # Just a dummy implementation for testing
        return True


class TestExporterPlugin(NiamotoTestCase):
    """Tests for the ExporterPlugin class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteExporterPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.EXPORTER)

    def test_export(self):
        """Test exporting data."""
        plugin = ConcreteExporterPlugin(MagicMock())
        result = plugin.export({"data": [1, 2, 3]}, {"plugin": "test_plugin"})
        self.assertTrue(result)


class ConcreteWidgetPlugin(WidgetPlugin):
    """Concrete implementation of WidgetPlugin for testing."""

    def validate_config(self, config):
        """Validate plugin configuration."""
        return self.config_model(**config)

    def render(self, data, config):
        """Render widget HTML/JS."""
        return f"<div>{data}</div>"


class TestWidgetPlugin(NiamotoTestCase):
    """Tests for the WidgetPlugin class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.WIDGET)

    def test_render(self):
        """Test rendering widget."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        result = plugin.render("test_data", {"plugin": "test_plugin"})
        self.assertEqual(result, "<div>test_data</div>")

    def test_get_dependencies(self):
        """Test getting dependencies."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        result = plugin.get_dependencies()
        self.assertEqual(result, [])

    def test_get_container_html(self):
        """Test getting container HTML."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        result = plugin.get_container_html(
            "content",
            {
                "plugin": "test_plugin",
                "width": "100%",
                "height": "200px",
                "title": "Test Title",
                "description": "Test Description",
            },
        )
        self.assertIn('<div class="widget "', result)
        self.assertIn("width:100%;height:200px", result)
        self.assertIn("<h3>Test Title</h3>", result)
        self.assertIn("<p>Test Description</p>", result)
        self.assertIn("content", result)


class TestRegisterDecorator(NiamotoTestCase):
    """Tests for the register decorator."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Patch the PluginRegistry in the registry module, not in base
        self.registry_patcher = self.patch(
            "niamoto.core.plugins.registry.PluginRegistry"
        )
        self.mock_registry = self.registry_patcher.start()

    def test_register_with_explicit_type(self):
        """Test registering a plugin with explicit type."""

        # Define a plugin class
        @register("test_plugin", PluginType.TRANSFORMER)
        class TestPlugin(Plugin):
            type = PluginType.TRANSFORMER

            def validate_config(self, config):
                pass

        # Check that the registry was called correctly
        self.mock_registry.register_plugin.assert_called_once_with(
            "test_plugin", TestPlugin, PluginType.TRANSFORMER
        )

    def test_register_with_inferred_type(self):
        """Test registering a plugin with inferred type."""

        # Define a plugin class
        @register("test_plugin")
        class TestPlugin(Plugin):
            type = PluginType.LOADER

            def validate_config(self, config):
                pass

        # Check that the registry was called correctly
        self.mock_registry.register_plugin.assert_called_once_with(
            "test_plugin", TestPlugin, PluginType.LOADER
        )


if __name__ == "__main__":
    unittest.main()
