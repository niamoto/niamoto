# tests/core/plugins/exporters/test_json_api_exporter.py

"""Tests for the JSON API Exporter plugin."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Import to trigger plugin registration

from niamoto.core.plugins.exporters.json_api_exporter import (
    JsonApiExporter,
    JsonApiExporterParams,
    DataMapper,
    GroupConfig,
    DetailConfig,
    IndexConfig,
    JsonOptions,
)
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType


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


# Integration tests
@pytest.mark.integration
class TestJsonApiExporterIntegration:
    """Integration tests for JSON API Exporter."""

    def test_full_export_with_real_data(self, tmp_path):
        """Test complete export with realistic data structure."""
        # This would test with actual database and file system
        # Placeholder for integration test
        pass
