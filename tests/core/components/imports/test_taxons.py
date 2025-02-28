"""
Tests for the TaxonomyImporter class.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path

from niamoto.core.components.imports.taxons import TaxonomyImporter
from niamoto.core.models.models import TaxonRef
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
)
from tests.common.base_test import NiamotoTestCase


class TestTaxonomyImporter(NiamotoTestCase):
    """Test case for the TaxonomyImporter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Use MagicMock directly instead of create_mock to avoid spec_set restrictions
        self.mock_db = MagicMock()
        # Set attributes that are accessed in the code
        self.mock_db.db_path = "mock_db_path"
        self.mock_db.engine = MagicMock()
        self.importer = TaxonomyImporter(self.mock_db)
        # Add db_path attribute to match other importers
        self.importer.db_path = "mock_db_path"

    def test_init(self):
        """Test initialization of TaxonomyImporter."""
        self.assertEqual(self.importer.db, self.mock_db)
        self.assertEqual(self.importer.db_path, "mock_db_path")

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv(self, mock_exists, mock_read_csv):
        """Test import_from_csv method."""
        # Setup mocks
        mock_exists.return_value = True

        # Create a mock DataFrame with the required columns
        mock_df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3],
                "full_name": ["Species1", "Species2", "Species3"],
                "authors": ["Author1", "Author2", "Author3"],
                "rank_name": ["species", "species", "species"],
                "family": [1, 1, 2],  # Example rank column
                "genus": [1, 2, 3],  # Example rank column
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock the internal methods
        with patch.object(
            self.importer, "_prepare_dataframe", return_value=mock_df
        ) as mock_prepare:
            with patch.object(
                self.importer, "_process_dataframe", return_value=3
            ) as mock_process:
                # Mock Path.resolve to return the original path
                with patch("pathlib.Path.resolve", return_value=Path("test.csv")):
                    # Call the method
                    result = self.importer.import_from_csv(
                        "test.csv", ("family", "genus")
                    )

                    # Verify results
                    self.assertEqual(result, "3 taxons imported from test.csv.")
                    mock_read_csv.assert_called_once_with("test.csv")
                    mock_prepare.assert_called_once()
                    mock_process.assert_called_once()

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv_file_not_found(self, mock_exists, mock_read_csv):
        """Test import_from_csv with file not found error."""
        mock_exists.return_value = False

        with self.assertRaises(FileReadError):
            self.importer.import_from_csv("nonexistent.csv", ("family", "genus"))

        mock_read_csv.assert_not_called()

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv_invalid_file(self, mock_exists, mock_read_csv):
        """Test import_from_csv with invalid file error."""
        mock_exists.return_value = True
        mock_read_csv.side_effect = Exception("Invalid file")

        with self.assertRaises(FileReadError):
            self.importer.import_from_csv("invalid.csv", ("family", "genus"))

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv_missing_columns(self, mock_exists, mock_read_csv):
        """Test import_from_csv with missing columns."""
        mock_exists.return_value = True

        # Create a DataFrame missing required columns
        mock_df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3],
                "full_name": ["Species1", "Species2", "Species3"],
                # Missing 'authors' and 'rank_name'
            }
        )
        mock_read_csv.return_value = mock_df

        with self.assertRaises(DataValidationError):
            self.importer.import_from_csv("test.csv", ("family", "genus"))

    def test_prepare_dataframe(self):
        """Test _prepare_dataframe method."""
        # Create a test DataFrame
        df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3],
                "full_name": ["Species1", "Species2", "Species3"],
                "authors": ["Author1", "Author2", "Author3"],
                "rank_name": ["species", "species", "species"],
                "family": [1, 1, 2],  # Example rank column
                "genus": [1, 2, 3],  # Example rank column
            }
        )

        # Call the method
        result_df = self.importer._prepare_dataframe(df, ("family", "genus"))

        # Verify results
        self.assertIn("rank", result_df.columns)
        self.assertIn("parent_id", result_df.columns)

        # Verify the data was processed correctly
        # This depends on the implementation of _get_rank and _get_parent_id
        # which we'll test separately

    def test_get_rank(self):
        """Test _get_rank method."""
        # Create a test row
        row = {"id_taxon": 1, "family": 1, "genus": 1, "species": 1}

        # Test with different ranks
        rank = self.importer._get_rank(row, ("family", "genus", "species"))
        self.assertEqual(rank, "species")

        # Test with a different ID
        row["id_taxon"] = 2
        rank = self.importer._get_rank(row, ("family", "genus", "species"))
        self.assertIsNone(rank)

        # Test with matching family
        row["id_taxon"] = 1
        row["genus"] = 2
        row["species"] = 2
        rank = self.importer._get_rank(row, ("family", "genus", "species"))
        self.assertEqual(rank, "family")

    def test_get_parent_id(self):
        """Test _get_parent_id method."""
        # Create a test row
        row = {"id_taxon": 3, "family": 1, "genus": 2, "species": 3}

        # Test with different ranks
        parent_id = self.importer._get_parent_id(row, ("family", "genus", "species"))
        self.assertEqual(parent_id, 2)  # Should be genus ID

        # Test with no parent
        row["id_taxon"] = 1
        row["family"] = 1
        row["genus"] = 1
        row["species"] = 1
        parent_id = self.importer._get_parent_id(row, ("family", "genus", "species"))
        self.assertIsNone(parent_id)

        # Test with NA values
        row["id_taxon"] = 3
        row["genus"] = pd.NA
        parent_id = self.importer._get_parent_id(row, ("family", "genus", "species"))
        self.assertEqual(parent_id, 1)  # Should fall back to family ID

    def test_convert_to_correct_type(self):
        """Test _convert_to_correct_type method."""
        # Test with integer float
        self.assertEqual(self.importer._convert_to_correct_type(1.0), 1)

        # Test with non-integer float
        self.assertEqual(self.importer._convert_to_correct_type(1.5), 1.5)

        # Test with string
        self.assertEqual(self.importer._convert_to_correct_type("test"), "test")

    @patch(
        "niamoto.core.components.imports.taxons.TaxonomyImporter._create_or_update_taxon"
    )
    def test_process_dataframe(self, mock_create_or_update):
        """Test _process_dataframe method."""
        # Setup mock
        mock_create_or_update.return_value = MagicMock()

        # Create a test DataFrame
        df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3],
                "full_name": ["Species1", "Species2", "Species3"],
                "authors": ["Author1", "Author2", "Author3"],
                "rank_name": ["species", "species", "species"],
                "rank": ["family", "genus", "species"],
                "parent_id": [None, 1, 2],
            }
        )

        # Mock session context manager
        mock_session = MagicMock()
        self.mock_db.session.return_value.__enter__.return_value = mock_session

        # Mock update_nested_set_values
        with patch.object(self.importer, "_update_nested_set_values") as mock_update:
            # Call the method
            result = self.importer._process_dataframe(
                df, ("family", "genus", "species")
            )

            # Verify results
            self.assertEqual(result, 3)
            self.assertEqual(mock_create_or_update.call_count, 3)
            mock_update.assert_called()
            mock_session.commit.assert_called()

    @patch("sqlalchemy.orm.Session")
    def test_create_or_update_taxon(self, mock_session):
        """Test _create_or_update_taxon method."""
        # Setup mocks
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None

        # Create a test row
        row = {
            "id_taxon": 1,
            "full_name": "Species1",
            "authors": "Author1",
            "rank_name": "species",
            "parent_id": 2,
            "extra_field": "extra_value",
        }

        # Call the method to create a new taxon
        taxon = self.importer._create_or_update_taxon(
            row, mock_session, ("family", "genus", "species")
        )

        # Verify results
        self.assertIsNotNone(taxon)
        mock_session.add.assert_called_once()

        # Setup mock for existing taxon
        existing_taxon = MagicMock(spec=TaxonRef)
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = existing_taxon

        # Call the method to update an existing taxon
        taxon = self.importer._create_or_update_taxon(
            row, mock_session, ("family", "genus", "species")
        )

        # Verify results
        self.assertEqual(taxon, existing_taxon)
        self.assertEqual(existing_taxon.full_name, "Species1")
        self.assertEqual(existing_taxon.authors, "Author1")
        self.assertEqual(existing_taxon.rank_name, "species")
        self.assertEqual(existing_taxon.parent_id, 2)
        self.assertIn("extra_field", existing_taxon.extra_data)

    @patch("sqlalchemy.orm.Session")
    def test_update_nested_set_values(self, mock_session):
        """Test _update_nested_set_values method."""
        # Create a simplified test that just verifies the method is called without errors
        # and that commit is called

        # Mock query chain for all taxons
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = []

        # Mock query chain for root taxons
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.all.return_value = []

        # Call the method
        self.importer._update_nested_set_values(mock_session)

        # Verify that commit was called
        mock_session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
