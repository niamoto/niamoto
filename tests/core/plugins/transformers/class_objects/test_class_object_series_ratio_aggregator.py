import pytest
import pandas as pd
import numpy as np

from niamoto.core.plugins.transformers.class_objects.series_ratio_aggregator import (
    ClassObjectSeriesRatioAggregator,
)
from niamoto.common.exceptions import DataTransformError


@pytest.fixture
def aggregator():
    """Provides an instance of the ClassObjectSeriesRatioAggregator."""
    # The base Plugin class requires a 'db' argument, provide None for this unit test.
    return ClassObjectSeriesRatioAggregator(db=None)


@pytest.fixture
def sample_config_ratio():
    """Provides a sample configuration for ratio mode."""
    return {
        "plugin": "class_object_series_ratio_aggregator",
        "params": {
            "source": "test_stats",
            "distributions": {
                "elevation_ratio": {
                    "total": "land_elevation",
                    "subset": "forest_elevation",
                    "complement_mode": "ratio",
                }
            },
            "numeric_class_name": True,
        },
    }


@pytest.fixture
def sample_config_difference(sample_config_ratio):
    """Provides a sample configuration for difference mode."""
    config = sample_config_ratio
    config_copy = config.copy()
    config_copy["params"] = config["params"].copy()
    config_copy["params"]["distributions"] = config["params"]["distributions"].copy()
    config_copy["params"]["distributions"]["elevation_ratio"] = config["params"][
        "distributions"
    ]["elevation_ratio"].copy()

    config_copy["params"]["distributions"]["elevation_ratio"]["complement_mode"] = (
        "difference"
    )
    config_copy["params"]["distributions"]["elevation_diff"] = config_copy["params"][
        "distributions"
    ].pop("elevation_ratio")
    return config_copy


@pytest.fixture
def sample_data():
    """Provides sample input data."""
    return pd.DataFrame(
        {
            "class_object": [
                "land_elevation",
                "land_elevation",
                "land_elevation",
                "land_elevation",
                "forest_elevation",
                "forest_elevation",
                "forest_elevation",
                "other_data",
            ],
            "class_name": [
                100,
                200,
                300,
                400,
                100,
                300,
                500,
                100,
            ],
            "class_value": [
                100,
                150,
                200,
                50,
                50,
                100,
                20,
                10,
            ],
        }
    )


@pytest.fixture
def sample_data_string_classes():
    """Provides sample input data with string class names."""
    return pd.DataFrame(
        {
            "class_object": [
                "land_elevation",
                "land_elevation",
                "land_elevation",
                "land_elevation",  # Total
                "forest_elevation",
                "forest_elevation",
                "forest_elevation",  # Subset
            ],
            "class_name": [
                "low",
                "medium",
                "high",
                "extra_total",  # Total classes
                "low",
                "high",
                "extra_subset",  # Subset classes
            ],
            "class_value": [
                100,
                150,
                200,
                50,  # Total values
                50,
                100,
                20,  # Subset values
            ],
        }
    )


@pytest.fixture
def sample_config_ratio_string(sample_config_ratio):
    """Provides a sample configuration for ratio mode with string classes."""
    config_copy = sample_config_ratio.copy()
    config_copy["params"] = sample_config_ratio["params"].copy()
    config_copy["params"]["numeric_class_name"] = False
    return config_copy


def test_transform_success_ratio_mode(aggregator, sample_config_ratio, sample_data):
    """Test successful transformation in ratio mode with misaligned classes."""
    result = aggregator.transform(data=sample_data, config=sample_config_ratio)

    assert "elevation_ratio" in result
    res_dist = result["elevation_ratio"]

    expected_classes = [100, 200, 300, 400, 500]
    assert res_dist["classes"] == expected_classes

    expected_subset = [50.0, 0.0, 100.0, 0.0, 20.0]
    np.testing.assert_allclose(res_dist["subset"], expected_subset)

    expected_complement = [0.5, 1.0, 0.5, 1.0, 1.0]
    np.testing.assert_allclose(res_dist["complement"], expected_complement)


def test_transform_success_difference_mode(
    aggregator, sample_config_difference, sample_data
):
    """Test successful transformation in difference mode."""
    result = aggregator.transform(data=sample_data, config=sample_config_difference)

    assert "elevation_diff" in result
    res_dist = result["elevation_diff"]

    expected_classes = [100, 200, 300, 400, 500]
    assert res_dist["classes"] == expected_classes

    expected_subset = [50.0, 0.0, 100.0, 0.0, 20.0]
    np.testing.assert_allclose(res_dist["subset"], expected_subset)

    expected_complement = [50.0, 150.0, 100.0, 50.0, -20.0]
    np.testing.assert_allclose(res_dist["complement"], expected_complement)


def test_transform_empty_subset(aggregator, sample_config_ratio, sample_data):
    """Test transformation when subset data is entirely missing.

    Update: Expect DataTransformError instead of successful transformation with zeros.
    """
    # Filter out subset data to make it empty
    empty_subset_data = sample_data[
        sample_data["class_object"] != "forest_elevation"
    ].copy()

    subset_field_name = sample_config_ratio["params"]["distributions"][
        "elevation_ratio"
    ]["subset"]

    # Check that the specific error for missing subset data is raised
    with pytest.raises(
        DataTransformError, match=f"No data found for subset field.*{subset_field_name}"
    ):
        aggregator.transform(data=empty_subset_data, config=sample_config_ratio)


def test_transform_empty_total_raises_error(
    aggregator, sample_config_ratio, sample_data
):
    """Test that DataTransformError is raised when total data is missing."""
    # Filter out total data
    empty_total_data = sample_data[
        sample_data["class_object"] != "land_elevation"
    ].copy()

    with pytest.raises(DataTransformError, match="No data found for total field"):
        aggregator.transform(data=empty_total_data, config=sample_config_ratio)


def test_transform_string_classes(
    aggregator, sample_config_ratio_string, sample_data_string_classes
):
    """Test successful transformation with string class names."""
    result = aggregator.transform(
        data=sample_data_string_classes, config=sample_config_ratio_string
    )

    assert "elevation_ratio" in result
    res_dist = result["elevation_ratio"]

    # Check classes: should include all unique string classes, sorted alphabetically
    expected_classes = sorted(["low", "medium", "high", "extra_total", "extra_subset"])
    assert res_dist["classes"] == expected_classes

    # Check subset values: aligned with sorted expected_classes
    # Original subset: {"low": 50, "high": 100, "extra_subset": 20}
    # Aligned subset: {"extra_subset": 20, "extra_total": 0, "high": 100, "low": 50, "medium": 0}
    expected_subset = [20.0, 0.0, 100.0, 50.0, 0.0]
    np.testing.assert_allclose(res_dist["subset"], expected_subset)

    # Check complement values (ratio mode: 1 - subset/total)
    # Total: {"low": 100, "medium": 150, "high": 200, "extra_total": 50}
    # Aligned total: {"extra_subset": 0, "extra_total": 50, "high": 200, "low": 100, "medium": 150}
    # Ratio (S/T): {"extra_subset": 0, "extra_total": 0, "high": 0.5, "low": 0.5, "medium": 0}
    # Complement (1-R): {"extra_subset": 1.0, "extra_total": 1.0, "high": 0.5, "low": 0.5, "medium": 1.0}
    expected_complement = [1.0, 1.0, 0.5, 0.5, 1.0]
    np.testing.assert_allclose(res_dist["complement"], expected_complement)


def test_transform_string_classes_with_numeric_true_raises_error(
    aggregator,
    sample_config_ratio,  # Uses numeric_class_name = True by default
    sample_data_string_classes,  # Data with string class names
):
    """Test DataTransformError when numeric_class_name=True but class names are strings."""
    with pytest.raises(
        DataTransformError, match="Failed to convert class names to numeric"
    ):
        aggregator.transform(
            data=sample_data_string_classes, config=sample_config_ratio
        )


def test_validate_config_missing_distributions_raises_error(aggregator):
    """Test that validation fails if 'distributions' is missing in config."""
    invalid_config = {
        "plugin": "class_object_series_ratio_aggregator",
        "params": {
            "source": "test_stats",
            # 'distributions' key is missing
            "numeric_class_name": True,
        },
    }
    # Expect the specific DataTransformError raised by the custom validation logic
    with pytest.raises(
        DataTransformError, match="At least one distribution must be specified"
    ):
        aggregator.validate_config(invalid_config)


def test_transform_missing_column_raises_error(
    aggregator, sample_config_ratio, sample_data
):
    """Test that DataTransformError is raised if a required column is missing."""
    # Test missing 'class_value'
    missing_value_data = sample_data.drop(columns=["class_value"])
    # Expect only DataTransformError with the specific message format
    with pytest.raises(
        DataTransformError, match="Required columns missing.*class_value"
    ):
        aggregator.transform(data=missing_value_data, config=sample_config_ratio)

    # Test missing 'class_name'
    missing_name_data = sample_data.drop(columns=["class_name"])
    with pytest.raises(
        DataTransformError, match="Required columns missing.*class_name"
    ):
        aggregator.transform(data=missing_name_data, config=sample_config_ratio)

    # Test missing 'class_object'
    missing_object_data = sample_data.drop(columns=["class_object"])
    with pytest.raises(
        DataTransformError, match="Required columns missing.*class_object"
    ):
        aggregator.transform(data=missing_object_data, config=sample_config_ratio)


# --- Placeholder for more tests --- #
# TODO: Test missing required columns in input data (error) <- DONE
