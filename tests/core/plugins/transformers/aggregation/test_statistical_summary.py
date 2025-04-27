"""Tests for the StatisticalSummary plugin."""

import unittest
import pandas as pd
import numpy as np

from niamoto.core.plugins.transformers.aggregation.statistical_summary import (
    StatisticalSummary,
)

# Sample DataFrame for testing
SAMPLE_DATA = pd.DataFrame(
    {
        "numeric_col1": [1, 2, 3, 4, 5, np.nan],
        "numeric_col2": [10.5, 20.0, 15.5, 25.0, 18.0, 22.0],
        "category_col": ["A", "B", "A", "C", "B", "A"],
        "constant_col": [5, 5, 5, 5, 5, 5],
        "all_nan_col": [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
    }
)


class TestStatisticalSummary(unittest.TestCase):
    """Test suite for the StatisticalSummary plugin."""

    # Mock the database dependency required by the base Plugin class
    db_mock = unittest.mock.Mock()

    def setUp(self):
        """Set up the test environment."""
        # Pass the mock db during initialization
        self.plugin = StatisticalSummary(db=self.db_mock)

    def test_initialization(self):
        """Test that the plugin initializes correctly."""
        self.assertIsInstance(self.plugin, StatisticalSummary)

    def test_transform_basic_stats(self):
        """Test calculating min, mean, max for a numeric column."""
        config = {
            "plugin": "statistical_summary",
            "params": {
                "source": "occurrences",
                "field": "numeric_col1",
                # Using default stats: ["min", "mean", "max"]
                # Using default units: ""
                # Using default max_value: 100
            },
        }

        expected_result = {
            "min": 1.00,  # min of [1, 2, 3, 4, 5]
            "mean": 3.00,  # mean of [1, 2, 3, 4, 5]
            "max": 5.00,  # max of [1, 2, 3, 4, 5]
            "units": "",  # Default
            "max_value": 100,  # Default, since 5 < 100
        }

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        self.assertEqual(result, expected_result)

    def test_transform_custom_stats_units_maxvalue(self):
        """Test specific stats, units, and max_value override."""
        config = {
            "plugin": "statistical_summary",
            "params": {
                "source": "occurrences",
                "field": "numeric_col2",
                "stats": ["min", "max"],  # Only request min and max
                "units": "m/s",
                "max_value": 20,  # Lower than the actual data max (25.0)
            },
        }

        # numeric_col2 data: [10.5, 20.0, 15.5, 25.0, 18.0, 22.0]
        expected_result = {
            "min": 10.50,
            # "mean" should not be present
            "max": 25.00,
            "units": "m/s",
            "max_value": 25.00,  # Actual data max (25.0) overrides config max_value (20)
        }

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        self.assertEqual(result, expected_result)

    def test_transform_empty_dataframe(self):
        """Test transformation with an empty DataFrame."""
        empty_df = pd.DataFrame(columns=SAMPLE_DATA.columns)
        config = {
            "plugin": "statistical_summary",
            "params": {
                "source": "occurrences",
                "field": "numeric_col1",
                "stats": ["min", "mean", "max"],
                "units": "widgets",
                "max_value": 50,
            },
        }

        expected_result = {
            "min": None,
            "mean": None,
            "max": None,
            "units": "widgets",
            "max_value": 50,  # Default max_value is returned
        }

        result = self.plugin.transform(empty_df, config)
        self.assertEqual(result, expected_result)

    def test_transform_all_nan_column(self):
        """Test transformation on a column with only NaN values."""
        config = {
            "plugin": "statistical_summary",
            "params": {
                "source": "occurrences",
                "field": "all_nan_col",
                "stats": ["min", "mean", "max"],
            },
        }

        expected_result = {
            "min": None,
            "mean": None,
            "max": None,
            "units": "",  # Default
            "max_value": 100,  # Default
        }

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        self.assertEqual(result, expected_result)

    def test_transform_non_numeric_column_raises_error(self):
        """Test that applying stats to non-numeric columns raises ValueError."""
        config = {
            "plugin": "statistical_summary",
            "params": {
                "source": "occurrences",
                "field": "category_col",  # Non-numeric
                "stats": ["mean"],  # Attempting mean on strings
            },
        }

        # Expect a ValueError because mean() is not valid on string data
        # The plugin's try-except block should catch the underlying TypeError
        # and re-raise it as a ValueError.
        with self.assertRaisesRegex(
            ValueError, "Invalid configuration:"
        ):  # Match the error message format
            self.plugin.transform(SAMPLE_DATA.copy(), config)

    # --- Add more test cases below ---
