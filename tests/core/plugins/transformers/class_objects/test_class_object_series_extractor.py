"""
Tests for the ClassObjectSeriesExtractor plugin.
"""

import pytest
import pandas as pd

from niamoto.core.plugins.transformers.class_objects.series_extractor import (
    ClassObjectSeriesExtractor,
)
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


# == Test Cases ==


def test_basic_extraction(mock_db, sample_data):
    """Test basic series extraction with default sorting and numeric conversion."""
    plugin = ClassObjectSeriesExtractor(mock_db)
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


def test_extraction_no_sort(mock_db, sample_data):
    """Test extraction without sorting the size axis."""
    plugin = ClassObjectSeriesExtractor(mock_db)
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


def test_error_missing_class_object_data(mock_db, sample_data):
    """Test that plugin returns empty result when the specified class_object is not found in data."""
    plugin = ClassObjectSeriesExtractor(mock_db)
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


def test_error_missing_input_field(mock_db, sample_data):
    """Test error when an input field (size or value) is missing."""
    plugin = ClassObjectSeriesExtractor(mock_db)
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


def test_error_invalid_config(mock_db):
    """Test error during validation for invalid configuration."""
    plugin = ClassObjectSeriesExtractor(mock_db)
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
