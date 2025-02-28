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
    ProcessError,
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
                    "grouping": "plots",
                    "relation": {"plugin": "join_table_loader", "key": "plot_id"},
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
                "grouping": "plots",
                "relation": {"plugin": "join_table_loader", "key": "plot_id"},
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
                "grouping": "plots",
                "relation": {
                    # Missing "plugin" or "type"
                    "key": "plot_id"
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

        group_config = {"source": {"grouping": "plots"}}

        result = self.transformer_service._get_group_ids(group_config)
        self.assertEqual(result, [1, 2, 3])

        # Verify SQL query
        self.transformer_service.db.execute_sql.assert_called_once()
        call_args = self.transformer_service.db.execute_sql.call_args[0][0]
        self.assertIn("SELECT DISTINCT id", call_args)
        self.assertIn("FROM plots", call_args)

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
                "grouping": "plots",
                "relation": {"plugin": "join_table_loader", "key": "plot_id"},
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
                "grouping": "plots",
                "relation": {"plugin": "join_table_loader", "key": "plot_id"},
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
                "grouping": "plots",
                "plugin": "join_table_loader",
                "key": "plot_id",
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

        # Check SQL structure
        self.assertIn(
            "INSERT INTO plot (plot_id, int_value, float_value, str_value, dict_value, list_value, none_value)",
            sql_call,
        )
        self.assertIn("VALUES (1, 42, 3.14, 'test',", sql_call)
        self.assertIn("ON CONFLICT (plot_id)", sql_call)
        self.assertIn("DO UPDATE SET", sql_call)

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

        # Check SQL structure
        self.assertIn("INSERT INTO plot (plot_id, widget1, widget2)", sql_call)
        self.assertIn("VALUES (1, 42, 3.14)", sql_call)
        self.assertIn("ON CONFLICT (plot_id)", sql_call)
        self.assertIn(
            "DO UPDATE SET widget1 = excluded.widget1, widget2 = excluded.widget2",
            sql_call,
        )

    def test_save_widget_results_error(self):
        """Test _save_widget_results method with error."""
        # Mock database error
        self.mock_db.execute_sql.side_effect = Exception("Database error")

        results = {"value": 42}

        with self.assertRaises(DataTransformError) as context:
            self.transformer_service._save_widget_results("plot", 1, results)

        self.assertIn("Failed to save results for group 1", str(context.exception))

    @patch("niamoto.core.services.transformer.Progress")
    @patch("niamoto.core.services.transformer.TransformerService._filter_configs")
    def test_transform_data(self, mock_filter_configs, mock_progress):
        """Test transform_data method."""
        # Mock filter_configs to return a simple configuration
        mock_filter_configs.return_value = [
            {
                "group_by": "plot",
                "source": {
                    "data": "occurrences",
                    "grouping": "plots",
                    "relation": {"plugin": "join_table_loader", "key": "plot_id"},
                },
                "widgets_data": {
                    "species_count": {"plugin": "count_transformer", "field": "species"}
                },
            }
        ]

        # Mock progress context manager
        mock_progress_instance = Mock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = "task1"

        # Mock other methods to avoid actual processing
        self.transformer_service._get_group_ids = Mock(return_value=[1, 2])
        self.transformer_service._create_group_table = Mock()
        self.transformer_service._get_group_data = Mock(return_value=pd.DataFrame())
        self.transformer_service._save_widget_results = Mock()

        # Mock plugin registry and transformer
        with patch("niamoto.core.services.transformer.PluginRegistry") as mock_registry:
            mock_transformer_class = Mock()
            mock_transformer = Mock()
            mock_transformer_class.return_value = mock_transformer
            mock_registry.get_plugin.return_value = mock_transformer_class
            mock_transformer.transform.return_value = {"result": 42}

            # Call the method
            self.transformer_service.transform_data(group_by="plot")

            # Verify method calls
            mock_filter_configs.assert_called_once_with("plot")
            self.transformer_service._get_group_ids.assert_called_once()
            self.transformer_service._create_group_table.assert_called_once()
            self.assertEqual(
                self.transformer_service._get_group_data.call_count, 2
            )  # Once for each group ID
            self.assertEqual(
                self.transformer_service._save_widget_results.call_count, 2
            )  # Once for each group ID
            self.assertEqual(
                mock_transformer.transform.call_count, 2
            )  # Once for each group ID

    @patch("niamoto.core.services.transformer.Progress")
    @patch("niamoto.core.services.transformer.TransformerService._filter_configs")
    def test_transform_data_error(self, mock_filter_configs, mock_progress):
        """Test transform_data method with error."""
        # Mock filter_configs to raise an error
        mock_filter_configs.side_effect = ConfigurationError("test", "Error message")

        # Mock progress context manager
        mock_progress_instance = Mock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        # Call the method and expect an error
        with self.assertRaises(ProcessError) as context:
            self.transformer_service.transform_data(group_by="plot")

        self.assertIn("Failed to transform data", str(context.exception))


if __name__ == "__main__":
    unittest.main()
