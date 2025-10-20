"""
Tests for the ClassObjectCategoriesExtractor plugin.
"""

import pytest
import pandas as pd
from unittest.mock import Mock

from niamoto.core.plugins.transformers.class_objects.categories_extractor import (
    ClassObjectCategoriesExtractor,
)
from niamoto.core.imports.registry import EntityRegistry
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


# Plugin fixture with mocked registry
@pytest.fixture
def plugin(mock_db):
    """Create plugin with mocked registry for legacy tests."""
    mock_registry = Mock(spec=EntityRegistry)
    return ClassObjectCategoriesExtractor(mock_db, registry=mock_registry)


# == Test Cases ==


def test_basic_category_extraction(plugin, sample_data):
    """Test basic extraction of ordered categories."""
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


def test_error_missing_columns(plugin):
    """Test error if required columns are missing from input data."""
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


def test_error_missing_field_data(plugin, sample_data):
    """Test error when data for the specified class_object is missing."""
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


def test_error_invalid_config(plugin):
    """Test errors during config validation."""

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


# == EntityRegistry Tests ==


def test_init_with_registry(mock_db):
    """Test plugin initialization with EntityRegistry."""
    mock_registry = Mock(spec=EntityRegistry)
    plugin = ClassObjectCategoriesExtractor(mock_db, registry=mock_registry)

    assert plugin.registry is mock_registry


def test_init_without_registry():
    """Test plugin initialization creates EntityRegistry if not provided."""
    # Use a real mock with execute_sql method
    mock_db = Mock()
    mock_db.execute_sql = Mock()

    plugin = ClassObjectCategoriesExtractor(mock_db)

    assert plugin.registry is not None
    assert isinstance(plugin.registry, EntityRegistry)


def test_resolve_table_name_with_registry(mock_db):
    """Test table name resolution via EntityRegistry."""
    mock_registry = Mock(spec=EntityRegistry)
    mock_metadata = Mock()
    mock_metadata.table_name = "entity_custom_stats"
    mock_registry.get.return_value = mock_metadata

    plugin = ClassObjectCategoriesExtractor(mock_db, registry=mock_registry)
    result = plugin._resolve_table_name("custom_stats")

    assert result == "entity_custom_stats"
    mock_registry.get.assert_called_once_with("custom_stats")


def test_resolve_table_name_fallback(mock_db):
    """Test fallback to logical name when entity not found in registry."""
    mock_registry = Mock(spec=EntityRegistry)
    mock_registry.get.side_effect = Exception("Entity not found")

    plugin = ClassObjectCategoriesExtractor(mock_db, registry=mock_registry)
    result = plugin._resolve_table_name("legacy_table")

    assert result == "legacy_table"


def test_transform_with_custom_entity_names(plugin, sample_data):
    """Test transform works with custom entity names via registry."""

    categories_order = ["NUM", "UM", "SEC"]
    config = {
        "plugin": "class_object_categories_extractor",
        "source": "habitat_stats",  # Custom entity name
        "params": {"class_object": "land_use", "categories_order": categories_order},
    }

    # The plugin doesn't use source in transform(), only in TransformerService
    # So this test validates that the plugin accepts custom entity names
    result = plugin.transform(sample_data, config)

    assert "categories" in result
    assert "values" in result
    assert result["categories"] == categories_order
