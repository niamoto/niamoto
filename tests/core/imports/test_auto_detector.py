"""Tests for AutoDetector module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import csv

from niamoto.core.imports.auto_detector import AutoDetector
from niamoto.core.imports.profiler import DatasetProfile, ColumnProfile


@pytest.fixture
def auto_detector():
    """Create an AutoDetector instance."""
    return AutoDetector()


@pytest.fixture
def temp_data_dir():
    """Create temporary directory with test data files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # Create a CSV file
        csv_file = data_dir / "occurrences.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "taxon", "location"])
            writer.writerow([1, "Species A", "Location 1"])
            writer.writerow([2, "Species B", "Location 2"])

        # Create a shapes subdirectory
        shapes_dir = data_dir / "shapes"
        shapes_dir.mkdir()
        shape_file = shapes_dir / "provinces.csv"
        with open(shape_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name"])
            writer.writerow([1, "Province A"])

        yield data_dir


@pytest.fixture
def mock_profile():
    """Create a COMPLETE mock DatasetProfile with all fields from real structure."""
    profile = MagicMock(spec=DatasetProfile)

    # ALL fields from DatasetProfile dataclass (profiler.py:56-68)
    profile.file_path = Path("/data/occurrences.csv")
    profile.record_count = 100
    profile.columns = []  # Empty by default, tests can add ColumnProfiles
    profile.detected_type = "tabular"
    profile.suggested_name = "occurrences"
    profile.relationships = []  # Complete field from dataclass
    profile.geometry_type = None  # Complete field from dataclass
    profile.confidence = 0.85  # Complete field from dataclass

    # Mock the to_dict method with complete structure
    profile.to_dict.return_value = {
        "file_path": str(profile.file_path),
        "record_count": profile.record_count,
        "columns": [],
        "detected_type": profile.detected_type,
        "suggested_name": profile.suggested_name,
        "relationships": profile.relationships,
        "geometry_type": profile.geometry_type,
        "confidence": round(profile.confidence, 2),
    }

    # Mock methods
    profile.has_taxonomy_columns.return_value = False
    profile.has_spatial_columns.return_value = False

    return profile


def create_column_profile(
    name: str,
    dtype: str = "object",
    semantic_type: str = None,
    unique_ratio: float = 0.5,
    null_ratio: float = 0.0,
    sample_values: list = None,
    confidence: float = 0.8,
) -> MagicMock:
    """Helper to create a COMPLETE ColumnProfile mock with all fields.

    All fields from ColumnProfile dataclass (profiler.py:31-42):
    - name, dtype, semantic_type, unique_ratio, null_ratio, sample_values, confidence
    """
    col = MagicMock(spec=ColumnProfile)
    col.name = name
    col.dtype = dtype
    col.semantic_type = semantic_type
    col.unique_ratio = unique_ratio
    col.null_ratio = null_ratio
    col.sample_values = sample_values or []
    col.confidence = confidence

    col.to_dict.return_value = {
        "name": name,
        "dtype": dtype,
        "semantic_type": semantic_type,
        "unique_ratio": round(unique_ratio, 4),
        "null_ratio": round(null_ratio, 4),
        "confidence": round(confidence, 2),
        "sample_values": (sample_values or [])[:5],
    }

    return col


class TestAutoDetectorInit:
    """Test AutoDetector initialization."""

    def test_init_creates_profiler(self, auto_detector):
        """Test that init creates a DataProfiler instance."""
        assert auto_detector.profiler is not None


class TestDiscoverFiles:
    """Test _discover_files method."""

    def test_discover_files_in_directory(self, auto_detector, temp_data_dir):
        """Test discovering files in a directory."""
        files = auto_detector._discover_files(temp_data_dir)

        assert len(files) >= 1
        assert any("occurrences.csv" in str(f) for f in files)

    def test_discover_files_in_shapes_subdirectory(self, auto_detector, temp_data_dir):
        """Test discovering files in shapes subdirectory."""
        files = auto_detector._discover_files(temp_data_dir)

        assert any("provinces.csv" in str(f) for f in files)

    def test_discover_files_skips_hidden_files(self, auto_detector):
        """Test that hidden files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create hidden file
            hidden = data_dir / ".hidden.csv"
            hidden.write_text("id,name\n1,test")

            # Create temp file
            temp = data_dir / "~temp.csv"
            temp.write_text("id,name\n1,test")

            # Create normal file
            normal = data_dir / "normal.csv"
            normal.write_text("id,name\n1,test")

            files = auto_detector._discover_files(data_dir)

            assert normal in files
            assert hidden not in files
            assert temp not in files

    def test_discover_files_supported_extensions(self, auto_detector):
        """Test only supported extensions are discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create files with different extensions
            (data_dir / "data.csv").write_text("test")
            (data_dir / "data.json").write_text("{}")
            (data_dir / "data.geojson").write_text("{}")
            (data_dir / "data.xlsx").write_text("excel")
            (data_dir / "data.txt").write_text("text")  # Not supported

            files = auto_detector._discover_files(data_dir)

            assert any("data.csv" in str(f) for f in files)
            assert any("data.json" in str(f) for f in files)
            assert any("data.geojson" in str(f) for f in files)
            assert any("data.xlsx" in str(f) for f in files)
            assert not any("data.txt" in str(f) for f in files)

    def test_discover_files_sorted(self, auto_detector):
        """Test that files are returned sorted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            (data_dir / "c.csv").write_text("test")
            (data_dir / "a.csv").write_text("test")
            (data_dir / "b.csv").write_text("test")

            files = auto_detector._discover_files(data_dir)
            file_names = [f.name for f in files]

            assert file_names == sorted(file_names)


class TestIsReferenceEntity:
    """Test _is_reference_entity method."""

    def test_hierarchical_type_is_reference(self, auto_detector, mock_profile):
        """Test hierarchical type is identified as reference."""
        mock_profile.detected_type = "hierarchical"
        assert auto_detector._is_reference_entity(mock_profile) is True

    def test_small_dataset_with_unique_id_is_reference(
        self, auto_detector, mock_profile
    ):
        """Test small dataset with unique ID is reference."""
        mock_profile.record_count = 500
        mock_profile.detected_type = "tabular"

        # Use complete column profile
        id_col = create_column_profile(
            name="id_taxon",
            dtype="int64",
            semantic_type="identifier",
            unique_ratio=0.95,
        )
        mock_profile.columns = [id_col]

        assert auto_detector._is_reference_entity(mock_profile) is True

    def test_plot_file_is_reference(self, auto_detector, mock_profile):
        """Test plot file is identified as reference."""
        mock_profile.suggested_name = "plots"
        mock_profile.record_count = 50
        mock_profile.columns = []

        assert auto_detector._is_reference_entity(mock_profile) is True

    def test_location_file_is_reference(self, auto_detector, mock_profile):
        """Test location file is identified as reference."""
        mock_profile.suggested_name = "locations"
        mock_profile.record_count = 100
        mock_profile.columns = []

        assert auto_detector._is_reference_entity(mock_profile) is True

    def test_large_dataset_without_unique_id_not_reference(
        self, auto_detector, mock_profile
    ):
        """Test large dataset without unique ID is not reference."""
        mock_profile.record_count = 10000
        mock_profile.detected_type = "tabular"

        # Use complete column profile
        col = create_column_profile(name="value", dtype="float64", unique_ratio=0.1)
        mock_profile.columns = [col]

        assert auto_detector._is_reference_entity(mock_profile) is False


class TestIsShapeEntity:
    """Test _is_shape_entity method."""

    def test_spatial_in_shapes_dir_is_shape(self, auto_detector, mock_profile):
        """Test spatial file in shapes directory is shape."""
        mock_profile.detected_type = "spatial"
        mock_profile.file_path = Path("/data/shapes/provinces.shp")

        assert auto_detector._is_shape_entity(mock_profile) is True

    def test_spatial_with_shape_in_name_is_shape(self, auto_detector, mock_profile):
        """Test spatial file with 'shape' in name is shape."""
        mock_profile.detected_type = "spatial"
        mock_profile.file_path = Path("/data/administrative_shapes.geojson")

        assert auto_detector._is_shape_entity(mock_profile) is True

    def test_non_spatial_not_shape(self, auto_detector, mock_profile):
        """Test non-spatial file is not shape."""
        mock_profile.detected_type = "tabular"
        mock_profile.file_path = Path("/data/shapes/data.csv")

        assert auto_detector._is_shape_entity(mock_profile) is False


class TestIsLayerEntity:
    """Test _is_layer_entity method."""

    def test_layer_in_name_is_layer(self, auto_detector, mock_profile):
        """Test file with 'layer' in name is layer."""
        mock_profile.file_path = Path("/data/elevation_layer.tif")

        assert auto_detector._is_layer_entity(mock_profile) is True

    def test_file_in_layers_dir_is_layer(self, auto_detector, mock_profile):
        """Test file in layers directory is layer."""
        mock_profile.file_path = Path("/data/layers/elevation.tif")

        assert auto_detector._is_layer_entity(mock_profile) is True

    def test_normal_file_not_layer(self, auto_detector, mock_profile):
        """Test normal file is not layer."""
        mock_profile.file_path = Path("/data/occurrences.csv")

        assert auto_detector._is_layer_entity(mock_profile) is False


class TestCreateReferenceConfig:
    """Test _create_reference_config method."""

    def test_create_config_for_hierarchical(self, auto_detector, mock_profile):
        """Test creating config for hierarchical reference."""
        mock_profile.detected_type = "hierarchical"
        mock_profile.file_path = Path("/project/data/taxonomy.csv")

        # Add complete taxonomy columns
        family_col = create_column_profile(
            name="family",
            dtype="object",
            semantic_type="taxonomy.family",
            unique_ratio=0.3,
            sample_values=["Fabaceae", "Myrtaceae"],
        )

        genus_col = create_column_profile(
            name="genus",
            dtype="object",
            semantic_type="taxonomy.genus",
            unique_ratio=0.6,
            sample_values=["Acacia", "Eucalyptus"],
        )

        id_col = create_column_profile(
            name="id_taxon",
            dtype="int64",
            semantic_type="taxonomy.taxon_id",
            unique_ratio=1.0,
            sample_values=[1, 2, 3, 4, 5],
        )

        mock_profile.columns = [family_col, genus_col, id_col]

        config = auto_detector._create_reference_config(mock_profile)

        assert config["type"] == "hierarchical"
        assert "hierarchy" in config
        assert "family" in config["hierarchy"]
        assert "genus" in config["hierarchy"]
        assert config["id_field"] == "id_taxon"

    def test_create_config_for_spatial_reference(self, auto_detector, mock_profile):
        """Test creating config for spatial reference."""
        mock_profile.detected_type = "spatial"
        mock_profile.file_path = Path("/project/data/plots.geojson")
        mock_profile.geometry_type = "Polygon"

        # Complete column profiles
        id_col = create_column_profile(
            name="id_plot",
            dtype="int64",
            semantic_type="identifier",
            unique_ratio=1.0,
            sample_values=[1, 2, 3],
        )

        name_col = create_column_profile(
            name="plot_name",
            dtype="object",
            semantic_type="location.plot",
            unique_ratio=1.0,
            sample_values=["Plot A", "Plot B", "Plot C"],
        )

        geom_col = create_column_profile(
            name="geometry",
            dtype="geometry",
            semantic_type="geometry",
            unique_ratio=1.0,
        )

        mock_profile.columns = [id_col, name_col, geom_col]

        config = auto_detector._create_reference_config(mock_profile)

        assert config["type"] == "spatial"
        assert config["id_field"] == "id_plot"
        assert config["name_field"] == "plot_name"
        assert config["geometry_field"] == "geometry"


class TestCreateShapeConfig:
    """Test _create_shape_config method."""

    def test_create_shape_config(self, auto_detector, mock_profile):
        """Test creating shape configuration."""
        mock_profile.suggested_name = "administrative_boundaries"
        mock_profile.file_path = Path("/project/data/shapes/admin.shp")

        # Complete column profile
        name_col = create_column_profile(
            name="province_name",
            dtype="object",
            semantic_type="location.name",
            unique_ratio=0.95,
            sample_values=["North", "South", "East"],
        )
        mock_profile.columns = [name_col]

        config = auto_detector._create_shape_config(mock_profile)

        assert "type" in config
        assert "Administrative Boundaries" in config["type"]
        assert "path" in config
        assert config["name_field"] == "province_name"

    def test_create_shape_config_finds_name_field(self, auto_detector, mock_profile):
        """Test that name field is correctly identified."""
        mock_profile.suggested_name = "regions"
        mock_profile.file_path = Path("/project/data/shapes/regions.shp")

        # Complete column profiles
        col1 = create_column_profile(
            name="id",
            dtype="int64",
            semantic_type="identifier",
            unique_ratio=1.0,
        )

        col2 = create_column_profile(
            name="label",
            dtype="object",
            semantic_type="location.name",
            unique_ratio=0.9,
            sample_values=["Region A", "Region B"],
        )

        mock_profile.columns = [col1, col2]

        config = auto_detector._create_shape_config(mock_profile)

        assert config["name_field"] == "label"


class TestCreateLayerConfig:
    """Test _create_layer_config method."""

    def test_create_layer_config_raster(self, auto_detector, mock_profile):
        """Test creating layer config for raster."""
        mock_profile.suggested_name = "elevation"
        mock_profile.file_path = Path("/project/data/layers/elevation.tif")

        config = auto_detector._create_layer_config(mock_profile)

        assert config["name"] == "elevation"
        assert config["type"] == "raster"
        assert "elevation.tif" in config["path"]

    def test_create_layer_config_vector(self, auto_detector, mock_profile):
        """Test creating layer config for vector."""
        mock_profile.suggested_name = "roads"
        mock_profile.file_path = Path("/project/data/layers/roads.geojson")

        config = auto_detector._create_layer_config(mock_profile)

        assert config["type"] == "vector"


class TestAnalyzeFiles:
    """Test analyze_files method."""

    def test_analyze_files_success(self, auto_detector):
        """Test analyzing files successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "data1.csv"
            file1.write_text("id,name\n1,A\n2,B")

            with patch.object(auto_detector.profiler, "profile") as mock_profile:
                profile = MagicMock(spec=DatasetProfile)
                profile.suggested_name = "data1"
                profile.detected_type = "tabular"
                profile.file_path = file1
                profile.columns = []
                profile.record_count = 2
                profile.to_dict.return_value = {}
                mock_profile.return_value = profile

                result = auto_detector.analyze_files([file1])

                assert "config" in result
                assert "profiles" in result
                assert "validation" in result
                assert "confidence" in result

    def test_analyze_files_handles_errors(self, auto_detector, capsys):
        """Test that analyze_files handles profiling errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "bad.csv"
            file1.write_text("invalid")

            with patch.object(
                auto_detector.profiler, "profile", side_effect=Exception("Parse error")
            ):
                result = auto_detector.analyze_files([file1])

                captured = capsys.readouterr()
                assert "Failed to analyze" in captured.out
                assert len(result["profiles"]) == 0


class TestAnalyzeDirectory:
    """Test analyze_directory method."""

    def test_analyze_directory_success(self, auto_detector, temp_data_dir, capsys):
        """Test analyzing directory successfully."""
        with patch.object(auto_detector.profiler, "profile") as mock_profile:
            profile = MagicMock(spec=DatasetProfile)
            profile.suggested_name = "occurrences"
            profile.detected_type = "tabular"
            profile.file_path = temp_data_dir / "occurrences.csv"
            profile.columns = []
            profile.record_count = 2
            profile.to_dict.return_value = {}
            mock_profile.return_value = profile

            result = auto_detector.analyze_directory(temp_data_dir)

            assert "config" in result
            assert "profiles" in result
            assert "validation" in result
            assert "confidence" in result
            assert "summary" in result

            captured = capsys.readouterr()
            assert "Analyzed" in captured.out

    def test_analyze_directory_displays_errors(
        self, auto_detector, temp_data_dir, capsys
    ):
        """Test that directory analysis shows errors."""
        with patch.object(
            auto_detector.profiler, "profile", side_effect=Exception("Error")
        ):
            auto_detector.analyze_directory(temp_data_dir)

            captured = capsys.readouterr()
            assert "Failed to analyze" in captured.out


class TestGenerateConfig:
    """Test _generate_config method."""

    def test_generate_config_empty_profiles(self, auto_detector):
        """Test generating config with no profiles."""
        config = auto_detector._generate_config([])

        assert "references" in config
        assert "data" in config
        # shapes and layers should be removed if empty
        assert "shapes" not in config or config["shapes"] == []
        assert "layers" not in config or config["layers"] == []

    def test_generate_config_with_reference(self, auto_detector, mock_profile):
        """Test generating config with reference entity."""
        mock_profile.detected_type = "hierarchical"
        mock_profile.suggested_name = "taxonomy"
        mock_profile.columns = []

        config = auto_detector._generate_config([mock_profile])

        assert "taxonomy" in config["references"]

    def test_generate_config_with_shape(self, auto_detector, mock_profile):
        """Test generating config with shape entity."""
        mock_profile.detected_type = "spatial"
        mock_profile.file_path = Path("/project/data/shapes/provinces.shp")
        mock_profile.suggested_name = "provinces"
        mock_profile.columns = []

        config = auto_detector._generate_config([mock_profile])

        assert "shapes" in config
        assert len(config["shapes"]) > 0

    def test_generate_config_with_layer(self, auto_detector, mock_profile):
        """Test generating config with layer entity."""
        mock_profile.file_path = Path("/project/data/layers/elevation.tif")
        mock_profile.suggested_name = "elevation"
        mock_profile.columns = []

        config = auto_detector._generate_config([mock_profile])

        assert "layers" in config
        assert len(config["layers"]) > 0

    def test_generate_config_removes_empty_sections(self, auto_detector, mock_profile):
        """Test that empty sections are removed from config."""
        mock_profile.detected_type = "tabular"
        mock_profile.suggested_name = "occurrences"
        mock_profile.columns = []

        config = auto_detector._generate_config([mock_profile])

        # shapes and layers should not be in config if empty
        assert "shapes" not in config
        assert "layers" not in config
