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
        # Check for Pydantic validation error message
        self.assertTrue(
            "Field required" in str(cm.exception) or "field" in str(cm.exception)
        )

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
        # Check for Pydantic's validation error message
        self.assertTrue(
            "number of labels" in str(cm.exception)
            and "must equal number of bins minus 1" in str(cm.exception)
        )

    def test_transform_from_db_source(self):
        """Test transformation with data loaded from a database source.

        Note: Since the plugin refactoring, the service layer is responsible
        for loading data from the database. The plugin only transforms the
        provided data.
        """
        # Simulate data that was loaded by the service layer from a DB source
        db_data = pd.DataFrame(
            {
                "value": [10, 20, 30, 40, 55, 65, 75, 85, 95, 110],
                "other_col": ["a"] * 10,
            }
        )

        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "dummy_table",  # This tells the service which table to load
                "field": "value",
                "bins": [0, 50, 100, 150],
            },
        }

        # Expected counts based on db_data and bins:
        # [0, 50): 4 values (10, 20, 30, 40)
        # [50, 100): 5 values (55, 65, 75, 85, 95)
        # [100, 150]: 1 value (110)
        expected_result = {"bins": [0, 50, 100, 150], "counts": [4, 5, 1]}

        # The plugin receives pre-loaded data from the service layer
        result = self.plugin.transform(db_data, config)

        # The plugin no longer calls the database directly
        self.db_mock.execute_select.assert_not_called()
        self.assertEqual(result, expected_result)

    def test_invalid_config_bins_too_short(self):
        """Test transform raises ValueError when bins has less than 2 values."""
        invalid_config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0],  # Only 1 bin edge
            },
        }
        with self.assertRaises(ValueError) as cm:
            self.plugin.transform(SAMPLE_DATA.copy(), invalid_config)
        # Check for Pydantic's validation error message
        self.assertTrue(
            "at least 2 items" in str(cm.exception)
            or "bins must have at least 2 values" in str(cm.exception)
        )

    def test_transform_empty_with_labels(self):
        """Test transformation with empty data but labels provided."""
        empty_df = pd.DataFrame(columns=["value"])
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 50, 100],
                "labels": ["Low", "High"],
            },
        }

        # Expected: Bins and labels are returned, but counts are zero
        expected_result = {
            "bins": [0, 50, 100],
            "counts": [0, 0],
            "labels": ["Low", "High"],
        }

        result = self.plugin.transform(empty_df, config)
        self.assertEqual(result, expected_result)

    def test_transform_with_percentages_all_zero(self):
        """Test percentage calculation when all data is filtered out.

        Note: When data is empty, percentages are not included in the result
        because the early return happens before percentage calculation.
        """
        nan_data = pd.DataFrame({"value": [np.nan, None, "text"]})
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 50, 100],
                "include_percentages": True,
            },
        }

        # When data is empty after filtering, percentages are not calculated
        # The early return at line 184-191 happens before percentage logic
        expected_result = {
            "bins": [0.0, 50.0, 100.0],
            "counts": [0, 0],
        }

        result = self.plugin.transform(nan_data, config)
        self.assertEqual(result, expected_result)

    def test_validate_config_directly(self):
        """Test the validate_config method directly."""
        valid_config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 50, 100],
            },
        }
        # Should not raise an error
        self.plugin.validate_config(valid_config)

    def test_validate_config_with_exception(self):
        """Test validate_config with invalid configuration."""
        invalid_config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                # Missing required field
                "bins": [0, 50, 100],
            },
        }
        with self.assertRaises(ValueError) as cm:
            self.plugin.validate_config(invalid_config)
        self.assertTrue("Invalid configuration" in str(cm.exception))

    def test_resolve_table_name_fallback(self):
        """Test _resolve_table_name fallback when entity not in registry."""
        # Mock the registry to raise an exception
        self.plugin.registry.get = MagicMock(side_effect=Exception("Not found"))

        # Should fallback to the logical name
        result = self.plugin._resolve_table_name("unknown_table")
        self.assertEqual(result, "unknown_table")

    def test_resolve_table_name_success(self):
        """Test _resolve_table_name when entity is found in registry."""
        # Mock the registry to return metadata
        mock_metadata = MagicMock()
        mock_metadata.table_name = "entity_occurrences"
        self.plugin.registry.get = MagicMock(return_value=mock_metadata)

        result = self.plugin._resolve_table_name("occurrences")
        self.assertEqual(result, "entity_occurrences")
        self.plugin.registry.get.assert_called_once_with("occurrences")

    def test_transform_with_missing_field(self):
        """Test transform with a field that doesn't exist in the data."""
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "non_existent_field",
                "bins": [0, 50, 100],
            },
        }

        with self.assertRaises(Exception):
            self.plugin.transform(SAMPLE_DATA.copy(), config)

    def test_transform_with_single_bin_edge(self):
        """Test transform with only one bin edge (edge case)."""
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [50],  # Invalid: only 1 edge
            },
        }

        with self.assertRaises(ValueError) as cm:
            self.plugin.transform(SAMPLE_DATA.copy(), config)
        # Check for Pydantic's validation error message
        self.assertTrue(
            "at least 2 items" in str(cm.exception)
            or "bins must have at least 2 values" in str(cm.exception)
        )

    def test_transform_percentages_with_valid_data(self):
        """Test percentage calculation with valid data (covers line 208-209)."""
        data = pd.DataFrame({"value": [10, 20, 30, 60, 70]})
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 50, 100],
                "include_percentages": True,
            },
        }

        # Expected counts: [0-50): 3 values, [50-100]: 2 values
        # Percentages: 60% and 40%
        expected_result = {
            "bins": [0, 50, 100],
            "counts": [3, 2],
            "percentages": [60.0, 40.0],
        }

        result = self.plugin.transform(data, config)
        self.assertEqual(result, expected_result)

    def test_transform_with_labels_no_percentages(self):
        """Test transformation with labels but without percentages (covers line 202-203)."""
        data = pd.DataFrame({"value": [10, 30, 70, 90]})
        config = {
            "plugin": "binned_distribution",
            "params": {
                "source": "occurrences",
                "field": "value",
                "bins": [0, 50, 100],
                "labels": ["Low", "High"],
                "include_percentages": False,
            },
        }

        expected_result = {
            "bins": [0, 50, 100],
            "counts": [2, 2],
            "labels": ["Low", "High"],
        }

        result = self.plugin.transform(data, config)
        self.assertEqual(result, expected_result)

    # --- Add more test cases below ---
