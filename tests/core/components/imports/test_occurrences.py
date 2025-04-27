"""
Tests for the OccurrenceImporter class.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.common.exceptions import (
    OccurrenceImportError,
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

    @patch("sqlite3.connect")
    @patch("pandas.read_sql")
    @patch("pandas.read_csv")
    @patch("pathlib.Path.resolve")
    @patch("pathlib.Path.exists")
    def test_import_occurrence_plot_links(
        self,
        mock_exists,
        mock_resolve,
        mock_read_csv,
        mock_read_sql,
        mock_sqlite_connect,
    ):
        """Test import_occurrence_plot_links method."""
        # Setup mocks for file checks
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        # Setup mock DataFrame with valid data
        mock_df = pd.DataFrame(
            {
                "id_occurrence": [1, 2, 3],
                "id_plot": [1, 2, 3],
                "plot_short_name": ["plot1", "plot2", "plot3"],
                "plot_full_name": ["Plot 1", "Plot 2", "Plot 3"],
                "occurrence_id_taxon": [101, 102, 103],
                "occurrence_taxon_full_name": ["Species1", "Species2", "Species3"],
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock pandas.read_sql to return plot_ref data
        mock_plot_ref_df = pd.DataFrame(
            {  # Data for plot_ref query
                "id": [1, 2, 3],
                "id_locality": [10, 11, 12],  # Match id_plot in mock_df
            }
        )
        mock_occurrence_df = pd.DataFrame(
            {  # Data for occurrences query
                "id": [101, 102, 103],
                "id_source": [20, 21, 22],  # Match id_occurrence in mock_df
            }
        )

        def read_sql_side_effect(sql, con):
            sql_lower = sql.lower()
            if "plot_ref" in sql_lower:
                return mock_plot_ref_df
            elif "occurrences" in sql_lower:
                return mock_occurrence_df
            else:
                # Return an empty DataFrame or raise an error for unexpected queries
                return pd.DataFrame()

        mock_read_sql.side_effect = read_sql_side_effect

        # Mock sqlite3.connect to return a mock connection for to_sql
        mock_connection = MagicMock()
        mock_sqlite_connect.return_value = mock_connection
        # Configure the connection's __enter__ and __exit__ methods for context management
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.__exit__.return_value = None

        # Configure the mock_db's execute_sql method
        def mock_execute_sql(*args, **kwargs):
            sql = args[0].lower()  # Get the SQL query string
            # Only expect DROP and CREATE table statements now
            if sql.startswith("drop table") or sql.startswith("create table"):
                return None  # Do nothing for DDL
            else:
                raise ValueError(f"Unexpected SQL query in mock: {sql}")

        # Patch db on the specific instance using context manager
        with patch.object(self.importer, "db") as mock_db:
            # IMPORTANT: Configure the mock db instance
            # This path is used by the real code to call sqlite3.connect
            mock_db.db_path = "mock_db_path"
            mock_db.execute_sql.side_effect = mock_execute_sql

            # Call the actual method (self.importer now uses the mocked db)
            result = self.importer.import_occurrence_plot_links("test.csv")

        # Verify results
        self.assertIn("Successfully imported", result)
        self.assertIn("3 occurrence-plot links", result)  # Check count
        mock_read_csv.assert_called_once_with("test.csv")

        # Verify execute_sql calls (should be 2: DROP, CREATE)
        # mock_db is only available inside the 'with' block, check calls *after*
        # However, the mock object retains call info after exiting the block.
        self.assertEqual(mock_db.execute_sql.call_count, 2)

        # Verify read_sql calls
        self.assertEqual(mock_read_sql.call_count, 2)
        # Check first call (plot_ref)
        call1_args = mock_read_sql.call_args_list[0][0]
        self.assertIn("plot_ref", call1_args[0].lower())
        self.assertEqual(call1_args[1], "sqlite:///mock_db_path")
        # Check second call (occurrences)
        call2_args = mock_read_sql.call_args_list[1][0]
        self.assertIn("occurrences", call2_args[0].lower())
        self.assertEqual(call2_args[1], "sqlite:///mock_db_path")

        # Verify sqlite3.connect call instead of sqlalchemy.create_engine
        mock_sqlite_connect.assert_called_once_with("mock_db_path")

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_occurrence_plot_links_file_not_found(
        self, mock_exists, mock_read_csv
    ):
        """Test import_occurrence_plot_links with file not found error."""
        # Setup mock for file check
        mock_exists.return_value = False

        # We need to catch OccurrenceImportError instead of FileReadError
        with self.assertRaises(OccurrenceImportError):
            self.importer.import_occurrence_plot_links("nonexistent.csv")

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
