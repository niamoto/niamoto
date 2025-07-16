"""
Tests for the TaxonomyImporter class.

This module contains comprehensive tests for the taxonomy import functionality,
including API enrichment, error handling, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import tempfile
import os
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.components.imports.taxons import TaxonomyImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
)


class TestTaxonomyImporter:
    """Test suite for the TaxonomyImporter class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        mock = Mock()
        mock.db_path = "mock_db_path"
        mock.engine = Mock()
        mock.session = Mock()
        return mock

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        import shutil

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def taxonomy_importer(self, mock_db, temp_config_dir):
        """Create a TaxonomyImporter instance with mocked dependencies."""
        with patch("niamoto.core.components.imports.taxons.Config") as mock_config:
            mock_config.return_value.plugins_dir = temp_config_dir
            return TaxonomyImporter(mock_db)

    @pytest.fixture
    def sample_occurrences_df(self):
        """Create a sample occurrences DataFrame."""
        return pd.DataFrame(
            {
                "id_taxonref": [1001, 1002, 1003, 1001, 1004],
                "family": [
                    "Dilleniaceae",
                    "Dilleniaceae",
                    "Dilleniaceae",
                    "Dilleniaceae",
                    "Myrtaceae",
                ],
                "genus": [
                    "Hibbertia",
                    "Hibbertia",
                    "Hibbertia",
                    "Hibbertia",
                    "Syzygium",
                ],
                "species": ["lucens", "lucens", "pancheri", "lucens", "acre"],
                "infra": [None, None, None, None, None],
                "taxonref": [
                    "Hibbertia lucens Brongn. & Gris ex Sebert & Pancher",
                    "Hibbertia lucens Brongn. & Gris ex Sebert & Pancher",
                    "Hibbertia pancheri Briquet",
                    "Hibbertia lucens Brongn. & Gris ex Sebert & Pancher",
                    "Syzygium acre (Merr. & L.M.Perry) Craven",
                ],
            }
        )

    @pytest.fixture
    def hierarchy_config(self):
        """Create a sample hierarchy configuration."""
        return {
            "levels": [
                {"name": "family", "column": "family"},
                {"name": "genus", "column": "genus"},
                {"name": "species", "column": "species"},
                {"name": "infra", "column": "infra"},
            ],
            "taxon_id_column": "id_taxonref",
            "authors_column": "taxonref",
        }

    def test_initialization(self, taxonomy_importer, mock_db):
        """Test TaxonomyImporter initialization."""
        assert taxonomy_importer.db == mock_db
        assert taxonomy_importer.db_path == "mock_db_path"
        assert hasattr(taxonomy_importer, "plugin_loader")

    # Taxonomy Import Tests
    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_taxonomy_success(
        self,
        mock_exists,
        mock_read_csv,
        taxonomy_importer,
        sample_occurrences_df,
        hierarchy_config,
    ):
        """Test successful taxonomy import from occurrences."""
        mock_exists.return_value = True
        mock_read_csv.return_value = sample_occurrences_df

        with patch.object(
            taxonomy_importer, "_extract_taxonomy_from_occurrences"
        ) as mock_extract:
            with patch.object(
                taxonomy_importer, "_process_taxonomy_with_relations", return_value=6
            ) as mock_process:
                mock_extract.return_value = (
                    pd.DataFrame()
                )  # Return empty DataFrame for simplicity

                result = taxonomy_importer.import_taxonomy(
                    "occurrences.csv", hierarchy_config
                )

        assert result == "6 taxons extracted and imported from occurrences.csv."
        mock_extract.assert_called_once()
        mock_process.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_import_taxonomy_file_not_found(
        self, mock_exists, taxonomy_importer, hierarchy_config
    ):
        """Test taxonomy import with non-existent file."""
        mock_exists.return_value = False

        with pytest.raises(FileReadError) as exc_info:
            taxonomy_importer.import_taxonomy("nonexistent.csv", hierarchy_config)

        assert "Occurrences file not found" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_taxonomy_read_error(
        self, mock_exists, mock_read_csv, taxonomy_importer, hierarchy_config
    ):
        """Test taxonomy import with read error."""
        mock_exists.return_value = True
        mock_read_csv.side_effect = Exception("Read error")

        with pytest.raises(FileReadError) as exc_info:
            taxonomy_importer.import_taxonomy("error.csv", hierarchy_config)

        assert "Failed to read CSV" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    def test_import_taxonomy_missing_hierarchy_config(
        self, mock_exists, taxonomy_importer
    ):
        """Test taxonomy import with missing hierarchy configuration."""
        mock_exists.return_value = True

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer.import_taxonomy("occurrences.csv", None)

        assert "Hierarchy configuration is required" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    def test_import_taxonomy_missing_levels(self, mock_exists, taxonomy_importer):
        """Test taxonomy import with missing levels in hierarchy configuration."""
        mock_exists.return_value = True
        hierarchy_config = {"taxon_id_column": "id_taxonref"}  # Missing 'levels'

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer.import_taxonomy("occurrences.csv", hierarchy_config)

        assert "Missing 'levels' in hierarchy configuration" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    def test_import_taxonomy_invalid_level_config(self, mock_exists, taxonomy_importer):
        """Test taxonomy import with invalid level configuration."""
        mock_exists.return_value = True
        hierarchy_config = {
            "levels": [
                {"name": "family"},  # Missing 'column'
                {"column": "genus"},  # Missing 'name'
            ]
        }

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer.import_taxonomy("occurrences.csv", hierarchy_config)

        assert "Each level must have 'name' and 'column'" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_taxonomy_missing_columns_in_file(
        self, mock_exists, mock_read_csv, taxonomy_importer
    ):
        """Test taxonomy import with columns missing in file."""
        mock_exists.return_value = True

        # DataFrame missing mapped columns
        mock_read_csv.return_value = pd.DataFrame(
            {
                "id_taxonref": [1, 2],
                "family": ["F1", "F2"],
                # Missing genus and species columns
            }
        )

        hierarchy_config = {
            "levels": [
                {"name": "family", "column": "family"},
                {"name": "genus", "column": "genus"},  # This column doesn't exist
                {"name": "species", "column": "species"},  # This column doesn't exist
            ],
            "taxon_id_column": "id_taxonref",
        }

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer.import_taxonomy("occurrences.csv", hierarchy_config)

        assert "Columns missing in occurrence file" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_taxonomy_with_api_config(
        self,
        mock_exists,
        mock_read_csv,
        taxonomy_importer,
        sample_occurrences_df,
        hierarchy_config,
    ):
        """Test taxonomy import with API enrichment configuration."""
        mock_exists.return_value = True
        mock_read_csv.return_value = sample_occurrences_df

        api_config = {
            "enabled": True,
            "plugin": "api_taxonomy_enricher",
            "api_key": "test_key",
        }

        with patch.object(
            taxonomy_importer, "_extract_taxonomy_from_occurrences"
        ) as mock_extract:
            with patch.object(
                taxonomy_importer, "_process_taxonomy_with_relations", return_value=4
            ) as mock_process:
                mock_extract.return_value = pd.DataFrame()

                result = taxonomy_importer.import_taxonomy(
                    "test.csv", hierarchy_config, api_config
                )

        assert result == "4 taxons extracted and imported from test.csv."
        # Verify API config was passed through
        _, _, api_arg = mock_process.call_args[0]
        assert api_arg == api_config

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_taxonomy_extended_hierarchy(
        self, mock_exists, mock_read_csv, taxonomy_importer
    ):
        """Test taxonomy import with extended hierarchy levels."""
        mock_exists.return_value = True

        # Create occurrences with extended hierarchy
        extended_df = pd.DataFrame(
            {
                "id_taxonref": [1, 2, 3],
                "kingdom": ["Plantae", "Plantae", "Plantae"],
                "phylum": ["Tracheophyta", "Tracheophyta", "Tracheophyta"],
                "class": ["Magnoliopsida", "Magnoliopsida", "Magnoliopsida"],
                "order": ["Dilleniaceae", "Dilleniaceae", "Myrtales"],
                "family": ["Dilleniaceae", "Dilleniaceae", "Myrtaceae"],
                "subfamily": ["Hibbertoideae", "Hibbertoideae", "Myrtoideae"],
                "tribe": ["Hibbertieae", "Hibbertieae", "Syzygieae"],
                "genus": ["Hibbertia", "Hibbertia", "Syzygium"],
                "species": ["lucens", "pancheri", "acre"],
                "authors": ["Brongn. & Gris", "Briquet", "(Merr. & L.M.Perry) Craven"],
            }
        )
        mock_read_csv.return_value = extended_df

        # Extended hierarchy configuration
        extended_hierarchy = {
            "levels": [
                {"name": "kingdom", "column": "kingdom"},
                {"name": "phylum", "column": "phylum"},
                {"name": "class", "column": "class"},
                {"name": "order", "column": "order"},
                {"name": "family", "column": "family"},
                {"name": "subfamily", "column": "subfamily"},
                {"name": "tribe", "column": "tribe"},
                {"name": "genus", "column": "genus"},
                {"name": "species", "column": "species"},
            ],
            "taxon_id_column": "id_taxonref",
            "authors_column": "authors",
        }

        with patch.object(
            taxonomy_importer, "_extract_taxonomy_from_occurrences"
        ) as mock_extract:
            with patch.object(
                taxonomy_importer, "_process_taxonomy_with_relations", return_value=15
            ):
                mock_extract.return_value = pd.DataFrame()

                result = taxonomy_importer.import_taxonomy(
                    "extended_occurrences.csv", extended_hierarchy
                )

        assert (
            result == "15 taxons extracted and imported from extended_occurrences.csv."
        )

        # Verify that all levels were passed correctly
        call_args = mock_extract.call_args[0]
        column_mapping = call_args[1]
        ranks = call_args[2]

        assert len(ranks) == 9  # All 9 levels
        assert "subfamily" in column_mapping
        assert "tribe" in column_mapping

    # Process Taxonomy with Relations Tests
    def test_process_taxonomy_with_relations_success(self, taxonomy_importer):
        """Test successful processing of taxonomy with relations."""
        sample_taxonomy_df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3, 4],
                "full_name": [
                    "Dilleniaceae",
                    "Hibbertia",
                    "Hibbertia lucens",
                    "Hibbertia pancheri",
                ],
                "authors": ["", "", "Brongn. & Gris", "Briquet"],
                "rank_name": ["family", "genus", "species", "species"],
                "family": [1, 1, 1, 1],
                "genus": [None, 2, 2, 2],
                "species": [None, None, 3, 4],
            }
        )

        mock_session = Mock()
        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        taxonomy_importer.db.session = Mock(return_value=context_manager)

        with patch.object(taxonomy_importer, "_update_nested_set_values"):
            with patch("niamoto.common.progress.get_progress_tracker") as mock_tracker:
                mock_progress = Mock()
                mock_context = Mock()
                mock_context.__enter__ = Mock(return_value=Mock())
                mock_context.__exit__ = Mock(return_value=None)
                mock_progress.track = Mock(return_value=mock_context)
                mock_tracker.return_value = mock_progress

                result = taxonomy_importer._process_taxonomy_with_relations(
                    sample_taxonomy_df, ("family", "genus", "species")
                )

        assert result == 4  # Number of rows in sample_taxonomy_df
        mock_session.commit.assert_called()

    def test_process_taxonomy_with_relations_with_api_enrichment(
        self, taxonomy_importer
    ):
        """Test processing taxonomy with API enrichment."""
        sample_taxonomy_df = pd.DataFrame(
            {
                "id_taxon": [1, 2],
                "full_name": ["Dilleniaceae", "Hibbertia"],
                "authors": ["", ""],
                "rank_name": ["family", "genus"],
                "family": [1, 1],
                "genus": [None, 2],
            }
        )

        api_config = {
            "enabled": True,
            "plugin": "test_enricher",
        }

        mock_session = Mock()
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        taxonomy_importer.db.session = Mock(return_value=context_manager)

        # Mock the PluginRegistry to return a mock enricher class
        mock_enricher = Mock()
        mock_enricher.load_data.return_value = {
            "external_id": "12345",
            "conservation_status": "LC",
        }
        mock_enricher.log_messages = []  # Add log_messages attribute
        mock_enricher_class = Mock(return_value=mock_enricher)

        with patch(
            "niamoto.core.plugins.registry.PluginRegistry.get_plugin",
            return_value=mock_enricher_class,
        ):
            with patch.object(taxonomy_importer, "_update_nested_set_values"):
                with patch(
                    "niamoto.common.progress.get_progress_tracker"
                ) as mock_tracker:
                    mock_progress = Mock()
                    mock_context = Mock()
                    mock_context.__enter__ = Mock(return_value=Mock())
                    mock_context.__exit__ = Mock(return_value=None)
                    mock_progress.track = Mock(return_value=mock_context)
                    mock_tracker.return_value = mock_progress

                    with patch("builtins.print"):  # Suppress print statements
                        result = taxonomy_importer._process_taxonomy_with_relations(
                            sample_taxonomy_df, ("family", "genus"), api_config
                        )

            assert result == 2
            # Verify enricher was called for each taxon
            assert mock_enricher.load_data.call_count == 2

    def test_extract_taxonomy_from_occurrences(self, taxonomy_importer):
        """Test taxonomy extraction from occurrences."""
        occurrences_df = pd.DataFrame(
            {
                "id_taxonref": [1, 2, 3, 1, 2],
                "family": ["Fabaceae", "Fabaceae", "Myrtaceae", "Fabaceae", "Fabaceae"],
                "genus": ["Acacia", "Acacia", "Syzygium", "Acacia", "Acacia"],
                "species": [
                    "mangium",
                    "auriculiformis",
                    "jambos",
                    "mangium",
                    "auriculiformis",
                ],
                "taxonref": [
                    "Acacia mangium Willd.",
                    "Acacia auriculiformis A.Cunn. ex Benth.",
                    "Syzygium jambos (L.) Alston",
                    "Acacia mangium Willd.",
                    "Acacia auriculiformis A.Cunn. ex Benth.",
                ],
            }
        )

        column_mapping = {
            "family": "family",
            "genus": "genus",
            "species": "species",
            "taxon_id": "id_taxonref",
            "authors": "taxonref",
        }

        result_df = taxonomy_importer._extract_taxonomy_from_occurrences(
            occurrences_df, column_mapping, ("family", "genus", "species")
        )

        # Should have unique combinations
        assert (
            len(result_df) == 7
        )  # 2 families + 2 genera + 3 species = 7 unique taxons

        # Check that all ranks are present
        assert set(result_df["rank_name"].unique()) == {"family", "genus", "species"}

        # Check that taxon IDs are preserved
        species_rows = result_df[result_df["rank_name"] == "species"]
        assert set(species_rows["taxon_id"]) == {1, 2, 3}

    def test_update_nested_set_values(self, taxonomy_importer):
        """Test updating nested set values."""
        mock_session = Mock()

        # Mock the SQLAlchemy operations to return empty results
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = []
        mock_query.filter.return_value = mock_query
        mock_session.query.return_value = mock_query

        # Call the method - should not raise any exceptions
        taxonomy_importer._update_nested_set_values(mock_session)

        # Verify session operations were called
        assert mock_session.query.called
        mock_session.commit.assert_called_once()

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_taxonomy_database_error(
        self,
        mock_exists,
        mock_read_csv,
        taxonomy_importer,
        sample_occurrences_df,
        hierarchy_config,
    ):
        """Test taxonomy import with database error."""
        mock_exists.return_value = True
        mock_read_csv.return_value = sample_occurrences_df

        with patch.object(
            taxonomy_importer, "_extract_taxonomy_from_occurrences"
        ) as mock_extract:
            with patch.object(
                taxonomy_importer, "_process_taxonomy_with_relations"
            ) as mock_process:
                mock_extract.return_value = pd.DataFrame()
                mock_process.side_effect = SQLAlchemyError("Database error")

                with pytest.raises(Exception) as exc_info:
                    taxonomy_importer.import_taxonomy(
                        "occurrences.csv", hierarchy_config
                    )

                assert "Failed to extract and import taxonomy from occurrences" in str(
                    exc_info.value
                )
