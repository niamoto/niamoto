"""Tests for the BinnedDistribution plugin."""

import unittest
from unittest.mock import MagicMock
import pandas as pd
import numpy as np

from niamoto.core.plugins.transformers.distribution.binned_distribution import (
    BinnedDistribution,
)

# Sample DataFrame for testing
SAMPLE_DATA = pd.DataFrame(
    {"value": [1, 5, 12, 18, 22, 28, 35, 42, 48, 50, 55, 61, 75, 88, 95, 100, np.nan]}
)


class TestBinnedDistribution(unittest.TestCase):
    """Test suite for the BinnedDistribution plugin."""

    db_mock = MagicMock()

    def setUp(self):
        """Set up the test environment."""
        self.plugin = BinnedDistribution(db=self.db_mock)
        self.db_mock.reset_mock()

    def test_initialization(self):
        """Test that the plugin initializes correctly."""
        self.assertIsInstance(self.plugin, BinnedDistribution)

    def test_transform_basic_bins(self):
        """Test basic binning with simple integer bins."""
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 25, 50, 75, 100],
            },
        }

        # Expected counts based on SAMPLE_DATA and bins:
        # [0, 25): 5 values (1, 5, 12, 18, 22)
        # [25, 50): 4 values (28, 35, 42, 48)
        # [50, 75): 3 values (50, 55, 61)
        # [75, 100]: 4 values (75, 88, 95, 100) - includes right edge
        expected_result = {"bins": [0, 25, 50, 75, 100], "counts": [5, 4, 3, 4]}

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        self.assertEqual(result, expected_result)

    def test_transform_with_labels_and_percentages(self):
        """Test binning with labels and included percentages."""
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 25, 50, 75, 100],
                "labels": ["Low", "Medium", "High", "Very High"],
                "include_percentages": True,
            },
        }

        # Expected counts: [5, 4, 3, 4]
        # Expected percentages: [31.25, 25.0, 18.75, 25.0]
        expected_result = {
            "bins": [0, 25, 50, 75, 100],
            "counts": [5, 4, 3, 4],
            "labels": ["Low", "Medium", "High", "Very High"],
            "percentages": [31.25, 25.0, 18.75, 25.0],
        }

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        self.assertEqual(result, expected_result)

    def test_transform_empty_dataframe(self):
        """Test transformation with an empty DataFrame."""
        empty_df = pd.DataFrame(columns=["value"])
        config = {
            "plugin": "binned_distribution",
            "params": {"source": "occurrences", "field": "value", "bins": [0, 50, 100]},
        }

        # Expected: Bins are returned, but counts are zero
        expected_result = {"bins": [0, 50, 100], "counts": [0, 0]}

        result = self.plugin.transform(empty_df, config)
        self.assertEqual(result, expected_result)

    def test_transform_all_nan_or_non_numeric(self):
        """Test transformation with only NaN or non-numeric data."""
        nan_data = pd.DataFrame({"value": [np.nan, None, "text", np.nan]})
        config = {
            "plugin": "binned_distribution",
            "params": {"source": "occurrences", "field": "value", "bins": [0, 50, 100]},
        }

        # Expected: Bins are returned, but counts are zero
        expected_result = {"bins": [0, 50, 100], "counts": [0, 0]}

        result = self.plugin.transform(nan_data, config)
        self.assertEqual(result, expected_result)

    def test_invalid_config_missing_field(self):
        """Test transform raises ValueError when 'field' is missing."""
        invalid_config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                # "field": "value", # Missing field
                "bins": [0, 50, 100],
            },
        }
        with self.assertRaises(ValueError) as cm:
            self.plugin.transform(SAMPLE_DATA.copy(), invalid_config)
        self.assertIn("Missing required field: field", str(cm.exception))

    def test_invalid_config_non_ascending_bins(self):
        """Test transform raises ValueError for non-ascending bins."""
        invalid_config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 100, 50],  # Non-ascending
            },
        }
        with self.assertRaises(ValueError) as cm:
            self.plugin.transform(SAMPLE_DATA.copy(), invalid_config)
        # Check for Pydantic's validation message or the plugin's own message
        self.assertTrue(
            "bins must be in strictly ascending order" in str(cm.exception)
            or "Invalid configuration: bins must be in strictly ascending order"
            in str(cm.exception)
        )

    def test_invalid_config_wrong_number_of_labels(self):
        """Test transform raises ValueError for incorrect number of labels."""
        invalid_config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 50, 100],  # Expects 2 labels
                "labels": ["One Label"],  # Only 1 label provided
            },
        }
        with self.assertRaises(ValueError) as cm:
            self.plugin.transform(SAMPLE_DATA.copy(), invalid_config)
        # Check for Pydantic's validation message
        self.assertTrue(
            "number of labels must be equal to number of bins - 1" in str(cm.exception)
            or "Invalid configuration: number of labels must be equal to number of bins - 1"
            in str(cm.exception)
        )

    def test_transform_from_db_source(self):
        """Test transformation when data source is a database table."""
        # Data that the mock DB will return
        mock_db_data = pd.DataFrame(
            {
                "db_value": [10, 20, 30, 40, 55, 65, 75, 85, 95, 110],
                "other_col": ["a"] * 10,
            }
        )

        # Mock the execute_select method
        mock_result = MagicMock()
        mock_cursor = MagicMock()
        mock_result.cursor = mock_cursor
        # Define column names as they would appear in cursor.description
        mock_cursor.description = [("db_value",), ("other_col",)]
        mock_result.fetchall.return_value = [tuple(x) for x in mock_db_data.to_numpy()]

        self.db_mock.execute_select.return_value = mock_result

        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "dummy_table",  # Read from DB
                "field": "db_value",
                "bins": [0, 50, 100, 150],
            },
        }

        # Expected counts based on mock_db_data and bins:
        # [0, 50): 4 values (10, 20, 30, 40)
        # [50, 100): 5 values (55, 65, 75, 85, 95)
        # [100, 150]: 1 value (110)
        expected_result = {"bins": [0, 50, 100, 150], "counts": [4, 5, 1]}

        # Pass an arbitrary DataFrame, it should be ignored because source != 'occurrences'
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # Verify the select query was called
        self.db_mock.execute_select.assert_called_once_with(
            "\n                    SELECT * FROM dummy_table\n                "
        )
        self.assertEqual(result, expected_result)

    # --- Add more test cases below ---
