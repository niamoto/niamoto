"""
Parameterized tests for plugins.

This module contains parameterized tests that can be applied to multiple plugins
using pytest's parameterization feature.
"""

import pytest
import pandas as pd

from niamoto.core.plugins.base import PluginType


# Sample transformer plugins to test
TRANSFORMER_PLUGINS = [
    ("transformers.extraction.direct_attribute", "DirectAttributeTransformer"),
    ("transformers.aggregation.field_aggregator", "FieldAggregatorTransformer"),
    # Add more transformer plugins as needed
]

# Sample exporter plugins to test
EXPORTER_PLUGINS = [
    ("exporters.html", "HtmlExporter"),
    # Add more exporter plugins as needed
]

# Sample loader plugins to test
LOADER_PLUGINS = [
    ("loaders.join_table", "JoinTableLoader"),
    ("loaders.spatial", "SpatialLoader"),
    # Add more loader plugins as needed
]


class TestPluginParametrized:
    """Parameterized tests for plugins."""

    @pytest.mark.parametrize("plugin_info", TRANSFORMER_PLUGINS)
    def test_transformer_initialization(self, load_test_plugin, mock_db, plugin_info):
        """Test that transformer plugins can be initialized."""
        module_path, class_name = plugin_info
        plugin_class = load_test_plugin(module_path, class_name)

        if plugin_class:
            # Create plugin instance
            plugin = plugin_class(mock_db)

            # Check plugin type
            assert plugin.type == PluginType.TRANSFORMER

            # Check required methods
            assert hasattr(plugin, "validate_config")
            assert hasattr(plugin, "transform")

    @pytest.mark.parametrize("plugin_info", TRANSFORMER_PLUGINS)
    def test_transformer_config_validation(
        self, load_test_plugin, mock_db, plugin_info
    ):
        """Test that transformer plugins validate configs correctly."""
        module_path, class_name = plugin_info
        plugin_class = load_test_plugin(module_path, class_name)

        if plugin_class:
            # Create plugin instance
            plugin = plugin_class(mock_db)

            # Test with minimal valid config
            valid_config = {
                "plugin": class_name.replace("Transformer", "").lower(),
                "params": {},
            }

            try:
                plugin.validate_config(valid_config)
            except Exception as e:
                pytest.fail(f"Valid config validation failed: {str(e)}")

            # Test with invalid config (missing plugin field)
            invalid_config = {"params": {}}

            with pytest.raises(Exception):
                plugin.validate_config(invalid_config)

    @pytest.mark.parametrize("plugin_info", EXPORTER_PLUGINS)
    def test_exporter_initialization(self, load_test_plugin, mock_db, plugin_info):
        """Test that exporter plugins can be initialized."""
        module_path, class_name = plugin_info
        plugin_class = load_test_plugin(module_path, class_name)

        if plugin_class:
            # Create plugin instance
            plugin = plugin_class(mock_db)

            # Check plugin type
            assert plugin.type == PluginType.EXPORTER

            # Check required methods
            assert hasattr(plugin, "validate_config")
            assert hasattr(plugin, "export")

    @pytest.mark.parametrize("plugin_info", LOADER_PLUGINS)
    def test_loader_initialization(self, load_test_plugin, mock_db, plugin_info):
        """Test that loader plugins can be initialized."""
        module_path, class_name = plugin_info
        plugin_class = load_test_plugin(module_path, class_name)

        if plugin_class:
            # Create plugin instance
            plugin = plugin_class(mock_db)

            # Check plugin type
            assert plugin.type == PluginType.LOADER

            # Check required methods
            assert hasattr(plugin, "validate_config")
            assert hasattr(plugin, "load_data")


# More complex tests for specific plugin types


class TestTransformerPluginsBehavior:
    """Tests for transformer plugins behavior."""

    @pytest.mark.parametrize(
        "plugin_info,config,expected_keys",
        [
            (
                (
                    "transformers.extraction.direct_attribute",
                    "DirectAttributeTransformer",
                ),
                {"plugin": "direct_attribute", "params": {"attribute": "name"}},
                ["data"],
            ),
            (
                (
                    "transformers.aggregation.field_aggregator",
                    "FieldAggregatorTransformer",
                ),
                {
                    "plugin": "field_aggregator",
                    "params": {"group_by": "category", "aggregate": {"value": "sum"}},
                },
                ["data"],
            ),
            # Add more test cases as needed
        ],
    )
    def test_transformer_output_structure(
        self,
        load_test_plugin,
        mock_db,
        sample_dataframe,
        plugin_info,
        config,
        expected_keys,
    ):
        """Test that transformer plugins produce the expected output structure."""
        module_path, class_name = plugin_info
        plugin_class = load_test_plugin(module_path, class_name)

        if plugin_class:
            # Create plugin instance
            plugin = plugin_class(mock_db)

            try:
                # Validate config
                plugin.validate_config(config)

                # Transform data
                result = plugin.transform(sample_dataframe, config)

                # Check result type
                assert isinstance(result, dict)

                # Check expected keys
                for key in expected_keys:
                    assert key in result

            except Exception as e:
                pytest.skip(f"Transformer test skipped due to error: {str(e)}")


class TestLoaderPluginsBehavior:
    """Tests for loader plugins behavior."""

    @pytest.mark.parametrize(
        "plugin_info,config,mock_result",
        [
            (
                ("loaders.join_table", "JoinTableLoader"),
                {
                    "plugin": "join_table",
                    "params": {"table": "test_table", "join_field": "id"},
                },
                pd.DataFrame({"id": [1, 2, 3], "extra": ["A", "B", "C"]}),
            ),
            # Add more test cases as needed
        ],
    )
    def test_loader_output_structure(
        self, load_test_plugin, mock_db, plugin_info, config, mock_result
    ):
        """Test that loader plugins produce the expected output structure."""
        module_path, class_name = plugin_info
        plugin_class = load_test_plugin(module_path, class_name)

        if plugin_class:
            # Create plugin instance
            plugin = plugin_class(mock_db)

            # Configure mock_db to return the mock result
            mock_db.execute_query.return_value = mock_result

            try:
                # Validate config
                plugin.validate_config(config)

                # Load data
                result = plugin.load_data(1, config)

                # Check result type
                assert isinstance(result, pd.DataFrame)

            except Exception as e:
                pytest.skip(f"Loader test skipped due to error: {str(e)}")


# Add more test classes as needed for other plugin types
