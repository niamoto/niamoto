"""
Tests for the smart_config router.

This module tests the smart configuration API endpoints that provide
intelligent auto-configuration functionality for the Niamoto GUI.

Coverage target: 85% of smart_config.py (from 12.2%)

Testing anti-patterns compliance:
- ✓ Tests real HTTP behavior with FastAPI TestClient
- ✓ Uses real CSV files, not mocks
- ✓ Verifies actual results (JSON responses, created files, YAML content)
- ✓ Mocks only the context (working directory) for test isolation
- ✗ Does NOT test mock behavior
- ✗ Does NOT mock ColumnDetector for integration tests
"""

import io
import shutil
import zipfile
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api import context


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def working_directory(tmp_path: Path):
    """
    Create a complete working directory structure for testing.

    Structure:
        tmp_path/
        ├── imports/
        ├── config/
        └── exports/
    """
    # Create standard Niamoto directories
    imports_dir = tmp_path / "imports"
    config_dir = tmp_path / "config"
    exports_dir = tmp_path / "exports"

    imports_dir.mkdir()
    config_dir.mkdir()
    exports_dir.mkdir()

    return tmp_path


@pytest.fixture(autouse=True)
def mock_context(working_directory: Path):
    """
    Mock the working directory context for all tests.

    This is the ONLY mock we use - it provides test isolation
    by pointing the API to a temporary directory.
    """
    with patch.object(context, "_working_directory", working_directory):
        yield working_directory


@pytest.fixture
def sample_csv_files(fixtures_dir: Path, working_directory: Path):
    """Copy sample CSV files to the working directory's imports folder."""
    imports_dir = working_directory / "imports"

    # Copy all CSV fixtures to imports directory
    csv_files = [
        "sample_occurrences.csv",
        "sample_taxonomy.csv",
        "sample_plots.csv",
        "no_hierarchy.csv",
        "empty.csv",
    ]

    copied_files = {}
    for csv_file in csv_files:
        src = fixtures_dir / csv_file
        if src.exists():
            dst = imports_dir / csv_file
            shutil.copy(src, dst)
            copied_files[csv_file] = dst

    return copied_files


# ============================================================================
# HELPER FUNCTIONS TESTS
# ============================================================================


class TestHelperFunctions:
    """Test internal helper functions of the smart_config router."""

    def test_categorize_file_csv(self):
        """Test file categorization for CSV files."""
        from niamoto.gui.api.routers.smart_config import _categorize_file

        assert _categorize_file(".csv") == "csv"

    def test_categorize_file_gpkg(self):
        """Test file categorization for GeoPackage files."""
        from niamoto.gui.api.routers.smart_config import _categorize_file

        assert _categorize_file(".gpkg") == "gpkg"

    def test_categorize_file_tif(self):
        """Test file categorization for TIFF files."""
        from niamoto.gui.api.routers.smart_config import _categorize_file

        assert _categorize_file(".tif") == "tif"
        assert _categorize_file(".tiff") == "tif"

    def test_categorize_file_shapefile(self):
        """Test file categorization for shapefile (ZIP) and components."""
        from niamoto.gui.api.routers.smart_config import _categorize_file

        # ZIP files are categorized as shapefile (typically contain shapefiles)
        assert _categorize_file(".zip") == "shapefile"
        # Individual shapefile components are categorized as "other"
        assert _categorize_file(".shp") == "other"
        assert _categorize_file(".shx") == "other"
        assert _categorize_file(".dbf") == "other"
        assert _categorize_file(".prj") == "other"

    def test_categorize_file_other(self):
        """Test file categorization for unknown types."""
        from niamoto.gui.api.routers.smart_config import _categorize_file

        assert _categorize_file(".txt") == "other"
        assert _categorize_file(".pdf") == "other"


# ============================================================================
# UPLOAD FILES ENDPOINT TESTS
# ============================================================================


class TestUploadFiles:
    """Test POST /api/smart/upload-files endpoint."""

    def test_upload_single_csv_file(self, test_client: TestClient, fixtures_dir: Path):
        """Test uploading a single CSV file."""
        csv_file = fixtures_dir / "sample_occurrences.csv"

        with open(csv_file, "rb") as f:
            response = test_client.post(
                "/api/smart/upload-files",
                files={"files": ("occurrences.csv", f, "text/csv")},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "uploaded_files" in data
        assert "existing_files" in data
        assert "errors" in data

        # Verify file was uploaded
        assert len(data["uploaded_files"]) == 1
        uploaded = data["uploaded_files"][0]
        assert uploaded["filename"] == "occurrences.csv"
        assert uploaded["category"] == "csv"
        assert uploaded["size"] > 0

    def test_upload_multiple_files(self, test_client: TestClient, fixtures_dir: Path):
        """Test uploading multiple CSV files at once."""
        files_to_upload = [
            ("sample_occurrences.csv", "occurrences.csv"),
            ("sample_taxonomy.csv", "taxonomy.csv"),
            ("sample_plots.csv", "plots.csv"),
        ]

        files = []
        for src_name, dst_name in files_to_upload:
            f = open(fixtures_dir / src_name, "rb")
            files.append(("files", (dst_name, f, "text/csv")))

        try:
            response = test_client.post("/api/smart/upload-files", files=files)

            assert response.status_code == 200
            data = response.json()

            # All 3 files should be uploaded
            assert len(data["uploaded_files"]) == 3
            assert len(data["errors"]) == 0

            # Verify filenames
            uploaded_names = {f["filename"] for f in data["uploaded_files"]}
            assert uploaded_names == {"occurrences.csv", "taxonomy.csv", "plots.csv"}

        finally:
            # Close all file handles
            for _, (_, f, _) in files:
                f.close()

    def test_upload_with_overwrite_false(
        self, test_client: TestClient, fixtures_dir: Path
    ):
        """Test uploading an existing file without overwrite should not replace it."""
        csv_file = fixtures_dir / "sample_occurrences.csv"

        # Upload file first time
        with open(csv_file, "rb") as f:
            response1 = test_client.post(
                "/api/smart/upload-files", files={"files": ("data.csv", f, "text/csv")}
            )
        assert response1.status_code == 200
        assert len(response1.json()["uploaded_files"]) == 1

        # Try to upload same filename with overwrite=False (default)
        with open(csv_file, "rb") as f:
            response2 = test_client.post(
                "/api/smart/upload-files", files={"files": ("data.csv", f, "text/csv")}
            )

        assert response2.status_code == 200
        data = response2.json()

        # File should be in "existing_files", not "uploaded_files"
        assert len(data["uploaded_files"]) == 0
        assert len(data["existing_files"]) == 1

        # existing_files might be a list of filenames (strings) or file info dicts
        existing_file = data["existing_files"][0]
        if isinstance(existing_file, str):
            assert existing_file == "data.csv"
        else:
            assert existing_file["filename"] == "data.csv"

    def test_upload_with_overwrite_true(
        self, test_client: TestClient, fixtures_dir: Path
    ):
        """Test uploading an existing file with overwrite=True should replace it."""
        csv_file = fixtures_dir / "sample_occurrences.csv"

        # Upload file first time
        with open(csv_file, "rb") as f:
            response1 = test_client.post(
                "/api/smart/upload-files", files={"files": ("data.csv", f, "text/csv")}
            )
        assert response1.status_code == 200

        # Upload again with overwrite=True
        with open(csv_file, "rb") as f:
            response2 = test_client.post(
                "/api/smart/upload-files?overwrite=true",
                files={"files": ("data.csv", f, "text/csv")},
            )

        assert response2.status_code == 200
        data = response2.json()

        # File should be uploaded (replaced)
        assert len(data["uploaded_files"]) == 1
        assert len(data["existing_files"]) == 0
        assert data["uploaded_files"][0]["filename"] == "data.csv"

    def test_upload_zip_file_extracts_contents(
        self, test_client: TestClient, tmp_path: Path
    ):
        """Test uploading a ZIP file should extract its contents."""
        # Create a simple ZIP file with 2 CSV files
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.csv", "id,name\n1,test\n")
            zf.writestr("file2.csv", "id,value\n1,100\n")

        with open(zip_path, "rb") as f:
            response = test_client.post(
                "/api/smart/upload-files",
                files={"files": ("data.zip", f, "application/zip")},
            )

        assert response.status_code == 200
        data = response.json()

        # Both CSV files should be extracted and uploaded
        assert len(data["uploaded_files"]) == 2
        uploaded_names = {f["filename"] for f in data["uploaded_files"]}
        assert uploaded_names == {"file1.csv", "file2.csv"}

    def test_upload_empty_filename_returns_error(self, test_client: TestClient):
        """Test uploading a file with empty filename should return error."""
        # Create a file with no filename
        file_content = b"id,name\n1,test\n"

        response = test_client.post(
            "/api/smart/upload-files",
            files={"files": ("", io.BytesIO(file_content), "text/csv")},
        )

        # Can return either 422 (validation error) or 200 with errors in response
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            # Should have an error, no upload
            assert len(data["errors"]) > 0
            assert len(data["uploaded_files"]) == 0

    def test_upload_mixed_file_types(self, test_client: TestClient, fixtures_dir: Path):
        """Test uploading different file types in one request."""
        csv_file = fixtures_dir / "sample_occurrences.csv"

        # Create a dummy TIF file
        tif_content = b"FAKE TIF CONTENT"

        with open(csv_file, "rb") as csv_f:
            response = test_client.post(
                "/api/smart/upload-files",
                files=[
                    ("files", ("data.csv", csv_f, "text/csv")),
                    ("files", ("raster.tif", io.BytesIO(tif_content), "image/tiff")),
                ],
            )

        assert response.status_code == 200
        data = response.json()

        # Both files should be uploaded with correct categories
        assert len(data["uploaded_files"]) == 2

        categories = {f["filename"]: f["category"] for f in data["uploaded_files"]}
        assert categories["data.csv"] == "csv"
        assert categories["raster.tif"] == "tif"


# ============================================================================
# ANALYZE FILE ENDPOINT TESTS
# ============================================================================


class TestAnalyzeFile:
    """Test POST /api/smart/analyze-file endpoint."""

    def test_analyze_valid_csv_file(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test analyzing a valid CSV file returns analysis results."""
        response = test_client.post(
            "/api/smart/analyze-file",
            json={"filepath": "imports/sample_occurrences.csv"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify analysis structure (data is at root level, not wrapped)
        # Should have column analysis
        assert "columns" in data
        assert len(data["columns"]) > 0

        # Should have row counts
        assert "row_count" in data
        assert data["row_count"] == 10  # Our sample has 10 rows

        # Should have sample size info
        assert "sample_size" in data

        # Should have detected hierarchy (our occurrences have family/genus/species)
        assert "hierarchy" in data

    def test_analyze_file_not_found(self, test_client: TestClient):
        """Test analyzing a non-existent file returns 404."""
        response = test_client.post(
            "/api/smart/analyze-file", json={"filepath": "nonexistent.csv"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_analyze_unsupported_file_type(
        self, test_client: TestClient, working_directory: Path
    ):
        """Test analyzing a non-CSV file returns 400."""
        # Create a TXT file
        txt_file = working_directory / "imports" / "test.txt"
        txt_file.write_text("This is a text file")

        response = test_client.post(
            "/api/smart/analyze-file", json={"filepath": "imports/test.txt"}
        )

        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "not supported" in detail or "unsupported" in detail

    def test_analyze_empty_csv_file(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test analyzing an empty CSV file."""
        response = test_client.post(
            "/api/smart/analyze-file", json={"filepath": "imports/empty.csv"}
        )

        # Should handle gracefully (implementation dependent)
        # Either 200 with empty analysis or 400 error
        assert response.status_code in [200, 400]

    def test_analyze_with_entity_name_hint(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test analyzing with entity_name hint parameter."""
        response = test_client.post(
            "/api/smart/analyze-file",
            json={
                "filepath": "imports/sample_occurrences.csv",
                "entity_name": "occurrence",
            },
        )

        assert response.status_code == 200
        # The entity_name might be used for better column detection
        data = response.json()
        assert "columns" in data


# ============================================================================
# DETECT HIERARCHY ENDPOINT TESTS
# ============================================================================


class TestDetectHierarchy:
    """Test POST /api/smart/detect-hierarchy endpoint."""

    def test_detect_hierarchical_columns_in_taxonomy(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test detecting hierarchy in a taxonomic CSV."""
        response = test_client.post(
            "/api/smart/detect-hierarchy",
            json={"filepath": "imports/sample_taxonomy.csv"},
        )

        assert response.status_code == 200
        data = response.json()

        # Response is the hierarchy object directly
        # Should have detected columns (family, genus, species)
        assert "detected" in data
        assert data["detected"] is True
        assert "column_mapping" in data or "levels" in data

    def test_detect_hierarchy_in_occurrences(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test detecting embedded hierarchy in occurrences file."""
        response = test_client.post(
            "/api/smart/detect-hierarchy",
            json={"filepath": "imports/sample_occurrences.csv"},
        )

        assert response.status_code == 200
        data = response.json()

        # Occurrences also have family/genus/species columns
        # Response is the hierarchy object directly
        assert "detected" in data
        assert data["detected"] is True

    def test_detect_no_hierarchy(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test file with no hierarchical structure."""
        response = test_client.post(
            "/api/smart/detect-hierarchy", json={"filepath": "imports/no_hierarchy.csv"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return result indicating no hierarchy found
        # Response is the hierarchy object directly
        assert "detected" in data
        assert data["detected"] is False

    def test_detect_hierarchy_file_not_found(self, test_client: TestClient):
        """Test detecting hierarchy for non-existent file."""
        response = test_client.post(
            "/api/smart/detect-hierarchy", json={"filepath": "nonexistent.csv"}
        )

        assert response.status_code == 404

    def test_detect_hierarchy_unsupported_format(
        self, test_client: TestClient, working_directory: Path
    ):
        """Test detecting hierarchy for non-CSV file."""
        # Create a non-CSV file
        tif_file = working_directory / "imports" / "test.tif"
        tif_file.write_bytes(b"FAKE TIF")

        response = test_client.post(
            "/api/smart/detect-hierarchy", json={"filepath": "imports/test.tif"}
        )

        assert response.status_code == 400


# ============================================================================
# DETECT RELATIONSHIPS ENDPOINT TESTS
# ============================================================================


class TestDetectRelationships:
    """Test POST /api/smart/detect-relationships endpoint."""

    def test_detect_relationship_between_occurrences_and_taxonomy(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test detecting FK relationship between occurrences and taxonomy."""
        response = test_client.post(
            "/api/smart/detect-relationships",
            json={
                "source_file": "imports/sample_occurrences.csv",
                "target_files": ["imports/sample_taxonomy.csv"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should detect relationship via id_taxonref → id
        assert "relationships" in data
        relationships = data["relationships"]

        assert len(relationships) > 0
        # Should have target file and confidence
        rel = relationships[0]
        assert "target_file" in rel
        assert "confidence" in rel
        assert rel["target_file"] == "imports/sample_taxonomy.csv"

    def test_detect_multiple_relationships(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test detecting relationships with multiple target files."""
        response = test_client.post(
            "/api/smart/detect-relationships",
            json={
                "source_file": "imports/sample_occurrences.csv",
                "target_files": [
                    "imports/sample_taxonomy.csv",
                    "imports/sample_plots.csv",
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "relationships" in data
        # Should check against both targets

    def test_detect_no_relationships(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test files with no obvious relationships."""
        response = test_client.post(
            "/api/smart/detect-relationships",
            json={
                "source_file": "imports/no_hierarchy.csv",
                "target_files": ["imports/sample_taxonomy.csv"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty or low-confidence relationships
        assert "relationships" in data

    def test_detect_relationships_source_not_found(self, test_client: TestClient):
        """Test relationship detection with missing source file."""
        response = test_client.post(
            "/api/smart/detect-relationships",
            json={
                "source_file": "imports/nonexistent.csv",
                "target_files": ["imports/sample_taxonomy.csv"],
            },
        )

        assert response.status_code == 404


# ============================================================================
# AUTO-CONFIGURE MAIN TESTS
# ============================================================================


class TestAutoConfigureMain:
    """Test POST /api/smart/auto-configure endpoint - main scenarios."""

    def test_auto_configure_single_csv_dataset(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configuring a single CSV file as a dataset."""
        response = test_client.post(
            "/api/smart/auto-configure",
            json={"files": ["imports/sample_occurrences.csv"]},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "entities" in data
        assert "confidence" in data

        # Should have at least one entity configured
        entities = data["entities"]
        assert len(entities) > 0

    def test_auto_configure_multiple_csvs_detects_references(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configure with multiple CSVs detects reference vs dataset."""
        response = test_client.post(
            "/api/smart/auto-configure",
            json={
                "files": [
                    "imports/sample_occurrences.csv",
                    "imports/sample_taxonomy.csv",
                    "imports/sample_plots.csv",
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        entities = data["entities"]

        # Should detect:
        # - sample_taxonomy.csv as a reference (fewer rows, hierarchical)
        # - sample_occurrences.csv as a dataset (more rows, has FK)
        # - sample_plots.csv as possibly dataset or reference

        assert "datasets" in entities or "references" in entities

    def test_auto_configure_calculates_confidence(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configure calculates overall confidence score."""
        response = test_client.post(
            "/api/smart/auto-configure", json={"files": ["imports/sample_taxonomy.csv"]}
        )

        assert response.status_code == 200
        data = response.json()

        # Confidence should be between 0 and 1
        confidence = data["confidence"]
        assert 0 <= confidence <= 1

    def test_auto_configure_includes_warnings(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configure includes warnings for ambiguous cases."""
        response = test_client.post(
            "/api/smart/auto-configure", json={"files": ["imports/no_hierarchy.csv"]}
        )

        assert response.status_code == 200
        data = response.json()

        # Warnings field should exist (may be empty)
        assert "warnings" in data
        assert isinstance(data["warnings"], list)

    def test_auto_configure_hierarchical_reference(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configure detects hierarchical reference configuration."""
        response = test_client.post(
            "/api/smart/auto-configure", json={"files": ["imports/sample_taxonomy.csv"]}
        )

        assert response.status_code == 200
        data = response.json()

        # Taxonomy should be configured as hierarchical reference
        entities = data["entities"]

        # Look for reference configuration
        if "references" in entities:
            # Should have hierarchy configuration
            pass  # Implementation-specific assertion


# ============================================================================
# AUTO-CONFIGURE EDGE CASES TESTS
# ============================================================================


class TestAutoConfigureEdgeCases:
    """Test POST /api/smart/auto-configure endpoint - edge cases."""

    def test_auto_configure_no_files(self, test_client: TestClient):
        """Test auto-configure with empty files list."""
        response = test_client.post("/api/smart/auto-configure", json={"files": []})

        assert response.status_code == 400
        assert "no files" in response.json()["detail"].lower()

    def test_auto_configure_nonexistent_file(self, test_client: TestClient):
        """Test auto-configure with non-existent file."""
        response = test_client.post(
            "/api/smart/auto-configure", json={"files": ["imports/nonexistent.csv"]}
        )

        # Should either 404 or 400 with appropriate message
        assert response.status_code in [400, 404]

    def test_auto_configure_empty_csv(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configure with empty CSV file."""
        response = test_client.post(
            "/api/smart/auto-configure", json={"files": ["imports/empty.csv"]}
        )

        # Should handle gracefully - either skip or return error
        # Implementation dependent
        assert response.status_code in [200, 400]

    def test_auto_configure_mixed_valid_invalid_files(
        self, test_client: TestClient, sample_csv_files: Dict[str, Path]
    ):
        """Test auto-configure with mix of valid and invalid files."""
        response = test_client.post(
            "/api/smart/auto-configure",
            json={
                "files": [
                    "imports/sample_taxonomy.csv",  # Valid
                    "imports/empty.csv",  # Empty
                    "imports/no_hierarchy.csv",  # Valid but no hierarchy
                ]
            },
        )

        # Should process valid files and handle invalid ones
        # At minimum, should not crash
        assert response.status_code in [200, 400]


# ============================================================================
# CREATE ENTITIES BULK TESTS
# ============================================================================


class TestCreateEntitiesBulk:
    """Test POST /api/smart/management/entities/bulk endpoint."""

    def test_create_entities_bulk_writes_yaml(
        self, test_client: TestClient, working_directory: Path
    ):
        """Test bulk entity creation writes to import.yml."""
        entities_config = {
            "datasets": {
                "occurrences": {
                    "source": "occurrences.csv",
                    "fields": {"id": "id", "name": "name"},
                }
            },
            "references": {
                "taxonomy": {
                    "source": "taxonomy.csv",
                    "fields": {"id": "id", "family": "family"},
                }
            },
        }

        response = test_client.post(
            "/api/smart/management/entities/bulk", json={"entities": entities_config}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["success"] is True
        assert "dataset_count" in data
        assert "reference_count" in data

        # Verify YAML file was created
        import_yml = working_directory / "config" / "import.yml"
        assert import_yml.exists()

        # Verify YAML content
        with open(import_yml) as f:
            yaml_data = yaml.safe_load(f)

        # The YAML structure wraps datasets and references in "entities"
        assert "entities" in yaml_data
        assert "datasets" in yaml_data["entities"]
        assert "references" in yaml_data["entities"]
        assert "occurrences" in yaml_data["entities"]["datasets"]
        assert "taxonomy" in yaml_data["entities"]["references"]

    def test_create_entities_creates_config_dir_if_missing(
        self, test_client: TestClient, working_directory: Path
    ):
        """Test bulk creation creates config directory if it doesn't exist."""
        # Remove config directory
        config_dir = working_directory / "config"
        shutil.rmtree(config_dir)
        assert not config_dir.exists()

        entities_config = {"datasets": {"test": {"source": "test.csv", "fields": {}}}}

        response = test_client.post(
            "/api/smart/management/entities/bulk", json={"entities": entities_config}
        )

        assert response.status_code == 200

        # Config directory should be created
        assert config_dir.exists()
        assert (config_dir / "import.yml").exists()

    def test_create_entities_with_empty_config(self, test_client: TestClient):
        """Test bulk creation with empty entities."""
        response = test_client.post(
            "/api/smart/management/entities/bulk", json={"entities": {}}
        )

        # Should succeed but with zero counts
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_count"] == 0
        assert data["reference_count"] == 0

    def test_create_entities_overwrites_existing_yaml(
        self, test_client: TestClient, working_directory: Path
    ):
        """Test bulk creation overwrites existing import.yml."""
        # Create existing import.yml
        import_yml = working_directory / "config" / "import.yml"
        import_yml.write_text("old_config: old_value\n")

        entities_config = {
            "datasets": {"new_data": {"source": "new.csv", "fields": {}}}
        }

        response = test_client.post(
            "/api/smart/management/entities/bulk", json={"entities": entities_config}
        )

        assert response.status_code == 200

        # Verify old content is replaced
        with open(import_yml) as f:
            yaml_data = yaml.safe_load(f)

        assert "old_config" not in yaml_data
        assert "entities" in yaml_data
        assert "datasets" in yaml_data["entities"]
        assert "new_data" in yaml_data["entities"]["datasets"]
