"""
Tests for the ClassObjectSeriesByAxisExtractor plugin.
"""

import pytest
import pandas as pd
import numpy as np

from niamoto.core.plugins.transformers.class_objects.series_by_axis_extractor import (
    ClassObjectSeriesByAxisExtractor,
)
from niamoto.common.exceptions import DataTransformError


# Fixture for sample shape statistics data in long format
@pytest.fixture
def sample_data():
    data = {
        "class_object": [
            # Data for type 'A' (mapped to 'class_obj_A')
            "class_obj_A",
            "class_obj_A",
            "class_obj_A",
            # Data for type 'B' (mapped to 'class_obj_B')
            "class_obj_B",
            "class_obj_B",
            "class_obj_B",
            # Data for type 'C' (no data)
            # Extra data
            "other_data",
        ],
        "class_name": [  # This will be the axis ('elevation')
            "200",
            "100",
            "300",  # Unsorted numeric axis for A
            "200",
            "100",
            "300",  # Unsorted numeric axis for B
            "100",
        ],
        "class_value": [
            10.1,
            5.5,
            15.6,  # Values for A
            22.2,
            11.1,
            33.3,  # Values for B
            99.9,
        ],
        "text_axis": [  # For non-numeric test
            "mid",
            "low",
            "high",
            "mid",
            "low",
            "high",
            "low",
        ],
    }
    return pd.DataFrame(data)


# Mock DB fixture
@pytest.fixture
def mock_db():
    class MockDb:
        pass

    return MockDb()


# Basic valid config
@pytest.fixture
def valid_config():
    return {
        "plugin": "class_object_series_by_axis_extractor",
        "params": {
            "axis": {
                "field": "class_name",
                "output_field": "elevation",
                "numeric": True,
                "sort": True,
            },
            "types": {
                "type_a": "class_obj_A",
                "type_b": "class_obj_B",
            },
        },
    }


# == Test Cases ==


def test_basic_extraction_sorted_numeric(mock_db, sample_data, valid_config):
    """Test basic series extraction with default sorting and numeric axis."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    result = plugin.transform(sample_data, valid_config)

    assert "elevation" in result
    assert "type_a" in result
    assert "type_b" in result

    # Check axis is sorted numeric
    assert result["elevation"] == [100, 200, 300]
    # Check values correspond to sorted axis
    assert np.allclose(result["type_a"], [5.5, 10.1, 15.6])
    assert np.allclose(result["type_b"], [11.1, 22.2, 33.3])


def test_extraction_unsorted_numeric(mock_db, sample_data, valid_config):
    """Test extraction with numeric axis but without sorting."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    config = valid_config.copy()
    config["params"]["axis"]["sort"] = False

    # Get axis order from the first type ('class_obj_A') before transform
    expected_axis_order = pd.to_numeric(
        sample_data[sample_data["class_object"] == "class_obj_A"]["class_name"]
    ).tolist()

    result = plugin.transform(sample_data, config)

    assert result["elevation"] == expected_axis_order  # Check original order
    # Values should match the original order of the axis for the first type
    assert np.allclose(result["type_a"], [10.1, 5.5, 15.6])
    # Values for type_b should be reordered to match the axis of type_a
    # Original B: 100->11.1, 200->22.2, 300->33.3
    # Axis order (from A): 200, 100, 300
    # Expected B: 22.2, 11.1, 33.3
    assert np.allclose(result["type_b"], [22.2, 11.1, 33.3])


def test_extraction_sorted_non_numeric(mock_db, sample_data, valid_config):
    """Test extraction with non-numeric, sorted axis."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    config = valid_config.copy()
    config["params"]["axis"]["field"] = "text_axis"
    config["params"]["axis"]["output_field"] = "level"
    config["params"]["axis"]["numeric"] = False
    config["params"]["axis"]["sort"] = True

    result = plugin.transform(sample_data, config)

    assert "level" in result
    assert result["level"] == ["high", "low", "mid"]  # Alphabetical sort
    # Check values correspond to sorted axis
    # Original A: low->5.5, mid->10.1, high->15.6
    # Expected A (sorted by axis 'high', 'low', 'mid'): 15.6, 5.5, 10.1
    assert np.allclose(result["type_a"], [15.6, 5.5, 10.1])
    # Original B: low->11.1, mid->22.2, high->33.3
    # Expected B (sorted by axis 'high', 'low', 'mid'): 33.3, 11.1, 22.2
    assert np.allclose(result["type_b"], [33.3, 11.1, 22.2])


def test_error_missing_type_data(mock_db, sample_data, valid_config):
    """Test error if data for a specified type (class_object) is missing."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    config = valid_config.copy()
    config["params"]["types"]["type_c"] = "class_obj_C"  # class_obj_C has no data

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "No data found for class_object class_obj_C" in str(exc_info.value)


def test_error_missing_axis_column(mock_db, sample_data, valid_config):
    """Test error if the specified axis field column is missing."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    config = valid_config.copy()
    config["params"]["axis"]["field"] = "non_existent_axis_col"

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
        # Check for the error raised when numeric conversion fails due to KeyError
        assert "Failed to convert axis values to numeric" in str(exc_info.value)
        assert "non_existent_axis_col" not in str(
            exc_info.value
        )  # Original KeyError detail is lost


def test_error_axis_numeric_conversion(mock_db, sample_data, valid_config):
    """Test error if axis values cannot be converted to numeric when requested."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    config = valid_config.copy()
    config["params"]["axis"]["field"] = "text_axis"  # Use text field
    config["params"]["axis"]["numeric"] = True  # But request numeric conversion

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "Failed to convert axis values to numeric" in str(exc_info.value)


def test_error_invalid_config(mock_db):
    """Test error if the configuration is invalid (e.g., missing 'types')."""
    plugin = ClassObjectSeriesByAxisExtractor(mock_db)
    invalid_config = {
        "plugin": "class_object_series_by_axis_extractor",
        "params": {
            "axis": {"field": "class_name", "output_field": "elevation"}
            # Missing 'types'
        },
    }
    with pytest.raises(DataTransformError) as exc_info:
        plugin.validate_config(invalid_config)
    # Check for the specific message raised by validate_config
    assert "At least one type must be specified" in str(exc_info.value)
    # assert "params.types" in str(exc_info.value) # Old assertion expecting Pydantic message
