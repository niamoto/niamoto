"""
Tests for the ClassObjectSeriesExtractor plugin.
"""

import pytest
import pandas as pd
from unittest.mock import Mock

from niamoto.core.plugins.transformers.class_objects.series_extractor import (
    ClassObjectSeriesExtractor,
)
from niamoto.core.imports.registry import EntityRegistry
from niamoto.common.exceptions import DataTransformError


# Fixture for sample shape statistics data
@pytest.fixture
def sample_data():
    data = {
        "class_object": [
            "forest_fragmentation",
            "forest_fragmentation",
            "forest_fragmentation",
            "forest_fragmentation",
            "other_data",
            "forest_fragmentation",
        ],
        "class_name": ["30", "10", "50", "20", "100", "40"],  # Sizes out of order
        "class_value": [35, 15, 15, 25, 99, 25],  # Values corresponding to class_name
        "other_col": [1, 2, 3, 4, 5, 6],
    }
    return pd.DataFrame(data)


# Mock DB fixture (assuming needed by base class, even if not used directly)
@pytest.fixture
def mock_db():
    # Simple mock, replace with actual mock if needed
    class MockDb:
        pass

    return MockDb()


# Plugin fixture with mocked registry
@pytest.fixture
def plugin(mock_db):
    """Create plugin with mocked registry for legacy tests."""
    mock_registry = Mock(spec=EntityRegistry)
    return ClassObjectSeriesExtractor(mock_db, registry=mock_registry)


# == Test Cases ==


def test_basic_extraction(plugin, sample_data):
    """Test basic series extraction with default sorting and numeric conversion."""
    config = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "raw_shape_stats",
            "class_object": "forest_fragmentation",
            "size_field": {
                "input": "class_name",
                "output": "sizes",
                "numeric": True,
                "sort": True,
            },
            "value_field": {
                "input": "class_value",
                "output": "values",
                "numeric": True,
            },
        },
    }

    result = plugin.transform(sample_data, config)

    assert "sizes" in result
    assert "values" in result
    # Check if sizes are sorted and numeric
    assert result["sizes"] == [10, 20, 30, 40, 50]
    # Check if values correspond to the *sorted* sizes
    assert result["values"] == [15, 25, 35, 25, 15]


def test_extraction_no_sort(plugin, sample_data):
    """Test extraction without sorting the size axis."""
    config = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "raw_shape_stats",
            "class_object": "forest_fragmentation",
            "size_field": {
                "input": "class_name",
                "output": "sizes",
                "numeric": True,
                "sort": False,  # Disable sorting
            },
            "value_field": {
                "input": "class_value",
                "output": "values",
                "numeric": True,
            },
        },
    }

    result = plugin.transform(sample_data, config)

    assert "sizes" in result
    assert "values" in result
    # Sizes should be in original order (after filtering) and numeric
    assert result["sizes"] == [30, 10, 50, 20, 40]
    # Values should correspond to the original order
    assert result["values"] == [35, 15, 15, 25, 25]


def test_error_missing_class_object_data(plugin, sample_data):
    """Test that plugin returns empty result when the specified class_object is not found in data."""
    config = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "raw_shape_stats",
            "class_object": "non_existent_object",  # This object is not in sample_data
            "size_field": {"input": "class_name", "output": "sizes"},
            "value_field": {"input": "class_value", "output": "values"},
        },
    }

    # Should return empty lists instead of raising an error
    result = plugin.transform(sample_data, config)
    assert result == {"sizes": [], "values": []}


def test_error_missing_input_field(plugin, sample_data):
    """Test error when an input field (size or value) is missing."""
    config_missing_size = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "raw_shape_stats",
            "class_object": "forest_fragmentation",
            "size_field": {"input": "missing_size_col", "output": "sizes"},
            "value_field": {"input": "class_value", "output": "values"},
        },
    }
    config_missing_value = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "raw_shape_stats",
            "class_object": "forest_fragmentation",
            "size_field": {"input": "class_name", "output": "sizes"},
            "value_field": {"input": "missing_value_col", "output": "values"},
        },
    }

    with pytest.raises(DataTransformError) as exc_info_size:
        plugin.transform(sample_data, config_missing_size)
    assert "Size field missing_size_col not found in data" in str(exc_info_size.value)

    with pytest.raises(DataTransformError) as exc_info_value:
        plugin.transform(sample_data, config_missing_value)
    assert "Value field missing_value_col not found in data" in str(
        exc_info_value.value
    )


def test_error_invalid_config(plugin):
    """Test error during validation for invalid configuration."""
    invalid_config = {
        "plugin": "class_object_series_extractor",
        "params": {  # Missing class_object, size_field, value_field
            "source": "raw_shape_stats",
        },
    }
    config_missing_size_input = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "raw_shape_stats",
            "class_object": "forest_fragmentation",
            "size_field": {"output": "sizes"},  # Missing input
            "value_field": {"input": "class_value", "output": "values"},
        },
    }

    # Expecting validation error from Pydantic via our validate_config method
    with pytest.raises(DataTransformError) as exc_info:
        plugin.validate_config(invalid_config)
    # The manual check for class_object should trigger first
    assert "class_object must be specified" in str(exc_info.value)

    with pytest.raises(DataTransformError) as exc_info_size:
        plugin.validate_config(config_missing_size_input)
    # The manual check for size_field.input should trigger
    assert "size_field.input must be specified" in str(exc_info_size.value)


# == EntityRegistry Tests ==


def test_init_with_registry(mock_db):
    """Test plugin initialization with EntityRegistry."""
    mock_registry = Mock(spec=EntityRegistry)
    plugin = ClassObjectSeriesExtractor(mock_db, registry=mock_registry)

    assert plugin.registry is mock_registry


def test_init_without_registry():
    """Test plugin initialization creates EntityRegistry if not provided."""
    # Use a real mock with execute_sql method
    mock_db = Mock()
    mock_db.execute_sql = Mock()

    plugin = ClassObjectSeriesExtractor(mock_db)

    assert plugin.registry is not None
    assert isinstance(plugin.registry, EntityRegistry)


def test_resolve_table_name_with_registry(mock_db):
    """Test table name resolution via EntityRegistry."""
    mock_registry = Mock(spec=EntityRegistry)
    mock_metadata = Mock()
    mock_metadata.table_name = "entity_custom_stats"
    mock_registry.get.return_value = mock_metadata

    plugin = ClassObjectSeriesExtractor(mock_db, registry=mock_registry)
    result = plugin._resolve_table_name("custom_stats")

    assert result == "entity_custom_stats"
    mock_registry.get.assert_called_once_with("custom_stats")


def test_resolve_table_name_fallback(mock_db):
    """Test fallback to logical name when entity not found in registry."""
    mock_registry = Mock(spec=EntityRegistry)
    mock_registry.get.side_effect = Exception("Entity not found")

    plugin = ClassObjectSeriesExtractor(mock_db, registry=mock_registry)
    result = plugin._resolve_table_name("legacy_table")

    assert result == "legacy_table"


def test_transform_with_custom_entity_names(plugin, sample_data):
    """Test transform works with custom entity names via registry."""

    config = {
        "plugin": "class_object_series_extractor",
        "params": {
            "source": "habitat_stats",  # Custom entity name
            "class_object": "forest_fragmentation",
            "size_field": {
                "input": "class_name",
                "output": "sizes",
                "numeric": True,
                "sort": True,
            },
            "value_field": {
                "input": "class_value",
                "output": "values",
                "numeric": True,
            },
        },
    }

    # The plugin doesn't use source in transform(), only in TransformerService
    # So this test validates that the plugin accepts custom entity names
    result = plugin.transform(sample_data, config)

    assert "sizes" in result
    assert "values" in result
