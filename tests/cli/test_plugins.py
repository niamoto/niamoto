"""Tests for the plugins CLI command."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch
import sys

from niamoto.core.plugins.base import PluginType


def create_mock_registry(plugins_dict=None):
    """Helper to create a properly structured mock registry."""
    if plugins_dict is None:
        plugins_dict = {}

    # Convert flat dict to registry structure
    registry_plugins = {ptype: {} for ptype in PluginType}

    for name, info in plugins_dict.items():
        ptype = info["type"]
        registry_plugins[ptype][name] = info["class"]

    mock_registry = Mock()
    mock_registry._plugins = registry_plugins
    return mock_registry


class TestPluginsCommand:
    """Test suite for the plugins command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def mock_registry(self):
        """Create a mock plugin registry with test plugins."""
        # Create mock classes with different attributes
        transformer_class = Mock(
            __name__="TestTransformer",
            __module__="test.module",
            __doc__="Test transformer plugin for unit tests.",
            spec=["__name__", "__module__", "__doc__", "param_schema"],
        )
        transformer_class.param_schema = Mock()  # Has schema

        widget_class = Mock(
            __name__="TestWidget",
            __module__="test.module",
            __doc__="Test widget plugin.\nSecond line should be ignored.",
            spec=["__name__", "__module__", "__doc__"],  # No param_schema
        )

        exporter_class = Mock(
            __name__="TestExporter",
            __module__="test.module",
            __doc__=None,  # No docstring
            spec=["__name__", "__module__", "__doc__"],  # No param_schema
        )

        mock_plugins = {
            "test_transformer": {
                "type": PluginType.TRANSFORMER,
                "class": transformer_class,
            },
            "test_widget": {
                "type": PluginType.WIDGET,
                "class": widget_class,
            },
            "test_exporter": {
                "type": PluginType.EXPORTER,
                "class": exporter_class,
            },
        }

        mock_registry = Mock()
        mock_registry._plugins = mock_plugins
        return mock_registry

    def test_list_all_plugins_table_format(self, runner, mock_registry):
        """Test listing all plugins in table format."""
        mock_registry_cls = create_mock_registry(mock_registry._plugins)

        # Patch all dependencies
        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    # Import after patching
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

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
        mock_registry_cls = create_mock_registry(mock_registry._plugins)

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins, ["--format", "simple"])

        assert result.exit_code == 0
        assert "TRANSFORMER PLUGINS:" in result.output
        assert "WIDGET PLUGINS:" in result.output
        assert "EXPORTER PLUGINS:" in result.output
        assert (
            "test_transformer - Test transformer plugin for unit tests" in result.output
        )

    def test_filter_by_type(self, runner, mock_registry):
        """Test filtering plugins by type."""
        mock_registry_cls = create_mock_registry(mock_registry._plugins)

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins, ["--type", "transformer"])

        assert result.exit_code == 0
        assert "test_transformer" in result.output
        assert "test_widget" not in result.output
        assert "test_exporter" not in result.output
        assert "Total: 1 plugins" in result.output

    def test_verbose_output(self, runner, mock_registry):
        """Test verbose output shows additional details."""
        mock_registry_cls = create_mock_registry(mock_registry._plugins)

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins, ["--verbose"])

        assert result.exit_code == 0
        assert "Module" in result.output
        assert "Class" in result.output
        assert "Schema" in result.output  # Column header might be wrapped
        assert "test.mod" in result.output  # Module name might be truncated
        assert "TestTran" in result.output  # Class name might be truncated
        assert "✓" in result.output  # Has schema (transformer)
        assert "✗" in result.output  # No schema (widget and exporter)

    def test_verbose_simple_format(self, runner, mock_registry):
        """Test verbose output in simple format."""
        mock_registry_cls = create_mock_registry(mock_registry._plugins)

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins, ["--format", "simple", "--verbose"])

        assert result.exit_code == 0
        assert "Module: test.module" in result.output
        assert "Class: TestTransformer" in result.output
        # Only transformer has param_schema
        assert "Has parameter schema: ✓" in result.output

    def test_no_plugins_found(self, runner):
        """Test when no plugins are found."""
        mock_registry_cls = create_mock_registry({})

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins)

        assert result.exit_code == 0
        assert "No plugins found" in result.output

    def test_no_plugins_of_type(self, runner, mock_registry):
        """Test when no plugins of specified type are found."""
        mock_registry_cls = create_mock_registry(mock_registry._plugins)

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins, ["--type", "loader"])

        assert result.exit_code == 0
        assert "No plugins found of type loader" in result.output

    def test_invalid_type(self, runner):
        """Test with invalid plugin type."""
        from niamoto.cli.commands.plugins import plugins

        result = runner.invoke(plugins, ["--type", "invalid"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_registry_error(self, runner):
        """Test handling of registry errors."""
        # Mock PluginLoader to raise an exception
        with patch(
            "niamoto.core.plugins.plugin_loader.PluginLoader",
            side_effect=Exception("Registry error"),
        ):
            if "niamoto.cli.commands.plugins" in sys.modules:
                del sys.modules["niamoto.cli.commands.plugins"]
            from niamoto.cli.commands.plugins import plugins

            result = runner.invoke(plugins)

        # Check that the command failed
        assert result.exit_code != 0
        # The error message should be in the output
        assert "Registry error" in result.output

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

        mock_registry_cls = create_mock_registry(mock_plugins)

        with patch("niamoto.core.plugins.plugin_loader.PluginLoader"):
            with patch("niamoto.common.config.Config"):
                with patch(
                    "niamoto.core.plugins.registry.PluginRegistry", mock_registry_cls
                ):
                    if "niamoto.cli.commands.plugins" in sys.modules:
                        del sys.modules["niamoto.cli.commands.plugins"]
                    from niamoto.cli.commands.plugins import plugins

                    result = runner.invoke(plugins)

        assert result.exit_code == 0
        assert "Single line description" in result.output  # Period removed
        assert "Multi-line with spaces" in result.output
        assert result.output.count("No description available") >= 1
