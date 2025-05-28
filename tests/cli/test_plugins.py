"""Tests for the plugins CLI command."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch

from niamoto.cli.commands.plugins import plugins
from niamoto.core.plugins.base import PluginType


class TestPluginsCommand:
    """Test suite for the plugins command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def mock_registry(self):
        """Create a mock plugin registry with test plugins."""
        mock_plugins = {
            "test_transformer": {
                "type": PluginType.TRANSFORMER,
                "class": Mock(
                    __name__="TestTransformer",
                    __module__="test.module",
                    __doc__="Test transformer plugin for unit tests.",
                    param_schema=Mock(),
                ),
            },
            "test_widget": {
                "type": PluginType.WIDGET,
                "class": Mock(
                    __name__="TestWidget",
                    __module__="test.module",
                    __doc__="Test widget plugin.\nSecond line should be ignored.",
                ),
            },
            "test_exporter": {
                "type": PluginType.EXPORTER,
                "class": Mock(
                    __name__="TestExporter",
                    __module__="test.module",
                    __doc__=None,  # No docstring
                ),
            },
        }

        mock_registry = Mock()
        mock_registry._plugins = mock_plugins
        return mock_registry

    def test_list_all_plugins_table_format(self, runner, mock_registry):
        """Test listing all plugins in table format."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins)

            assert result.exit_code == 0
            assert "Available Niamoto Plugins" in result.output
            assert "test_transformer" in result.output
            assert "test_widget" in result.output
            assert "test_exporter" in result.output
            assert "Test transformer plugin for unit tests" in result.output
            assert "Test widget plugin" in result.output
            assert "No description available" in result.output
            assert "Total: 3 plugins" in result.output

    def test_list_plugins_simple_format(self, runner, mock_registry):
        """Test listing plugins in simple format."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins, ["--format", "simple"])

            assert result.exit_code == 0
            assert "TRANSFORMER PLUGINS:" in result.output
            assert "WIDGET PLUGINS:" in result.output
            assert "EXPORTER PLUGINS:" in result.output
            assert (
                "test_transformer - Test transformer plugin for unit tests"
                in result.output
            )

    def test_filter_by_type(self, runner, mock_registry):
        """Test filtering plugins by type."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins, ["--type", "transformer"])

            assert result.exit_code == 0
            assert "test_transformer" in result.output
            assert "test_widget" not in result.output
            assert "test_exporter" not in result.output
            assert "Total: 1 plugins" in result.output

    def test_verbose_output(self, runner, mock_registry):
        """Test verbose output shows additional details."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins, ["--verbose"])

            assert result.exit_code == 0
            assert "Module" in result.output
            assert "Class" in result.output
            assert "Has Schema" in result.output
            assert "test.module" in result.output
            assert "TestTransformer" in result.output
            assert "✓" in result.output  # Has schema
            assert "✗" in result.output  # No schema

    def test_verbose_simple_format(self, runner, mock_registry):
        """Test verbose output in simple format."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins, ["--format", "simple", "--verbose"])

            assert result.exit_code == 0
            assert "Module: test.module" in result.output
            assert "Class: TestTransformer" in result.output
            assert "Has parameter schema: ✓" in result.output

    def test_no_plugins_found(self, runner):
        """Test when no plugins are found."""
        mock_registry = Mock()
        mock_registry._plugins = {}

        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins)

            assert result.exit_code == 0
            assert "No plugins found" in result.output

    def test_no_plugins_of_type(self, runner, mock_registry):
        """Test when no plugins of specified type are found."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins, ["--type", "loader"])

            assert result.exit_code == 0
            assert "No plugins found of type loader" in result.output

    def test_invalid_type(self, runner):
        """Test with invalid plugin type."""
        result = runner.invoke(plugins, ["--type", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_registry_error(self, runner):
        """Test handling of registry errors."""
        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry",
            side_effect=Exception("Registry error"),
        ):
            result = runner.invoke(plugins)

            assert result.exit_code != 0
            assert "Error listing plugins: Registry error" in result.output

    def test_description_extraction(self, runner):
        """Test proper extraction of plugin descriptions."""
        mock_plugins = {
            "test1": {
                "type": PluginType.TRANSFORMER,
                "class": Mock(
                    __name__="Test1",
                    __module__="test",
                    __doc__="Single line description.",
                ),
            },
            "test2": {
                "type": PluginType.TRANSFORMER,
                "class": Mock(
                    __name__="Test2",
                    __module__="test",
                    __doc__="\n\n  Multi-line with spaces.  \n\nMore text.",
                ),
            },
            "test3": {
                "type": PluginType.TRANSFORMER,
                "class": Mock(__name__="Test3", __module__="test", __doc__=""),
            },
        }

        mock_registry = Mock()
        mock_registry._plugins = mock_plugins

        with patch(
            "niamoto.cli.commands.plugins.PluginRegistry", return_value=mock_registry
        ):
            result = runner.invoke(plugins)

            assert result.exit_code == 0
            assert "Single line description" in result.output  # Period removed
            assert "Multi-line with spaces" in result.output
            assert result.output.count("No description available") >= 1
