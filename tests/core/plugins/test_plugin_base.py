# tests/core/plugins/test_plugin_base.py

"""
Tests for the base plugin classes.

This module contains tests for the abstract base plugin classes
in the core.plugins.base module. It verifies class structure,
type attributes, and basic method callability.
"""

import unittest
import pandas as pd
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from typing import Any

# Import base classes and decorator to be tested
from niamoto.core.plugins.base import (
    Plugin,
    PluginType,
    LoaderPlugin,
    TransformerPlugin,
    ExporterPlugin,
    WidgetPlugin,
    register,
)

# Assuming NiamotoTestCase and necessary base exceptions exist
from tests.common.base_test import NiamotoTestCase

# Import exception for testing decorator failure
from niamoto.core.plugins.exceptions import PluginRegistrationError

# --- TestPluginConfig class removed ---
# This model now resides in core.plugins.models.py and its tests
# (if any) should be moved accordingly.


# --- Concrete implementations for testing abstract base classes ---


# Dummy Pydantic model to simulate validated params
class MockValidatedParams(BaseModel):
    dummy_param: str = "value"


class ConcretePlugin(Plugin):
    """Concrete implementation of Plugin for testing basic inheritance."""

    type = PluginType.TRANSFORMER
    # No implementation needed for abstract methods in this specific test class


class TestPlugin(NiamotoTestCase):
    """Tests for the Plugin abstract base class itself."""

    def test_initialization(self):
        """Test plugin initialization stores db."""
        mock_db = MagicMock()
        # We need a concrete class to instantiate Plugin
        plugin = ConcretePlugin(mock_db)
        self.assertEqual(plugin.db, mock_db)

    def test_type_attribute_on_concrete_class(self):
        """Test plugin type attribute is correctly set on a concrete class."""
        plugin = ConcretePlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.TRANSFORMER)

    # --- Tests for the removed validate_config method are deleted ---


class ConcreteLoaderPlugin(LoaderPlugin):
    """Concrete implementation of LoaderPlugin for testing."""

    # No config_model or validate_config needed for base class testing

    def load_data(self, *args, **kwargs) -> pd.DataFrame:
        """Load dummy data."""
        print(f"ConcreteLoaderPlugin.load_data called: {args=}, {kwargs=}")
        # Return expected type for testing callability
        return pd.DataFrame({"data": [1, 2, 3]})


class TestLoaderPlugin(NiamotoTestCase):
    """Tests for the LoaderPlugin base class."""

    def test_type(self):
        """Test plugin type is correctly set."""
        plugin = ConcreteLoaderPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.LOADER)

    def test_load_data_callable(self):
        """Test the abstract load_data method can be called on a concrete instance."""
        plugin = ConcreteLoaderPlugin(MagicMock())
        # Call with plausible arguments; we only test if it runs and returns correct type
        result = plugin.load_data(group_id=1, params=MockValidatedParams())
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result.shape, (3, 1))


class ConcreteTransformerPlugin(TransformerPlugin):
    """Concrete implementation of TransformerPlugin for testing."""

    # No config_model or validate_config needed for base class testing

    def transform(self, data: pd.DataFrame, params: BaseModel) -> dict:
        """Transform input data based on validated parameters."""
        print(
            f"ConcreteTransformerPlugin.transform called: data={data.shape}, params={params}"
        )
        # Simple implementation using data for testing callability
        return {"transformed": data.sum().to_dict()}


class TestTransformerPlugin(NiamotoTestCase):
    """Tests for the TransformerPlugin base class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteTransformerPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.TRANSFORMER)

    def test_transform_callable(self):
        """Test the abstract transform method can be called."""
        plugin = ConcreteTransformerPlugin(MagicMock())
        data = pd.DataFrame({"data": [1, 2, 3]})
        # Pass a dummy Pydantic model instance for params, as per the new signature
        dummy_params = MockValidatedParams()
        result = plugin.transform(data, params=dummy_params)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"transformed": {"data": 6}})


class ConcreteExporterPlugin(ExporterPlugin):
    """Concrete implementation of ExporterPlugin for testing."""

    # No config_model or validate_config needed for base class testing

    def export(self, target_config: "TargetConfig", repository: Any) -> None:  # noqa: F821
        """Dummy export implementation."""
        print("ConcreteExporterPlugin.export called.")
        # No return value expected
        pass


class TestExporterPlugin(NiamotoTestCase):
    """Tests for the ExporterPlugin base class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteExporterPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.EXPORTER)

    def test_export_callable(self):
        """Test the abstract export method can be called."""
        plugin = ConcreteExporterPlugin(MagicMock())
        # Pass dummy objects for target_config and repository
        mock_target_config = (
            MagicMock()
        )  # In real tests, this would be a TargetConfig instance
        mock_repository = MagicMock()
        try:
            # Check that export runs without raising NotImplementedError
            plugin.export(target_config=mock_target_config, repository=mock_repository)
        except Exception as e:
            self.fail(f"ExporterPlugin.export raised exception unexpectedly: {e}")


class ConcreteWidgetPlugin(WidgetPlugin):
    """Concrete implementation of WidgetPlugin for testing."""

    # No config_model or validate_config needed for base class testing

    def render(self, data: Any, params: BaseModel) -> str:
        """Render dummy widget HTML."""
        print(f"ConcreteWidgetPlugin.render called: data={data}, params={params}")
        return f"<div>{data}</div>"


class TestWidgetPlugin(NiamotoTestCase):
    """Tests for the WidgetPlugin base class."""

    def test_type(self):
        """Test plugin type."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        self.assertEqual(plugin.type, PluginType.WIDGET)

    def test_render_callable(self):
        """Test the abstract render method can be called."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        dummy_params = MockValidatedParams()
        result = plugin.render("test_data", params=dummy_params)
        self.assertEqual(result, "<div>test_data</div>")

    def test_get_dependencies(self):
        """Test getting default dependencies (should be empty list)."""
        plugin = ConcreteWidgetPlugin(MagicMock())
        result = plugin.get_dependencies()
        self.assertEqual(result, [])

    def test_get_container_html(self):
        """Test getting container HTML with mocked config."""
        plugin = ConcreteWidgetPlugin(MagicMock())

        mock_widget_config = MagicMock(spec=["title", "description", "params"])
        mock_widget_config.title = "Test Title"
        mock_widget_config.description = "Test Description"
        mock_widget_config.params = {
            "width": "100%",
            "height": "200px",
            "class_name": "test-class",
        }
        widget_content_html = "<p>Widget Content</p>"

        result = plugin.get_container_html(
            widget_id="widget-123",
            content=widget_content_html,
            config=mock_widget_config,
        )

        self.assertIn(
            '<div id="widget-123" class="widget widget-modern test-class"', result
        )
        self.assertIn('style="width:100%; height:200px;"', result)
        self.assertIn('<h3 class="widget-title-modern">', result)
        self.assertIn("Test Title", result)
        self.assertIn(
            '<span class="info-tooltip" data-tooltip="Test Description">', result
        )

        self.assertIn('<div class="widget-content">', result)
        self.assertIn(widget_content_html, result)
        self.assertTrue(result.strip().endswith("</div>"))


class TestRegisterDecorator(NiamotoTestCase):
    """Tests for the @register decorator."""

    def setUp(self):
        """Set up test fixtures, patching the registry."""
        super().setUp()
        # Patch PluginRegistry where it's defined
        self.registry_patcher = patch("niamoto.core.plugins.registry.PluginRegistry")
        self.mock_registry = self.registry_patcher.start()
        # Ensure mock has the required method
        self.mock_registry.register_plugin = MagicMock()

    def tearDown(self):
        """Stop patcher."""
        self.registry_patcher.stop()
        super().tearDown()

    def test_register_with_explicit_type(self):
        """Test registering a plugin with explicit type argument."""

        @register("test_plugin_explicit", PluginType.TRANSFORMER)
        class TestPluginExplicit(TransformerPlugin):  # Use specific base
            # Dummy implementation for abstract method
            def transform(self, data: Any, params: BaseModel) -> Any:
                return None

        # Check registry was called correctly
        self.mock_registry.register_plugin.assert_called_once_with(
            "test_plugin_explicit", TestPluginExplicit, PluginType.TRANSFORMER
        )

    def test_register_with_inferred_type(self):
        """Test registering a plugin with inferred type from class attribute."""

        @register("test_plugin_inferred")
        class TestPluginInferred(LoaderPlugin):  # Use specific base
            # Type is inferred from LoaderPlugin.type
            # Dummy implementation for abstract method
            def load_data(self, *args, **kwargs) -> pd.DataFrame:
                return pd.DataFrame()

        # Check registry was called correctly
        self.mock_registry.register_plugin.assert_called_once_with(
            "test_plugin_inferred", TestPluginInferred, PluginType.LOADER
        )

    def test_register_raises_error_if_no_type(self):
        """Test decorator raises TypeError if type cannot be determined."""

        with self.assertRaisesRegex(
            TypeError, "must either have a 'type' class attribute"
        ):

            @register("test_plugin_no_type")
            class TestPluginNoType(
                Plugin
            ):  # Inheriting directly from Plugin without 'type'
                # Need dummy implementations if Plugin itself becomes abstract later
                pass  # Fails because Plugin itself has no 'type' attr value

        self.mock_registry.register_plugin.assert_not_called()

    def test_register_raises_error_if_registry_fails(self):
        """Test decorator propagates exceptions from PluginRegistry."""
        # Configure the mock registry to raise a specific error
        self.mock_registry.register_plugin.side_effect = PluginRegistrationError(
            "Duplicate!"
        )

        with self.assertRaises(PluginRegistrationError):

            @register("test_plugin_duplicate", PluginType.WIDGET)
            class TestWidgetDuplicate(WidgetPlugin):
                def render(self, data: Any, params: BaseModel) -> str:
                    return ""

        self.mock_registry.register_plugin.assert_called_once()


if __name__ == "__main__":
    unittest.main()
