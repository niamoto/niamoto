"""Tests for class_object_field_aggregator plugin"""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from niamoto.core.plugins.transformers.class_objects.field_aggregator import (
    ClassObjectFieldAggregator,
)
from niamoto.common.exceptions import DataTransformError


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    return MagicMock()


@pytest.fixture
def sample_data():
    """Sample data for testing"""
    data = {
        "id": [1] * 4,
        "label": ["PROVINCE NORD"] * 4,
        "class_object": [
            "land_area_ha",
            "forest_area_ha",
            "rainfall_min",
            "rainfall_max",
        ],
        "class_name": ["", "", "", ""],  # Empty class names for simple values
        "class_value": [941252.41, 321711.77, 510, 4820],
    }
    df = pd.DataFrame(data)
    # Ensure class_object is treated as a string column
    df["class_object"] = df["class_object"].astype(str)
    return df


def test_single_field(mock_db, sample_data):
    """Test single field extraction"""
    with patch(
        "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {}
        plugin = ClassObjectFieldAggregator(mock_db)
    config = {
        "plugin": "class_object_field_aggregator",
        "params": {
            "fields": [
                {
                    "class_object": "land_area_ha",
                    "source": "shape_stats",
                    "target": "land_area",
                    "units": "ha",
                }
            ]
        },
    }

    result = plugin.transform(sample_data, config)
    assert result["land_area"]["value"] == 941252.41
    assert result["land_area"]["units"] == "ha"


def test_range_field(mock_db, sample_data):
    """Test range field extraction"""
    with patch(
        "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {}
        plugin = ClassObjectFieldAggregator(mock_db)
    config = {
        "plugin": "class_object_field_aggregator",
        "params": {
            "fields": [
                {
                    "class_object": ["rainfall_min", "rainfall_max"],
                    "source": "shape_stats",
                    "target": "rainfall",
                    "units": "mm/an",
                    "format": "range",
                }
            ]
        },
    }

    result = plugin.transform(sample_data, config)
    assert result["rainfall"]["min"] == 510.0
    assert result["rainfall"]["max"] == 4820.0
    assert result["rainfall"]["units"] == "mm/an"


def test_missing_field(mock_db, sample_data):
    """Test error when field is missing"""
    with patch(
        "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {}
        plugin = ClassObjectFieldAggregator(mock_db)
    config = {
        "plugin": "class_object_field_aggregator",
        "params": {
            "fields": [
                {
                    "class_object": "missing_field",
                    "source": "shape_stats",
                    "target": "missing",
                    "units": "",
                }
            ]
        },
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "not found in data" in str(exc_info.value)


def test_invalid_range_field(mock_db, sample_data):
    """Test error when range field is invalid"""
    with patch(
        "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {}
        plugin = ClassObjectFieldAggregator(mock_db)
    config = {
        "plugin": "class_object_field_aggregator",
        "params": {
            "fields": [
                {
                    "class_object": ["rainfall_min"],  # Should be a list of 2 fields
                    "source": "shape_stats",
                    "target": "rainfall",
                    "units": "mm/an",
                    "format": "range",
                }
            ]
        },
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "Range fields must specify exactly two fields" in str(exc_info.value)


def test_multiple_fields(mock_db, sample_data):
    """Test multiple field extraction"""
    with patch(
        "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {}
        plugin = ClassObjectFieldAggregator(mock_db)
    config = {
        "plugin": "class_object_field_aggregator",
        "params": {
            "fields": [
                {
                    "class_object": "land_area_ha",
                    "source": "shape_stats",
                    "target": "land_area",
                    "units": "ha",
                },
                {
                    "class_object": ["rainfall_min", "rainfall_max"],
                    "source": "shape_stats",
                    "target": "rainfall",
                    "units": "mm/an",
                    "format": "range",
                },
            ]
        },
    }

    result = plugin.transform(sample_data, config)
    assert result["land_area"]["value"] == 941252.41
    assert result["land_area"]["units"] == "ha"
    assert result["rainfall"]["min"] == 510.0
    assert result["rainfall"]["max"] == 4820.0
    assert result["rainfall"]["units"] == "mm/an"


def test_missing_source(mock_db, sample_data):
    """Test error when source is missing"""
    with patch(
        "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {}
        plugin = ClassObjectFieldAggregator(mock_db)
    config = {
        "plugin": "class_object_field_aggregator",
        "params": {
            "fields": [
                {
                    "class_object": "land_area_ha",
                    "target": "land_area",
                    "units": "ha",
                }
            ]
        },
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "source must be specified for each field" in str(exc_info.value)
