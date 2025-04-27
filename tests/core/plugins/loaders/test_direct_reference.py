"""
Tests for the DirectReferenceLoader plugin.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from niamoto.common.exceptions import DatabaseError
from pydantic import ValidationError

from niamoto.core.plugins.loaders.direct_reference import DirectReferenceLoader
from tests.common.base_test import NiamotoTestCase


class TestDirectReferenceLoader(NiamotoTestCase):
    """Test case for the DirectReferenceLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Mock the database connection (as expected by Plugin.__init__)
        self.mock_db = MagicMock()
        # Mock the engine attribute as it's used in tests
        self.mock_db.engine = MagicMock()
        self.loader = DirectReferenceLoader(db=self.mock_db)

    def test_validate_config_success(self):
        """Test successful validation of a configuration."""
        # --- Arrange ---
        config = {
            "plugin": "direct_reference",
            "data": "main_table",
            "grouping": "ref_table",
            "key": "ref_key",
        }

        # --- Act ---
        validated_config = self.loader.validate_config(config)

        # --- Assert ---
        self.assertEqual(validated_config.data, "main_table")
        self.assertEqual(validated_config.grouping, "ref_table")
        self.assertEqual(validated_config.key, "ref_key")

    def test_validate_config_missing_key(self):
        """Test validation failure when 'key' key is missing."""
        # --- Arrange ---
        config = {
            "plugin": "direct_reference",
            "data": "main_table",
            "grouping": "ref_table",
        }

        # --- Act & Assert ---
        try:
            self.loader.validate_config(config)
            self.fail("ValidationError was not raised for missing 'key' key")
        except ValidationError:
            pass  # Expected exception

    @patch.object(DirectReferenceLoader, "_get_table_columns")
    @patch.object(DirectReferenceLoader, "_check_table_exists")
    @patch("pandas.read_sql")
    def test_load_data_success(
        self, mock_pd_read_sql, mock_check_exists, mock_get_cols
    ):
        """Test successful data loading with load_data."""
        # --- Arrange ---
        test_group_id = 101
        test_config = {
            "plugin": "direct_reference",
            "data": "main_data_table",
            "grouping": "ref_group_table",
            "key": "ref_id",
        }
        expected_df = pd.DataFrame({"col1": [1, 2], "ref_id": [101, 101]})

        # Mock helper methods
        mock_check_exists.return_value = True
        mock_get_cols.return_value = ["col1", "col2", "ref_id"]

        # Mock pandas read_sql for the final data query
        mock_pd_read_sql.return_value = expected_df

        # --- Act ---
        result_df = self.loader.load_data(test_group_id, test_config)

        # --- Assert ---
        # Check mocks
        self.assertEqual(mock_check_exists.call_count, 2)
        mock_check_exists.assert_any_call("main_data_table")
        mock_check_exists.assert_any_call("ref_group_table")
        mock_get_cols.assert_called_once_with("main_data_table")

        # Check pd.read_sql call
        expected_query = """
                SELECT m.*
                FROM main_data_table m
                WHERE m.ref_id = :id
            """
        mock_pd_read_sql.assert_called_once()
        call_args = mock_pd_read_sql.call_args
        # Clean up whitespace for comparison
        actual_query_cleaned = " ".join(call_args[0][0].split())
        expected_query_cleaned = " ".join(expected_query.split())
        self.assertEqual(actual_query_cleaned, expected_query_cleaned)
        # Check the second positional argument (engine)
        self.assertEqual(call_args[0][1], self.mock_db.engine)
        self.assertEqual(call_args.kwargs["params"], {"id": test_group_id})

        # Check result DataFrame
        pd.testing.assert_frame_equal(result_df, expected_df)

    @patch("pandas.read_sql")
    def test_load_data_missing_main_table(self, mock_pd_read_sql):
        """Test ValueError if 'data' (main_table) is missing in config."""
        test_group_id = 101
        test_config = {
            "plugin": "direct_reference",
            # "data": "main_data_table", # Missing
            "grouping": "ref_group_table",
            "key": "ref_id",
        }

        with self.assertRaisesRegex(ValueError, "No main table specified"):
            self.loader.load_data(test_group_id, test_config)

        # Ensure read_sql was not called
        mock_pd_read_sql.assert_not_called()

    @patch("pandas.read_sql")
    def test_load_data_missing_ref_table(self, mock_pd_read_sql):
        """Test ValueError if 'grouping' (ref_table) is missing in config."""
        test_group_id = 101
        test_config = {
            "plugin": "direct_reference",
            "data": "main_data_table",
            # "grouping": "ref_group_table", # Missing
            "key": "ref_id",
        }

        with self.assertRaisesRegex(ValueError, "No reference table specified"):
            self.loader.load_data(test_group_id, test_config)

        # Ensure read_sql was not called
        mock_pd_read_sql.assert_not_called()

    @patch.object(DirectReferenceLoader, "_get_table_columns")
    @patch.object(DirectReferenceLoader, "_check_table_exists")
    @patch("pandas.read_sql")
    def test_load_data_main_table_not_exists(
        self, mock_pd_read_sql, mock_check_exists, mock_get_cols
    ):
        """Test DatabaseError if main table does not exist."""
        # --- Arrange ---
        test_group_id = 101
        main_table_name = "non_existent_main_table"
        test_config = {
            "plugin": "direct_reference",
            "data": main_table_name,
            "grouping": "ref_group_table",
            "key": "ref_id",
        }

        # Mock _check_table_exists to return False for the main table
        mock_check_exists.return_value = False

        # --- Act & Assert ---
        with self.assertRaisesRegex(
            DatabaseError, f"Main table '{main_table_name}' does not exist"
        ):
            self.loader.load_data(test_group_id, test_config)

        # Verify mocks
        mock_check_exists.assert_called_once_with(main_table_name)
        mock_get_cols.assert_not_called()  # Should fail before getting columns
        mock_pd_read_sql.assert_not_called()  # Should fail before reading SQL

    @patch.object(DirectReferenceLoader, "_get_table_columns")
    @patch.object(DirectReferenceLoader, "_check_table_exists")
    @patch("pandas.read_sql")
    def test_load_data_ref_table_not_exists(
        self, mock_pd_read_sql, mock_check_exists, mock_get_cols
    ):
        """Test DatabaseError if reference table does not exist."""
        # --- Arrange ---
        test_group_id = 101
        main_table_name = "main_data_table"
        ref_table_name = "non_existent_ref_table"
        test_config = {
            "plugin": "direct_reference",
            "data": main_table_name,
            "grouping": ref_table_name,
            "key": "ref_id",
        }

        # Mock _check_table_exists: True for main, False for ref
        mock_check_exists.side_effect = lambda table_name: table_name == main_table_name

        # --- Act & Assert ---
        with self.assertRaisesRegex(
            DatabaseError, f"Reference table '{ref_table_name}' does not exist"
        ):
            self.loader.load_data(test_group_id, test_config)

        # Verify mocks
        self.assertEqual(mock_check_exists.call_count, 2)
        mock_check_exists.assert_any_call(main_table_name)
        mock_check_exists.assert_any_call(ref_table_name)
        mock_get_cols.assert_not_called()  # Should fail before getting columns
        mock_pd_read_sql.assert_not_called()  # Should fail before reading SQL

    @patch.object(DirectReferenceLoader, "_get_table_columns")
    @patch.object(DirectReferenceLoader, "_check_table_exists")
    @patch("pandas.read_sql")
    def test_load_data_key_not_in_main_table(
        self, mock_pd_read_sql, mock_check_exists, mock_get_cols
    ):
        """Test DatabaseError if key field is not in main table columns."""
        # --- Arrange ---
        test_group_id = 101
        main_table_name = "main_data_table"
        ref_table_name = "ref_group_table"
        key_field_name = "non_existent_key"
        test_config = {
            "plugin": "direct_reference",
            "data": main_table_name,
            "grouping": ref_table_name,
            "key": key_field_name,
        }

        # Mock table checks (both exist)
        mock_check_exists.return_value = True

        # Mock get_table_columns to return columns *without* the key
        main_table_columns = ["col1", "col2", "another_id"]
        mock_get_cols.return_value = main_table_columns

        # --- Act & Assert ---
        expected_error_msg = (
            f"Key field '{key_field_name}' not found in table '{main_table_name}'"
        )
        with self.assertRaisesRegex(DatabaseError, expected_error_msg):
            self.loader.load_data(test_group_id, test_config)

        # Verify mocks
        self.assertEqual(mock_check_exists.call_count, 2)  # Checks main and ref
        mock_check_exists.assert_any_call(main_table_name)
        mock_check_exists.assert_any_call(ref_table_name)
        mock_get_cols.assert_called_once_with(main_table_name)
        mock_pd_read_sql.assert_not_called()  # Should fail before reading SQL

    @patch.object(DirectReferenceLoader, "_get_table_columns")
    @patch.object(DirectReferenceLoader, "_check_table_exists")
    @patch("pandas.read_sql")
    def test_load_data_read_sql_error(
        self, mock_pd_read_sql, mock_check_exists, mock_get_cols
    ):
        """Test DatabaseError if pd.read_sql fails."""
        # --- Arrange ---
        test_group_id = 101
        main_table_name = "main_data_table"
        ref_table_name = "ref_group_table"
        key_field_name = "ref_id"
        test_config = {
            "plugin": "direct_reference",
            "data": main_table_name,
            "grouping": ref_table_name,
            "key": key_field_name,
        }

        # Mocks for successful checks
        mock_check_exists.return_value = True
        mock_get_cols.return_value = ["colA", "colB", key_field_name]

        # Mock pd.read_sql to raise DatabaseError
        mock_pd_read_sql.side_effect = DatabaseError("SQL query failed")

        # --- Act & Assert ---
        with self.assertRaisesRegex(DatabaseError, "SQL query failed"):
            self.loader.load_data(test_group_id, test_config)

        # Verify mocks
        self.assertEqual(mock_check_exists.call_count, 2)
        mock_get_cols.assert_called_once_with(main_table_name)
        mock_pd_read_sql.assert_called_once()  # Should be called this time


if __name__ == "__main__":
    unittest.main()
