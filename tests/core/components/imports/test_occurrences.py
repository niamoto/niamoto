"""
Tests for the OccurrenceImporter class.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.common.exceptions import (
    FileReadError,
    CSVError,
    DataValidationError,
)
from tests.common.base_test import NiamotoTestCase


class TestOccurrenceImporter(NiamotoTestCase):
    """Test case for the OccurrenceImporter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Use MagicMock directly instead of create_mock to avoid spec_set restrictions
        self.mock_db = MagicMock()
        # Set attributes that are accessed in the code
        self.mock_db.db_path = "mock_db_path"
        self.mock_db.engine = MagicMock()
        self.importer = OccurrenceImporter(self.mock_db)

    def test_init(self):
        """Test initialization of OccurrenceImporter."""
        self.assertEqual(self.importer.db, self.mock_db)
        self.assertEqual(self.importer.db_path, "mock_db_path")

    @patch("pandas.read_csv")
    def test_analyze_data(self, mock_read_csv):
        """Test analyze_data method."""
        # Setup mock DataFrame
        mock_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Species1", "Species2", "Species3"],
                "lat": [10.1, 10.2, 10.3],
                "lon": [20.1, 20.2, 20.3],
            }
        )
        mock_read_csv.return_value = mock_df

        # Call the method
        result = self.importer.analyze_data("test.csv")

        # Verify results
        self.assertEqual(len(result), 4)  # 4 columns
        self.assertIn(("id", "INTEGER"), result)
        self.assertIn(("name", "TEXT"), result)
        self.assertIn(("lat", "REAL"), result)
        self.assertIn(("lon", "REAL"), result)

    @patch("pandas.read_csv")
    def test_analyze_data_file_not_found(self, mock_read_csv):
        """Test analyze_data with file not found error."""
        # Set up the side effect to raise FileNotFoundError
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        # We need to catch the CSVError that wraps the FileNotFoundError
        with self.assertRaises(CSVError):
            self.importer.analyze_data("nonexistent.csv")

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences(self, mock_resolve, mock_exists, mock_read_csv):
        """Test import_valid_occurrences method."""
        # Setup mocks for file checks
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        # Setup mock DataFrame
        mock_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "scientific_name": ["Species1", "Species2", "Species3"],
                "latitude": [10.1, 10.2, 10.3],
                "longitude": [20.1, 20.2, 20.3],
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock analyze_data to avoid it calling read_csv
        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.return_value = [
                ("id", "INTEGER"),
                ("scientific_name", "TEXT"),
                ("latitude", "REAL"),
                ("longitude", "REAL"),
            ]

            # Mock _create_table_structure to avoid database operations
            with patch.object(
                self.importer, "_create_table_structure"
            ) as mock_create_table:
                # Mock _import_data to avoid actual data import
                with patch.object(self.importer, "_import_data") as mock_import_data:
                    mock_import_data.return_value = (
                        3  # Return count of imported records
                    )

                    # Call the method with required parameters
                    result = self.importer.import_valid_occurrences(
                        "test.csv",
                        taxon_id_column="scientific_name",
                        location_column="latitude",
                    )

                    # Verify results
                    self.assertIn("occurrences imported", result)
                    mock_analyze.assert_called_once()
                    mock_create_table.assert_called_once()
                    mock_import_data.assert_called_once()

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_valid_occurrences_file_not_found(self, mock_exists, mock_read_csv):
        """Test import_valid_occurrences with file not found error."""
        # Setup mock for file check
        mock_exists.return_value = False

        with self.assertRaises(FileReadError):
            self.importer.import_valid_occurrences(
                "nonexistent.csv",
                taxon_id_column="scientific_name",
                location_column="latitude",
            )

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_missing_taxon_id(
        self, mock_resolve, mock_exists, mock_read_csv
    ):
        """Test import_valid_occurrences with missing taxon_id_column."""
        # Setup mocks for file checks
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        # Mock analyze_data to return schema WITHOUT taxon_id_column
        with patch.object(self.importer, "analyze_data") as mock_analyze:
            # Example: Schema missing 'sci_name' which we'll use as taxon_id_column
            mock_analyze.return_value = [
                ("id", "INTEGER"),
                # ("sci_name", "TEXT"), # Missing!
                ("latitude", "REAL"),
                ("longitude", "REAL"),
            ]

            # Expect DataValidationError
            with self.assertRaises(DataValidationError) as cm:
                self.importer.import_valid_occurrences(
                    "test.csv",
                    taxon_id_column="sci_name",  # The column we expect to be missing
                    location_column="latitude",
                )
            # Optional: Check exception details
            self.assertIn("Missing required column", str(cm.exception))
            self.assertIn(
                "sci_name", str(cm.exception.details)
            )  # Check if field name is in details

            mock_analyze.assert_called_once()  # Ensure analyze_data was called

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_missing_location(
        self, mock_resolve, mock_exists, mock_read_csv
    ):
        """Test import_valid_occurrences with missing location_column."""
        # Setup mocks for file checks
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        # Mock analyze_data to return schema WITHOUT location_column
        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.return_value = [
                ("id", "INTEGER"),
                ("scientific_name", "TEXT"),
                # ("lat", "REAL"), # Missing!
                ("longitude", "REAL"),
            ]

            # Expect DataValidationError
            with self.assertRaises(DataValidationError) as cm:
                self.importer.import_valid_occurrences(
                    "test.csv",
                    taxon_id_column="scientific_name",
                    location_column="lat",  # The column we expect to be missing
                )

            # Optional: Check exception details
            self.assertIn("Missing required column", str(cm.exception))
            self.assertIn(
                "lat", str(cm.exception.details)
            )  # Check if field name is in details

            mock_analyze.assert_called_once()  # Ensure analyze_data was called


if __name__ == "__main__":
    unittest.main()
