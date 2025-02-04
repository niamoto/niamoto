"""
Tests for the OccurrenceImporter class.
"""

import unittest
from pathlib import Path
import pandas as pd
import sqlalchemy

from niamoto.common.database import Database
from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    CSVError,
)


class TestOccurrenceImporter(unittest.TestCase):
    """Test cases for the OccurrenceImporter class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create test directories
        self.test_dir = Path("tests/test_data")
        self.db_dir = self.test_dir / "db"
        self.source_dir = self.test_dir / "sources"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(parents=True, exist_ok=True)

        # Set up test database
        self.db_path = str(self.db_dir / "test.db")
        self.db = Database(self.db_path)
        self.importer = OccurrenceImporter(self.db)

        # Create test data
        self.csv_file = self.source_dir / "test_occurrences.csv"
        self.create_test_csv()
        self.create_test_database()

    def create_test_csv(self):
        """Create a test CSV file with sample data."""
        data = {
            "id_source": [1, 2],
            "source": ["test1", "test2"],
            "taxon_id": [100, 101],
            "location": ["POINT(1 1)", "POINT(2 2)"],
        }
        df = pd.DataFrame(data)
        df.to_csv(self.csv_file, index=False)

    def create_test_database(self):
        """Create test database tables."""
        with self.db.engine.connect() as conn:
            # Create taxon_ref table
            conn.execute(
                sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS taxon_ref (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            """)
            )

            # Insert test taxa
            conn.execute(
                sqlalchemy.text("""
                INSERT INTO taxon_ref (id, name) VALUES
                (100, 'Test Taxon 1'),
                (101, 'Test Taxon 2')
            """)
            )
            conn.commit()

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_analyze_data_success(self):
        """Test successful CSV data analysis."""
        result = self.importer.analyze_data(str(self.csv_file))
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(item, tuple) for item in result))
        self.assertTrue(all(len(item) == 2 for item in result))

    def test_analyze_data_nonexistent_file(self):
        """Test analyzing a non-existent CSV file."""
        with self.assertRaises(CSVError):
            self.importer.analyze_data("nonexistent.csv")

    def test_import_valid_occurrences_success(self):
        """Test successful import of valid occurrences."""
        result = self.importer.import_valid_occurrences(
            str(self.csv_file), "taxon_id", "location"
        )
        self.assertIsInstance(result, str)
        self.assertIn("valid occurrences imported", result.lower())

    def test_import_nonexistent_file(self):
        """Test importing from a non-existent file."""
        with self.assertRaises(FileReadError) as cm:
            self.importer.import_valid_occurrences(
                "nonexistent.csv", "taxon_id", "location"
            )
        self.assertIn("not found", str(cm.exception))

    def test_import_missing_required_column(self):
        """Test importing with missing required columns."""
        # Create CSV without required column
        data = {"col1": [1, 2], "col2": [3, 4]}
        df = pd.DataFrame(data)
        csv_path = self.source_dir / "missing_column.csv"
        df.to_csv(csv_path, index=False)

        with self.assertRaises(DataValidationError) as cm:
            self.importer.import_valid_occurrences(
                str(csv_path), "taxon_id", "location"
            )
        self.assertIn("missing required column", str(cm.exception).lower())

    def test_import_invalid_taxon_ids(self):
        """Test that invalid taxon IDs are detected."""
        data = {
            "taxon_id": [999],  # Non-existent ID
            "location": ["POINT(1 1)"],
        }
        df = pd.DataFrame(data)
        csv_path = self.source_dir / "invalid_taxons.csv"
        df.to_csv(csv_path, index=False)

        result = self.importer.import_valid_occurrences(
            str(csv_path), "taxon_id", "location"
        )
        self.assertIn("0 valid occurrences imported", result)

    def test_import_with_null_values(self):
        """Test importing occurrences with NULL values."""
        # Create CSV with NULL values
        data = {
            "id_source": [1, None],
            "source": [None, "test2"],
            "taxon_id": [100, 101],
            "location": ["POINT(1 1)", "POINT(2 2)"],
        }
        df = pd.DataFrame(data)
        csv_path = self.source_dir / "null_values.csv"
        df.to_csv(csv_path, index=False)

        result = self.importer.import_valid_occurrences(
            str(csv_path), "taxon_id", "location"
        )
        self.assertIn("2 valid occurrences imported", result)

        # Verify NULL values were imported correctly
        with self.db.engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text(
                    "SELECT id_source, source FROM occurrences WHERE id_source IS NULL"
                )
            ).fetchone()
            self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
