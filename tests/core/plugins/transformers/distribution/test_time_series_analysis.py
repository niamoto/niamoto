import pandas as pd

from niamoto.core.plugins.transformers.distribution.time_series_analysis import (
    TimeSeriesAnalysis,
)


def test_single_field_non_binary_values_are_bounded_presence_percentages():
    plugin = TimeSeriesAnalysis(db=None, registry=object())
    data = pd.DataFrame(
        {
            "month_obs": [1, 1, 1, 2, 2],
            "abundance": [5, 0, 2, None, 10],
        }
    )
    config = {
        "plugin": "time_series_analysis",
        "params": {"field": "abundance", "time_field": "month_obs"},
    }

    result = plugin.transform(data, config)

    assert result["month_data"]["value"][0] == 66.67
    assert result["month_data"]["value"][1] == 50.0
    assert all(value <= 100 for value in result["month_data"]["value"])


def test_multi_field_non_binary_values_are_bounded_presence_percentages():
    plugin = TimeSeriesAnalysis(db=None, registry=object())
    data = pd.DataFrame(
        {
            "month_obs": [1, 1, 2, 2],
            "flowers_count": [3, 0, 4, 8],
            "fruits_count": [0, 9, None, -1],
        }
    )
    config = {
        "plugin": "time_series_analysis",
        "params": {
            "fields": {
                "flowers": "flowers_count",
                "fruits": "fruits_count",
            },
            "time_field": "month_obs",
        },
    }

    result = plugin.transform(data, config)

    assert result["month_data"]["flowers"][0] == 50.0
    assert result["month_data"]["flowers"][1] == 100.0
    assert result["month_data"]["fruits"][0] == 50.0
    assert result["month_data"]["fruits"][1] == 0.0
    assert all(
        value <= 100 for series in result["month_data"].values() for value in series
    )
