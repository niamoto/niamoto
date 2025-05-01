"""
Tests for the ClassObjectCategoriesMapper plugin.
"""

import pytest
import pandas as pd

from niamoto.core.plugins.transformers.class_objects.categories_mapper import (
    ClassObjectCategoriesMapper,
)
from niamoto.common.exceptions import DataTransformError


# Fixture for sample shape statistics data in long format
@pytest.fixture
def sample_data():
    data = {
        "class_object": [
            "forest_type",
            "forest_type",  # Field for category 1
            "holdridge",
            "holdridge",
            "holdridge",  # Field for category 2
            "soil_depth",  # Field for category 3 (partial data)
            "other_data",
        ],
        "class_name": [
            "resineux",
            "feuillus",  # Classes for category 1
            "sec",
            "humide",
            "tres_humide",  # Classes for category 2
            "deep",  # Class for category 3 (shallow missing)
            "X",
        ],
        "class_value": [
            100.5,
            250.2,  # Values for category 1
            180.0,
            170.7,
            50.1,  # Values for category 2
            500.8,  # Value for category 3
            99,
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


def test_single_category_mapping(mock_db, sample_data):
    """Test mapping for a single output category."""
    plugin = ClassObjectCategoriesMapper(mock_db)
    config = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Forest Type": {
                    "class_object": "forest_type",
                    "mapping": {"Resinous": "resineux", "Leafy": "feuillus"},
                }
            },
        },
    }

    result = plugin.transform(sample_data, config)

    assert "Forest Type" in result
    assert len(result) == 1

    forest_type_result = result["Forest Type"]
    assert "Resinous" in forest_type_result
    assert "Leafy" in forest_type_result
    assert pytest.approx(forest_type_result["Resinous"]) == 100.5
    assert pytest.approx(forest_type_result["Leafy"]) == 250.2


def test_multiple_category_mapping(mock_db, sample_data):
    """Test mapping for multiple output categories."""
    plugin = ClassObjectCategoriesMapper(mock_db)
    config = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Forest Type": {
                    "class_object": "forest_type",
                    "mapping": {"Resinous": "resineux", "Leafy": "feuillus"},
                },
                "Climate": {
                    "class_object": "holdridge",
                    "mapping": {
                        "Humid": "humide",
                        "Dry": "sec",
                        "Very Humid": "tres_humide",
                    },
                },
            },
        },
    }

    result = plugin.transform(sample_data, config)

    assert "Forest Type" in result
    assert "Climate" in result
    assert len(result) == 2

    forest_type = result["Forest Type"]
    assert pytest.approx(forest_type["Resinous"]) == 100.5
    assert pytest.approx(forest_type["Leafy"]) == 250.2

    climate = result["Climate"]
    assert "Humid" in climate
    assert "Dry" in climate
    assert "Very Humid" in climate
    assert pytest.approx(climate["Dry"]) == 180.0
    assert pytest.approx(climate["Humid"]) == 170.7
    assert pytest.approx(climate["Very Humid"]) == 50.1


def test_mapping_with_missing_source_class(mock_db, sample_data):
    """Test mapping when a source class_name is missing in data.

    It should raise a DataTransformError.
    """
    plugin = ClassObjectCategoriesMapper(mock_db)
    config = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Soil Depth": {
                    "class_object": "soil_depth",
                    "mapping": {"Deep Soil": "deep", "Shallow Soil": "shallow"},
                }
            },
        },
    }

    result = plugin.transform(sample_data, config)

    assert "Soil Depth" in result
    soil_depth_result = result["Soil Depth"]
    assert "Deep Soil" in soil_depth_result
    assert "Shallow Soil" in soil_depth_result
    assert pytest.approx(soil_depth_result["Deep Soil"]) == 500.8
    assert pytest.approx(soil_depth_result["Shallow Soil"]) == 0.0


def test_error_missing_columns(mock_db):
    """Test error if required columns are missing from input data."""
    plugin = ClassObjectCategoriesMapper(mock_db)
    bad_data = pd.DataFrame({"col_a": [1, 2]})  # Missing required columns
    config = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {"Test": {"class_object": "a", "mapping": {"x": "Y"}}},
        },
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(bad_data, config)
    assert "Required columns missing from data" in str(exc_info.value)


def test_error_invalid_config(mock_db, sample_data):
    """Test errors during config validation and transform for bad config."""
    plugin = ClassObjectCategoriesMapper(mock_db)

    # Case 1: Missing 'categories' entirely in params
    config_missing_categories = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats"
            # Missing 'categories'
        },
    }
    with pytest.raises(DataTransformError) as exc_info_cat:
        plugin.validate_config(config_missing_categories)
    error_str_cat = str(exc_info_cat.value)
    assert "params.categories" in error_str_cat and "Field required" in error_str_cat

    # Case 4: Missing 'class_object' within a category definition
    config_missing_co = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Bad Cat": {"mapping": {"a": "B"}}  # Missing class_object
            },
        },
    }
    with pytest.raises(DataTransformError) as exc_info_co:
        plugin.validate_config(config_missing_co)
    error_str_co = str(exc_info_co.value)
    assert (
        "params.categories.Bad Cat.class_object" in error_str_co
        and "Field required" in error_str_co
    )

    # Case 5: Missing 'mapping' within a category definition
    config_missing_map = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Bad Cat": {"class_object": "forest_type"}  # Missing mapping
            },
        },
    }
    with pytest.raises(DataTransformError) as exc_info_map:
        plugin.validate_config(config_missing_map)
    error_str_map = str(exc_info_map.value)
    assert (
        "params.categories.Bad Cat.mapping" in error_str_map
        and "Field required" in error_str_map
    )

    # Case 6: 'categories' is not a dict
    config_categories_not_dict = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": "not a dict",  # Not a dict
        },
    }
    with pytest.raises(DataTransformError) as exc_info_type:
        plugin.validate_config(config_categories_not_dict)
    assert "Input should be a valid dictionary" in str(exc_info_type.value)

    # Case 8: Transform error due to missing class_object in data
    config_valid_but_data_missing = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Forest": {"class_object": "non_existent_co", "mapping": {"a": "b"}}
            },
        },
    }
    with pytest.raises(DataTransformError) as exc_info_data_co:
        plugin.transform(sample_data, config_valid_but_data_missing)
    assert "No data found for class_object non_existent_co" in str(
        exc_info_data_co.value
    )

    # Case 9: Transform error due to missing class_name in data for a subcategory (this should now return 0.0)
    config_valid_but_name_missing = {
        "plugin": "class_object_categories_mapper",
        "params": {
            "source": "shape_stats",
            "categories": {
                "Forest": {
                    "class_object": "forest_type",
                    "mapping": {
                        "Resinous": "resineux",
                        "NonExistentName": "missing_sub",
                    },
                }
            },
        },
    }
    # This case should now pass and return 0.0 for the missing subcategory, not raise an error
    result = plugin.transform(sample_data, config_valid_but_name_missing)
    assert "Forest" in result
    assert "NonExistentName" in result["Forest"]
    assert result["Forest"]["NonExistentName"] == 0.0
