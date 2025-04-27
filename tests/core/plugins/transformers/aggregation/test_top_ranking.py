"""Tests for the TopRanking plugin."""

import unittest
from unittest.mock import MagicMock
import pandas as pd
import numpy as np

from niamoto.core.plugins.transformers.aggregation.top_ranking import TopRanking

# Sample DataFrame simulating occurrences data
SAMPLE_DATA = pd.DataFrame(
    {
        "taxon_ref_id": [
            101,
            102,
            101,
            103,
            102,  # Species level IDs
            201,
            201,
            202,  # Infra-species level IDs (belonging to species 101 and 102)
            101,
            103,
            103,  # More species occurrences
            np.nan,  # Handle NaN
        ]
    }
)

# Mock data simulating taxon_ref table results
# (id, full_name, rank_name, parent_id)
MOCK_TAXON_REF = {
    # Initial IDs from SAMPLE_DATA
    101: (101, "Species A", "species", 301),
    102: (102, "Species B", "species", 301),
    103: (103, "Species C", "species", 302),
    201: (201, "Infra A1", "infra", 101),  # Child of Species A
    202: (202, "Infra B1", "infra", 102),  # Child of Species B
    # Parent IDs
    301: (301, "Genus Alpha", "genus", 401),
    302: (302, "Genus Beta", "genus", 401),
    401: (401, "Family Foo", "family", None),
}


class TestTopRanking(unittest.TestCase):
    """Test suite for the TopRanking plugin."""

    db_mock = MagicMock()

    def setUp(self):
        """Set up the test environment."""
        self.plugin = TopRanking(db=self.db_mock)
        # Reset the mock before each test
        self.db_mock.reset_mock()

    def test_initialization(self):
        """Test that the plugin initializes correctly."""
        self.assertIsInstance(self.plugin, TopRanking)

    def test_transform_top_species(self):
        """Test getting the top N species."""
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "occurrences",
                "field": "taxon_ref_id",
                "target_ranks": ["species"],
                "count": 2,  # Get Top 2
            },
        }

        # --- Mocking db.execute_select ---
        # This mock needs to simulate multiple calls the plugin makes:
        # 1. Get initial taxa based on IDs in SAMPLE_DATA (101, 102, 103, 201, 202)
        # 2. Get parents of initial taxa (301, 302)
        # 3. Get parents of those parents (401)

        # We define the return values for each expected SELECT query
        def mock_execute_select(query):
            mock_result = MagicMock()
            mock_cursor = MagicMock()
            mock_result.cursor = mock_cursor

            # Extract IDs from the 'WHERE id IN (...)' clause
            try:
                ids_str = query.split("WHERE id IN (")[1].split(")")[0]
                ids_queried = {int(id_str.strip()) for id_str in ids_str.split(",")}
            except IndexError:
                # If query format is unexpected, return empty
                mock_cursor.description = []
                mock_result.fetchall.return_value = []
                return mock_result

            # Simulate fetchall based on queried IDs
            results_for_query = [
                MOCK_TAXON_REF[id_] for id_ in ids_queried if id_ in MOCK_TAXON_REF
            ]

            if results_for_query:
                # Simulate cursor description (important for DataFrame creation inside plugin)
                mock_cursor.description = [
                    ("id",),
                    ("full_name",),
                    ("rank_name",),
                    ("parent_id",),
                ]
                mock_result.fetchall.return_value = results_for_query
                return mock_result
            else:
                # Simulate no results found
                mock_cursor.description = []
                mock_result.fetchall.return_value = []
                return mock_result

        self.db_mock.execute_select.side_effect = mock_execute_select
        # --- End Mocking ---

        # Expected result:
        # Occurrences: 101 (x4), 102 (x2), 103 (x3), 201 (x2 -> maps to 101), 202 (x1 -> maps to 102)
        # Counts per species:
        #   Species A (101): 4 (direct) + 2 (from Infra A1) = 6
        #   Species B (102): 2 (direct) + 1 (from Infra B1) = 3
        #   Species C (103): 3 (direct) = 3
        # --> Correction based on re-trace: A=5, B=3, C=3
        # Top 2: Species A, Species B (or C, order might vary for ties)
        expected_tops = ["Species A", "Species B"]  # Or ["Species A", "Species C"]
        expected_counts = [5, 3]

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # Assertions
        self.assertCountEqual(result["tops"], expected_tops, "Top names do not match")
        self.assertCountEqual(result["counts"], expected_counts, "Counts do not match")

        # Verify db calls (optional but good practice)
        # Check that execute_select was called multiple times
        self.assertTrue(self.db_mock.execute_select.call_count >= 3)
        # Example: Check the first call was for the initial IDs
        first_call_args = self.db_mock.execute_select.call_args_list[0].args[0]
        self.assertIn("WHERE id IN (", first_call_args)
        self.assertIn("101", first_call_args)
        self.assertIn("102", first_call_args)
        self.assertIn("103", first_call_args)
        self.assertIn("201", first_call_args)
        self.assertIn("202", first_call_args)

    def test_transform_top_genus(self):
        """Test getting the top N genera."""
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "occurrences",
                "field": "taxon_ref_id",
                "target_ranks": ["genus"],  # Target genus level
                "count": 1,  # Get Top 1
            },
        }

        # Same mock setup as test_transform_top_species
        def mock_execute_select(query):
            # Simplified mock logic from previous test
            mock_result = MagicMock()
            mock_cursor = MagicMock()
            mock_result.cursor = mock_cursor
            try:
                ids_str = query.split("WHERE id IN (")[1].split(")")[0]
                ids_queried = {int(id_str.strip()) for id_str in ids_str.split(",")}
            except IndexError:
                mock_cursor.description = []
                mock_result.fetchall.return_value = []
                return mock_result
            results_for_query = [
                MOCK_TAXON_REF[id_] for id_ in ids_queried if id_ in MOCK_TAXON_REF
            ]
            if results_for_query:
                mock_cursor.description = [
                    ("id",),
                    ("full_name",),
                    ("rank_name",),
                    ("parent_id",),
                ]
                mock_result.fetchall.return_value = results_for_query
                return mock_result
            else:
                mock_cursor.description = []
                mock_result.fetchall.return_value = []
                return mock_result

        self.db_mock.execute_select.side_effect = mock_execute_select

        # Expected: Genus Alpha (8), Genus Beta (3). Top 1 is Genus Alpha.
        expected_tops = ["Genus Alpha"]
        expected_counts = [8]

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        self.assertCountEqual(result["tops"], expected_tops)
        self.assertCountEqual(result["counts"], expected_counts)

    def test_transform_empty_dataframe(self):
        """Test transformation with an empty DataFrame."""
        empty_df = pd.DataFrame(columns=["taxon_ref_id", "other_col"])
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "occurrences",
                "field": "taxon_ref_id",
                "target_ranks": ["species"],
                "count": 5,
            },
        }

        expected_result = {"tops": [], "counts": []}

        result = self.plugin.transform(empty_df, config)

        # Verify no DB call was made for an empty DataFrame
        self.db_mock.execute_select.assert_not_called()
        self.assertEqual(result, expected_result)

    def test_transform_missing_field_column(self):
        """Test when the configured 'field' column is missing."""
        # Use SAMPLE_DATA which has 'taxon_ref_id'
        data_without_field = SAMPLE_DATA.drop(columns=["taxon_ref_id"])
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "occurrences",
                "field": "taxon_ref_id",  # This field is missing now
                "target_ranks": ["species"],
                "count": 5,
            },
        }

        expected_result = {"tops": [], "counts": []}

        result = self.plugin.transform(data_without_field, config)

        # Verify no DB call was made
        self.db_mock.execute_select.assert_not_called()
        self.assertEqual(result, expected_result)

    def test_transform_no_taxa_found_in_db(self):
        """Test when initial DB query returns no matching taxa."""
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "occurrences",
                "field": "taxon_ref_id",
                "target_ranks": ["species"],
                "count": 5,
            },
        }

        # Mock execute_select to always return empty results
        def mock_empty_select(query):
            mock_result = MagicMock()
            mock_cursor = MagicMock()
            mock_result.cursor = mock_cursor
            mock_cursor.description = []
            mock_result.fetchall.return_value = []
            return mock_result

        self.db_mock.execute_select.side_effect = mock_empty_select

        expected_result = {"tops": [], "counts": []}

        # Use the original SAMPLE_DATA which contains valid IDs
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # Verify DB was called (at least once for the initial query)
        self.db_mock.execute_select.assert_called()
        self.assertEqual(result, expected_result)

    # --- Add more test cases below ---
