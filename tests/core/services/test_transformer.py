"""
Comprehensive tests for the TransformerService class.

This module contains unit tests for the TransformerService class, which is
responsible for transforming data based on YAML configuration.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.services.transformer import TransformerService
from niamoto.common.exceptions import DatabaseQueryError
from niamoto.common.exceptions import (
    ConfigurationError,
    ValidationError,
    DatabaseWriteError,
    DataTransformError,
)


class TestTransformerService:
    """Test suite for TransformerService class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        mock = Mock()
        mock.execute_sql = Mock()
        return mock

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        mock = Mock()
        mock.get_transforms_config.return_value = [
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "plot_ref",
                        "relation": {
                            "plugin": "direct_reference",
                            "key": "plot_ref_id",
                        },
                    }
                ],
                "widgets_data": {
                    "species_count": {
                        "plugin": "count_transformer",
                        "field": "species",
                        "params": {"distinct": True},
                    },
                    "stats": {
                        "plugin": "statistics_transformer",
                        "field": "height",
                        "params": {},
                    },
                },
            },
            {
                "group_by": "taxa",
                "sources": [
                    {
                        "name": "observations",
                        "data": "observations",
                        "grouping": "taxon_ref",
                        "relation": {"plugin": "taxon_loader", "key": "taxon_id"},
                    }
                ],
                "widgets_data": {
                    "distribution": {
                        "plugin": "distribution_transformer",
                        "params": {"bins": 10},
                    }
                },
            },
        ]
        mock.plugins_dir = "/mock/plugins"
        return mock

    @pytest.fixture
    def mock_plugin_loader(self):
        """Create a mock plugin loader."""
        with patch("niamoto.core.services.transformer.PluginLoader") as mock:
            loader_instance = Mock()
            mock.return_value = loader_instance
            yield loader_instance

    @pytest.fixture
    def transformer_service(self, mock_db, mock_config, mock_plugin_loader):
        """Create a TransformerService instance with mocked dependencies."""
        with patch("niamoto.core.services.transformer.Database") as mock_db_class:
            with patch(
                "niamoto.core.services.transformer.EntityRegistry"
            ) as mock_registry:
                mock_db_class.return_value = mock_db
                registry_instance = Mock()
                registry_instance.get.side_effect = DatabaseQueryError(
                    query="registry_lookup", message="missing"
                )
                mock_registry.return_value = registry_instance
                service = TransformerService("mock_db_path", mock_config)
                return service

    def test_initialization(self, mock_db, mock_config, mock_plugin_loader):
        """Test TransformerService initialization."""
        with patch("niamoto.core.services.transformer.Database") as mock_db_class:
            mock_db_class.return_value = mock_db

            with patch(
                "niamoto.core.services.transformer.EntityRegistry"
            ) as mock_registry:
                registry_instance = Mock()
                registry_instance.get.side_effect = DatabaseQueryError(
                    query="registry_lookup", message="missing"
                )
                mock_registry.return_value = registry_instance
                service = TransformerService("mock_db_path", mock_config)

            assert service.db == mock_db
            assert service.config == mock_config
            assert service.transforms_config == mock_config.get_transforms_config()
            assert service.transform_metrics is None

            # Verify plugin loader was initialized and plugins loaded
            mock_plugin_loader.load_core_plugins.assert_called_once()
            mock_plugin_loader.load_project_plugins.assert_called_once_with(
                "/mock/plugins"
            )
            mock_registry.assert_called_once_with(mock_db)

    def test_filter_configs_no_group(self, transformer_service):
        """Test _filter_configs with no group specified."""
        result = transformer_service._filter_configs(None)

        assert result == transformer_service.transforms_config
        assert len(result) == 2

    def test_filter_configs_exact_match(self, transformer_service):
        """Test _filter_configs with exact group match."""
        result = transformer_service._filter_configs("plots")

        assert len(result) == 1
        assert result[0]["group_by"] == "plots"

    def test_filter_configs_case_insensitive_match(self, transformer_service):
        """Test _filter_configs with case-insensitive match."""
        # Mock console to verify warning message
        transformer_service.console = Mock()

        result = transformer_service._filter_configs("PLOTS")

        assert len(result) == 1
        assert result[0]["group_by"] == "plots"
        transformer_service.console.print.assert_called_once()
        assert "Using group 'plots' instead of 'PLOTS'" in str(
            transformer_service.console.print.call_args
        )

    def test_filter_configs_singular_plural_match(self, transformer_service):
        """Test _filter_configs with singular/plural matching."""
        # Mock console to verify warning message
        transformer_service.console = Mock()

        # Test singular form when config has plural
        result = transformer_service._filter_configs("plot")

        assert len(result) == 1
        assert result[0]["group_by"] == "plots"
        assert "Using plural form 'plots' instead of 'plot'" in str(
            transformer_service.console.print.call_args
        )

    def test_filter_configs_no_match(self, transformer_service):
        """Test _filter_configs with no matching group."""
        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service._filter_configs("nonexistent")

        assert "No configuration found for group: nonexistent" in str(exc_info.value)
        assert exc_info.value.config_key == "transforms"
        assert "available_groups" in exc_info.value.details

    def test_filter_configs_no_transforms_config(self, transformer_service):
        """Test _filter_configs when no transforms configuration exists."""
        transformer_service.transforms_config = None

        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service._filter_configs("plots")

        assert "No transforms configuration found" in str(exc_info.value)

    def test_validate_configuration_valid(self, transformer_service):
        """Test validate_configuration with valid config."""
        config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                }
            ]
        }

        # Should not raise any exception
        transformer_service.validate_configuration(config)

    def test_validate_configuration_missing_sources(self, transformer_service):
        """Test validate_configuration with missing sources."""
        config = {}

        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service.validate_configuration(config)

        assert "Missing or empty sources configuration" in str(exc_info.value)
        assert exc_info.value.config_key == "sources"

    def test_validate_configuration_missing_source_fields(self, transformer_service):
        """Test validate_configuration with missing source fields."""
        config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    # Missing "grouping" and "relation"
                }
            ]
        }

        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service.validate_configuration(config)

        assert "Missing required fields in source" in str(exc_info.value)
        assert exc_info.value.config_key == "sources[0]"

    def test_validate_configuration_missing_relation_fields(self, transformer_service):
        """Test validate_configuration with missing relation fields."""
        config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {
                        # Missing "plugin" and "key"
                    },
                }
            ]
        }

        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service.validate_configuration(config)

        assert "Missing required relation fields" in str(exc_info.value)

    def test_validate_configuration_duplicate_source_names(self, transformer_service):
        """Test validate_configuration with duplicate source names."""
        config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                },
                {
                    "name": "occurrences",  # Duplicate name
                    "data": "other_table",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                },
            ]
        }

        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service.validate_configuration(config)

        assert "Duplicate source name" in str(exc_info.value)

    def test_get_group_ids_success(self, transformer_service, mock_db):
        """Test _get_group_ids successful execution."""
        # Mock database response
        mock_db.execute_sql.return_value = [(1,), (2,), (3,)]

        group_config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                }
            ]
        }

        result = transformer_service._get_group_ids(group_config)

        assert result == [1, 2, 3]
        mock_db.execute_sql.assert_called_once()
        sql = mock_db.execute_sql.call_args[0][0]
        assert "SELECT DISTINCT id" in sql
        assert "FROM plot_ref" in sql

    def test_get_group_ids_database_error(self, transformer_service, mock_db):
        """Test _get_group_ids with database error."""
        mock_db.execute_sql.side_effect = Exception("Database error")

        group_config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                }
            ]
        }

        with pytest.raises(DataTransformError) as exc_info:
            transformer_service._get_group_ids(group_config)

        assert "Failed to get group IDs" in str(exc_info.value)

    @patch("pandas.read_csv")
    def test_get_group_data_from_csv(self, mock_read_csv, transformer_service):
        """Test _get_group_data from CSV file."""
        # Mock CSV data
        mock_df = pd.DataFrame({"id": [1, 2, 3], "species": ["A", "B", "C"]})
        mock_read_csv.return_value = mock_df

        group_config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                }
            ]
        }

        result = transformer_service._get_group_data(group_config, "test.csv", 1)

        assert isinstance(result, dict)
        assert "csv_data" in result
        assert isinstance(result["csv_data"], pd.DataFrame)
        assert result["csv_data"].equals(mock_df)
        mock_read_csv.assert_called_once_with("test.csv")

    @patch("niamoto.core.services.transformer.PluginRegistry")
    def test_get_group_data_from_database(
        self, mock_registry, transformer_service, mock_db
    ):
        """Test _get_group_data from database using loader plugin."""
        # Mock loader plugin
        mock_loader_class = Mock()
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        mock_registry.get_plugin.return_value = mock_loader_class

        # Mock loader response
        mock_df = pd.DataFrame({"id": [1, 2, 3], "species": ["A", "B", "C"]})
        mock_loader.load_data.return_value = mock_df

        # Mock database response for reference table
        mock_result = Mock()
        mock_result.returns_rows = True
        mock_result.cursor.description = [("id",), ("name",)]
        mock_result.fetchall.return_value = [(1, "test")]
        mock_db.execute_sql.return_value = mock_result

        group_config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                }
            ]
        }

        result = transformer_service._get_group_data(group_config, None, 1)

        assert isinstance(result, dict)
        assert "occurrences" in result
        assert isinstance(result["occurrences"], pd.DataFrame)
        assert result["occurrences"].equals(mock_df)
        from niamoto.core.plugins.base import PluginType

        mock_registry.get_plugin.assert_called_once_with(
            "direct_reference", PluginType.LOADER
        )
        mock_loader.load_data.assert_called_once()

    @patch("niamoto.core.services.transformer.PluginRegistry")
    def test_get_group_data_multiple_sources(
        self, mock_registry, transformer_service, mock_db
    ):
        """Test _get_group_data with multiple sources."""
        # Mock loader plugins
        mock_loader_class1 = Mock()
        mock_loader1 = Mock()
        mock_loader_class1.return_value = mock_loader1

        mock_loader_class2 = Mock()
        mock_loader2 = Mock()
        mock_loader_class2.return_value = mock_loader2

        mock_registry.get_plugin.side_effect = [mock_loader_class1, mock_loader_class2]

        # Mock loader responses
        mock_df1 = pd.DataFrame({"id": [1, 2], "species": ["A", "B"]})
        mock_df2 = pd.DataFrame({"id": [1, 2], "stat_value": [10, 20]})
        mock_loader1.load_data.return_value = mock_df1
        mock_loader2.load_data.return_value = mock_df2

        group_config = {
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "direct_reference", "key": "plot_ref_id"},
                },
                {
                    "name": "stats",
                    "data": "plot_stats.csv",
                    "grouping": "plot_ref",
                    "relation": {"plugin": "stats_loader", "key": "plot_id"},
                },
            ]
        }

        result = transformer_service._get_group_data(group_config, None, 1)

        assert isinstance(result, dict)
        assert "occurrences" in result
        assert "stats" in result
        assert result["occurrences"].equals(mock_df1)
        assert result["stats"].equals(mock_df2)

    def test_create_group_table_with_recreate(self, transformer_service, mock_db):
        """Test _create_group_table with table recreation."""
        widgets_config = {
            "species_count": {"plugin": "count_transformer"},
            "diversity_index": {"plugin": "diversity_transformer"},
        }

        transformer_service._create_group_table(
            "plots", widgets_config, recreate_table=True
        )

        # Should execute DROP TABLE and CREATE TABLE
        assert mock_db.execute_sql.call_count == 2

        # First call should be DROP TABLE
        drop_call = mock_db.execute_sql.call_args_list[0][0][0]
        assert "DROP TABLE IF EXISTS plots" in drop_call

        # Second call should be CREATE TABLE
        create_call = mock_db.execute_sql.call_args_list[1][0][0]
        assert "CREATE TABLE IF NOT EXISTS plots" in create_call
        assert "plots_id BIGINT PRIMARY KEY" in create_call
        assert "species_count JSON" in create_call
        assert "diversity_index JSON" in create_call

    def test_create_group_table_without_recreate(self, transformer_service, mock_db):
        """Test _create_group_table without table recreation."""
        widgets_config = {"species_count": {"plugin": "count_transformer"}}

        transformer_service._create_group_table(
            "plots", widgets_config, recreate_table=False
        )

        # Should only execute CREATE TABLE
        assert mock_db.execute_sql.call_count == 1
        create_call = mock_db.execute_sql.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS plots" in create_call

    def test_create_group_table_error(self, transformer_service, mock_db):
        """Test _create_group_table with database error."""
        mock_db.execute_sql.side_effect = Exception("Database error")

        widgets_config = {"test": {"plugin": "test"}}

        with pytest.raises(DataTransformError) as exc_info:
            transformer_service._create_group_table("plots", widgets_config)

        assert "Failed to create table for group plots" in str(exc_info.value)

    def test_save_widget_results_success(self, transformer_service, mock_db):
        """Test _save_widget_results with various data types."""
        results = {
            "int_value": 42,
            "float_value": 3.14,
            "str_value": "test",
            "dict_value": {"key": "value", "count": 10},
            "list_value": [1, 2, 3],
            "none_value": None,
            "numpy_int": np.int64(100),
            "numpy_float": np.float64(2.718),
            "numpy_array": [
                1,
                2,
                3,
            ],  # Arrays should be passed as lists, not numpy arrays
            "numpy_scalar": np.float32(1.5),  # Single numpy scalar
        }

        transformer_service._save_widget_results("plots", 1, results)

        # Verify SQL execution
        mock_db.execute_sql.assert_called_once()
        sql, params = mock_db.execute_sql.call_args[0]

        # Check SQL structure
        assert "INSERT INTO plots" in sql
        assert "ON CONFLICT (plots_id)" in sql
        assert "DO UPDATE SET" in sql

        # Check parameters
        assert params["plots_id"] == 1
        assert params["int_value"] == "42"
        assert params["float_value"] == "3.14"
        assert params["str_value"] == "test"
        # JSON values should be serialized
        assert json.loads(params["dict_value"]) == {"key": "value", "count": 10}
        assert json.loads(params["list_value"]) == [1, 2, 3]
        assert params["none_value"] is None
        # Numpy scalars should be converted to Python types
        assert isinstance(params["numpy_int"], int) and params["numpy_int"] == 100
        assert (
            isinstance(params["numpy_float"], float)
            and abs(params["numpy_float"] - 2.718) < 0.0001
        )
        assert (
            isinstance(params["numpy_scalar"], float)
            and abs(params["numpy_scalar"] - 1.5) < 0.0001
        )
        # Regular array should be JSON serialized
        assert json.loads(params["numpy_array"]) == [1, 2, 3]

    def test_save_widget_results_no_results(self, transformer_service):
        """Test _save_widget_results with no results."""
        with pytest.raises(ValidationError) as exc_info:
            transformer_service._save_widget_results("plots", 1, {})

        assert "No results to save" in str(exc_info.value)

    def test_save_widget_results_database_error(self, transformer_service, mock_db):
        """Test _save_widget_results with database error."""
        mock_db.execute_sql.side_effect = SQLAlchemyError("Database error")

        results = {"test": "value"}

        with pytest.raises(DatabaseWriteError) as exc_info:
            transformer_service._save_widget_results("plots", 1, results)

        assert "Failed to save results for group 1" in str(exc_info.value)

    def test_save_widget_results_json_encode_error(self, transformer_service, mock_db):
        """Test _save_widget_results with JSON encoding error."""

        # Create an object that can't be JSON serialized
        class NonSerializable:
            pass

        # The service converts objects to strings by default, so we need a dict/list with non-serializable
        results = {"bad_value": {"nested": NonSerializable()}}

        with pytest.raises(DataTransformError) as exc_info:
            transformer_service._save_widget_results("plots", 1, results)

        assert "Failed to encode results for group 1" in str(exc_info.value)

    @patch("niamoto.core.services.transformer.CLI_CONTEXT", False)
    def test_transform_data_simple_mode(self, transformer_service, mock_db):
        """Test transform_data in simple mode (no CLI context)."""
        # Mock group IDs
        mock_db.execute_sql.return_value = [(1,), (2,)]

        # Mock plugin registry and transformer
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"count": 5}

        with patch("niamoto.core.services.transformer.PluginRegistry") as mock_registry:
            mock_registry.get_plugin.return_value = (
                lambda db, registry=None: mock_transformer
            )

            with patch.object(transformer_service, "_get_group_data") as mock_get_data:
                mock_get_data.return_value = pd.DataFrame(
                    {"id": [1, 2], "species": ["A", "B"]}
                )

                result = transformer_service.transform_data(group_by="plots")

        assert "plots" in result
        assert result["plots"]["total_items"] == 2
        assert result["plots"]["widgets_generated"] == 4  # 2 widgets * 2 groups
        assert "start_time" in result["plots"]
        assert "end_time" in result["plots"]

    @patch("niamoto.core.services.transformer.CLI_CONTEXT", True)
    @patch("niamoto.core.services.transformer.ProgressManager")
    @patch("niamoto.core.services.transformer.OperationMetrics")
    def test_transform_data_with_progress(
        self, mock_metrics_class, mock_progress_class, transformer_service, mock_db
    ):
        """Test transform_data with CLI progress display."""
        # Mock metrics
        mock_metrics = Mock()
        mock_metrics_class.return_value = mock_metrics

        # Mock progress manager
        mock_progress = Mock()
        mock_progress_ctx = Mock()
        mock_progress_ctx.__enter__ = Mock(return_value=mock_progress)
        mock_progress_ctx.__exit__ = Mock(return_value=None)
        mock_progress.progress_context.return_value = mock_progress_ctx
        mock_progress._start_time = datetime.now()
        mock_progress_class.return_value = mock_progress

        # Mock group IDs
        mock_db.execute_sql.return_value = [(1,)]

        # Mock transformer
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"count": 5}

        with patch("niamoto.core.services.transformer.PluginRegistry") as mock_registry:
            mock_registry.get_plugin.return_value = (
                lambda db, registry=None: mock_transformer
            )

            with patch.object(transformer_service, "_get_group_data") as mock_get_data:
                mock_get_data.return_value = pd.DataFrame({"id": [1], "species": ["A"]})

                transformer_service.use_cli_integration = True

                transformer_service.transform_data(group_by="plots")

        # Verify metrics were tracked
        mock_metrics.add_metric.assert_called()
        mock_metrics.finish.assert_called_once()

        # Verify progress was tracked
        mock_progress.add_task.assert_called()
        mock_progress.update_task.assert_called()
        mock_progress.complete_task.assert_called()

    def test_transform_data_with_widget_error(self, transformer_service, mock_db):
        """Test transform_data when a widget transformation fails."""
        # Mock group IDs
        mock_db.execute_sql.return_value = [(1,)]

        # Mock transformer that fails
        mock_transformer = Mock()
        mock_transformer.transform.side_effect = Exception("Widget error")

        with patch("niamoto.core.services.transformer.PluginRegistry") as mock_registry:
            mock_registry.get_plugin.return_value = (
                lambda db, registry=None: mock_transformer
            )

            with patch.object(transformer_service, "_get_group_data") as mock_get_data:
                mock_get_data.return_value = pd.DataFrame({"id": [1], "species": ["A"]})

                # Should not raise, but log the error
                result = transformer_service.transform_data(group_by="plots")

        # Result should still be returned even with widget errors
        assert "plots" in result
        assert (
            result["plots"]["widgets_generated"] == 0
        )  # No widgets successfully generated

    def test_transform_data_no_config_found(self, transformer_service):
        """Test transform_data when no configuration is found."""
        transformer_service.transforms_config = None

        with pytest.raises(ConfigurationError) as exc_info:
            transformer_service.transform_data()

        assert "No transforms configuration found" in str(exc_info.value)

    def test_transform_data_with_csv_file(self, transformer_service, mock_db):
        """Test transform_data with CSV file input."""
        # Mock group IDs
        mock_db.execute_sql.return_value = [(1,)]

        # Mock transformer
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"count": 5}

        with patch("niamoto.core.services.transformer.PluginRegistry") as mock_registry:
            mock_registry.get_plugin.return_value = (
                lambda db, registry=None: mock_transformer
            )

            with patch("pandas.read_csv") as mock_read_csv:
                mock_read_csv.return_value = pd.DataFrame({"id": [1], "species": ["A"]})

                result = transformer_service.transform_data(
                    group_by="plots", csv_file="test.csv"
                )

        # Verify CSV was used
        mock_read_csv.assert_called_with("test.csv")
        assert "plots" in result

    def test_complex_numpy_conversion(self, transformer_service, mock_db):
        """Test _save_widget_results with complex numpy data structures."""
        results = {
            "nested_numpy": {
                "array": np.array([[1, 2], [3, 4]]),
                "scalar": np.float32(1.5),
                "nested_dict": {"values": [np.int32(10), np.int64(20)]},
            }
        }

        transformer_service._save_widget_results("plots", 1, results)

        # Verify the data was properly converted
        sql, params = mock_db.execute_sql.call_args[0]
        nested_data = json.loads(params["nested_numpy"])

        assert nested_data["array"] == [[1, 2], [3, 4]]
        assert nested_data["scalar"] == 1.5
        assert nested_data["nested_dict"]["values"] == [10, 20]

    @pytest.mark.parametrize(
        "group_name,search_term,expected_match",
        [
            ("plots", "plot", True),  # Singular/plural
            ("taxa", "taxas", True),  # Plural/singular
            ("PLOTS", "plots", True),  # Case insensitive
            ("plot_data", "plot-data", False),  # No match for different separators
        ],
    )
    def test_filter_configs_various_matches(
        self, transformer_service, group_name, search_term, expected_match
    ):
        """Test _filter_configs with various matching scenarios."""
        # Add test config
        transformer_service.transforms_config = [
            {
                "group_by": group_name,
                "sources": [
                    {
                        "name": "test",
                        "data": "test",
                        "grouping": "test",
                        "relation": {"plugin": "test", "key": "id"},
                    }
                ],
            }
        ]

        if expected_match:
            result = transformer_service._filter_configs(search_term)
            assert len(result) == 1
        else:
            with pytest.raises(ConfigurationError):
                transformer_service._filter_configs(search_term)


@pytest.mark.integration
class TestTransformerServiceIntegration:
    """Integration tests for TransformerService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        mock = Mock()
        mock.execute_sql = Mock()
        return mock

    @pytest.fixture
    def real_config(self):
        """Create a realistic configuration."""
        mock = Mock()
        mock.get_transforms_config.return_value = [
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "plot_ref",
                        "relation": {
                            "plugin": "direct_reference",
                            "key": "plot_ref_id",
                        },
                    }
                ],
                "widgets_data": {
                    "species_richness": {
                        "plugin": "count_transformer",
                        "field": "species",
                        "params": {"distinct": True},
                    },
                    "basal_area": {
                        "plugin": "sum_transformer",
                        "field": "dbh",
                        "params": {"formula": "pi * (dbh/200)^2"},
                    },
                },
            }
        ]
        mock.plugins_dir = "/tmp/plugins"
        return mock

    def test_full_transformation_workflow(self, mock_db, real_config, tmp_path):
        """Test complete transformation workflow."""
        # Mock result for reference table queries
        mock_ref_result = Mock()
        mock_ref_result.returns_rows = True
        mock_ref_result.cursor.description = [("id",), ("name",)]
        mock_ref_result.fetchall.return_value = [(1, "plot1"), (2, "plot2")]

        def execute_sql_side_effect(sql, params=None, fetch=False, fetch_all=False):
            if "SELECT DISTINCT id" in sql:
                return [(1,), (2,)]
            if sql.strip().startswith("SELECT * FROM plot_ref"):
                return mock_ref_result
            return None

        mock_db.execute_sql.side_effect = execute_sql_side_effect

        # Mock plugin registry
        with patch("niamoto.core.services.transformer.PluginRegistry") as mock_registry:
            # Mock loader
            mock_loader_class = Mock()
            mock_loader = Mock()
            mock_loader_class.return_value = mock_loader
            mock_loader.load_data.side_effect = [
                pd.DataFrame({"species": ["A", "B"], "dbh": [10, 20]}),
                pd.DataFrame({"species": ["C", "D", "E"], "dbh": [15, 25, 30]}),
            ]

            # Mock transformers
            mock_count_transformer = Mock()
            mock_count_transformer.transform.side_effect = [{"count": 2}, {"count": 3}]

            mock_sum_transformer = Mock()
            mock_sum_transformer.transform.side_effect = [
                {"sum": 0.0157},
                {"sum": 0.0442},
            ]

            def get_plugin_side_effect(name, plugin_type):
                if name == "direct_reference":
                    return mock_loader_class
                elif name == "count_transformer":
                    return lambda db, registry=None: mock_count_transformer
                elif name == "sum_transformer":
                    return lambda db, registry=None: mock_sum_transformer

            mock_registry.get_plugin.side_effect = get_plugin_side_effect

            with patch("niamoto.core.services.transformer.PluginLoader"):
                with patch(
                    "niamoto.core.services.transformer.EntityRegistry"
                ) as mock_registry_cls:
                    registry_instance = Mock()
                    registry_instance.get.side_effect = DatabaseQueryError(
                        query="registry_lookup", message="missing"
                    )
                    mock_registry_cls.return_value = registry_instance

                    with patch(
                        "niamoto.core.services.transformer.Database"
                    ) as mock_db_class:
                        mock_db_class.return_value = mock_db

                        db_path = str(tmp_path / "test.db")
                        service = TransformerService(db_path, real_config)
                        result = service.transform_data(group_by="plots")

        # Verify results
        assert "plots" in result
        assert result["plots"]["total_items"] == 2
        assert result["plots"]["widgets_generated"] == 4  # 2 widgets * 2 groups
        assert result["plots"]["widgets"]["species_richness"] == 2
        assert result["plots"]["widgets"]["basal_area"] == 2
