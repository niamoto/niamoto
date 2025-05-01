"""
Tests for the ClassObjectCategoriesExtractor plugin.
"""

import pytest
import pandas as pd

from niamoto.core.plugins.transformers.class_objects.categories_extractor import (
    ClassObjectCategoriesExtractor,
)
from niamoto.common.exceptions import DataTransformError


# Fixture for sample shape statistics data in long format
@pytest.fixture
def sample_data():
    data = {
        "class_object": [
            "land_use",
            "land_use",
            "land_use",
            "land_use",  # Field for the test
            "other_data",
            "other_data",
        ],
        "class_name": [
            "UM",
            "NUM",
            "SEC",
            "FORET",  # Categories for land_use
            "X",
            "Y",
        ],
        "class_value": [
            220.5,
            720.1,
            245.8,
            321.7,  # Values for land_use
            10,
            20,
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


def test_basic_category_extraction(mock_db, sample_data):
    """Test basic extraction of ordered categories."""
    plugin = ClassObjectCategoriesExtractor(mock_db)
    categories_order = [
        "NUM",
        "UM",
        "SEC",
        "FORET",
        "HUMIDE",
    ]  # HUMIDE is missing in data
    config = {
        "plugin": "class_object_categories_extractor",
        "params": {"class_object": "land_use", "categories_order": categories_order},
    }

    result = plugin.transform(sample_data, config)

    assert "categories" in result
    assert "values" in result
    assert result["categories"] == categories_order
    assert len(result["values"]) == len(categories_order)

    # Check values correspond to the order, with 0 for missing
    assert pytest.approx(result["values"][0]) == 720.1  # NUM
    assert pytest.approx(result["values"][1]) == 220.5  # UM
    assert pytest.approx(result["values"][2]) == 245.8  # SEC
    assert pytest.approx(result["values"][3]) == 321.7  # FORET
    assert pytest.approx(result["values"][4]) == 0.0  # HUMIDE (missing)


def test_error_missing_columns(mock_db):
    """Test error if required columns are missing from input data."""
    plugin = ClassObjectCategoriesExtractor(mock_db)
    bad_data = pd.DataFrame(
        {"col_a": [1, 2], "col_b": [3, 4]}
    )  # Missing required columns
    config = {
        "plugin": "class_object_categories_extractor",
        "params": {"class_object": "land_use", "categories_order": ["A", "B"]},
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(bad_data, config)
    assert "Required columns missing from data" in str(exc_info.value)
    assert "'class_object'" in str(exc_info.value)
    assert "'class_name'" in str(exc_info.value)
    assert "'class_value'" in str(exc_info.value)


def test_error_missing_field_data(mock_db, sample_data):
    """Test error when data for the specified class_object is missing."""
    plugin = ClassObjectCategoriesExtractor(mock_db)
    config = {
        "plugin": "class_object_categories_extractor",
        "params": {
            "class_object": "non_existent_field",  # This field is not in sample_data
            "categories_order": ["A", "B"],
        },
    }

    with pytest.raises(DataTransformError) as exc_info:
        plugin.transform(sample_data, config)
    assert "No data found for class_object non_existent_field" in str(exc_info.value)


def test_error_invalid_config(mock_db):
    """Test errors during config validation."""
    plugin = ClassObjectCategoriesExtractor(mock_db)

    # Case 1: Missing class_object
    config_missing_co = {
        "plugin": "class_object_categories_extractor",
        "params": {
            # Missing "class_object"
            "categories_order": ["A", "B"]
        },
    }
    with pytest.raises(DataTransformError) as exc_info_co:
        plugin.validate_config(config_missing_co)
    error_str = str(exc_info_co.value)
    assert "params.class_object" in error_str and "Field required" in error_str

    # Case 2: Missing categories_order
    config_missing_cat = {
        "plugin": "class_object_categories_extractor",
        "params": {
            "class_object": "land_use"
            # Missing "categories_order"
        },
    }
    with pytest.raises(DataTransformError) as exc_info_cat:
        plugin.validate_config(config_missing_cat)
    error_str_cat = str(exc_info_cat.value)
    assert (
        "params.categories_order" in error_str_cat and "Field required" in error_str_cat
    )

    # Case 3: categories_order is not a list
    config_cat_not_list = {
        "plugin": "class_object_categories_extractor",
        "params": {"class_object": "land_use", "categories_order": "not_a_list"},
    }
    with pytest.raises(DataTransformError) as exc_info_cat_type:
        plugin.validate_config(config_cat_not_list)
    error_str_cat_type = str(exc_info_cat_type.value)
    assert (
        "params.categories_order" in error_str_cat_type
        and "Input should be a valid list" in error_str_cat_type
    )

    # Case 4: categories_order contains non-string items
    config_cat_not_str = {
        "plugin": "class_object_categories_extractor",
        "params": {
            "class_object": "land_use",
            "categories_order": ["A", 123, "C"],  # Contains integer
        },
    }
    with pytest.raises(DataTransformError) as exc_info_cat_item:
        plugin.validate_config(config_cat_not_str)
    error_str_cat_item = str(exc_info_cat_item.value)
    assert (
        "params.categories_order" in error_str_cat_item
        and "Input should be a valid string" in error_str_cat_item
    )
