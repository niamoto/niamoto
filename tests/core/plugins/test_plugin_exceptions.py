"""
Tests for the plugin exceptions.

This module contains tests for the plugin exceptions in the core.plugins.exceptions module.
"""

import unittest

from niamoto.core.plugins.exceptions import (
    PluginError,
    PluginRegistrationError,
    PluginNotFoundError,
    PluginConfigError,
    PluginLoadError,
    PluginValidationError,
    PluginExecutionError,
    PluginDependencyError,
    PluginTypeError,
    PluginStateError,
)
from tests.common.base_test import NiamotoTestCase


class TestPluginExceptions(NiamotoTestCase):
    """Tests for the plugin exceptions."""

    def test_plugin_error(self):
        """Test the base PluginError."""
        # Create error without details
        error = PluginError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"key": "value", "code": 123}
        error = PluginError("Test error", details)
        self.assertEqual(
            str(error), "Test error\nDetails: {'key': 'value', 'code': 123}"
        )
        self.assertEqual(error.details, details)

    def test_plugin_registration_error(self):
        """Test PluginRegistrationError."""
        # Create error without details
        error = PluginRegistrationError("Test error")
        self.assertEqual(str(error), "Plugin registration failed: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"plugin": "test_plugin", "type": "transformer"}
        error = PluginRegistrationError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin registration failed: Test error\n"
            "Details: {'plugin': 'test_plugin', 'type': 'transformer'}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_not_found_error(self):
        """Test PluginNotFoundError."""
        # Create error without details
        error = PluginNotFoundError("Test error")
        self.assertEqual(str(error), "Plugin not found: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"plugin": "test_plugin", "type": "transformer"}
        error = PluginNotFoundError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin not found: Test error\n"
            "Details: {'plugin': 'test_plugin', 'type': 'transformer'}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_config_error(self):
        """Test PluginConfigError."""
        # Create error without details
        error = PluginConfigError("Test error")
        self.assertEqual(str(error), "Plugin configuration error: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"plugin": "test_plugin", "config": {"param": "value"}}
        error = PluginConfigError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin configuration error: Test error\n"
            "Details: {'plugin': 'test_plugin', 'config': {'param': 'value'}}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_load_error(self):
        """Test PluginLoadError."""
        # Create error without details
        error = PluginLoadError("Test error")
        self.assertEqual(str(error), "Plugin loading failed: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"plugin": "test_plugin", "path": "/path/to/plugin"}
        error = PluginLoadError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin loading failed: Test error\n"
            "Details: {'plugin': 'test_plugin', 'path': '/path/to/plugin'}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_validation_error(self):
        """Test PluginValidationError."""
        # Create error without details
        error = PluginValidationError("Test error")
        self.assertEqual(str(error), "Plugin validation failed: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"plugin": "test_plugin", "errors": ["Invalid type", "Missing field"]}
        error = PluginValidationError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin validation failed: Test error\n"
            "Details: {'plugin': 'test_plugin', 'errors': ['Invalid type', 'Missing field']}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_execution_error(self):
        """Test PluginExecutionError."""
        # Create error without details
        error = PluginExecutionError("Test error")
        self.assertEqual(str(error), "Plugin execution failed: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {
            "plugin": "test_plugin",
            "input": "test_input",
            "error": "Division by zero",
        }
        error = PluginExecutionError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin execution failed: Test error\n"
            "Details: {'plugin': 'test_plugin', 'input': 'test_input', 'error': 'Division by zero'}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_dependency_error(self):
        """Test PluginDependencyError."""
        # Create error without details
        error = PluginDependencyError("Test error")
        self.assertEqual(str(error), "Plugin dependency error: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {"plugin": "test_plugin", "dependencies": ["dep1", "dep2"]}
        error = PluginDependencyError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin dependency error: Test error\n"
            "Details: {'plugin': 'test_plugin', 'dependencies': ['dep1', 'dep2']}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_type_error(self):
        """Test PluginTypeError."""
        # Create error without details
        error = PluginTypeError("Test error")
        self.assertEqual(str(error), "Plugin type error: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {
            "plugin": "test_plugin",
            "expected": "transformer",
            "actual": "loader",
        }
        error = PluginTypeError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin type error: Test error\n"
            "Details: {'plugin': 'test_plugin', 'expected': 'transformer', 'actual': 'loader'}",
        )
        self.assertEqual(error.details, details)

    def test_plugin_state_error(self):
        """Test PluginStateError."""
        # Create error without details
        error = PluginStateError("Test error")
        self.assertEqual(str(error), "Plugin state error: Test error")
        self.assertEqual(error.details, {})

        # Create error with details
        details = {
            "plugin": "test_plugin",
            "state": "initialized",
            "expected": "running",
        }
        error = PluginStateError("Test error", details)
        self.assertEqual(
            str(error),
            "Plugin state error: Test error\n"
            "Details: {'plugin': 'test_plugin', 'state': 'initialized', 'expected': 'running'}",
        )
        self.assertEqual(error.details, details)


if __name__ == "__main__":
    unittest.main()
