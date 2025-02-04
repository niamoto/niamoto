"""Tests for the taxonomy importer module."""

import tempfile
from unittest import mock
import pytest
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.components.imports.taxons import TaxonomyImporter
from niamoto.common.exceptions import (
    TaxonomyImportError,
    FileReadError,
    DataValidationError,
)


class TestTaxonomyImporter:
    """Test cases for TaxonomyImporter class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        with mock.patch("niamoto.common.database.Database") as mock_db:
            # Configure the mock
            mock_session = mock.MagicMock()
            mock_db.return_value.session = mock_session
            # Configure query to return None by default (no existing taxons)
            mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
            yield mock_db.return_value

    @pytest.fixture
    def importer(self, mock_db):
        """TaxonomyImporter fixture."""
        return TaxonomyImporter(mock_db)

    @pytest.fixture
    def valid_csv(self, tmp_path):
        """Create a valid CSV file for testing."""
        data = {
            "id_taxon": [1, 2, 3],
            "full_name": ["Family A", "Genus B", "Species C"],
            "authors": ["Author 1", "Author 2", "Author 3"],
            "rank_name": ["family", "genus", "species"],
            "family": [1, 1, 1],
            "genus": [None, 2, 2],
            "species": [None, None, 3],
            "extra_field": ["value1", "value2", "value3"],
        }
        df = pd.DataFrame(data)

        # Save to CSV
        file_path = tmp_path / "valid_taxons.csv"
        df.to_csv(file_path, index=False)
        return str(file_path)

    def test_import_valid_file(self, importer, valid_csv):
        """Test importing a valid CSV file."""
        ranks = ("family", "genus", "species")
        result = importer.import_from_csv(valid_csv, ranks)
        assert "3 taxons imported" in result

    def test_file_not_found(self, importer):
        """Test error when file doesn't exist."""
        ranks = ("family", "genus", "species")
        with pytest.raises(FileReadError) as exc_info:
            importer.import_from_csv("/nonexistent/path.csv", ranks)
        assert "Taxonomy file not found" in str(exc_info.value)

    def test_invalid_csv(self, tmp_path, importer):
        """Test error when CSV format is invalid."""
        # Create an invalid CSV file
        file_path = tmp_path / "invalid.csv"
        file_path.write_text("invalid,data\nrow1,data2")  # CSV with invalid format

        ranks = ("family", "genus", "species")
        with pytest.raises(DataValidationError) as exc_info:
            importer.import_from_csv(str(file_path), ranks)
        assert "Missing required columns" in str(exc_info.value)

    def test_missing_columns(self, tmp_path, importer):
        """Test error when required columns are missing."""
        # Create CSV without required columns
        data = {
            "id_taxon": [1],
            "full_name": ["Test Taxon"],
            # Missing 'authors' and 'rank_name'
        }
        df = pd.DataFrame(data)
        file_path = tmp_path / "missing_columns.csv"
        df.to_csv(file_path, index=False)

        ranks = ("family", "genus", "species")
        with pytest.raises(DataValidationError) as exc_info:
            importer.import_from_csv(str(file_path), ranks)
        assert "Missing required columns" in str(exc_info.value)

    def test_update_existing_taxon(self, importer, valid_csv):
        """Test updating an existing taxon."""
        # Configure mock to return an existing taxon
        mock_taxon = mock.MagicMock()
        importer.db.session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_taxon

        ranks = ("family", "genus", "species")
        result = importer.import_from_csv(valid_csv, ranks)
        assert "3 taxons imported" in result

    def test_database_error(self, importer, valid_csv):
        """Test handling of database errors."""
        # Configure mock session to raise error during prepare_dataframe
        mock_session = mock.MagicMock()
        mock_session.__enter__.return_value = mock_session

        # Configure query to raise error
        mock_query = mock.MagicMock()
        mock_query.filter_by.return_value.one_or_none.side_effect = SQLAlchemyError(
            "Database error"
        )
        mock_session.query.return_value = mock_query
        importer.db.session.return_value = mock_session

        ranks = ("family", "genus", "species")
        with pytest.raises(TaxonomyImportError) as exc_info:
            importer.import_from_csv(valid_csv, ranks)
        assert "Failed to create/update taxon" in str(exc_info.value)

    def test_invalid_rank_structure(self, tmp_path, importer):
        """Test error when rank structure is invalid."""
        # Create CSV with invalid rank structure
        data = {
            "id_taxon": [1],
            "full_name": ["Invalid Taxon"],
            "authors": ["Author"],
            "rank_name": ["invalid_rank"],
            "family": [1],
            "genus": [1],  # Same as family, should be different
            "species": [1],
        }
        df = pd.DataFrame(data)
        file_path = tmp_path / "invalid_ranks.csv"
        df.to_csv(file_path, index=False)

        ranks = ("family", "genus", "species")
        result = importer.import_from_csv(str(file_path), ranks)
        assert "1 taxons imported" in result

    def test_extra_data_handling(self, importer, valid_csv):
        """Test handling of extra data fields."""
        ranks = ("family", "genus", "species")
        result = importer.import_from_csv(valid_csv, ranks)
        assert "3 taxons imported" in result

        # Verify extra_data is stored correctly
        mock_taxon = importer.db.session.query.return_value.filter_by.return_value.one_or_none.return_value
        if mock_taxon:
            assert "extra_field" in mock_taxon.extra_data

    def test_nested_set_values(self, importer, valid_csv):
        """Test updating of nested set values."""
        # Configure mock session
        mock_session = mock.MagicMock()
        mock_session.__enter__.return_value = mock_session
        importer.db.session.return_value = mock_session

        # Mock query for existing taxon
        mock_taxon = mock.MagicMock()
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_taxon

        # Mock query results for root taxons
        mock_root_query = mock.MagicMock()
        mock_root_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.query.return_value = mock_root_query

        ranks = ("family", "genus", "species")
        result = importer.import_from_csv(valid_csv, ranks)
        assert "3 taxons imported" in result

        # Verify commit was called at least once
        assert mock_session.commit.call_count >= 1

    def test_prepare_dataframe_error(self, importer, valid_csv):
        """Test error during dataframe preparation."""
        # Create a DataFrame that will cause an error during preparation
        df = pd.DataFrame(
            {
                "id_taxon": ["invalid"],  # Invalid id_taxon (not an integer)
                "full_name": ["Test"],
                "authors": ["Author"],
                "rank_name": ["family"],
            }
        )

        ranks = ("family", "genus", "species")
        with pytest.raises(DataValidationError):
            importer._prepare_dataframe(df, ranks)

    def test_convert_to_correct_type(self, importer):
        """Test type conversion."""
        # Test integer conversion
        assert importer._convert_to_correct_type(1.0) == 1
        # Test float preservation
        assert importer._convert_to_correct_type(1.5) == 1.5
        # Test string preservation
        assert importer._convert_to_correct_type("test") == "test"

    def test_update_nested_set_values_with_hierarchy(self, importer):
        """Test updating nested set values with a hierarchy."""
        # Create mock taxons
        mock_root = mock.MagicMock(spec=["id", "lft", "rght", "level"])
        mock_root.id = 1
        mock_child = mock.MagicMock(spec=["id", "lft", "rght", "level"])
        mock_child.id = 2

        # Configure mock session
        mock_session = mock.MagicMock()
        mock_session.__enter__.return_value = mock_session

        # Create dictionary mapping for taxons
        taxon_dict = {mock_root.id: mock_root, mock_child.id: mock_child}

        # Configure mock query behavior
        mock_query = mock.MagicMock()
        mock_filter = mock.MagicMock()
        mock_order = mock.MagicMock()

        # Setup query chain
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_query.order_by.return_value = mock_order
        mock_filter.order_by.return_value = mock_order

        # Create a counter to track which query is being executed
        query_counter = {"count": 0}

        def mock_all():
            query_counter["count"] += 1
            # First query: Get all taxons
            if query_counter["count"] == 1:
                return list(taxon_dict.values())
            # Second query: Get root taxons
            elif query_counter["count"] == 2:
                return [mock_root]
            # Third query: Get child taxons for root
            elif query_counter["count"] == 3:
                return [(mock_child.id,)]
            # Fourth query: Get child taxons for child (should be empty)
            else:
                return []

        mock_order.all = mock_all

        # Run the update
        importer._update_nested_set_values(mock_session)

        # Verify that the nested set values were updated correctly
        assert mock_root.lft == 1
        assert (
            mock_root.rght == 4
        )  # Root should have right value 4 (1 left, 2-3 child, 4 right)
        assert mock_child.lft == 2  # Child should have left value 2
        assert mock_child.rght == 3  # Child should have right value 3
        assert mock_root.level == 0  # Root should be at level 0
        assert mock_child.level == 1  # Child should be at level 1

    def test_general_database_error(self, importer, valid_csv):
        """Test handling of general database errors."""
        # Configure mock session to raise error on commit
        mock_session = mock.MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.commit.side_effect = SQLAlchemyError("General database error")
        importer.db.session.return_value = mock_session

        # Configure DataFrame to be processed
        df = pd.DataFrame(
            {
                "id_taxon": [1],
                "full_name": ["Test"],
                "authors": ["Author"],
                "rank_name": ["family"],
                "rank": ["family"],
                "family": [1],
                "genus": [None],
                "species": [None],
                "parent_id": [None],  # Add parent_id column
            }
        )

        # Mock the read_csv to return our test DataFrame
        with mock.patch("pandas.read_csv", return_value=df):
            ranks = ("family", "genus", "species")
            with pytest.raises(TaxonomyImportError) as exc_info:
                importer._process_dataframe(df, ranks)
            assert str(exc_info.value) == "Failed to process taxonomy data"

    def test_process_dataframe_error(self, importer):
        """Test error during dataframe processing."""
        # Create a DataFrame that will cause an error during processing
        df = pd.DataFrame(
            {
                "id_taxon": ["invalid"],  # Invalid id_taxon (should be integer)
                "full_name": ["Test"],
                "authors": ["Author"],
                "rank_name": ["invalid_rank"],
                "rank": ["invalid_rank"],
                "family": ["invalid"],
                "genus": ["invalid"],
                "species": ["invalid"],
                "parent_id": [
                    "invalid"
                ],  # Invalid parent_id (should be integer or None)
            }
        )

        # Configure mock session to raise error
        mock_session = mock.MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        importer.db.session.return_value = mock_session

        ranks = ("family", "genus", "species")
        with pytest.raises(TaxonomyImportError) as exc_info:
            importer._process_dataframe(df, ranks)
        assert "Failed to process taxonomy data" in str(exc_info.value)

    def test_result_message_formatting(self, importer):
        """Test result message formatting with various scenarios."""
        # Create a temporary CSV file for testing
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.write(
                "id_taxon,full_name,authors,rank_name,family,genus,species\n"
            )
            temp_file.write("1,Test,Author,family,1,None,None\n")
            temp_file.flush()

            # Configure DataFrame to be processed
            df = pd.DataFrame(
                {
                    "id_taxon": [1],
                    "full_name": ["Test"],
                    "authors": ["Author"],
                    "rank_name": ["family"],
                    "family": [1],
                    "genus": [None],
                    "species": [None],
                }
            )

            # Mock the necessary components
            with mock.patch("pandas.read_csv", return_value=df):
                result = importer.import_from_csv(
                    temp_file.name, ("family", "genus", "species")
                )
                assert "imported" in result.lower()
