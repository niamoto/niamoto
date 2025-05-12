import pytest
import pandas as pd
import numpy as np

from niamoto.core.plugins.transformers.class_objects.series_matrix_extractor import (
    ClassObjectSeriesMatrixExtractor,
    ClassObjectSeriesMatrixConfig,
)
from niamoto.common.exceptions import DataTransformError

# --- Fixtures ---


@pytest.fixture
def valid_config():
    return {
        "plugin": "class_object_series_matrix_extractor",
        "params": {
            "source": "test_stats",
            "axis": {"field": "elevation", "numeric": True, "sort": True},
            "series": [
                {"name": "series1", "class_object": "co1", "scale": 10},
                {"name": "series2", "class_object": "co2"},
            ],
        },
    }


@pytest.fixture
def sample_data():
    # Data for two class objects across different elevations
    data = {
        "class_object": ["co1", "co1", "co1", "co2", "co2", "co2", "co3", "co3"],
        "elevation": [200, 100, 300, 100, 300, 200, 100, 200],  # Unsorted elevations
        "class_value": [
            5,
            2,
            8,
            15,
            25,
            20,
            99,
            88,
        ],  # Values for each co at each elevation
    }
    return pd.DataFrame(data)


@pytest.fixture
def data_missing_series2():
    data = {
        "class_object": ["co1", "co1", "co1"],
        "elevation": [200, 100, 300],
        "class_value": [5, 2, 8],
    }
    return pd.DataFrame(data)


@pytest.fixture
def data_missing_axis_field_in_series2():
    data = {
        "class_object": ["co1", "co1", "co1", "co2", "co2", "co2"],
        "elevation": [200, 100, 300, 100, 300, 200],  # elevation exists for co1
        "some_other_field": [1, 2, 3, 4, 5, 6],  # co2 has different field
        "class_value": [5, 2, 8, 15, 25, 20],
    }
    df = pd.DataFrame(data)
    # Manually ensure 'elevation' does not exist where class_object is 'co2'
    df.loc[df["class_object"] == "co2", "elevation"] = np.nan
    df = df.drop(
        columns=["elevation"], errors="ignore"
    )  # Drop if exists from initial creation
    # Add the correct column for co1
    df_co1 = df[df["class_object"] == "co1"].copy()
    df_co1["elevation"] = [200, 100, 300]
    # Recreate co2 data without elevation
    df_co2 = df[df["class_object"] == "co2"].copy()
    df_co2 = df_co2[["class_object", "some_other_field", "class_value"]]
    # Need a common column for concat if possible, or handle carefully
    # Let's restructure based on the test case need
    data_co1 = {
        "class_object": ["co1", "co1", "co1"],
        "elevation": [200, 100, 300],
        "class_value": [5, 2, 8],
    }
    data_co2 = {
        "class_object": ["co2", "co2", "co2"],
        "some_other_field": [100, 300, 200],
        "class_value": [15, 25, 20],
    }  # Use other field for axis values
    return pd.concat(
        [pd.DataFrame(data_co1), pd.DataFrame(data_co2)], ignore_index=True
    )


@pytest.fixture
def extractor():
    """Fixture to provide an instance of the extractor plugin."""
    # Pass None for the 'db' argument required by the base Plugin class
    return ClassObjectSeriesMatrixExtractor(db=None)


# --- Test Cases ---


def test_validate_config_valid(extractor, valid_config):
    """Test successful validation of a correct config."""
    validated = extractor.validate_config(valid_config)
    assert isinstance(validated, ClassObjectSeriesMatrixConfig)
    # Access nested attributes
    assert validated.params.axis.field == "elevation"
    assert validated.params.axis.numeric is True
    assert len(validated.params.series) == 2
    assert validated.params.series[0].name == "series1"
    assert validated.params.series[0].scale == 10
    assert validated.params.series[1].scale == 1.0  # Default value


@pytest.mark.parametrize(
    "invalid_params, match_str",
    [
        ({}, "Field required"),  # Missing axis and series triggers Pydantic error
        ({"axis": {"field": "e"}}, "Field required"),  # Missing series
        (
            {"series": [{"name": "s1", "class_object": "co1"}]},
            "Field required",
        ),  # Missing axis
        (
            {"axis": {"field": "e"}, "series": []},
            "List should have at least 1 item",
        ),  # Empty series list
        (
            {
                "axis": {"field": "e", "numeric": True, "sort": True},
                "series": [{"name": "s1"}],
            },
            "Field required",
        ),  # Missing class_object in series
        (
            {
                "axis": {"numeric": True, "sort": True},
                "series": [{"name": "s1", "class_object": "co1"}],
            },
            "Field required",
        ),  # Missing field in axis
    ],
)
def test_validate_config_invalid(extractor, invalid_params, match_str):
    """Test validation failure for various invalid configs using Pydantic checks."""
    config = {
        "plugin": "class_object_series_matrix_extractor",
        "params": invalid_params,
    }
    with pytest.raises(DataTransformError) as exc_info:
        extractor.validate_config(config)
    # Check if the specific Pydantic error message is contained within the exception details
    assert match_str in str(exc_info.value)


def test_transform_success(extractor, valid_config, sample_data):
    """Test successful transformation with valid data and config."""
    result = extractor.transform(data=sample_data, config=valid_config)

    # Axis field name comes from config
    axis_field = valid_config["params"]["axis"]["field"]
    assert axis_field in result
    expected_axis = [100, 200, 300]
    assert result[axis_field] == expected_axis

    # Output is now a dict of series
    assert "series" in result
    assert isinstance(result["series"], dict)
    assert len(result["series"]) == 2

    # co1 values at 100, 200, 300 are 2, 5, 8 -> scaled by 10 -> 20, 50, 80
    assert "series1" in result["series"]
    np.testing.assert_array_equal(result["series"]["series1"], [20, 50, 80])

    # co2 values at 100, 200, 300 are 15, 20, 25 -> default scale 1.0 -> 15, 20, 25
    assert "series2" in result["series"]
    np.testing.assert_array_equal(result["series"]["series2"], [15, 20, 25])


def test_transform_axis_not_numeric_or_sorted(extractor, sample_data):
    """Test transformation when axis is not numeric or sorted in config."""
    config = {
        "plugin": "p",
        "params": {
            "source": "test",
            "axis": {"field": "elevation", "numeric": False, "sort": False},
            "series": [{"name": "s1", "class_object": "co1"}],
        },
    }
    # Axis is derived from unique values of the first series, in order of appearance if not sorted
    data_co1 = sample_data[sample_data["class_object"] == "co1"].copy()
    # numeric=False means values are treated as objects/strings
    expected_axis_order = (
        data_co1["elevation"].unique().tolist()
    )  # Order depends on unique() -> [200, 100, 300]

    result = extractor.transform(data=sample_data, config=config)

    axis_field = config["params"]["axis"]["field"]
    assert axis_field in result
    # We expect the unique values, but order might not be guaranteed without sort=True
    # Let's check the content is correct, and length matches
    assert sorted(result[axis_field]) == sorted(expected_axis_order)
    assert len(result[axis_field]) == len(expected_axis_order)

    # Values should correspond to the axis order returned by the transform
    # We need to re-fetch the data and align it manually based on the *actual* axis returned
    actual_axis = result[axis_field]
    expected_values_map = dict(zip(data_co1["elevation"], data_co1["class_value"]))
    expected_values_aligned = [
        expected_values_map.get(ax_val) for ax_val in actual_axis
    ]

    assert "series" in result
    assert "s1" in result["series"]
    np.testing.assert_array_equal(result["series"]["s1"], expected_values_aligned)


def test_transform_missing_series_data(
    extractor, valid_config, data_missing_series2, caplog
):
    """Test transformation when data for one series is missing (fills with NaN)."""
    result = extractor.transform(data=data_missing_series2, config=valid_config)

    axis_field = valid_config["params"]["axis"]["field"]
    expected_axis = [100, 200, 300]  # Axis derived from co1
    assert result[axis_field] == expected_axis

    assert "series" in result
    # co1 values scaled: 20, 50, 80
    assert "series1" in result["series"]
    np.testing.assert_array_equal(result["series"]["series1"], [20, 50, 80])

    # co2 values missing: nan, nan, nan
    assert "series2" in result["series"]
    np.testing.assert_array_equal(result["series"]["series2"], [np.nan, np.nan, np.nan])

    # Check log message
    assert (
        "No data found for class_object 'co2'. Filling series 'series2' with NaN."
        in caplog.text
    )


def test_transform_error_missing_initial_axis_data(extractor, valid_config):
    """Test error when data for the first series (used for axis) is missing."""
    empty_data = pd.DataFrame(
        {"class_object": ["co_other"], "elevation": [1], "class_value": [1]}
    )
    # The error message now includes the specific class_object name
    with pytest.raises(
        DataTransformError,
        match="No data found for initial class_object 'co1' needed for axis",
    ):
        extractor.transform(data=empty_data, config=valid_config)


def test_transform_error_axis_field_all_null_in_series(
    extractor, valid_config, data_missing_axis_field_in_series2
):
    """Test error when axis field contains only null values FOR THE INITIAL series."""
    # This test case needs adjustment. The code now only fails if the *initial* series
    # used for the axis has all nulls. It warns and fills NaN for subsequent series.
    # Let's create data where co1 (initial) has null elevations.
    data_co1_null_axis = {
        "class_object": ["co1", "co1", "co2", "co2"],
        "elevation": [np.nan, np.nan, 100, 200],  # co1 has null elevations
        "class_value": [5, 2, 15, 20],
    }
    df_null_axis = pd.DataFrame(data_co1_null_axis)

    with pytest.raises(
        DataTransformError,
        match="Axis field 'elevation' contains only null values for initial class_object 'co1'",
    ):
        extractor.transform(data=df_null_axis, config=valid_config)


def test_transform_error_axis_conversion_fails(extractor, valid_config):
    """Test error when axis field for initial series cannot be converted to numeric."""
    data = {
        "class_object": [
            "co1",
            "co1",
            "co1",
            "co2",
            "co2",
        ],  # Add co2 data to make co1 the definitive initial series
        "elevation": [100, "invalid", 300, 100, 200],  # Non-numeric value in co1
        "class_value": [2, 5, 8, 15, 20],
    }
    df = pd.DataFrame(data)
    # Error message specifies the initial class_object
    with pytest.raises(
        DataTransformError,
        match="Failed to convert axis values to numeric for initial class_object 'co1'",
    ):
        extractor.transform(data=df, config=valid_config)


def test_transform_error_series_axis_conversion_fails(
    extractor, valid_config, sample_data, caplog
):
    """Test WARNING (not error) when axis field for a specific subsequent series cannot be converted."""
    # Modify sample data to make co2 elevation non-numeric
    sample_data_copy = sample_data.copy()
    sample_data_copy.loc[sample_data_copy["class_object"] == "co2", "elevation"] = (
        "not_a_number"
    )

    # Should not raise an error, but log a warning and fill series2 with NaN
    result = extractor.transform(data=sample_data_copy, config=valid_config)

    axis_field = valid_config["params"]["axis"]["field"]
    expected_axis = [100, 200, 300]  # Axis derived from co1
    assert result[axis_field] == expected_axis

    # co1 is processed correctly
    assert "series1" in result["series"]
    np.testing.assert_array_equal(result["series"]["series1"], [20, 50, 80])

    # co2 fails conversion, should be NaN
    assert "series2" in result["series"]
    np.testing.assert_array_equal(result["series"]["series2"], [np.nan, np.nan, np.nan])

    # Check log
    assert (
        "Failed to convert axis values to numeric for class_object 'co2'. Skipping series 'series2'"
        in caplog.text
    )


# Add test for when axis field is missing entirely for initial series
def test_transform_error_axis_field_missing_initial(extractor, valid_config):
    data = {
        "class_object": ["co1", "co1"],
        "value": [1, 2],
        "class_value": [5, 2],
    }  # Missing 'elevation'
    df = pd.DataFrame(data)
    with pytest.raises(
        DataTransformError,
        match="Axis field 'elevation' not found in data for initial class_object 'co1'",
    ):
        extractor.transform(data=df, config=valid_config)


# Add test for when axis field is missing for subsequent series (should warn and NaN)
def test_transform_warn_axis_field_all_nan_subsequent(
    extractor, valid_config, sample_data, caplog
):
    sample_data_copy = sample_data.copy()
    # Remove 'elevation' column specifically where class_object is 'co2'
    # This is tricky, easier to reconstruct
    data_co1 = sample_data_copy[sample_data_copy["class_object"] == "co1"][
        ["class_object", "elevation", "class_value"]
    ]
    data_co2 = sample_data_copy[sample_data_copy["class_object"] == "co2"][
        ["class_object", "class_value"]
    ]
    data_co2["some_other_col"] = [1, 2, 3]  # Add some other column
    df_missing_axis_co2 = pd.concat([data_co1, data_co2], ignore_index=True)

    result = extractor.transform(data=df_missing_axis_co2, config=valid_config)

    axis_field = valid_config["params"]["axis"]["field"]
    expected_axis = [100, 200, 300]
    assert result[axis_field] == expected_axis

    assert "series1" in result["series"]
    np.testing.assert_array_equal(result["series"]["series1"], [20, 50, 80])
    assert "series2" in result["series"]
    np.testing.assert_array_equal(result["series"]["series2"], [np.nan, np.nan, np.nan])
    assert (
        "No valid data points (after dropping nulls in ['elevation', 'class_value']) for class_object 'co2'. Filling series 'series2' with NaN."
        in caplog.text
    )
