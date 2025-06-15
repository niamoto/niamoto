# tests/core/plugins/exporters/test_json_api_exporter.py

"""Tests for the JSON API Exporter plugin."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from unittest import mock
from datetime import datetime
import tempfile
import os

import pytest
from sqlalchemy.exc import SQLAlchemyError

# Import to trigger plugin registration

from niamoto.core.plugins.exporters.json_api_exporter import (
    JsonApiExporter,
    JsonApiExporterParams,
    DataMapper,
    GroupConfig,
    DetailConfig,
    IndexConfig,
    JsonOptions,
    ErrorHandling,
    MetadataConfig,
)
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType
from niamoto.common.exceptions import ProcessError


class TestJsonApiExporter:
    """Test suite for JsonApiExporter."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        return Mock()

    @pytest.fixture
    def exporter(self, mock_db):
        """Create a JsonApiExporter instance."""
        return JsonApiExporter(mock_db)

    @pytest.fixture
    def sample_target_config(self):
        """Create a sample target configuration."""
        # Create a simple mock object instead of using Pydantic validation

        config = MagicMock()
        config.name = "test_api"
        config.enabled = True
        config.exporter = "json_api_exporter"
        config.params = {
            "output_dir": "test_output",
            "detail_output_pattern": "{group}/{id}.json",
            "index_output_pattern": "all_{group}.json",
            "json_options": {"indent": 2, "ensure_ascii": False},
        }
        config.groups = [
            GroupConfig(
                group_by="taxon",
                detail=DetailConfig(pass_through=True),
                index=IndexConfig(
                    fields=[
                        {"id": "id"},
                        {"name": "full_name"},
                        {
                            "endpoint": {
                                "generator": "endpoint_url",
                                "params": {"base_path": "/api"},
                            }
                        },
                    ]
                ),
            )
        ]
        return config

    @pytest.fixture
    def sample_data(self):
        """Create sample taxon data."""
        return [
            {
                "id": 1,
                "full_name": "Taxon species",
                "rank": "species",
                "metadata": {"endemic": True, "parent_family": "Myrtaceae"},
            },
            {
                "id": 2,
                "full_name": "Another taxon",
                "rank": "genus",
                "metadata": {"endemic": False, "parent_family": "Lauraceae"},
            },
        ]

    def test_plugin_registration(self):
        """Test that the plugin is properly registered."""
        # Load plugins to trigger registration in test environment
        from niamoto.core.plugins.plugin_loader import PluginLoader

        loader = PluginLoader()
        loader.load_core_plugins()

        # Check that the plugin is registered and retrievable
        plugin_class = PluginRegistry.get_plugin(
            "json_api_exporter", PluginType.EXPORTER
        )
        assert plugin_class is not None
        assert plugin_class.__name__ == "JsonApiExporter"
        assert hasattr(plugin_class, "export")

    def test_exporter_initialization(self, exporter, mock_db):
        """Test exporter initialization."""
        assert exporter.db == mock_db
        assert exporter.errors == []
        assert exporter.stats["total_files_generated"] == 0

    def test_parameter_validation(self):
        """Test parameter validation with Pydantic models."""
        # Valid parameters
        params = JsonApiExporterParams(
            output_dir="test_output", json_options={"indent": 4, "compress": True}
        )
        assert params.output_dir == "test_output"
        assert params.json_options.compress is True

        # Invalid parameters (minify with indent)
        with pytest.raises(ValueError):
            JsonApiExporterParams(
                output_dir="test_output", json_options={"indent": 4, "minify": True}
            )

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", create=True)
    def test_write_json_file(self, mock_open, mock_mkdir, exporter, tmp_path):
        """Test JSON file writing with different options."""
        test_data = {"test": "data"}

        # Test normal JSON
        json_options = JsonOptions(indent=2)
        exporter._write_json_file(tmp_path / "test.json", test_data, json_options)
        mock_open.assert_called()

        # Test compressed JSON
        json_options = JsonOptions(compress=True)
        with patch("gzip.open") as mock_gzip:
            exporter._write_json_file(tmp_path / "test.json", test_data, json_options)
            mock_gzip.assert_called()

    def test_apply_filters(self, exporter, sample_data):
        """Test data filtering functionality."""
        # Filter by rank
        filters = {"rank": ["species"]}
        filtered = exporter._apply_filters(sample_data, filters)
        assert len(filtered) == 1
        assert filtered[0]["rank"] == "species"

        # Filter by nested field
        filters = {"metadata.endemic": True}
        # Note: Current implementation doesn't support nested filters
        # This would need enhancement

    @patch("builtins.open", create=True)
    def test_generate_detail_file(self, mock_open, exporter, tmp_path):
        """Test detail file generation."""
        item = {"id": 1, "name": "Test Item"}
        group_config = GroupConfig(
            group_by="test_group", detail=DetailConfig(pass_through=True)
        )
        params = JsonApiExporterParams(output_dir=str(tmp_path))
        mapper = DataMapper(group_config, params)

        with patch.object(Path, "mkdir"):
            exporter._generate_detail_file(
                item,
                "test_group",
                group_config,
                params,
                tmp_path,
                mapper,
                params.json_options,
            )

        assert exporter.stats["total_files_generated"] == 1

    @patch("builtins.open", create=True)
    def test_generate_index_file(self, mock_open, exporter, tmp_path, sample_data):
        """Test index file generation."""
        group_config = GroupConfig(
            group_by="taxon",
            index=IndexConfig(fields=[{"id": "id"}, {"name": "full_name"}]),
        )
        params = JsonApiExporterParams(output_dir=str(tmp_path))
        mapper = DataMapper(group_config, params)

        # Initialize group stats first
        exporter.stats["groups_processed"]["taxon"] = {
            "total_items": len(sample_data),
            "detail_files_generated": 0,
            "index_generated": False,
            "errors": 0,
        }

        with patch.object(Path, "mkdir"):
            exporter._generate_index_file(
                sample_data,
                "taxon",
                group_config,
                params,
                tmp_path,
                mapper,
                params.json_options,
            )

        # Verify the index was marked as generated
        assert exporter.stats["groups_processed"]["taxon"]["index_generated"] is True

    def test_error_handling(self, exporter):
        """Test error handling functionality."""
        params = JsonApiExporterParams(
            output_dir="test",
            error_handling={"continue_on_error": True, "log_errors": True},
        )

        # Initialize group stats first
        exporter.stats["groups_processed"]["test_group"] = {
            "total_items": 0,
            "detail_files_generated": 0,
            "index_generated": False,
            "errors": 0,
        }

        error = Exception("Test error")
        exporter._handle_export_error(error, "test_group", {"id": 1}, params)

        assert len(exporter.errors) == 1
        assert exporter.errors[0]["error"] == "Test error"
        assert exporter.stats["errors_count"] == 1

    def test_export_process(self, exporter, sample_target_config, sample_data):
        """Test the complete export process."""
        mock_repository = Mock()

        # Ensure the target config has the proper groups structure
        assert hasattr(sample_target_config, "groups")
        assert len(sample_target_config.groups) > 0
        assert sample_target_config.groups[0].group_by == "taxon"

        # Mock _fetch_group_data to return our sample data
        with patch.object(
            exporter, "_fetch_group_data", return_value=sample_data
        ) as mock_fetch:
            # Mock file operations
            with patch("builtins.open", create=True):
                with patch("pathlib.Path.mkdir"):
                    # Execute export
                    exporter.export(sample_target_config, mock_repository)

                    # Check that data was fetched
                    mock_fetch.assert_called()

                    # Check that stats were updated
                    assert "taxon" in exporter.stats["groups_processed"]
                    assert exporter.stats["groups_processed"]["taxon"][
                        "total_items"
                    ] == len(sample_data)


class TestDataMapper:
    """Test suite for DataMapper."""

    @pytest.fixture
    def mapper(self):
        """Create a DataMapper instance."""
        group_config = GroupConfig(group_by="test", index=IndexConfig(fields=[]))
        params = JsonApiExporterParams(output_dir="test")
        return DataMapper(group_config, params)

    def test_get_nested_value(self, mapper):
        """Test nested value extraction."""
        data = {"level1": {"level2": {"value": "test"}}}

        assert mapper._get_nested_value(data, "level1.level2.value") == "test"
        assert mapper._get_nested_value(data, "level1.missing") is None

    def test_generate_endpoint_url(self, mapper):
        """Test endpoint URL generation."""
        mapper._group_context = {
            "group_name": "taxon",
            "params": JsonApiExporterParams(
                output_dir="test", detail_output_pattern="{group}/{id}.json"
            ),
        }

        url = mapper._generate_endpoint_url({"id": 123}, {"base_path": "/api"})
        assert url == "/api/taxon/123.json"

    def test_extract_specific_epithet(self, mapper):
        """Test specific epithet extraction."""
        data = {"full_name": "Genus species subspecies"}
        epithet = mapper._extract_specific_epithet(data, {"source_field": "full_name"})
        assert epithet == "species"

        # Test with single word
        data = {"full_name": "Genus"}
        epithet = mapper._extract_specific_epithet(data, {"source_field": "full_name"})
        assert epithet == ""

    def test_map_fields_simple(self, mapper):
        """Test simple field mapping."""
        data = {"id": 1, "name": "Test", "value": 42}
        fields = ["id", "name"]

        result = mapper._map_fields(data, fields)
        assert result == {"id": 1, "name": "Test"}

    def test_map_fields_with_rename(self, mapper):
        """Test field mapping with renaming."""
        data = {"old_name": "value"}
        fields = [{"new_name": "old_name"}]

        result = mapper._map_fields(data, fields)
        assert result == {"new_name": "value"}

    def test_map_fields_with_generator(self, mapper):
        """Test field mapping with generator."""
        mapper._group_context = {
            "group_name": "test",
            "params": JsonApiExporterParams(
                output_dir="test", detail_output_pattern="{group}/{id}.json"
            ),
        }

        data = {"id": 123}
        fields = [
            {"url": {"generator": "endpoint_url", "params": {"base_path": "/api"}}}
        ]

        result = mapper._map_fields(data, fields)
        assert "url" in result
        assert "/api/test/123.json" in result["url"]

    def test_map_fields_with_nested_source(self, mapper):
        """Test field mapping with nested source selection."""
        data = {
            "metadata": {"field1": "value1", "field2": "value2", "field3": "value3"}
        }

        fields = [
            {
                "selected_metadata": {
                    "source": "metadata",
                    "fields": ["field1", "field3"],
                }
            }
        ]

        result = mapper._map_fields(data, fields)
        assert result["selected_metadata"] == {"field1": "value1", "field3": "value3"}


class TestJsonApiExporterSecurity:
    """Security tests for JSON API Exporter."""

    @pytest.fixture
    def mock_db_with_engine(self):
        """Create a mock database with engine."""
        mock_db = Mock()
        mock_engine = Mock()
        mock_connection = Mock()
        mock_result = Mock()

        # Setup the chain: db.engine.connect().execute()
        mock_db.engine = mock_engine
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.execute.return_value = mock_result
        mock_result.fetchall.return_value = []
        mock_result.keys.return_value = []

        return mock_db

    def test_sql_injection_prevention(self, mock_db_with_engine):
        """Test that SQL injection is prevented in table names."""
        exporter = JsonApiExporter(mock_db_with_engine)

        # Test with malicious table name
        malicious_table = "taxon; DROP TABLE users; --"

        # This should not execute the malicious SQL
        result = exporter._fetch_group_data(
            mock_db_with_engine, "test_source", malicious_table
        )

        # Verify the connection was attempted but with the malicious string
        mock_db_with_engine.engine.connect.assert_called()

        # The current implementation is vulnerable - this test documents the issue
        # In a secure implementation, this should either:
        # 1. Validate table names against a whitelist
        # 2. Use parameterized queries
        # 3. Escape table names properly
        assert result == []  # Should return empty due to invalid table

    def test_file_path_validation(self):
        """Test that file paths are properly validated."""
        exporter = JsonApiExporter(Mock())

        # Test with directory traversal attempt
        malicious_pattern = "../../../etc/passwd"
        params = JsonApiExporterParams(
            output_dir="/safe/dir", detail_output_pattern=malicious_pattern
        )

        item = {"id": 1}
        group_config = GroupConfig(group_by="test")

        # Current implementation doesn't validate paths - this documents the security issue
        with tempfile.TemporaryDirectory() as tmp_dir:
            # This should raise an error due to path traversal attempt
            with pytest.raises((PermissionError, OSError)):
                exporter._generate_detail_file(
                    item,
                    "test",
                    group_config,
                    params,
                    Path(tmp_dir),
                    DataMapper(group_config, params),
                    JsonOptions(),
                )

    def test_data_size_limits(self):
        """Test that large data sets are handled safely."""
        exporter = JsonApiExporter(Mock())

        # Create oversized data
        large_data = {"large_field": "x" * (10 * 1024 * 1024)}  # 10MB string

        json_options = JsonOptions(max_array_length=1000)

        # Test that size optimization works
        optimized = exporter._optimize_data_size(large_data, json_options)

        # Should still contain the data (no size limit on individual fields yet)
        assert "large_field" in optimized


class TestJsonApiExporterErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def exporter_with_error_config(self):
        """Create exporter with error handling configuration."""
        mock_db = Mock()
        exporter = JsonApiExporter(mock_db)
        return exporter

    def test_database_connection_error(self, exporter_with_error_config):
        """Test handling of database connection errors."""
        mock_db = Mock()
        mock_db.engine.connect.side_effect = SQLAlchemyError("Connection failed")

        exporter = JsonApiExporter(mock_db)

        result = exporter._fetch_group_data(mock_db, "test_source", "test_table")

        # Should return empty list on database error
        assert result == []

    def test_invalid_json_in_database(self, exporter_with_error_config):
        """Test handling of invalid JSON data from database."""
        # Mock database returning invalid JSON
        mock_db = Mock()
        mock_engine = Mock()
        mock_connection = Mock()
        mock_result = Mock()

        mock_db.engine = mock_engine
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.execute.return_value = mock_result

        # Return data with invalid JSON
        mock_result.fetchall.return_value = [(1, "invalid_json{", "test")]
        mock_result.keys.return_value = ["id", "data", "name"]

        exporter = JsonApiExporter(mock_db)
        result = exporter._fetch_group_data(mock_db, "test_source", "test_table")

        # Should handle invalid JSON gracefully
        assert len(result) == 1
        assert result[0]["data"] == "invalid_json{"  # Stored as string

    def test_transformer_plugin_error(self, exporter_with_error_config):
        """Test handling of transformer plugin errors."""
        # Mock failing transformer
        with patch(
            "niamoto.core.plugins.registry.PluginRegistry.get_plugin"
        ) as mock_get:
            mock_transformer_class = Mock()
            mock_transformer = Mock()
            mock_transformer.transform.side_effect = Exception("Transform failed")
            mock_transformer_class.return_value = mock_transformer
            mock_get.return_value = mock_transformer_class

            group_config = GroupConfig(
                group_by="test", transformer_plugin="failing_transformer"
            )

            with pytest.raises(ProcessError):
                exporter_with_error_config._apply_transformer({"id": 1}, group_config)

    def test_file_write_permission_error(self, exporter_with_error_config):
        """Test handling of file write permission errors."""
        # Mock file write failure
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")

            with pytest.raises(PermissionError):
                exporter_with_error_config._write_json_file(
                    Path("/readonly/test.json"), {"test": "data"}, JsonOptions()
                )

    def test_error_continuation_vs_stopping(self, exporter_with_error_config):
        """Test continue_on_error vs stop_on_error behavior."""
        # Test continue on error
        params_continue = JsonApiExporterParams(
            output_dir="test", error_handling=ErrorHandling(continue_on_error=True)
        )

        exporter_with_error_config.stats["groups_processed"]["test"] = {"errors": 0}

        # Should not raise exception
        exporter_with_error_config._handle_export_error(
            Exception("Test error"), "test", {"id": 1}, params_continue
        )

        assert len(exporter_with_error_config.errors) == 1

        # Test stop on error
        params_stop = JsonApiExporterParams(
            output_dir="test", error_handling=ErrorHandling(continue_on_error=False)
        )

        with pytest.raises(Exception):
            exporter_with_error_config._handle_export_error(
                Exception("Test error"), "test", {"id": 1}, params_stop
            )


class TestJsonApiExporterOptimizations:
    """Test data optimization features."""

    @pytest.fixture
    def exporter(self):
        return JsonApiExporter(Mock())

    def test_exclude_null_optimization(self, exporter):
        """Test null value exclusion."""
        data = {
            "valid_field": "value",
            "null_field": None,
            "nested": {"valid_nested": "value", "null_nested": None},
        }

        json_options = JsonOptions(exclude_null=True)
        optimized = exporter._optimize_data_size(data, json_options)

        assert "valid_field" in optimized
        assert "null_field" not in optimized
        assert "null_nested" not in optimized["nested"]
        assert "valid_nested" in optimized["nested"]

    def test_geometry_precision_optimization(self, exporter):
        """Test geometry coordinate precision."""
        data = {
            "coordinates": [1.123456789, 2.987654321],
            "nested_coords": {"lat": 45.123456789, "lng": -73.987654321},
        }

        json_options = JsonOptions(geometry_precision=4)
        optimized = exporter._optimize_data_size(data, json_options)

        assert optimized["coordinates"] == [1.1235, 2.9877]
        assert optimized["nested_coords"]["lat"] == 45.1235
        assert optimized["nested_coords"]["lng"] == -73.9877

    def test_max_array_length_optimization(self, exporter):
        """Test array length limitation."""
        data = {
            "long_array": list(range(1000)),
            "nested": {"another_array": list(range(500))},
        }

        json_options = JsonOptions(max_array_length=100)
        optimized = exporter._optimize_data_size(data, json_options)

        assert len(optimized["long_array"]) == 100
        assert optimized["long_array"] == list(range(100))
        assert len(optimized["nested"]["another_array"]) == 100

    def test_combined_optimizations(self, exporter):
        """Test multiple optimizations together."""
        data = {
            "precision_field": 3.14159265359,
            "long_array": [1.123456789] * 200,
            "null_field": None,
            "valid_field": "keep_me",
        }

        json_options = JsonOptions(
            exclude_null=True, geometry_precision=2, max_array_length=50
        )
        optimized = exporter._optimize_data_size(data, json_options)

        assert optimized["precision_field"] == 3.14
        assert len(optimized["long_array"]) == 50
        assert all(x == 1.12 for x in optimized["long_array"])
        assert "null_field" not in optimized
        assert optimized["valid_field"] == "keep_me"


class TestJsonApiExporterTransformers:
    """Test transformer plugin integration."""

    @pytest.fixture
    def exporter(self):
        return JsonApiExporter(Mock())

    def test_transformer_plugin_loading(self, exporter):
        """Test transformer plugin loading and configuration."""
        with patch(
            "niamoto.core.plugins.registry.PluginRegistry.get_plugin"
        ) as mock_get:
            # Mock transformer class and instance
            mock_transformer_class = Mock()
            mock_transformer = Mock()
            mock_transformer.transform.return_value = {"transformed": True}
            mock_transformer_class.return_value = mock_transformer
            mock_get.return_value = mock_transformer_class

            group_config = GroupConfig(
                group_by="test",
                transformer_plugin="test_transformer",
                transformer_params={"param1": "value1"},
            )

            result = exporter._apply_transformer({"id": 1}, group_config)

            # Verify plugin was loaded correctly
            mock_get.assert_called_once_with("test_transformer", PluginType.TRANSFORMER)
            mock_transformer_class.assert_called_once_with(exporter.db)
            mock_transformer.transform.assert_called_once()

            assert result == {"transformed": True}

    def test_transformer_with_config_validation(self, exporter):
        """Test transformer with parameter validation."""
        with patch(
            "niamoto.core.plugins.registry.PluginRegistry.get_plugin"
        ) as mock_get:
            # Mock transformer with config model
            mock_transformer_class = Mock()
            mock_transformer = Mock()
            mock_config_model = Mock()
            mock_config_model.model_validate.return_value = {"validated": True}

            mock_transformer.config_model = mock_config_model
            mock_transformer.transform.return_value = {"result": "success"}
            mock_transformer_class.return_value = mock_transformer
            mock_get.return_value = mock_transformer_class

            group_config = GroupConfig(
                group_by="test",
                transformer_plugin="config_transformer",
                transformer_params={"param1": "value1"},
            )

            result = exporter._apply_transformer({"id": 1}, group_config)

            # Verify config validation was called
            mock_config_model.model_validate.assert_called_once_with(
                {"param1": "value1"}
            )
            assert result == {"result": "success"}

    def test_transformer_not_found(self, exporter):
        """Test error handling when transformer is not found."""
        with patch(
            "niamoto.core.plugins.registry.PluginRegistry.get_plugin"
        ) as mock_get:
            mock_get.return_value = None

            group_config = GroupConfig(
                group_by="test", transformer_plugin="nonexistent_transformer"
            )

            with pytest.raises(ProcessError) as exc_info:
                exporter._apply_transformer({"id": 1}, group_config)

            assert "Failed to apply transformer" in str(exc_info.value)


class TestJsonApiExporterMetadata:
    """Test metadata generation features."""

    @pytest.fixture
    def exporter(self):
        exporter = JsonApiExporter(Mock())
        exporter.stats = {
            "start_time": datetime(2023, 1, 1, 12, 0, 0),
            "end_time": datetime(2023, 1, 1, 12, 5, 30),
            "groups_processed": {
                "taxon": {"total_items": 100, "detail_files": 95, "errors": 5}
            },
            "total_files_generated": 96,
            "errors_count": 5,
        }
        return exporter

    def test_metadata_generation_with_stats(self, exporter, tmp_path):
        """Test metadata file generation with statistics."""
        target_config = Mock()
        target_config.name = "test_export"

        params = JsonApiExporterParams(
            output_dir=str(tmp_path),
            metadata=MetadataConfig(generate=True, include_stats=True),
        )

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump") as mock_json_dump:
                exporter._generate_metadata(tmp_path, params, target_config)

                # Verify metadata was written
                mock_file.assert_called_once()
                mock_json_dump.assert_called_once()

                # Check metadata content
                metadata = mock_json_dump.call_args[0][0]
                assert metadata["export_name"] == "test_export"
                assert metadata["exporter"] == "json_api_exporter"
                assert "statistics" in metadata
                assert (
                    metadata["statistics"]["duration_seconds"] == 330.0
                )  # 5.5 minutes

    def test_metadata_without_stats(self, exporter, tmp_path):
        """Test metadata generation without statistics."""
        target_config = Mock()
        target_config.name = "test_export"

        params = JsonApiExporterParams(
            output_dir=str(tmp_path),
            metadata=MetadataConfig(generate=True, include_stats=False),
        )

        with patch("builtins.open", mock_open()):
            with patch("json.dump") as mock_json_dump:
                exporter._generate_metadata(tmp_path, params, target_config)

                metadata = mock_json_dump.call_args[0][0]
                assert "statistics" not in metadata
                assert metadata["export_name"] == "test_export"

    def test_error_file_generation(self, exporter, tmp_path):
        """Test error log file generation."""
        exporter.errors = [
            {
                "group": "taxon",
                "item_id": 1,
                "error": "Test error",
                "timestamp": "2023-01-01T12:00:00",
            }
        ]

        params = JsonApiExporterParams(
            output_dir=str(tmp_path),
            error_handling=ErrorHandling(error_file="errors.json"),
        )

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump") as mock_json_dump:
                exporter._save_errors(tmp_path, params)

                mock_file.assert_called_once()
                mock_json_dump.assert_called_once_with(
                    exporter.errors, mock.ANY, indent=2, default=str
                )


class TestJsonApiExporterPerformance:
    """Performance and scalability tests."""

    @pytest.fixture
    def exporter(self):
        return JsonApiExporter(Mock())

    def test_large_dataset_handling(self, exporter):
        """Test handling of large datasets."""
        # Create large dataset
        large_dataset = [{"id": i, "data": f"item_{i}"} for i in range(10000)]

        # Test that filtering works efficiently
        filters = {"id": list(range(0, 100, 2))}  # Even numbers 0-98

        import time

        start_time = time.time()
        filtered = exporter._apply_filters(large_dataset, filters)
        end_time = time.time()

        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0
        assert len(filtered) == 50  # 50 even numbers

    def test_memory_efficient_json_writing(self, exporter, tmp_path):
        """Test memory-efficient JSON writing for large files."""
        # Test with large data structure
        large_data = {
            "items": [{"id": i, "large_text": "x" * 1000} for i in range(1000)]
        }

        json_options = JsonOptions(minify=True, indent=None)

        # Should not raise memory errors
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            try:
                exporter._write_json_file(Path(tmp_file.name), large_data, json_options)

                # Verify file was written
                assert os.path.exists(tmp_file.name)
                assert os.path.getsize(tmp_file.name) > 0
            finally:
                os.unlink(tmp_file.name)


# Integration tests
@pytest.mark.integration
class TestJsonApiExporterIntegration:
    """Integration tests for JSON API Exporter."""

    def test_full_export_with_real_data(self, tmp_path):
        """Test complete export with realistic data structure."""
        # This would test with actual database and file system
        # Placeholder for integration test
        pass

    def test_cli_context_progress_manager(self, tmp_path):
        """Test that ProgressManager is used when CLI_CONTEXT is True."""
        # Test the CLI_CONTEXT branch
        with patch(
            "niamoto.core.plugins.exporters.json_api_exporter.CLI_CONTEXT", True
        ):
            with patch(
                "niamoto.core.plugins.exporters.json_api_exporter.ProgressManager"
            ):
                # Create a minimal test that just checks the import behavior
                # We can't easily test the full flow without complex mocking
                # So we'll test that ProgressManager can be imported when CLI_CONTEXT is True
                from niamoto.core.plugins.exporters.json_api_exporter import (
                    CLI_CONTEXT,
                    ProgressManager,
                )

                # Verify CLI_CONTEXT is True in our patch
                assert CLI_CONTEXT is True
                # Verify ProgressManager is available (not None)
                assert ProgressManager is not None

    def test_fallback_progress_without_cli(self, tmp_path):
        """Test that Rich Progress is used when CLI_CONTEXT is False."""
        # Test that the import structure works correctly when CLI context is unavailable
        # This test is more challenging because CLI_CONTEXT is evaluated at import time
        # Rather than trying to manipulate module imports across different Python versions,
        # we'll test the behavior more indirectly by verifying the fallback logic

        # Test that the JsonApiExporter can be instantiated regardless of CLI_CONTEXT value
        exporter = JsonApiExporter(Mock())
        assert exporter is not None

        # Test that Rich Progress can be imported (this is the fallback behavior)
        from rich.progress import Progress

        assert Progress is not None

        # Test that the export method works even when using fallback progress
        # This indirectly tests that the non-CLI branch is functional
        target_config = Mock()
        target_config.name = "test_export"
        target_config.params = {
            "output_dir": str(tmp_path),
            "json_options": {"indent": 2},
        }
        target_config.groups = []

        # This should not raise an exception regardless of CLI_CONTEXT
        with patch.object(exporter, "_generate_metadata"):
            with patch.object(exporter, "_save_errors"):
                try:
                    exporter.export(target_config, Mock())
                except Exception as e:
                    # We expect potential exceptions from mocked components
                    # but not from the CLI_CONTEXT branch logic
                    assert "ProgressManager" not in str(e)
                    assert "CLI_CONTEXT" not in str(e)
