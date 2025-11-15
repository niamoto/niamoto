"""Tests for Darwin Core Archive Exporter plugin."""

import os
import zipfile
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from niamoto.core.plugins.exporters.dwc_archive_exporter import (
    DwcArchiveExporter,
    DwcArchiveExporterParams,
    DatasetMetadata,
)
from niamoto.core.plugins.models import TargetConfig
from niamoto.common.database import Database


@pytest.fixture
def mock_db():
    """Create a mock database instance."""
    return MagicMock(spec=Database)


@pytest.fixture
def exporter(mock_db):
    """Create a DwcArchiveExporter instance."""
    return DwcArchiveExporter(db=mock_db)


@pytest.fixture
def sample_occurrences():
    """Create sample occurrence data."""
    return [
        {
            "occurrenceID": "occ1",
            "scientificName": "Species A",
            "decimalLatitude": -21.5,
            "decimalLongitude": 165.5,
            "eventDate": "2024-01-15",
        },
        {
            "occurrenceID": "occ2",
            "scientificName": "Species B",
            "decimalLatitude": -22.0,
            "decimalLongitude": 166.0,
            "eventDate": "2024-01-16",
        },
    ]


class TestDatasetMetadata:
    """Test DatasetMetadata model."""

    def test_dataset_metadata_defaults(self):
        """Test DatasetMetadata with default values."""
        metadata = DatasetMetadata()
        assert metadata.title == "Niamoto Biodiversity Data"
        assert metadata.description == "Biodiversity occurrence data from Niamoto"
        assert metadata.publisher == "Niamoto"
        assert metadata.contact_name == "Niamoto Project"
        assert metadata.contact_email == "contact@niamoto.nc"
        assert metadata.rights == "CC-BY-4.0"
        assert metadata.language == "fr"
        assert metadata.geographic_coverage == "New Caledonia"

    def test_dataset_metadata_custom_values(self):
        """Test DatasetMetadata with custom values."""
        metadata = DatasetMetadata(
            title="Custom Title",
            description="Custom Description",
            publisher="Custom Publisher",
            contact_name="John Doe",
            contact_email="john@example.com",
            rights="CC0",
            citation="Cite this",
            homepage="https://example.com",
            language="en",
            geographic_coverage="Pacific",
        )
        assert metadata.title == "Custom Title"
        assert metadata.description == "Custom Description"
        assert metadata.publisher == "Custom Publisher"
        assert metadata.contact_name == "John Doe"
        assert metadata.contact_email == "john@example.com"
        assert metadata.rights == "CC0"
        assert metadata.citation == "Cite this"
        assert metadata.homepage == "https://example.com"
        assert metadata.language == "en"
        assert metadata.geographic_coverage == "Pacific"


class TestDwcArchiveExporterParams:
    """Test DwcArchiveExporterParams model."""

    def test_params_defaults(self):
        """Test parameters with default values."""
        params = DwcArchiveExporterParams()
        assert params.output_dir == "exports/dwc-archive"
        assert params.archive_name == "dwc-archive.zip"
        assert params.compress_csv is False
        assert params.delimiter == "\t"
        assert params.encoding == "utf-8"
        assert isinstance(params.metadata, DatasetMetadata)

    def test_params_custom_values(self):
        """Test parameters with custom values."""
        metadata = DatasetMetadata(title="Test Dataset")
        params = DwcArchiveExporterParams(
            output_dir="custom/output",
            archive_name="custom-archive.zip",
            metadata=metadata,
            compress_csv=True,
            delimiter=",",
            encoding="utf-16",
        )
        assert params.output_dir == "custom/output"
        assert params.archive_name == "custom-archive.zip"
        assert params.compress_csv is True
        assert params.delimiter == ","
        assert params.encoding == "utf-16"
        assert params.metadata.title == "Test Dataset"

    def test_params_validation(self):
        """Test that parameters are properly validated."""
        # Valid params
        params = DwcArchiveExporterParams.model_validate(
            {"output_dir": "test", "archive_name": "test.zip"}
        )
        assert params.output_dir == "test"


class TestDwcArchiveExporterInit:
    """Test DwcArchiveExporter initialization."""

    def test_init_with_db(self, mock_db):
        """Test initialization with database."""
        exporter = DwcArchiveExporter(db=mock_db)
        assert exporter.db == mock_db
        assert exporter.stats["start_time"] is None
        assert exporter.stats["end_time"] is None
        assert exporter.stats["total_occurrences"] == 0
        assert exporter.stats["total_taxa"] == 0

    def test_init_with_registry(self, mock_db):
        """Test initialization with registry."""
        mock_registry = MagicMock()
        exporter = DwcArchiveExporter(db=mock_db, registry=mock_registry)
        assert exporter.registry == mock_registry


class TestGenerateOccurrenceCSV:
    """Test CSV generation."""

    def test_generate_uncompressed_csv(self, exporter, sample_occurrences):
        """Test generating uncompressed CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "occurrence.csv"
            params = DwcArchiveExporterParams(compress_csv=False)
            terms = [
                "occurrenceID",
                "scientificName",
                "decimalLatitude",
                "decimalLongitude",
                "eventDate",
            ]

            exporter._generate_occurrence_csv(
                sample_occurrences, terms, output_path, params
            )

            assert output_path.exists()
            with open(output_path, "r") as f:
                content = f.read()
                assert "occurrenceID" in content
                assert "occ1" in content
                assert "Species A" in content

    def test_generate_compressed_csv(self, exporter, sample_occurrences):
        """Test generating compressed CSV file."""
        import gzip

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "occurrence.csv.gz"
            params = DwcArchiveExporterParams(compress_csv=True)
            terms = ["occurrenceID", "scientificName"]

            exporter._generate_occurrence_csv(
                sample_occurrences, terms, output_path, params
            )

            assert output_path.exists()
            with gzip.open(output_path, "rt") as f:
                content = f.read()
                assert "occurrenceID" in content
                assert "occ1" in content

    def test_generate_csv_with_custom_delimiter(self, exporter, sample_occurrences):
        """Test generating CSV with custom delimiter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "occurrence.csv"
            params = DwcArchiveExporterParams(delimiter=",")
            terms = ["occurrenceID", "scientificName"]

            exporter._generate_occurrence_csv(
                sample_occurrences, terms, output_path, params
            )

            with open(output_path, "r") as f:
                content = f.read()
                assert "," in content
                assert "\t" not in content.split("\n")[1]  # Skip header

    def test_generate_csv_with_none_values(self, exporter):
        """Test CSV generation handles None values."""
        occurrences = [
            {"occurrenceID": "occ1", "scientificName": None, "eventDate": "2024-01-01"}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "occurrence.csv"
            params = DwcArchiveExporterParams()
            terms = ["occurrenceID", "scientificName", "eventDate"]

            exporter._generate_occurrence_csv(occurrences, terms, output_path, params)

            with open(output_path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 2  # Header + 1 data row

    def test_generate_csv_empty_occurrences(self, exporter):
        """Test CSV generation with empty occurrences list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "occurrence.csv"
            params = DwcArchiveExporterParams()
            terms = ["occurrenceID", "scientificName"]

            exporter._generate_occurrence_csv([], terms, output_path, params)

            assert output_path.exists()
            with open(output_path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 1  # Only header


class TestGenerateMetaXml:
    """Test meta.xml generation."""

    def test_generate_meta_xml(self, exporter):
        """Test generating meta.xml file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.xml"
            params = DwcArchiveExporterParams()
            terms = ["occurrenceID", "scientificName", "decimalLatitude"]
            csv_filename = "occurrence.csv"

            exporter._generate_meta_xml(terms, csv_filename, output_path, params)

            assert output_path.exists()
            with open(output_path, "r") as f:
                content = f.read()
                assert '<?xml version="1.0" ?>' in content
                assert "http://rs.tdwg.org/dwc/text/" in content
                assert "occurrence.csv" in content
                assert "occurrenceID" in content
                assert "scientificName" in content

    def test_generate_meta_xml_with_compressed_csv(self, exporter):
        """Test meta.xml references compressed CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.xml"
            params = DwcArchiveExporterParams(compress_csv=True)
            terms = ["occurrenceID"]
            csv_filename = "occurrence.csv.gz"

            exporter._generate_meta_xml(terms, csv_filename, output_path, params)

            with open(output_path, "r") as f:
                content = f.read()
                assert "occurrence.csv.gz" in content

    def test_generate_meta_xml_field_indices(self, exporter):
        """Test that field indices are correct in meta.xml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.xml"
            params = DwcArchiveExporterParams()
            terms = ["occurrenceID", "scientificName", "eventDate"]
            csv_filename = "occurrence.csv"

            exporter._generate_meta_xml(terms, csv_filename, output_path, params)

            with open(output_path, "r") as f:
                content = f.read()
                assert 'index="0"' in content
                assert 'index="1"' in content
                assert 'index="2"' in content

    def test_generate_meta_xml_with_custom_encoding(self, exporter):
        """Test meta.xml with custom encoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.xml"
            params = DwcArchiveExporterParams(encoding="utf-16")
            terms = ["occurrenceID"]
            csv_filename = "occurrence.csv"

            exporter._generate_meta_xml(terms, csv_filename, output_path, params)

            with open(output_path, "r") as f:
                content = f.read()
                assert 'encoding="utf-16"' in content


class TestGenerateEmlXml:
    """Test eml.xml generation."""

    def test_generate_eml_xml_default_metadata(self, exporter):
        """Test generating eml.xml with default metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "eml.xml"
            metadata = DatasetMetadata()

            exporter._generate_eml_xml(output_path, metadata)

            assert output_path.exists()
            with open(output_path, "r") as f:
                content = f.read()
                assert '<?xml version="1.0" ?>' in content
                assert "eml://ecoinformatics.org/eml-2.1.1" in content
                assert "Niamoto Biodiversity Data" in content
                assert "Niamoto" in content
                assert "contact@niamoto.nc" in content
                assert "CC-BY-4.0" in content
                assert "New Caledonia" in content

    def test_generate_eml_xml_custom_metadata(self, exporter):
        """Test generating eml.xml with custom metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "eml.xml"
            metadata = DatasetMetadata(
                title="Custom Dataset",
                description="Custom description",
                publisher="Custom Publisher",
                contact_name="Jane Doe",
                contact_email="jane@example.com",
                rights="CC0",
                language="en",
                geographic_coverage="Pacific Islands",
            )

            exporter._generate_eml_xml(output_path, metadata)

            with open(output_path, "r") as f:
                content = f.read()
                assert "Custom Dataset" in content
                assert "Custom description" in content
                assert "Custom Publisher" in content
                assert "Jane Doe" in content
                assert "jane@example.com" in content
                assert "CC0" in content
                assert 'xml:lang="en"' in content
                assert "Pacific Islands" in content

    def test_generate_eml_xml_without_geographic_coverage(self, exporter):
        """Test eml.xml generation without geographic coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "eml.xml"
            metadata = DatasetMetadata(geographic_coverage=None)

            exporter._generate_eml_xml(output_path, metadata)

            assert output_path.exists()
            # Should still generate valid EML even without geographic coverage

    def test_generate_eml_xml_has_pub_date(self, exporter):
        """Test that eml.xml includes publication date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "eml.xml"
            metadata = DatasetMetadata()

            exporter._generate_eml_xml(output_path, metadata)

            with open(output_path, "r") as f:
                content = f.read()
                # Should contain today's date
                today = datetime.now().strftime("%Y-%m-%d")
                assert today in content


class TestCreateZipArchive:
    """Test ZIP archive creation."""

    def test_create_zip_archive(self, exporter):
        """Test creating ZIP archive with multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "test1.txt"
            file2 = Path(tmpdir) / "test2.txt"
            file1.write_text("content1")
            file2.write_text("content2")

            archive_path = Path(tmpdir) / "archive.zip"
            exporter._create_zip_archive(archive_path, [file1, file2])

            assert archive_path.exists()
            with zipfile.ZipFile(archive_path, "r") as zf:
                assert "test1.txt" in zf.namelist()
                assert "test2.txt" in zf.namelist()

    def test_create_zip_archive_with_nonexistent_file(self, exporter):
        """Test ZIP creation skips nonexistent files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "existing.txt"
            file1.write_text("content")
            nonexistent = Path(tmpdir) / "nonexistent.txt"

            archive_path = Path(tmpdir) / "archive.zip"
            exporter._create_zip_archive(archive_path, [file1, nonexistent])

            assert archive_path.exists()
            with zipfile.ZipFile(archive_path, "r") as zf:
                assert "existing.txt" in zf.namelist()
                assert "nonexistent.txt" not in zf.namelist()

    def test_create_zip_archive_empty_file_list(self, exporter):
        """Test ZIP creation with empty file list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / "empty.zip"
            exporter._create_zip_archive(archive_path, [])

            assert archive_path.exists()
            with zipfile.ZipFile(archive_path, "r") as zf:
                assert len(zf.namelist()) == 0


class TestFetchGroupData:
    """Test fetching group data from database."""

    def test_fetch_group_data_success(self, exporter):
        """Test successful data fetch from database."""
        # Create mock database without spec to allow engine attribute
        mock_db = MagicMock()

        # Mock database response
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "Species A", '{"latitude": -21.5, "longitude": 165.5}'),
            (2, "Species B", '{"latitude": -22.0, "longitude": 166.0}'),
        ]
        mock_result.keys.return_value = ["id", "name", "data"]

        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        mock_db.engine.connect.return_value.__enter__.return_value = mock_connection

        result = exporter._fetch_group_data(mock_db, "test_table")

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Species A"
        assert "latitude" in result[0]

    def test_fetch_group_data_empty_result(self, exporter):
        """Test fetch with no data returned."""
        mock_db = MagicMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        mock_db.engine.connect.return_value.__enter__.return_value = mock_connection

        result = exporter._fetch_group_data(mock_db, "empty_table")

        assert result == []

    def test_fetch_group_data_handles_non_json_columns(self, exporter):
        """Test fetch handles non-JSON column values."""
        mock_db = MagicMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "Simple Text", 42),
        ]
        mock_result.keys.return_value = ["id", "name", "count"]

        mock_connection = MagicMock()
        mock_connection.execute.return_value = mock_result
        mock_db.engine.connect.return_value.__enter__.return_value = mock_connection

        result = exporter._fetch_group_data(mock_db, "test_table")

        assert len(result) == 1
        assert result[0]["name"] == "Simple Text"
        assert result[0]["count"] == 42

    def test_fetch_group_data_error_handling(self, exporter):
        """Test error handling during data fetch."""
        mock_db = MagicMock()
        mock_db.engine.connect.side_effect = Exception("Database error")

        result = exporter._fetch_group_data(mock_db, "failing_table")

        assert result == []


class TestApplyTransformer:
    """Test applying transformer to data."""

    def test_apply_transformer_with_dict_config(self, exporter, mock_db):
        """Test applying transformer with dict config."""
        item = {"id": 1, "name": "Test"}
        group_config = {
            "transformer_plugin": "test_transformer",
            "transformer_params": {"param1": "value1"},
        }

        mock_transformer = MagicMock()
        mock_transformer.return_value.transform.return_value = [
            {"occurrenceID": "occ1"},
            {"occurrenceID": "occ2"},
        ]

        with patch(
            "niamoto.core.plugins.exporters.dwc_archive_exporter.PluginRegistry.get_plugin",
            return_value=mock_transformer,
        ):
            result = exporter._apply_transformer(item, group_config)

            assert len(result) == 2
            assert result[0]["occurrenceID"] == "occ1"

    def test_apply_transformer_with_object_config(self, exporter):
        """Test applying transformer with object config."""
        item = {"id": 1}
        mock_group_config = MagicMock()
        mock_group_config.transformer_plugin = "test_transformer"
        mock_group_config.transformer_params = {"param": "value"}

        mock_transformer = MagicMock()
        mock_transformer.return_value.transform.return_value = [
            {"occurrenceID": "occ1"}
        ]

        with patch(
            "niamoto.core.plugins.exporters.dwc_archive_exporter.PluginRegistry.get_plugin",
            return_value=mock_transformer,
        ):
            result = exporter._apply_transformer(item, mock_group_config)

            assert len(result) == 1

    def test_apply_transformer_no_plugin_configured(self, exporter):
        """Test transformer application with no plugin configured."""
        item = {"id": 1}
        group_config = {"transformer_plugin": None}

        result = exporter._apply_transformer(item, group_config)

        assert result == []

    def test_apply_transformer_plugin_not_found(self, exporter):
        """Test transformer application when plugin not found."""
        item = {"id": 1}
        group_config = {"transformer_plugin": "nonexistent_plugin"}

        with patch(
            "niamoto.core.plugins.exporters.dwc_archive_exporter.PluginRegistry.get_plugin",
            return_value=None,
        ):
            result = exporter._apply_transformer(item, group_config)

            assert result == []

    def test_apply_transformer_returns_non_list(self, exporter):
        """Test transformer returns non-list value."""
        item = {"id": 1}
        group_config = {"transformer_plugin": "test_transformer"}

        mock_transformer = MagicMock()
        mock_transformer.return_value.transform.return_value = "not a list"

        with patch(
            "niamoto.core.plugins.exporters.dwc_archive_exporter.PluginRegistry.get_plugin",
            return_value=mock_transformer,
        ):
            result = exporter._apply_transformer(item, group_config)

            assert result == []

    def test_apply_transformer_raises_exception(self, exporter):
        """Test transformer application error handling."""
        item = {"id": 1}
        group_config = {"transformer_plugin": "failing_transformer"}

        mock_transformer = MagicMock()
        mock_transformer.return_value.transform.side_effect = Exception(
            "Transform error"
        )

        with patch(
            "niamoto.core.plugins.exporters.dwc_archive_exporter.PluginRegistry.get_plugin",
            return_value=mock_transformer,
        ):
            result = exporter._apply_transformer(item, group_config)

            assert result == []


class TestCollectOccurrences:
    """Test collecting occurrences from groups."""

    def test_collect_occurrences_single_group(self, exporter):
        """Test collecting occurrences from single group."""
        mock_db = MagicMock()
        groups = [{"group_by": "taxon", "transformer_plugin": "test_transformer"}]

        # Mock fetch_group_data
        with patch.object(
            exporter,
            "_fetch_group_data",
            return_value=[{"id": 1, "name": "Species A"}],
        ):
            # Mock apply_transformer
            with patch.object(
                exporter,
                "_apply_transformer",
                return_value=[{"occurrenceID": "occ1"}],
            ):
                occurrences, terms = exporter._collect_occurrences(groups, mock_db)

                assert len(occurrences) == 1
                assert "occurrenceID" in terms
                assert exporter.stats["total_taxa"] == 1
                assert exporter.stats["total_occurrences"] == 1

    def test_collect_occurrences_multiple_groups(self, exporter):
        """Test collecting occurrences from multiple groups."""
        mock_db = MagicMock()
        groups = [
            {"group_by": "taxon"},
            {"group_by": "plots"},
        ]

        with patch.object(
            exporter, "_fetch_group_data", return_value=[{"id": 1}, {"id": 2}]
        ):
            with patch.object(
                exporter,
                "_apply_transformer",
                return_value=[{"occurrenceID": "occ1", "scientificName": "Species"}],
            ):
                occurrences, terms = exporter._collect_occurrences(groups, mock_db)

                # 2 groups × 2 items each = 4 occurrences
                assert len(occurrences) == 4
                assert "occurrenceID" in terms
                assert "scientificName" in terms

    def test_collect_occurrences_empty_group(self, exporter):
        """Test collecting when group has no data."""
        mock_db = MagicMock()
        groups = [{"group_by": "empty_table"}]

        with patch.object(exporter, "_fetch_group_data", return_value=[]):
            occurrences, terms = exporter._collect_occurrences(groups, mock_db)

            assert len(occurrences) == 0
            assert len(terms) == 0

    def test_collect_occurrences_handles_object_config(self, exporter):
        """Test collecting with object-based group config."""
        mock_db = MagicMock()
        mock_group = MagicMock()
        mock_group.group_by = "taxon"

        with patch.object(exporter, "_fetch_group_data", return_value=[{"id": 1}]):
            with patch.object(
                exporter, "_apply_transformer", return_value=[{"occurrenceID": "occ1"}]
            ):
                occurrences, terms = exporter._collect_occurrences(
                    [mock_group], mock_db
                )

                assert len(occurrences) == 1


class TestGenerateArchive:
    """Test complete archive generation."""

    def test_generate_archive_creates_all_files(self, exporter, sample_occurrences):
        """Test that generate_archive creates all required files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            params = DwcArchiveExporterParams(
                output_dir=str(output_dir), archive_name="test-archive.zip"
            )
            terms = {"occurrenceID", "scientificName"}

            exporter._generate_archive(sample_occurrences, terms, output_dir, params)

            # Check that archive was created
            assert (output_dir / "test-archive.zip").exists()

            # Verify archive contains expected files
            with zipfile.ZipFile(output_dir / "test-archive.zip", "r") as zf:
                assert "occurrence.csv" in zf.namelist()
                assert "meta.xml" in zf.namelist()
                assert "eml.xml" in zf.namelist()

    def test_generate_archive_with_compressed_csv(self, exporter, sample_occurrences):
        """Test archive generation with compressed CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            params = DwcArchiveExporterParams(
                output_dir=str(output_dir), compress_csv=True
            )
            terms = {"occurrenceID"}

            exporter._generate_archive(sample_occurrences, terms, output_dir, params)

            # Verify CSV is compressed
            with zipfile.ZipFile(output_dir / "dwc-archive.zip", "r") as zf:
                assert "occurrence.csv.gz" in zf.namelist()


class TestExportMethod:
    """Test the main export() method."""

    def test_export_with_no_occurrences(self, exporter):
        """Test export when no occurrences are found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_config = TargetConfig(
                name="test_target",
                exporter="dwc_archive_exporter",
                params={"output_dir": tmpdir},
                groups=[],  # Empty groups
            )

            mock_db = MagicMock()

            # Should not raise, just log warning
            exporter.export(target_config, mock_db)

            # Stats should show 0 occurrences
            assert exporter.stats["total_occurrences"] == 0

    def test_export_creates_output_directory(self, exporter):
        """Test that export creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "new_dir", "dwc_output")

            target_config = TargetConfig(
                name="test_target",
                exporter="dwc_archive_exporter",
                params={"output_dir": output_dir},
                groups=[],
            )

            mock_db = MagicMock()

            exporter.export(target_config, mock_db)

            # Directory should be created
            assert os.path.exists(output_dir)

    def test_export_with_group_filter(self, exporter):
        """Test export with group_filter parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create groups with different group_by values
            mock_group1 = MagicMock()
            mock_group1.group_by = "taxon"

            mock_group2 = MagicMock()
            mock_group2.group_by = "plots"

            target_config = TargetConfig(
                name="test_target",
                exporter="dwc_archive_exporter",
                params={"output_dir": tmpdir},
                groups=[mock_group1, mock_group2],
            )

            mock_db = MagicMock()

            # Mock both _fetch_group_data and _apply_transformer
            with patch.object(exporter, "_fetch_group_data", return_value=[{"id": 1}]):
                with patch.object(exporter, "_apply_transformer", return_value=[]):
                    exporter.export(target_config, mock_db, group_filter="taxon")

                    # Check that groups were filtered correctly
                    assert (
                        exporter.stats["total_taxa"] == 1
                    )  # Only taxon group processed

    def test_export_handles_errors(self, exporter):
        """Test that export handles errors properly."""
        from niamoto.common.exceptions import ProcessError

        target_config = TargetConfig(
            name="test_target",
            exporter="dwc_archive_exporter",
            params={"output_dir": "/invalid/path/that/should/fail"},
            groups=[],
        )

        mock_db = MagicMock()

        # Mock permission error on directory creation
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("No permission")):
            with pytest.raises(ProcessError):
                exporter.export(target_config, mock_db)

    def test_export_tracks_stats(self, exporter):
        """Test that export tracks start/end times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_config = TargetConfig(
                name="test_target",
                exporter="dwc_archive_exporter",
                params={"output_dir": tmpdir},
                groups=[],
            )

            mock_db = MagicMock()

            exporter.export(target_config, mock_db)

            # Stats should have timestamps
            assert exporter.stats["start_time"] is not None
            assert exporter.stats["end_time"] is not None
            assert exporter.stats["start_time"] <= exporter.stats["end_time"]

    def test_export_integration_with_data(self, exporter):
        """Integration test: export with mocked data collection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_group = MagicMock()
            mock_group.group_by = "taxon"

            target_config = TargetConfig(
                name="test_target",
                exporter="dwc_archive_exporter",
                params={"output_dir": tmpdir, "archive_name": "test.zip"},
                groups=[mock_group],
            )

            mock_db = MagicMock()

            # Mock _fetch_group_data to return some data
            with patch.object(
                exporter, "_fetch_group_data", return_value=[{"id": 1}, {"id": 2}]
            ):
                # Mock _apply_transformer to return occurrences
                with patch.object(
                    exporter,
                    "_apply_transformer",
                    return_value=[
                        {"occurrenceID": "occ1", "scientificName": "Species A"}
                    ],
                ):
                    exporter.export(target_config, mock_db)

                    # Archive should be created
                    archive_path = Path(tmpdir) / "test.zip"
                    assert archive_path.exists()

                    # Verify archive contents
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        assert "occurrence.csv" in zf.namelist()
                        assert "meta.xml" in zf.namelist()
                        assert "eml.xml" in zf.namelist()

                    # Stats should reflect data
                    assert exporter.stats["total_occurrences"] == 2  # 2 items processed
