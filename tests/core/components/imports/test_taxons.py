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
    DatabaseError,
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
    def sample_taxonomy_df(self):
        """Create a sample taxonomy DataFrame."""
        return pd.DataFrame(
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

    def test_initialization(self, taxonomy_importer, mock_db):
        """Test TaxonomyImporter initialization."""
        assert taxonomy_importer.db == mock_db
        assert taxonomy_importer.db_path == "mock_db_path"
        assert hasattr(taxonomy_importer, "plugin_loader")

    # CSV Import Tests
    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv_success(
        self, mock_exists, mock_read_csv, taxonomy_importer, sample_taxonomy_df
    ):
        """Test successful CSV import."""
        mock_exists.return_value = True
        mock_read_csv.return_value = sample_taxonomy_df

        with patch.object(
            taxonomy_importer, "_prepare_dataframe", return_value=sample_taxonomy_df
        ):
            with patch.object(taxonomy_importer, "_process_dataframe", return_value=4):
                result = taxonomy_importer.import_from_csv(
                    "test.csv", ("family", "genus", "species")
                )

        assert result == "4 taxons imported from test.csv."
        mock_read_csv.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_import_from_csv_file_not_found(self, mock_exists, taxonomy_importer):
        """Test CSV import with non-existent file."""
        mock_exists.return_value = False

        with pytest.raises(FileReadError) as exc_info:
            taxonomy_importer.import_from_csv("nonexistent.csv", ("family", "genus"))

        assert "Taxonomy file not found" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv_read_error(
        self, mock_exists, mock_read_csv, taxonomy_importer
    ):
        """Test CSV import with read error."""
        mock_exists.return_value = True
        mock_read_csv.side_effect = Exception("Read error")

        with pytest.raises(FileReadError) as exc_info:
            taxonomy_importer.import_from_csv("error.csv", ("family", "genus"))

        assert "Failed to read CSV" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_csv_with_api_config(
        self, mock_exists, mock_read_csv, taxonomy_importer, sample_taxonomy_df
    ):
        """Test CSV import with API enrichment configuration."""
        mock_exists.return_value = True
        mock_read_csv.return_value = sample_taxonomy_df

        api_config = {
            "enabled": True,
            "plugin": "api_taxonomy_enricher",
            "api_key": "test_key",
        }

        with patch.object(
            taxonomy_importer, "_prepare_dataframe", return_value=sample_taxonomy_df
        ):
            with patch.object(
                taxonomy_importer, "_process_dataframe", return_value=4
            ) as mock_process:
                result = taxonomy_importer.import_from_csv(
                    "test.csv", ("family", "genus"), api_config
                )

        assert result == "4 taxons imported from test.csv."
        # Verify API config was passed through
        mock_process.assert_called_once_with(
            sample_taxonomy_df, ("family", "genus"), api_config
        )

    # Occurrences Import Tests
    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_occurrences_success(
        self, mock_exists, mock_read_csv, taxonomy_importer, sample_occurrences_df
    ):
        """Test successful import from occurrences."""
        mock_exists.return_value = True
        mock_read_csv.return_value = sample_occurrences_df

        column_mapping = {
            "taxon_id": "id_taxonref",
            "family": "family",
            "genus": "genus",
            "species": "species",
            "infra": "infra",
            "authors": "taxonref",
        }

        with patch.object(
            taxonomy_importer, "_extract_taxonomy_from_occurrences"
        ) as mock_extract:
            with patch.object(
                taxonomy_importer, "_process_taxonomy_with_relations", return_value=6
            ) as mock_process:
                mock_extract.return_value = (
                    pd.DataFrame()
                )  # Return empty DataFrame for simplicity

                result = taxonomy_importer.import_from_occurrences(
                    "occurrences.csv", ("family", "genus", "species"), column_mapping
                )

        assert result == "6 taxons extracted and imported from occurrences.csv."
        mock_extract.assert_called_once()
        mock_process.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_import_from_occurrences_missing_mapping(
        self, mock_exists, taxonomy_importer
    ):
        """Test import from occurrences with missing column mapping."""
        mock_exists.return_value = True

        # Missing required columns in mapping
        column_mapping = {
            "taxon_id": "id_taxonref",
            "family": "family",
            # Missing genus and species
        }

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer.import_from_occurrences(
                "occurrences.csv", ("family", "genus", "species"), column_mapping
            )

        assert "Missing required column mappings" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("pathlib.Path.exists")
    def test_import_from_occurrences_missing_columns_in_file(
        self, mock_exists, mock_read_csv, taxonomy_importer
    ):
        """Test import from occurrences with columns missing in file."""
        mock_exists.return_value = True

        # DataFrame missing mapped columns
        mock_read_csv.return_value = pd.DataFrame(
            {
                "id_taxonref": [1, 2],
                "family": ["F1", "F2"],
                # Missing genus and species columns
            }
        )

        column_mapping = {
            "taxon_id": "id_taxonref",
            "family": "family",
            "genus": "genus",  # This column doesn't exist in DataFrame
            "species": "species",  # This column doesn't exist in DataFrame
        }

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer.import_from_occurrences(
                "occurrences.csv", ("family", "genus", "species"), column_mapping
            )

        assert "Columns missing in occurrence file" in str(exc_info.value)

    # Process Taxonomy with Relations Tests
    def test_process_taxonomy_with_relations_success(
        self, taxonomy_importer, sample_taxonomy_df
    ):
        """Test successful processing of taxonomy with relations."""
        mock_session = Mock()
        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        taxonomy_importer.db.session = Mock(return_value=context_manager)

        with patch.object(taxonomy_importer, "_update_nested_set_values"):
            with patch("niamoto.core.components.imports.taxons.Progress"):
                result = taxonomy_importer._process_taxonomy_with_relations(
                    sample_taxonomy_df, ("family", "genus", "species")
                )

        assert result == 4  # Number of rows in sample_taxonomy_df
        mock_session.commit.assert_called()

    def test_process_taxonomy_with_relations_with_api_enrichment(
        self, taxonomy_importer
    ):
        """Test processing with API enrichment enabled."""
        # Create a DataFrame that matches what the method expects
        df = pd.DataFrame(
            {
                "full_name": ["Test Species"],
                "rank_name": ["species"],
                "authors": ["Test Author"],
                "parent_genus_name": ["Test Genus"],
                "taxon_id": [None],  # Add taxon_id column
            }
        )

        # Mock the API enricher plugin
        mock_enricher = Mock()
        mock_enricher.load_data.return_value = {
            "full_name": "Test Species",
            "rank_name": "species",
            "authors": "Test Author Enhanced",
            "taxon_id": None,
            "api_enrichment": {"source": "API", "verified": True},
        }
        # Add log_messages attribute for the method that checks it
        mock_enricher.log_messages = []

        api_config = {"enabled": True, "plugin": "api_taxonomy_enricher"}

        mock_session = Mock()
        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        taxonomy_importer.db.session = Mock(return_value=context_manager)

        with patch(
            "niamoto.core.plugins.registry.PluginRegistry.get_plugin"
        ) as mock_get_plugin:
            mock_get_plugin.return_value = lambda db: mock_enricher

            with patch.object(taxonomy_importer, "_update_nested_set_values"):
                with patch("niamoto.core.components.imports.taxons.Progress"):
                    result = taxonomy_importer._process_taxonomy_with_relations(
                        df, ("family", "genus", "species"), api_config
                    )

        assert result == 1
        mock_enricher.load_data.assert_called_once()
        mock_session.add.assert_called()

    def test_process_taxonomy_with_relations_database_error(self, taxonomy_importer):
        """Test handling of database errors during processing."""
        df = pd.DataFrame(
            {
                "full_name": ["Test"],
                "rank_name": ["family"],
                "authors": [""],  # Add required column
                "taxon_id": [None],  # Add taxon_id column
            }
        )

        mock_session = Mock()
        mock_session.add.side_effect = SQLAlchemyError("Database error")
        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        taxonomy_importer.db.session = Mock(return_value=context_manager)

        with pytest.raises(DatabaseError) as exc_info:
            with patch("niamoto.core.components.imports.taxons.Progress"):
                taxonomy_importer._process_taxonomy_with_relations(df, ("family",))

        assert "Database error" in str(exc_info.value)

    # Extract Taxonomy Tests
    def test_extract_taxonomy_from_occurrences_complete(
        self, taxonomy_importer, sample_occurrences_df
    ):
        """Test complete extraction of taxonomy from occurrences."""
        column_mapping = {
            "taxon_id": "id_taxonref",
            "family": "family",
            "genus": "genus",
            "species": "species",
            "infra": "infra",
            "authors": "taxonref",
        }

        result_df = taxonomy_importer._extract_taxonomy_from_occurrences(
            sample_occurrences_df,
            column_mapping,
            ("family", "genus", "species", "infra"),
        )

        # Verify structure
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) > 0
        assert all(
            col in result_df.columns
            for col in ["full_name", "rank_name", "authors", "taxon_id"]
        )

        # Verify hierarchy is built correctly
        families = result_df[result_df["rank_name"] == "family"]
        genera = result_df[result_df["rank_name"] == "genus"]
        species = result_df[result_df["rank_name"] == "species"]

        assert len(families) == 2  # Dilleniaceae and Myrtaceae
        assert len(genera) == 2  # Hibbertia and Syzygium
        assert len(species) >= 2  # At least lucens and pancheri

    def test_extract_taxonomy_with_missing_data(self, taxonomy_importer):
        """Test extraction with missing/incomplete data."""
        df = pd.DataFrame(
            {
                "id_taxonref": [1, 2, 3],
                "family": ["F1", None, "F3"],
                "genus": [None, "G2", "G3"],
                "species": [None, None, "S3"],
            }
        )

        column_mapping = {
            "taxon_id": "id_taxonref",
            "family": "family",
            "genus": "genus",
            "species": "species",
        }

        result_df = taxonomy_importer._extract_taxonomy_from_occurrences(
            df, column_mapping, ("family", "genus", "species")
        )

        # Should still process valid entries
        assert len(result_df) > 0

    def test_extract_taxonomy_with_duplicate_handling(self, taxonomy_importer):
        """Test that duplicates are properly handled."""
        df = pd.DataFrame(
            {
                "id_taxonref": [1, 1, 1, 2],  # Duplicates
                "family": ["F1", "F1", "F1", "F2"],
                "genus": ["G1", "G1", "G1", "G2"],
                "species": ["S1", "S1", "S1", "S2"],
            }
        )

        column_mapping = {
            "taxon_id": "id_taxonref",
            "family": "family",
            "genus": "genus",
            "species": "species",
        }

        result_df = taxonomy_importer._extract_taxonomy_from_occurrences(
            df, column_mapping, ("family", "genus", "species")
        )

        # Verify duplicates are removed
        species_entries = result_df[result_df["rank_name"] == "species"]
        unique_species_names = species_entries["full_name"].unique()
        assert len(unique_species_names) == len(species_entries)

    # Build Full Name Tests
    def test_build_full_name_complete(self, taxonomy_importer):
        """Test building full name with all components."""
        row = pd.Series(
            {
                "genus": "Hibbertia",
                "species": "lucens",
                "infra": "var. glabrata",
            }
        )

        column_mapping = {
            "genus": "genus",
            "species": "species",
            "infra": "infra",
        }

        result = taxonomy_importer._build_full_name(row, column_mapping)
        assert result == "var. glabrata"  # Infra takes precedence

    def test_build_full_name_genus_species(self, taxonomy_importer):
        """Test building full name from genus and species."""
        row = pd.Series(
            {
                "genus": "Hibbertia",
                "species": "lucens",
                "infra": None,
            }
        )

        column_mapping = {
            "genus": "genus",
            "species": "species",
            "infra": "infra",
        }

        result = taxonomy_importer._build_full_name(row, column_mapping)
        assert result == "Hibbertia lucens"

    def test_build_full_name_species_with_genus_prefix(self, taxonomy_importer):
        """Test building full name when species already contains genus."""
        row = pd.Series(
            {
                "genus": "Hibbertia",
                "species": "Hibbertia lucens",  # Already contains genus
                "infra": None,
            }
        )

        column_mapping = {
            "genus": "genus",
            "species": "species",
            "infra": "infra",
        }

        result = taxonomy_importer._build_full_name(row, column_mapping)
        assert result == "Hibbertia lucens"  # Should not duplicate genus

    def test_build_full_name_fallback_to_family(self, taxonomy_importer):
        """Test fallback to family when no other data available."""
        row = pd.Series(
            {
                "family": "Dilleniaceae",
                "genus": None,
                "species": None,
                "infra": None,
            }
        )

        column_mapping = {
            "family": "family",
            "genus": "genus",
            "species": "species",
            "infra": "infra",
        }

        result = taxonomy_importer._build_full_name(row, column_mapping)
        assert result == "Dilleniaceae"

    # Extract Authors Tests
    def test_extract_authors_from_comparison(self, taxonomy_importer):
        """Test extracting authors by comparing with species name."""
        row = pd.Series(
            {
                "species": "Hibbertia lucens",
                "taxonref": "Hibbertia lucens Brongn. & Gris ex Sebert & Pancher",
            }
        )

        column_mapping = {
            "species": "species",
            "authors": "taxonref",
        }

        result = taxonomy_importer._extract_authors(row, column_mapping)
        assert result == "Brongn. & Gris ex Sebert & Pancher"

    def test_extract_authors_direct_field(self, taxonomy_importer):
        """Test extracting authors from direct field."""
        row = pd.Series(
            {
                "author_field": "Test Author",
            }
        )

        column_mapping = {
            "authors": "author_field",
        }

        result = taxonomy_importer._extract_authors(row, column_mapping)
        assert result == "Test Author"

    def test_extract_authors_no_mapping(self, taxonomy_importer):
        """Test extracting authors with no mapping."""
        row = pd.Series(
            {
                "some_field": "value",
            }
        )

        column_mapping = {
            "species": "species",
        }

        result = taxonomy_importer._extract_authors(row, column_mapping)
        assert result == ""

    # Update Nested Set Values Tests
    def test_update_nested_set_values(self, taxonomy_importer):
        """Test updating nested set values for taxonomy tree."""
        # Create mock taxons with parent-child relationships
        taxon1 = Mock(id=1, parent_id=None, rank_name="family", full_name="F1")
        taxon2 = Mock(id=2, parent_id=1, rank_name="genus", full_name="G1")
        taxon3 = Mock(id=3, parent_id=2, rank_name="species", full_name="S1")

        mock_session = Mock()

        # First query returns all taxons
        mock_session.query.return_value.order_by.return_value.all.return_value = [
            taxon1,
            taxon2,
            taxon3,
        ]

        # Subsequent queries for children
        def query_side_effect(*args):
            query_mock = Mock()
            if args and hasattr(args[0], "id"):
                # Return appropriate children based on parent_id
                if args[0].id == 1:
                    query_mock.filter.return_value.order_by.return_value.all.return_value = [
                        (2,)
                    ]
                elif args[0].id == 2:
                    query_mock.filter.return_value.order_by.return_value.all.return_value = [
                        (3,)
                    ]
                else:
                    query_mock.filter.return_value.order_by.return_value.all.return_value = []
            return query_mock

        mock_session.query.side_effect = [
            # First call for all taxons
            Mock(
                order_by=Mock(
                    return_value=Mock(all=Mock(return_value=[taxon1, taxon2, taxon3]))
                )
            ),
            # Second call for root taxons
            Mock(
                filter=Mock(
                    return_value=Mock(
                        order_by=Mock(
                            return_value=Mock(all=Mock(return_value=[taxon1]))
                        )
                    )
                )
            ),
            # Subsequent calls for children
            Mock(
                filter=Mock(
                    return_value=Mock(
                        order_by=Mock(return_value=Mock(all=Mock(return_value=[(2,)])))
                    )
                )
            ),
            Mock(
                filter=Mock(
                    return_value=Mock(
                        order_by=Mock(return_value=Mock(all=Mock(return_value=[(3,)])))
                    )
                )
            ),
            Mock(
                filter=Mock(
                    return_value=Mock(
                        order_by=Mock(return_value=Mock(all=Mock(return_value=[])))
                    )
                )
            ),
        ]

        taxonomy_importer._update_nested_set_values(mock_session)

        # Verify nested set values were assigned
        assert taxon1.lft == 1
        assert taxon1.rght == 6
        assert taxon1.level == 0

        assert taxon2.lft == 2
        assert taxon2.rght == 5
        assert taxon2.level == 1

        assert taxon3.lft == 3
        assert taxon3.rght == 4
        assert taxon3.level == 2

        mock_session.commit.assert_called_once()

    # Error Handling Tests
    def test_prepare_dataframe_missing_required_fields(self, taxonomy_importer):
        """Test prepare_dataframe with missing required fields."""
        df = pd.DataFrame(
            {
                "id_taxon": [1, 2],
                # Missing full_name and rank_name
            }
        )

        with pytest.raises(DataValidationError) as exc_info:
            taxonomy_importer._prepare_dataframe(df, ("family", "genus"))

        assert "Required field" in str(exc_info.value)

    def test_create_or_update_taxon_database_error(self, taxonomy_importer):
        """Test create_or_update_taxon with database error."""
        row = {
            "id_taxon": 1,
            "full_name": "Test",
            "authors": "Author",
            "rank_name": "species",
            "parent_id": None,
        }

        mock_session = Mock()
        mock_session.query.side_effect = SQLAlchemyError("DB Error")

        with pytest.raises(DatabaseError) as exc_info:
            taxonomy_importer._create_or_update_taxon(
                row, mock_session, ("family", "genus", "species")
            )

        assert "Failed to create/update taxon" in str(exc_info.value)

    # Integration Tests
    @pytest.mark.integration
    def test_full_import_workflow(self, taxonomy_importer, temp_config_dir):
        """Test complete import workflow from CSV to database."""
        # Create a temporary CSV file
        csv_path = os.path.join(temp_config_dir, "taxonomy.csv")
        df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3],
                "full_name": ["Family1", "Genus1", "Species1"],
                "authors": ["", "", "Author1"],
                "rank_name": ["family", "genus", "species"],
                "family": [1, 1, 1],
                "genus": [None, 2, 2],
                "species": [None, None, 3],
            }
        )
        df.to_csv(csv_path, index=False)

        # Mock database operations
        mock_session = Mock()
        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        taxonomy_importer.db.session = Mock(return_value=context_manager)

        # Patch _process_dataframe to use _process_taxonomy_with_relations internally
        def mock_process_dataframe(df, ranks, api_config=None):
            return taxonomy_importer._process_taxonomy_with_relations(
                df, ranks, api_config
            )

        with patch.object(
            taxonomy_importer, "_process_dataframe", side_effect=mock_process_dataframe
        ):
            with patch.object(taxonomy_importer, "_update_nested_set_values"):
                with patch("niamoto.core.components.imports.taxons.Progress"):
                    result = taxonomy_importer.import_from_csv(
                        csv_path, ("family", "genus", "species")
                    )

        assert "3 taxons imported" in result
        assert mock_session.add.call_count >= 3
        assert mock_session.commit.called

    @pytest.mark.parametrize(
        "rank_names,expected",
        [
            (("famille", "genre", "espèce"), ["famille", "genre", "espèce"]),
            (("id_famille", "id_genre", "id_espèce"), ["famille", "genre", "espèce"]),
            (
                ("family", "genus", "species", "subspecies"),
                ["family", "genus", "species", "subspecies"],
            ),
        ],
    )
    def test_get_rank_names_from_config(self, taxonomy_importer, rank_names, expected):
        """Test extraction of rank names from configuration."""
        result = taxonomy_importer._get_rank_names_from_config(rank_names)
        assert result == expected

    def test_convert_to_correct_type_various_inputs(self, taxonomy_importer):
        """Test type conversion for various inputs."""
        assert taxonomy_importer._convert_to_correct_type(1.0) == 1
        assert taxonomy_importer._convert_to_correct_type(1.5) == 1.5
        assert taxonomy_importer._convert_to_correct_type("text") == "text"
        assert taxonomy_importer._convert_to_correct_type(None) is None
        assert taxonomy_importer._convert_to_correct_type([1, 2, 3]) == [1, 2, 3]
