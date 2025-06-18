"""
Tests for the OccurrenceImporter class.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.common.exceptions import (
    FileReadError,
    CSVError,
    DataValidationError,
    DatabaseError,
    OccurrenceImportError,
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

    # Tests for analyze_data method
    @patch("pandas.read_csv")
    def test_analyze_data_success(self, mock_read_csv):
        """Test successful analyze_data method."""
        # Setup mock DataFrame with various data types
        mock_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Species1", "Species2", "Species3"],
                "lat": [10.1, 10.2, 10.3],
                "lon": [20.1, 20.2, 20.3],
                "count": [5, 10, 15],
                "active": [True, False, True],
            }
        )
        mock_read_csv.return_value = mock_df

        # Call the method
        result = self.importer.analyze_data("test.csv")

        # Verify results
        self.assertEqual(len(result), 6)  # 6 columns
        self.assertIn(("id", "INTEGER"), result)
        self.assertIn(("name", "TEXT"), result)
        self.assertIn(("lat", "REAL"), result)
        self.assertIn(("lon", "REAL"), result)
        self.assertIn(("count", "INTEGER"), result)
        self.assertIn(("active", "INTEGER"), result)

    @patch("pandas.read_csv")
    def test_analyze_data_datetime_column(self, mock_read_csv):
        """Test analyze_data with datetime column."""
        mock_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
                "id": [1, 2, 3],
            }
        )
        mock_read_csv.return_value = mock_df

        result = self.importer.analyze_data("test.csv")

        # Datetime columns get mapped to TEXT by default since pandas dtype is "datetime64[ns]"
        # not just "datetime64"
        self.assertIn(("date", "TEXT"), result)
        self.assertIn(("id", "INTEGER"), result)

    @patch("pandas.read_csv")
    def test_analyze_data_exact_datetime64_type(self, mock_read_csv):
        """Test analyze_data with exact datetime64 type in mapping."""
        # Create a mock DataFrame where we can control the dtype string
        mock_df = MagicMock()
        mock_df.columns = ["date", "id"]

        # Mock the dtype to return exact "datetime64" string
        mock_date_series = MagicMock()
        mock_date_series.dtype = "datetime64"
        mock_id_series = MagicMock()
        mock_id_series.dtype = "int64"

        mock_df.__getitem__.side_effect = lambda col: {
            "date": mock_date_series,
            "id": mock_id_series,
        }[col]

        mock_read_csv.return_value = mock_df

        result = self.importer.analyze_data("test.csv")

        # Should map to TIMESTAMP when dtype is exactly "datetime64"
        self.assertIn(("date", "TIMESTAMP"), result)
        self.assertIn(("id", "INTEGER"), result)

    @patch("pandas.read_csv")
    def test_analyze_data_unknown_type_defaults_to_text(self, mock_read_csv):
        """Test analyze_data with unknown data type defaults to TEXT."""
        # Create a DataFrame with a custom dtype that's not in the mapping
        mock_df = pd.DataFrame({"complex_col": [1 + 2j, 3 + 4j]})
        mock_read_csv.return_value = mock_df

        result = self.importer.analyze_data("test.csv")

        # Should default to TEXT for unknown types
        self.assertIn(("complex_col", "TEXT"), result)

    @patch("pandas.read_csv")
    def test_analyze_data_file_not_found(self, mock_read_csv):
        """Test analyze_data with file not found error."""
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        with self.assertRaises(CSVError) as context:
            self.importer.analyze_data("nonexistent.csv")

        self.assertIn("Failed to analyze CSV structure", str(context.exception))

    @patch("pandas.read_csv")
    def test_analyze_data_csv_parsing_error(self, mock_read_csv):
        """Test analyze_data with CSV parsing error."""
        mock_read_csv.side_effect = pd.errors.ParserError("CSV parse error")

        with self.assertRaises(CSVError) as context:
            self.importer.analyze_data("invalid.csv")

        self.assertIn("Failed to analyze CSV structure", str(context.exception))

    # Tests for import_occurrences method (legacy method)
    @patch.object(OccurrenceImporter, "analyze_data")
    @patch.object(OccurrenceImporter, "validate_taxon_links")
    def test_import_occurrences_success(self, mock_validate, mock_analyze):
        """Test successful import_occurrences method."""
        # Mock analyze_data return
        mock_analyze.return_value = [
            ("id", "INTEGER"),
            ("scientific_name", "TEXT"),
            ("latitude", "REAL"),
        ]

        # Mock validate_taxon_links return
        mock_validate.return_value = "Validation complete"

        # Mock database operations
        mock_count_result = MagicMock()
        mock_count_result.fetchone.return_value = [100]
        self.mock_db.execute_sql.return_value = mock_count_result

        result = self.importer.import_occurrences("test.csv", "scientific_name")

        self.assertIn("Total occurrences imported: 100", result)
        self.assertIn("Validation complete", result)
        mock_analyze.assert_called_once_with("test.csv")
        mock_validate.assert_called_once()

    @patch.object(OccurrenceImporter, "analyze_data")
    def test_import_occurrences_missing_taxon_column(self, mock_analyze):
        """Test import_occurrences with missing taxon column."""
        mock_analyze.return_value = [
            ("id", "INTEGER"),
            ("latitude", "REAL"),
            # Missing 'scientific_name'
        ]

        with self.assertRaises(ValueError) as context:
            self.importer.import_occurrences("test.csv", "scientific_name")

        self.assertIn(
            "Column scientific_name not found in CSV file", str(context.exception)
        )

    @patch.object(OccurrenceImporter, "analyze_data")
    def test_import_occurrences_with_existing_id_column(self, mock_analyze):
        """Test import_occurrences when CSV already has ID column."""
        mock_analyze.return_value = [
            ("id", "INTEGER"),
            ("scientific_name", "TEXT"),
            ("latitude", "REAL"),
        ]

        # Mock database operations
        mock_count_result = MagicMock()
        mock_count_result.fetchone.return_value = [50]
        self.mock_db.execute_sql.return_value = mock_count_result

        # Mock validate_taxon_links
        with patch.object(
            self.importer, "validate_taxon_links", return_value="Validation complete"
        ):
            result = self.importer.import_occurrences("test.csv", "scientific_name")

        self.assertIn("Total occurrences imported: 50", result)
        # Verify SQL statements were called
        self.assertTrue(self.mock_db.execute_sql.called)

    # Tests for import_valid_occurrences method
    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_success(
        self, mock_resolve, mock_exists, mock_read_csv
    ):
        """Test successful import_valid_occurrences method."""
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
                    self.assertIn("3 occurrences imported", result)
                    mock_analyze.assert_called_once()
                    mock_create_table.assert_called_once()
                    mock_import_data.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_import_valid_occurrences_file_not_found(self, mock_exists):
        """Test import_valid_occurrences with file not found error."""
        mock_exists.return_value = False

        with self.assertRaises(FileReadError) as context:
            self.importer.import_valid_occurrences(
                "nonexistent.csv",
                taxon_id_column="scientific_name",
                location_column="latitude",
            )

        self.assertIn("Occurrence file not found", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_missing_taxon_id(self, mock_resolve, mock_exists):
        """Test import_valid_occurrences with missing taxon_id_column."""
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        # Mock analyze_data to return schema WITHOUT taxon_id_column
        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.return_value = [
                ("id", "INTEGER"),
                ("latitude", "REAL"),
                ("longitude", "REAL"),
            ]

            with self.assertRaises(DataValidationError) as context:
                self.importer.import_valid_occurrences(
                    "test.csv",
                    taxon_id_column="scientific_name",
                    location_column="latitude",
                )

            self.assertIn("Missing required column", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_missing_location(self, mock_resolve, mock_exists):
        """Test import_valid_occurrences with missing location_column."""
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.return_value = [
                ("id", "INTEGER"),
                ("scientific_name", "TEXT"),
                ("longitude", "REAL"),
            ]

            with self.assertRaises(DataValidationError) as context:
                self.importer.import_valid_occurrences(
                    "test.csv",
                    taxon_id_column="scientific_name",
                    location_column="latitude",
                )

            self.assertIn("Missing required column", str(context.exception))

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_with_only_existing_taxons(
        self, mock_resolve, mock_exists
    ):
        """Test import_valid_occurrences with only_existing_taxons=True."""
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.return_value = [
                ("scientific_name", "TEXT"),
                ("latitude", "REAL"),
            ]

            with patch.object(self.importer, "_create_table_structure"):
                with patch.object(self.importer, "_import_data") as mock_import:
                    mock_import.return_value = 5

                    result = self.importer.import_valid_occurrences(
                        "test.csv",
                        taxon_id_column="scientific_name",
                        location_column="latitude",
                        only_existing_taxons=True,
                    )

                    self.assertIn("5 occurrences imported", result)
                    # Verify only_existing_taxons was passed
                    mock_import.assert_called_with(
                        "test.csv", "scientific_name", False, True
                    )

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_database_error(self, mock_resolve, mock_exists):
        """Test import_valid_occurrences with database error."""
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.return_value = [
                ("scientific_name", "TEXT"),
                ("latitude", "REAL"),
            ]

            with patch.object(self.importer, "_create_table_structure") as mock_create:
                mock_create.side_effect = SQLAlchemyError("Database connection failed")

                with self.assertRaises(DatabaseError) as context:
                    self.importer.import_valid_occurrences(
                        "test.csv",
                        taxon_id_column="scientific_name",
                        location_column="latitude",
                    )

                self.assertIn(
                    "Failed to create occurrences table", str(context.exception)
                )

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.resolve")
    def test_import_valid_occurrences_generic_error(self, mock_resolve, mock_exists):
        """Test import_valid_occurrences with generic error."""
        mock_resolve.return_value = "test.csv"
        mock_exists.return_value = True

        with patch.object(self.importer, "analyze_data") as mock_analyze:
            mock_analyze.side_effect = Exception("Unexpected error")

            with self.assertRaises(OccurrenceImportError) as context:
                self.importer.import_valid_occurrences(
                    "test.csv",
                    taxon_id_column="scientific_name",
                    location_column="latitude",
                )

            self.assertIn("Failed to import occurrences", str(context.exception))

    # Tests for _create_table_structure method
    def test_create_table_structure_without_id(self):
        """Test _create_table_structure when CSV doesn't have ID column."""
        column_schema = [
            ("scientific_name", "TEXT"),
            ("latitude", "REAL"),
            ("longitude", "REAL"),
        ]

        self.importer._create_table_structure(column_schema, id_column_exists=False)

        # Verify SQL commands were called
        calls = self.mock_db.execute_sql.call_args_list
        self.assertEqual(len(calls), 2)  # DROP and CREATE

        # Check DROP TABLE was called
        self.assertIn("DROP TABLE IF EXISTS occurrences", calls[0][0][0])

        # Check CREATE TABLE was called with correct structure
        create_call = calls[1][0][0]
        self.assertIn("CREATE TABLE occurrences", create_call)
        self.assertIn("id INTEGER PRIMARY KEY", create_call)
        self.assertIn("taxon_ref_id INTEGER REFERENCES taxon_ref(id)", create_call)

    def test_create_table_structure_with_id(self):
        """Test _create_table_structure when CSV has ID column."""
        column_schema = [
            ("id", "INTEGER"),
            ("scientific_name", "TEXT"),
            ("latitude", "REAL"),
        ]

        self.importer._create_table_structure(column_schema, id_column_exists=True)

        calls = self.mock_db.execute_sql.call_args_list
        create_call = calls[1][0][0]

        # Should not add separate ID column
        self.assertNotIn("id INTEGER PRIMARY KEY,", create_call)
        self.assertIn("taxon_ref_id INTEGER REFERENCES taxon_ref(id)", create_call)

    def test_create_table_structure_database_error(self):
        """Test _create_table_structure with database error."""
        column_schema = [("name", "TEXT")]

        self.mock_db.execute_sql.side_effect = SQLAlchemyError("Database error")

        with self.assertRaises(DatabaseError) as context:
            self.importer._create_table_structure(column_schema, False)

        self.assertIn("Failed to create table structure", str(context.exception))

    # Tests for _import_data method
    @patch("pandas.read_csv")
    @patch("sqlalchemy.create_engine")
    @patch("pandas.read_sql")
    def test_import_data_success(
        self, mock_read_sql, mock_create_engine, mock_read_csv
    ):
        """Test successful _import_data method."""
        # Mock CSV data
        mock_df = pd.DataFrame(
            {
                "scientific_name": ["Species1", "Species2"],
                "latitude": [10.1, 10.2],
                "longitude": [20.1, 20.2],
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock database count queries
        self.mock_db.execute_sql.return_value = [2]

        # Mock validate_taxon_links
        with patch.object(self.importer, "validate_taxon_links"):
            result = self.importer._import_data(
                "test.csv",
                "scientific_name",
                id_column_exists=False,
                only_existing_taxons=False,
            )

        self.assertEqual(result, 2)

    @patch("pandas.read_csv")
    @patch("sqlalchemy.create_engine")
    @patch("pandas.read_sql")
    def test_import_data_with_existing_taxons_filter(
        self, mock_read_sql, mock_create_engine, mock_read_csv
    ):
        """Test _import_data with only_existing_taxons=True."""
        # Mock CSV data
        mock_df = pd.DataFrame(
            {
                "scientific_name": ["Species1", "Species2", "Species3"],
                "latitude": [10.1, 10.2, 10.3],
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock existing taxon IDs (only Species1 and Species3 exist)
        mock_taxon_df = pd.DataFrame({"id": ["Species1", "Species3"]})
        mock_read_sql.return_value = mock_taxon_df

        # Mock database operations
        self.mock_db.execute_sql.return_value = [2]

        with patch.object(self.importer, "validate_taxon_links"):
            result = self.importer._import_data(
                "test.csv",
                "scientific_name",
                id_column_exists=False,
                only_existing_taxons=True,
            )

        # Should filter out Species2
        self.assertEqual(result, 2)

    @patch("pandas.read_csv")
    def test_import_data_file_read_error(self, mock_read_csv):
        """Test _import_data with file read error."""
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        with self.assertRaises(FileReadError) as context:
            self.importer._import_data(
                "nonexistent.csv", "scientific_name", False, False
            )

        self.assertIn("Failed to read or process file", str(context.exception))

    @patch("pandas.read_csv")
    def test_import_data_database_error(self, mock_read_csv):
        """Test _import_data with database error."""
        mock_read_csv.return_value = pd.DataFrame({"name": ["test"]})

        # Mock the database connection to raise an error
        self.mock_db.engine.connect.side_effect = SQLAlchemyError(
            "Database connection failed"
        )

        with self.assertRaises(DatabaseError) as context:
            self.importer._import_data("test.csv", "name", False, False)

        self.assertIn("Database error during import", str(context.exception))

    # Tests for validate_taxon_links method
    def test_validate_taxon_links_all_already_linked(self):
        """Test validate_taxon_links when all occurrences are already linked."""
        # Mock helper methods
        with patch.object(self.importer, "_get_occurrence_count", return_value=100):
            with patch.object(
                self.importer, "_get_linked_occurrence_count", return_value=100
            ):
                result = self.importer.validate_taxon_links("scientific_name")

        self.assertIn("All 100 occurrences already linked", result)

    def test_validate_taxon_links_needs_processing(self):
        """Test validate_taxon_links when processing is needed."""
        # Mock helper methods
        with patch.object(self.importer, "_get_occurrence_count", return_value=100):
            with patch.object(
                self.importer, "_get_linked_occurrence_count", side_effect=[50, 80]
            ):
                with patch.object(
                    self.importer, "_process_taxon_links"
                ) as mock_process:
                    mock_process.return_value = {
                        "linked_count": 30,
                        "unlinked_examples": "Sample unlinked",
                    }
                    with patch.object(self.importer, "_format_link_status"):
                        self.importer.validate_taxon_links("scientific_name")

                # Verify processing was called
                mock_process.assert_called_once_with("scientific_name")

    def test_validate_taxon_links_error_handling(self):
        """Test validate_taxon_links error handling."""
        with patch.object(
            self.importer,
            "_get_occurrence_count",
            side_effect=Exception("Database error"),
        ):
            with self.assertRaises(OccurrenceImportError) as context:
                self.importer.validate_taxon_links("scientific_name")

            self.assertIn("Error validating taxon links", str(context.exception))

    # Tests for helper methods
    def test_get_occurrence_count(self):
        """Test _get_occurrence_count method."""
        self.mock_db.execute_sql.return_value = [150]

        result = self.importer._get_occurrence_count()

        self.assertEqual(result, 150)
        self.mock_db.execute_sql.assert_called_with(
            "SELECT COUNT(*) FROM occurrences;", fetch=True
        )

    def test_get_linked_occurrence_count(self):
        """Test _get_linked_occurrence_count method."""
        self.mock_db.execute_sql.return_value = [120]

        result = self.importer._get_linked_occurrence_count()

        self.assertEqual(result, 120)
        self.mock_db.execute_sql.assert_called_with(
            "SELECT COUNT(*) FROM occurrences WHERE taxon_ref_id IS NOT NULL;",
            fetch=True,
        )

    # Tests for _process_taxon_links method
    @patch("pandas.read_sql")
    @patch("sqlalchemy.create_engine")
    def test_process_taxon_links_success(self, mock_create_engine, mock_read_sql):
        """Test successful _process_taxon_links method."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock taxon data
        taxon_df = pd.DataFrame({"id": [1, 2, 3], "taxon_id": [101, 102, 103]})

        # Mock occurrence data
        occurrence_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "scientific_name": [101, 102, 999],  # 999 doesn't exist in taxon
            }
        )

        mock_read_sql.side_effect = [taxon_df, occurrence_df]

        with patch.object(self.importer, "_apply_batch_updates") as mock_apply:
            with patch.object(
                self.importer, "_get_unlinked_examples", return_value="Examples"
            ):
                result = self.importer._process_taxon_links("scientific_name")

        self.assertEqual(result["linked_count"], 2)  # Two should be linked
        self.assertEqual(result["unlinked_examples"], "Examples")
        mock_apply.assert_called_once()

    @patch("pandas.read_sql")
    @patch("sqlalchemy.create_engine")
    def test_process_taxon_links_no_unlinked_occurrences(
        self, mock_create_engine, mock_read_sql
    ):
        """Test _process_taxon_links when no unlinked occurrences."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock empty occurrence DataFrame
        mock_read_sql.side_effect = [
            pd.DataFrame({"id": [1], "taxon_id": [101]}),  # taxon data
            pd.DataFrame(),  # empty occurrences
        ]

        result = self.importer._process_taxon_links("scientific_name")

        self.assertEqual(result["by_taxon_id"], 0)
        self.assertEqual(result["unlinked_examples"], "")

    @patch("pandas.read_sql")
    @patch("sqlalchemy.create_engine")
    def test_process_taxon_links_with_float_taxon_ids(
        self, mock_create_engine, mock_read_sql
    ):
        """Test _process_taxon_links with float taxon IDs."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock taxon data with float IDs that are integers
        taxon_df = pd.DataFrame(
            {
                "id": [1, 2],
                "taxon_id": [101.0, 102.0],  # Float values that are integers
            }
        )

        occurrence_df = pd.DataFrame(
            {
                "id": [1, 2],
                "scientific_name": [101, 102],  # Should match after conversion
            }
        )

        mock_read_sql.side_effect = [taxon_df, occurrence_df]

        with patch.object(self.importer, "_apply_batch_updates"):
            with patch.object(self.importer, "_get_unlinked_examples", return_value=""):
                result = self.importer._process_taxon_links("scientific_name")

        self.assertEqual(result["linked_count"], 2)

    # Tests for _apply_batch_updates method
    def test_apply_batch_updates_empty_list(self):
        """Test _apply_batch_updates with empty updates list."""
        self.importer._apply_batch_updates([])

        # Should not call database
        self.mock_db.execute_sql.assert_not_called()

    def test_apply_batch_updates_single_batch(self):
        """Test _apply_batch_updates with single batch."""
        updates = [
            {"occ_id": 1, "taxon_id": 10},
            {"occ_id": 2, "taxon_id": 20},
        ]

        self.importer._apply_batch_updates(updates)

        # Should call database once
        self.mock_db.execute_sql.assert_called_once()
        call_args = self.mock_db.execute_sql.call_args[0][0]
        self.assertIn("UPDATE occurrences", call_args)
        self.assertIn("CASE id", call_args)
        self.assertIn("WHEN 1 THEN 10", call_args)
        self.assertIn("WHEN 2 THEN 20", call_args)

    def test_apply_batch_updates_multiple_batches(self):
        """Test _apply_batch_updates with multiple batches."""
        # Create updates that will exceed batch size (1000)
        updates = [{"occ_id": i, "taxon_id": i + 100} for i in range(1500)]

        self.importer._apply_batch_updates(updates)

        # Should call database twice (2 batches)
        self.assertEqual(self.mock_db.execute_sql.call_count, 2)

    # Tests for _get_unlinked_examples method
    @patch("pandas.read_sql")
    @patch("sqlalchemy.create_engine")
    def test_get_unlinked_examples(self, mock_create_engine, mock_read_sql):
        """Test _get_unlinked_examples method."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock sample data
        sample_df = pd.DataFrame(
            {"id": [1, 2, 3], "scientific_name": ["Species1", "Species2", None]}
        )
        mock_read_sql.return_value = sample_df

        result = self.importer._get_unlinked_examples("scientific_name", limit=3)

        expected_lines = [
            "  - ID: 1, Original Taxon ID: Species1",
            "  - ID: 2, Original Taxon ID: Species2",
            "  - ID: 3, Original Taxon ID: N/A",
        ]
        self.assertEqual(result, "\n".join(expected_lines))

    @patch("pandas.read_sql")
    @patch("sqlalchemy.create_engine")
    def test_get_unlinked_examples_empty(self, mock_create_engine, mock_read_sql):
        """Test _get_unlinked_examples with empty result."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_read_sql.return_value = pd.DataFrame()

        result = self.importer._get_unlinked_examples("scientific_name")

        self.assertEqual(result, "")

    # Tests for _format_link_status method
    def test_format_link_status(self):
        """Test _format_link_status method."""
        result = self.importer._format_link_status(
            total_count=100,
            linked_count=80,
            linked_by_taxon_id=75,
            unlinked_count=20,
            unlinked_examples="  - ID: 1, Original Taxon ID: Species1\n  - ID: 2, Original Taxon ID: Species2",
            console=None,
        )

        # Verify returned data structure
        self.assertIn("linking_stats", result)
        self.assertIn("unlinked_samples", result)

        # Check linking stats
        stats = result["linking_stats"]
        self.assertEqual(stats["total"], 100)
        self.assertEqual(stats["linked"], 80)
        self.assertEqual(stats["failed"], 20)
        self.assertEqual(stats["type"], "occurrences")

        # Check unlinked samples
        samples = result["unlinked_samples"]
        self.assertEqual(len(samples), 2)
        self.assertIn("ID: 1, Original Taxon ID: Species1", samples[0])
        self.assertIn("ID: 2, Original Taxon ID: Species2", samples[1])

    def test_format_link_status_no_unlinked(self):
        """Test _format_link_status with no unlinked occurrences."""
        result = self.importer._format_link_status(
            total_count=100,
            linked_count=100,
            linked_by_taxon_id=100,
            unlinked_count=0,
            unlinked_examples="",
            console=None,
        )

        # Verify returned data structure
        self.assertIn("linking_stats", result)
        self.assertIn("unlinked_samples", result)

        # Check linking stats
        stats = result["linking_stats"]
        self.assertEqual(stats["total"], 100)
        self.assertEqual(stats["linked"], 100)
        self.assertEqual(stats["failed"], 0)

        # Should have no unlinked samples
        self.assertEqual(len(result["unlinked_samples"]), 0)

    def test_format_link_status_zero_total(self):
        """Test _format_link_status with zero total count."""
        result = self.importer._format_link_status(
            total_count=0,
            linked_count=0,
            linked_by_taxon_id=0,
            unlinked_count=0,
            unlinked_examples="",
            console=None,
        )

        # Verify returned data structure even with zero counts
        self.assertIn("linking_stats", result)
        self.assertIn("unlinked_samples", result)

        # Check linking stats
        stats = result["linking_stats"]
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["linked"], 0)
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(stats["type"], "occurrences")

        # Should have no unlinked samples
        self.assertEqual(len(result["unlinked_samples"]), 0)


if __name__ == "__main__":
    unittest.main()
