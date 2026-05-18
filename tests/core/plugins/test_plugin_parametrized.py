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
    ("transformers.extraction.direct_attribute", "DirectAttribute"),
    ("transformers.aggregation.field_aggregator", "FieldAggregator"),
    # Add more transformer plugins as needed
]

# Sample exporter plugins to test
EXPORTER_PLUGINS = [
    ("exporters.json_api_exporter", "JsonApiExporter"),
    # Add more exporter plugins as needed
]

# Sample loader plugins to test
LOADER_PLUGINS = [
    ("loaders.join_table", "JoinTableLoader"),
    ("loaders.spatial", "SpatialLoader"),
    # Add more loader plugins as needed
]

VALID_TRANSFORMER_CONFIGS = {
    "DirectAttribute": {
        "plugin": "direct_attribute",
        "params": {"field": "name"},
    },
    "FieldAggregator": {
        "plugin": "field_aggregator",
        "params": {
            "fields": [
                {
                    "field": "value",
                    "target": "total_value",
                    "transformation": "sum",
                }
            ]
        },
    },
}


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
            valid_config = VALID_TRANSFORMER_CONFIGS[class_name]

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
                ("transformers.extraction.direct_attribute", "DirectAttribute"),
                {
                    "plugin": "direct_attribute",
                    "params": {"field": "name"},
                    "group_id": 1,
                },
                ["value"],
            ),
            (
                ("transformers.aggregation.field_aggregator", "FieldAggregator"),
                {
                    "plugin": "field_aggregator",
                    "params": {
                        "fields": [
                            {
                                "field": "value",
                                "target": "total_value",
                                "transformation": "sum",
                            }
                        ]
                    },
                },
                ["total_value"],
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

            # Validate config
            plugin.validate_config(config)

            # Transform data
            result = plugin.transform(sample_dataframe, config)

            # Check result type
            assert isinstance(result, dict)

            # Check expected keys
            for key in expected_keys:
                assert key in result


class TestLoaderPluginsBehavior:
    """Tests for loader plugins behavior."""

    @pytest.mark.parametrize(
        "plugin_info,config,mock_result",
        [
            (
                ("loaders.join_table", "JoinTableLoader"),
                {
                    "plugin": "join_table",
                    "data": "test_table",
                    "key": "id",
                    "join_table": "test_join_table",
                    "keys": {"source": "id_source", "reference": "id_reference"},
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
            mock_db.has_table.return_value = True
            mock_db.get_table_columns.side_effect = lambda name: ["id", "value"]
            mock_db.execute_query.return_value = mock_result
            mock_db.engine.connect.return_value.__enter__.return_value = mock_db

            # Validate config
            plugin.validate_config(config)

            # Load data
            from unittest.mock import patch

            with patch("pandas.read_sql", return_value=mock_result):
                result = plugin.load_data(1, config)

            # Check result type
            assert isinstance(result, pd.DataFrame)


# Add more test classes as needed for other plugin types
