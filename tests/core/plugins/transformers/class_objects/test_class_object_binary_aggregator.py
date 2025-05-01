"""
Tests for the ClassObjectBinaryAggregator plugin.
"""

import pytest
import pandas as pd

from niamoto.core.plugins.transformers.class_objects.binary_aggregator import (
    ClassObjectBinaryAggregator,
)
from niamoto.common.exceptions import DataTransformError


# Fixture for sample shape statistics data in long format
@pytest.fixture
def sample_data():
    data = {
        "class_object": [
            "cover_forest",
            "cover_forest",  # Field for group 1
            "artificial_areas",
            "artificial_areas",  # Field for group 2
            "usage",
            "usage",
            "usage",  # Field for group 3 (ternary)
        ],
        "class_name": [
            "Forêt",
            "Hors-forêt",  # Classes for group 1
            "Bâti",
            "Non-Bâti",  # Classes for group 2
            "Urbain",
            "Agricole",
            "Naturel",  # Classes for group 3
        ],
        "class_value": [
            300,
            700,  # Values for group 1 (Total 1000)
            150,
            850,  # Values for group 2 (Total 1000)
            100,
            400,
            500,  # Values for group 3 (Total 1000)
        ],
    }
    return pd.DataFrame(data)


# Mock DB fixture
@pytest.fixture
def mock_db():
    class MockDb:
        pass

    return MockDb()


# == Test Cases ==


def test_single_group_aggregation(mock_db, sample_data):
    """Test aggregation for a single group with default mapping."""
    plugin = ClassObjectBinaryAggregator(mock_db)
    config = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [
                {
                    "label": "forest_cover",
                    "field": "cover_forest",
                    # Default classes/mapping inferred from data if not provided
                }
            ],
        },
    }

    result = plugin.transform(sample_data, config)

    assert "forest_cover" in result
    dist = result["forest_cover"]
    assert len(dist) == 2
    assert dist["Forêt"] == 300
    assert dist["Hors-forêt"] == 700


def test_multiple_groups_aggregation(mock_db, sample_data):
    """Test aggregation with multiple groups."""
    plugin = ClassObjectBinaryAggregator(mock_db)
    config = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [
                {
                    "label": "forest_cover",
                    "field": "cover_forest",
                },
                {
                    "label": "artificialization",
                    "field": "artificial_areas",
                },
            ],
        },
    }

    result = plugin.transform(sample_data, config)

    assert "forest_cover" in result
    assert "artificialization" in result

    dist1 = result["forest_cover"]
    assert dist1["Forêt"] == 300
    assert dist1["Hors-forêt"] == 700

    dist2 = result["artificialization"]
    assert dist2["Bâti"] == 150
    assert dist2["Non-Bâti"] == 850


def test_custom_class_mapping(mock_db, sample_data):
    """Test aggregation with a custom class mapping."""
    plugin = ClassObjectBinaryAggregator(mock_db)
    config = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [
                {
                    "label": "land_usage_simplified",
                    "field": "usage",
                    "class_mapping": {
                        "Urbain": "Utilisé",  # Map Urbain to Utilisé
                        "Agricole": "Utilisé",  # Map Agricole to Utilisé
                        "Naturel": "Naturel",  # Keep Naturel as Naturel
                    },
                }
            ],
        },
    }

    result = plugin.transform(sample_data, config)

    assert "land_usage_simplified" in result
    dist = result["land_usage_simplified"]
    assert len(dist) == 2  # Should aggregate into 2 output classes
    # Urbain (100) + Agricole (400) = 500.
    assert dist["Utilisé"] == 500
    # Naturel (500).
    assert dist["Naturel"] == 500


def test_error_missing_field_data(mock_db, sample_data):
    """Test error when data for a specified field is missing."""
    plugin = ClassObjectBinaryAggregator(mock_db)
    config = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [
                {
                    "label": "non_existent",
                    "field": "non_existent_field",  # This field is not in sample_data
                }
            ],
        },
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "No data found for class_object non_existent_field" in str(exc_info.value)


def test_error_missing_class_in_data(mock_db, sample_data):
    """Test error when a class in data is missing from the class_mapping."""
    plugin = ClassObjectBinaryAggregator(mock_db)

    # --- Test Case: Data class is missing from the mapping ---
    config_missing_mapping = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [
                {
                    "label": "forest_cover",
                    "field": "cover_forest",
                    "class_mapping": {
                        "Forêt": "Forest"  # Mapping for "Hors-forêt" is missing
                    },
                }
            ],
        },
    }
    # This should raise an error because 'Hors-forêt' is in the data but not in the mapping keys
    with pytest.raises(DataTransformError) as exc_info_refined:
        plugin.transform(sample_data, config_missing_mapping)
    assert "Missing class mapping for classes: ['Hors-forêt']" in str(
        exc_info_refined.value
    )


def test_error_invalid_config(mock_db):
    """Test error during validation for invalid configuration."""
    plugin = ClassObjectBinaryAggregator(mock_db)
    config_missing_source = {
        "plugin": "class_object_binary_aggregator",
        "params": {  # Missing source
            "groups": [{"label": "a", "field": "b"}]
        },
    }
    config_missing_groups = {
        "plugin": "class_object_binary_aggregator",
        "params": {  # Missing groups
            "source": "shape_stats",
        },
    }
    config_missing_label = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [{"field": "b"}],  # Missing label
        },
    }
    config_missing_field = {
        "plugin": "class_object_binary_aggregator",
        "params": {
            "source": "shape_stats",
            "groups": [{"label": "a"}],  # Missing field
        },
    }

    # Expecting validation errors triggered by our manual checks in validate_config
    with pytest.raises(DataTransformError) as exc_info_src:
        plugin.validate_config(config_missing_source)
    assert "source must be specified" in str(exc_info_src.value)

    with pytest.raises(DataTransformError) as exc_info_groups:
        plugin.validate_config(config_missing_groups)
    assert "At least one group must be specified" in str(exc_info_groups.value)

    with pytest.raises(DataTransformError) as exc_info_label:
        plugin.validate_config(config_missing_label)
    assert "Group must specify 'label'" in str(exc_info_label.value)

    with pytest.raises(DataTransformError) as exc_info_field:
        plugin.validate_config(config_missing_field)
    assert "Group must specify 'field'" in str(exc_info_field.value)
