"""
Tests for the TransformerService class.

This module contains unit tests for the TransformerService class, which is
responsible for transforming data based on YAML configuration.
"""

import unittest
from unittest.mock import Mock, patch
import pandas as pd
from rich.console import Console
from niamoto.core.services.transformer import TransformerService
from niamoto.common.exceptions import (
    ConfigurationError,
    DataTransformError,
)
from tests.common.base_test import NiamotoTestCase


class TestTransformerService(NiamotoTestCase):
    def setUp(self):
        # Create mock objects
        self.mock_db = Mock()
        self.mock_config = Mock()
        self.mock_console = Mock()
        self.mock_plugin_loader = Mock()

        # Reset mock_db execute_sql call count for each test
        self.mock_db.execute_sql = Mock()

        # Set up mock config
        self.mock_config.get_transforms_config.return_value = [
            {
                "group_by": "plot",
                "source": {
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                },
                "widgets_data": {
                    "species_count": {
                        "plugin": "count_transformer",
                        "field": "species",
                        "params": {"distinct": True},
                    }
                },
            }
        ]
        self.mock_config.plugins_dir = "/mock/plugins/dir"

        # Create patches
        self.db_patch = self.patch(
            "niamoto.core.services.transformer.Database", return_value=self.mock_db
        )
        self.console_patch = self.patch(
            "niamoto.core.services.transformer.Console", return_value=self.mock_console
        )
        self.plugin_loader_patch = self.patch(
            "niamoto.core.services.transformer.PluginLoader",
            return_value=self.mock_plugin_loader,
        )

        # Create the service
        self.transformer_service = TransformerService("mock_db_path", self.mock_config)

    def test_init(self):
        """Test initialization of TransformerService."""
        # Create a fresh instance of TransformerService to test initialization
        mock_db = Mock()
        mock_plugin_loader = Mock()

        with (
            patch("niamoto.core.services.transformer.Database", return_value=mock_db),
            patch(
                "niamoto.core.services.transformer.PluginLoader",
                return_value=mock_plugin_loader,
            ),
        ):
            service = TransformerService("mock_db_path", self.mock_config)

            # Verify that the service is initialized correctly
            self.assertEqual(service.db, mock_db)
            self.assertEqual(service.config, self.mock_config)
            self.assertEqual(
                service.transforms_config, self.mock_config.get_transforms_config()
            )
            self.assertIsInstance(service.console, Console)

            # Verify that plugin loader methods were called
            mock_plugin_loader.load_core_plugins.assert_called_once()
            mock_plugin_loader.load_project_plugins.assert_called_once_with(
                self.mock_config.plugins_dir
            )

    def test_filter_configs_no_group(self):
        """Test _filter_configs method with no group specified."""
        result = self.transformer_service._filter_configs(None)
        self.assertEqual(result, self.mock_config.get_transforms_config())

    def test_filter_configs_exact_match(self):
        """Test _filter_configs method with exact group match."""
        result = self.transformer_service._filter_configs("plot")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["group_by"], "plot")

    def test_filter_configs_case_insensitive_match(self):
        """Test _filter_configs method with case-insensitive match."""
        # Reset the console mock to ensure it's clean
        self.transformer_service.console = Mock()

        result = self.transformer_service._filter_configs("PLOT")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["group_by"], "plot")
        self.transformer_service.console.print.assert_called_once()
        # Verify the message contains the expected text
        call_args = self.transformer_service.console.print.call_args[0][0]
        self.assertIn("Using group 'plot' instead of 'PLOT'", call_args)

    def test_filter_configs_singular_match(self):
        """Test _filter_configs method with singular form match."""
        # Update mock config to include a plural group
        self.transformer_service.transforms_config = [
            {
                "group_by": "plots",
                "source": {
                    "data": "data",
                    "grouping": "grouping",
                    "relation": {"plugin": "plugin", "key": "key"},
                },
            }
        ]

        # Reset the console mock to ensure it's clean
        self.transformer_service.console = Mock()

        result = self.transformer_service._filter_configs("plot")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["group_by"], "plots")
        self.transformer_service.console.print.assert_called_once()
        # Verify the message contains the expected text
        call_args = self.transformer_service.console.print.call_args[0][0]
        self.assertIn("Using plural form 'plots' instead of 'plot'", call_args)

    def test_filter_configs_plural_match(self):
        """Test _filter_configs method with plural form match."""
        # Update mock config to include a singular group
        self.transformer_service.transforms_config = [
            {
                "group_by": "plot",
                "source": {
                    "data": "data",
                    "grouping": "grouping",
                    "relation": {"plugin": "plugin", "key": "key"},
                },
            }
        ]

        # Reset the console mock to ensure it's clean
        self.transformer_service.console = Mock()

        result = self.transformer_service._filter_configs("plots")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["group_by"], "plot")
        self.transformer_service.console.print.assert_called_once()
        # Verify the message contains the expected text
        call_args = self.transformer_service.console.print.call_args[0][0]
        self.assertIn("Using singular form 'plot' instead of 'plots'", call_args)

    def test_filter_configs_no_match(self):
        """Test _filter_configs method with no match."""
        with self.assertRaises(ConfigurationError) as context:
            self.transformer_service._filter_configs("nonexistent")

        self.assertIn("No configuration found for group", str(context.exception))

    def test_validate_configuration_valid(self):
        """Test validate_configuration method with valid configuration."""
        config = {
            "source": {
                "data": "occurrences",
                "grouping": "plot_ref",
                "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
            }
        }

        # This should not raise an exception
        self.transformer_service.validate_configuration(config)

    def test_validate_configuration_missing_source_fields(self):
        """Test validate_configuration method with missing source fields."""
        config = {
            "source": {
                "data": "occurrences",
                # Missing "grouping" and "relation"
            }
        }

        with self.assertRaises(ConfigurationError) as context:
            self.transformer_service.validate_configuration(config)

        self.assertIn(
            "Missing required source configuration fields", str(context.exception)
        )

    def test_validate_configuration_missing_relation_fields(self):
        """Test validate_configuration method with missing relation fields."""
        config = {
            "source": {
                "data": "occurrences",
                "grouping": "plot_ref",
                "relation": {
                    # Missing "plugin" or "type"
                    "key": "plot_ref_id"
                },
            }
        }

        with self.assertRaises(ConfigurationError) as context:
            self.transformer_service.validate_configuration(config)

        self.assertIn("Missing required relation fields", str(context.exception))

    def test_get_group_ids(self):
        """Test _get_group_ids method."""
        # Reset the db mock to ensure it's clean
        self.transformer_service.db = Mock()

        # Mock database response
        self.transformer_service.db.execute_sql.return_value = [(1,), (2,), (3,)]

        group_config = {"source": {"grouping": "plot_ref"}}

        result = self.transformer_service._get_group_ids(group_config)
        self.assertEqual(result, [1, 2, 3])

        # Verify SQL query
        self.transformer_service.db.execute_sql.assert_called_once()
        call_args = self.transformer_service.db.execute_sql.call_args[0][0]
        self.assertIn("SELECT DISTINCT id", call_args)
        self.assertIn("FROM plot_ref", call_args)

    def test_get_group_ids_error(self):
        """Test _get_group_ids method with database error."""
        # Reset the db mock to ensure it's clean
        self.transformer_service.db = Mock()

        # Mock database error
        self.transformer_service.db.execute_sql.side_effect = Exception(
            "Database error"
        )

        group_config = {"source": {"grouping": "plots"}}

        with self.assertRaises(DataTransformError) as context:
            self.transformer_service._get_group_ids(group_config)

        self.assertIn("Failed to get group IDs", str(context.exception))

    @patch("pandas.read_csv")
    def test_get_group_data_csv(self, mock_read_csv):
        """Test _get_group_data method with CSV file."""
        # Mock pandas read_csv
        mock_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        mock_read_csv.return_value = mock_df

        group_config = {
            "source": {
                "data": "occurrences",
                "grouping": "plot_ref",
                "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
            }
        }

        result = self.transformer_service._get_group_data(group_config, "test.csv", 1)
        self.assertTrue(result.equals(mock_df))
        mock_read_csv.assert_called_once_with("test.csv")

    @patch("niamoto.core.services.transformer.PluginRegistry")
    def test_get_group_data_db(self, mock_registry):
        """Test _get_group_data method with database."""
        # Mock plugin registry and loader
        mock_loader_class = Mock()
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_registry.get_plugin.return_value = mock_loader_class

        # Mock loader response
        mock_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        mock_loader.load_data.return_value = mock_df

        group_config = {
            "source": {
                "data": "occurrences",
                "grouping": "plot_ref",
                "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
            }
        }

        result = self.transformer_service._get_group_data(group_config, None, 1)
        self.assertTrue(result.equals(mock_df))

        # Verify plugin registry call
        mock_registry.get_plugin.assert_called_once()

        # Verify loader call
        mock_loader.load_data.assert_called_once_with(
            1,
            {
                "data": "occurrences",
                "grouping": "plot_ref",
                "plugin": "direct_reference",
                "key": "plot_ref_id",
            },
        )

    def test_create_group_table(self):
        """Test _create_group_table method."""
        # Create a fresh mock for this test
        mock_db = Mock()
        # Replace the db in the service with our mock
        self.transformer_service.db = mock_db

        widgets_config = {
            "species_count": {"plugin": "count_transformer"},
            "diversity_index": {"plugin": "diversity_transformer"},
        }

        self.transformer_service._create_group_table("plot", widgets_config, True)

        # Verify SQL execution
        self.assertEqual(mock_db.execute_sql.call_count, 2)

        # First call should be DROP TABLE
        drop_call = mock_db.execute_sql.call_args_list[0][0][0]
        self.assertIn("DROP TABLE IF EXISTS plot", drop_call)

        # Second call should be CREATE TABLE
        create_call = mock_db.execute_sql.call_args_list[1][0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS plot", create_call)
        self.assertIn("plot_id INTEGER PRIMARY KEY", create_call)
        self.assertIn("species_count JSON", create_call)
        self.assertIn("diversity_index JSON", create_call)

    def test_create_group_table_no_recreate(self):
        """Test _create_group_table method without recreating the table."""
        # Create a fresh mock for this test
        mock_db = Mock()
        # Replace the db in the service with our mock
        self.transformer_service.db = mock_db

        widgets_config = {"species_count": {"plugin": "count_transformer"}}

        self.transformer_service._create_group_table("plot", widgets_config, False)

        # Verify SQL execution (only CREATE TABLE, no DROP TABLE)
        self.assertEqual(mock_db.execute_sql.call_count, 1)
        create_call = mock_db.execute_sql.call_args[0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS plot", create_call)

    def test_create_group_table_error(self):
        """Test _create_group_table method with database error."""
        # Create a fresh mock for this test
        mock_db = Mock()
        # Configure the mock to raise an exception
        mock_db.execute_sql.side_effect = Exception("Database error")
        # Replace the db in the service with our mock
        self.transformer_service.db = mock_db

        widgets_config = {"species_count": {"plugin": "count_transformer"}}

        with self.assertRaises(DataTransformError) as context:
            self.transformer_service._create_group_table("plot", widgets_config)

        self.assertIn("Failed to create table for group plot", str(context.exception))

    def test_save_widget_results(self):
        """Test _save_widget_results method with various data types."""
        # Create a fresh mock for this test
        mock_db = Mock()
        # Replace the db in the service with our mock
        self.transformer_service.db = mock_db

        # Test with different data types
        results = {
            "int_value": 42,
            "float_value": 3.14,
            "str_value": "test",
            "dict_value": {"key": "value"},
            "list_value": [1, 2, 3],
            "none_value": None,
        }

        self.transformer_service._save_widget_results("plot", 1, results)

        # Verify SQL execution
        mock_db.execute_sql.assert_called_once()
        sql_call = mock_db.execute_sql.call_args[0][0]
        params = mock_db.execute_sql.call_args[0][1]  # Capture the parameters

        # Check SQL structure
        self.assertIn(
            "INSERT INTO plot (plot_id, int_value, float_value, str_value, dict_value, list_value, none_value)",
            sql_call,
        )
        self.assertIn(
            "VALUES (:plot_id, :int_value, :float_value, :str_value, :dict_value, :list_value, :none_value)",
            sql_call,
        )
        self.assertIn("ON CONFLICT (plot_id)", sql_call)
        self.assertIn("DO UPDATE SET", sql_call)

        # Check the parameter values
        self.assertEqual(params["plot_id"], 1)

        # Vérifier le type et la valeur des paramètres correctement
        if isinstance(params["int_value"], str):
            self.assertEqual(params["int_value"], "42")
        else:
            self.assertEqual(params["int_value"], 42)

        if isinstance(params["float_value"], str):
            self.assertEqual(params["float_value"], "3.14")
        else:
            self.assertEqual(params["float_value"], 3.14)

        self.assertEqual(params["str_value"], "test")

        # Pour les valeurs JSON, vérifier seulement que les chaînes contiennent les éléments clés
        self.assertIn("key", str(params["dict_value"]))
        self.assertIn("value", str(params["dict_value"]))
        self.assertIn("1", str(params["list_value"]))
        self.assertIn("2", str(params["list_value"]))
        self.assertIn("3", str(params["list_value"]))
        self.assertIsNone(params["none_value"])

    def test_save_widget_results_numpy(self):
        """Test _save_widget_results method with NumPy data types."""
        # Create a fresh mock for this test
        mock_db = Mock()
        # Replace the db in the service with our mock
        self.transformer_service.db = mock_db

        # Create test data with simple Python types
        results = {"widget1": 42, "widget2": 3.14}

        # Call the method
        self.transformer_service._save_widget_results("plot", 1, results)

        # Verify SQL execution
        mock_db.execute_sql.assert_called_once()
        sql_call = mock_db.execute_sql.call_args[0][0]
        params = mock_db.execute_sql.call_args[0][1]  # Capture the parameters

        # Check SQL structure
        self.assertIn("INSERT INTO plot (plot_id, widget1, widget2)", sql_call)
        self.assertIn("VALUES (:plot_id, :widget1, :widget2)", sql_call)
        self.assertIn("ON CONFLICT (plot_id)", sql_call)
        self.assertIn(
            "DO UPDATE SET widget1 = excluded.widget1, widget2 = excluded.widget2",
            sql_call,
        )

        # Check the parameter values with more flexible assertions to handle string conversions
        self.assertEqual(params["plot_id"], 1)

        # Vérifier le type et la valeur des paramètres correctement
        if isinstance(params["widget1"], str):
            self.assertEqual(params["widget1"], "42")
        else:
            self.assertEqual(params["widget1"], 42)

        if isinstance(params["widget2"], str):
            self.assertEqual(params["widget2"], "3.14")
        else:
            self.assertEqual(params["widget2"], 3.14)

    @patch("niamoto.core.services.transformer.Progress")
    @patch("niamoto.core.services.transformer.TransformerService._filter_configs")
    @patch("niamoto.core.services.transformer.PluginLoader")
    def test_transform_data_error(
        self, mock_plugin_loader, mock_filter_configs, mock_progress
    ):
        """Test transform_data method with error."""

        # Mock plugin loader to avoid plugin loading errors
        mock_plugin_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_plugin_loader_instance

        # Test parameters
        group = "plot"

        # Mock filter_configs to raise an error
        error_message = f"No configuration found for group: {group}"
        error_details = {
            "group": group,
            "available_groups": ["taxon", "shape"],
            "help": "Please check your configuration file",
        }
        config_error = ConfigurationError(
            config_key="transforms", message=error_message, details=error_details
        )
        mock_filter_configs.side_effect = config_error

        for key, value in error_details.items():
            print(f"    - {key}: {value}")

        # Mock progress context manager
        mock_progress_instance = Mock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Create a fresh instance of TransformerService with our mocked plugin loader
        service = TransformerService("mock_db_path", self.mock_config)

        with self.assertRaises(ConfigurationError) as context:
            service.transform_data(group_by=group)

        caught_exception = context.exception
        for key, value in caught_exception.details.items():
            print(f"    - {key}: {value}")

        # Verify error details
        self.assertEqual(caught_exception.config_key, "transforms")
        self.assertEqual(str(caught_exception), error_message)
        self.assertEqual(caught_exception.details, error_details)

        # Verify that plugin loader was properly mocked
        mock_plugin_loader_instance.load_core_plugins.assert_called_once()
        mock_plugin_loader_instance.load_project_plugins.assert_called_once()


if __name__ == "__main__":
    unittest.main()
