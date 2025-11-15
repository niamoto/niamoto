"""Tests for DataBootstrap module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch
import yaml

from niamoto.core.imports.bootstrap import DataBootstrap


@pytest.fixture
def bootstrap():
    """Create a DataBootstrap instance."""
    return DataBootstrap()


@pytest.fixture
def bootstrap_with_instance(tmp_path):
    """Create a DataBootstrap with an instance path."""
    instance_path = tmp_path / "niamoto-instance"
    return DataBootstrap(instance_path=instance_path)


@pytest.fixture
def temp_data_dir():
    """Create temporary directory with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        # Create a simple CSV file
        csv_file = data_dir / "data.csv"
        csv_file.write_text("id,name\n1,A\n2,B")
        yield data_dir


@pytest.fixture
def mock_analysis():
    """Create mock analysis result."""
    return {
        "config": {
            "references": {},
            "data": {"occurrences": {"source": "occurrences.csv"}},
        },
        "profiles": [
            {
                "file_path": "data/occurrences.csv",
                "detected_type": "tabular",
                "record_count": 100,
            }
        ],
        "validation": {"warnings": [], "errors": []},
        "confidence": 0.85,
        "summary": {
            "total_files": 1,
            "total_records": 100,
            "references": 0,
            "data": 1,
            "detected_entities": {
                "references": [],
                "data": [{"name": "occurrences", "records": 100}],
            },
        },
    }


class TestDataBootstrapInit:
    """Test DataBootstrap initialization."""

    def test_init_without_instance_path(self, bootstrap):
        """Test initialization without instance path."""
        assert bootstrap.instance_path is None
        assert bootstrap.detector is not None

    def test_init_with_instance_path(self, tmp_path):
        """Test initialization with instance path."""
        instance = tmp_path / "instance"
        bootstrap = DataBootstrap(instance_path=instance)

        assert bootstrap.instance_path == instance
        assert bootstrap.detector is not None


class TestRun:
    """Test run method."""

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_basic_workflow(
        self, mock_analyze, bootstrap, temp_data_dir, mock_analysis
    ):
        """Test basic bootstrap workflow with real config generation and saving."""
        mock_analyze.return_value = mock_analysis

        # Let _generate_all_configs and _save_configurations run for real
        result = bootstrap.run(
            data_dir=temp_data_dir,
            auto_confirm=True,
            interactive=False,
        )

        assert result["status"] == "completed"
        assert "timestamp" in result
        assert "steps" in result
        assert len(result["steps"]) >= 3

        # Verify real config files were created
        config_dir = temp_data_dir.parent / "config"
        assert (config_dir / "import.yml").exists()
        assert (config_dir / "transform.yml").exists()
        assert (config_dir / "export.yml").exists()

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_with_output_dir(
        self, mock_analyze, bootstrap, temp_data_dir, mock_analysis, tmp_path
    ):
        """Test run with custom output directory creates files in specified location."""
        output_dir = tmp_path / "custom_config"
        mock_analyze.return_value = mock_analysis

        bootstrap.run(
            data_dir=temp_data_dir,
            output_dir=output_dir,
            auto_confirm=True,
            interactive=False,
        )

        # Verify files were created in custom output dir
        assert (output_dir / "import.yml").exists()
        assert (output_dir / "transform.yml").exists()
        assert (output_dir / "export.yml").exists()

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_default_output_dir(
        self, mock_analyze, bootstrap, temp_data_dir, mock_analysis
    ):
        """Test run with default output directory creates files in parent/config."""
        mock_analyze.return_value = mock_analysis

        bootstrap.run(
            data_dir=temp_data_dir,
            auto_confirm=True,
            interactive=False,
        )

        # Default output should be data_dir.parent / "config"
        expected_output = temp_data_dir.parent / "config"
        assert (expected_output / "import.yml").exists()
        assert (expected_output / "transform.yml").exists()
        assert (expected_output / "export.yml").exists()

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_with_interactive_displays_summary(
        self, mock_analyze, bootstrap, temp_data_dir, mock_analysis, capsys
    ):
        """Test that interactive mode displays progress steps."""
        mock_analyze.return_value = mock_analysis

        bootstrap.run(
            data_dir=temp_data_dir,
            auto_confirm=True,
            interactive=True,
        )

        captured = capsys.readouterr()
        assert "Step 1" in captured.out
        assert "Analyzing" in captured.out

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    @patch.object(DataBootstrap, "_confirm_configuration", return_value=False)
    def test_run_cancelled_by_user(
        self, mock_confirm, mock_analyze, bootstrap, temp_data_dir, mock_analysis
    ):
        """Test that run can be cancelled when user rejects configuration."""
        mock_analyze.return_value = mock_analysis

        result = bootstrap.run(
            data_dir=temp_data_dir,
            auto_confirm=False,
            interactive=True,
        )

        assert result["status"] == "cancelled"
        mock_confirm.assert_called_once()

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_with_instance_creation(
        self, mock_analyze, bootstrap_with_instance, temp_data_dir, mock_analysis
    ):
        """Test run with instance structure creation creates instance directories."""
        mock_analyze.return_value = mock_analysis

        result = bootstrap_with_instance.run(
            data_dir=temp_data_dir,
            auto_confirm=True,
            interactive=False,
        )

        assert result["instance_created"] is True

        # Verify instance structure was actually created
        instance_path = bootstrap_with_instance.instance_path
        assert (instance_path / "config").exists()
        assert (instance_path / "data").exists()
        assert (instance_path / "exports").exists()
        assert (instance_path / "logs").exists()
        assert (instance_path / "README.md").exists()

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_analysis_step_recorded(
        self, mock_analyze, bootstrap, temp_data_dir, mock_analysis
    ):
        """Test that analysis step is recorded in results with correct metadata."""
        mock_analyze.return_value = mock_analysis

        result = bootstrap.run(
            data_dir=temp_data_dir,
            auto_confirm=True,
            interactive=False,
        )

        analysis_step = next(
            (s for s in result["steps"] if s["name"] == "analysis"), None
        )
        assert analysis_step is not None
        assert analysis_step["status"] == "completed"
        assert "files_analyzed" in analysis_step

    @patch("niamoto.core.imports.auto_detector.AutoDetector.analyze_directory")
    def test_run_config_generation_step_recorded(
        self, mock_analyze, bootstrap, temp_data_dir, mock_analysis
    ):
        """Test that config generation step is recorded in results."""
        mock_analyze.return_value = mock_analysis

        result = bootstrap.run(
            data_dir=temp_data_dir,
            auto_confirm=True,
            interactive=False,
        )

        config_step = next(
            (s for s in result["steps"] if s["name"] == "config_generation"),
            None,
        )
        assert config_step is not None
        assert config_step["status"] == "completed"


class TestDisplayAnalysisSummary:
    """Test _display_analysis_summary method."""

    def test_display_summary_basic(self, bootstrap, mock_analysis, capsys):
        """Test displaying basic analysis summary."""
        bootstrap._display_analysis_summary(mock_analysis)

        captured = capsys.readouterr()
        assert "Analysis complete" in captured.out
        assert "Found 1 files" in captured.out
        assert "100 total records" in captured.out
        assert "85%" in captured.out

    def test_display_summary_with_warnings(self, bootstrap, mock_analysis, capsys):
        """Test displaying summary with warnings."""
        mock_analysis["validation"]["warnings"] = [
            "Warning 1",
            "Warning 2",
        ]

        bootstrap._display_analysis_summary(mock_analysis)

        captured = capsys.readouterr()
        assert "Warnings:" in captured.out
        assert "Warning 1" in captured.out
        assert "Warning 2" in captured.out

    def test_display_summary_formats_record_count(self, bootstrap, capsys):
        """Test that large record counts are formatted with commas."""
        analysis = {
            "summary": {"total_files": 5, "total_records": 1000000},
            "confidence": 0.9,
            "validation": {"warnings": []},
        }

        bootstrap._display_analysis_summary(analysis)

        captured = capsys.readouterr()
        assert "1,000,000" in captured.out


class TestConfirmConfiguration:
    """Test _confirm_configuration method."""

    def test_confirm_shows_configuration(self, bootstrap, mock_analysis, capsys):
        """Test that confirmation displays configuration."""
        with patch("builtins.input", return_value="y"):
            result = bootstrap._confirm_configuration(mock_analysis)

            captured = capsys.readouterr()
            assert "DETECTED CONFIGURATION" in captured.out
            assert result is True

    def test_confirm_user_accepts(self, bootstrap, mock_analysis):
        """Test user accepting configuration."""
        with patch("builtins.input", return_value="y"):
            result = bootstrap._confirm_configuration(mock_analysis)
            assert result is True

    def test_confirm_user_rejects(self, bootstrap, mock_analysis):
        """Test user rejecting configuration."""
        with patch("builtins.input", return_value="n"):
            result = bootstrap._confirm_configuration(mock_analysis)
            assert result is False

    def test_confirm_user_uppercase_yes(self, bootstrap, mock_analysis):
        """Test user input is case-insensitive."""
        with patch("builtins.input", return_value="Y"):
            result = bootstrap._confirm_configuration(mock_analysis)
            assert result is True


class TestGenerateAllConfigs:
    """Test _generate_all_configs method."""

    def test_generate_all_configs_creates_three_configs(self, bootstrap):
        """Test that _generate_all_configs creates import, transform, and export configs."""
        import_config = {
            "references": {"taxonomy": {"type": "hierarchical"}},
            "data": {"occurrences": {"source": "occurrences.csv"}},
        }

        configs = bootstrap._generate_all_configs(import_config)

        # Verify all three config files are generated
        assert "import.yml" in configs
        assert "transform.yml" in configs
        assert "export.yml" in configs

        # Verify structures are correct types
        assert isinstance(configs["import.yml"], dict)
        assert isinstance(configs["transform.yml"], list)
        assert isinstance(configs["export.yml"], dict)

    def test_generate_all_configs_preserves_import_config(self, bootstrap):
        """Test that import config is preserved in the output."""
        import_config = {
            "references": {"taxonomy": {"type": "hierarchical"}},
            "data": {"occurrences": {"source": "occurrences.csv"}},
        }

        configs = bootstrap._generate_all_configs(import_config)

        # Import config should be preserved as-is
        assert configs["import.yml"] == import_config

    def test_generate_all_configs_creates_export_with_site(self, bootstrap):
        """Test that export config contains site configuration."""
        import_config = {"references": {}, "data": {"occurrences": {}}}

        configs = bootstrap._generate_all_configs(import_config)

        # Export config should have site section
        assert "site" in configs["export.yml"]
        assert "title" in configs["export.yml"]["site"]
        assert "pages" in configs["export.yml"]


class TestSaveConfigurations:
    """Test _save_configurations method."""

    def test_save_configurations_creates_yaml_files(self, bootstrap, tmp_path):
        """Test that _save_configurations creates YAML files in output directory."""
        output_dir = tmp_path / "config"
        configs = {
            "import.yml": {"references": {}, "data": {}},
            "transform.yml": [],
            "export.yml": {"site": {"title": "Test"}},
        }

        saved_files = bootstrap._save_configurations(configs, output_dir)

        # Verify all files were created
        assert len(saved_files) == 3
        assert (output_dir / "import.yml").exists()
        assert (output_dir / "transform.yml").exists()
        assert (output_dir / "export.yml").exists()

    def test_save_configurations_creates_directory_if_missing(
        self, bootstrap, tmp_path
    ):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "nonexistent" / "config"
        configs = {"import.yml": {}}

        bootstrap._save_configurations(configs, output_dir)

        assert output_dir.exists()
        assert (output_dir / "import.yml").exists()

    def test_save_configurations_backs_up_existing_files(self, bootstrap, tmp_path):
        """Test that existing files are backed up before overwriting."""
        output_dir = tmp_path / "config"
        output_dir.mkdir()

        # Create existing file
        existing_file = output_dir / "import.yml"
        existing_file.write_text("old: content")

        configs = {"import.yml": {"new": "content"}}
        bootstrap._save_configurations(configs, output_dir)

        # Original file should be updated
        with open(existing_file) as f:
            content = yaml.safe_load(f)
        assert content == {"new": "content"}

        # Backup should exist
        backups = list(output_dir.glob("import.backup.*"))
        assert len(backups) == 1


class TestCreateInstanceStructure:
    """Test _create_instance_structure method."""

    def test_create_instance_structure_creates_directories(self, bootstrap, tmp_path):
        """Test that instance structure creates all necessary directories."""
        instance_path = tmp_path / "instance"
        data_dir = tmp_path / "data"
        config_dir = tmp_path / "config"

        data_dir.mkdir()
        config_dir.mkdir()

        bootstrap._create_instance_structure(instance_path, data_dir, config_dir)

        # Verify all required directories are created
        assert (instance_path / "config").exists()
        assert (instance_path / "data").exists()
        assert (instance_path / "exports").exists()
        assert (instance_path / "logs").exists()

    def test_create_instance_structure_copies_config_files(self, bootstrap, tmp_path):
        """Test that config files are copied to instance."""
        instance_path = tmp_path / "instance"
        data_dir = tmp_path / "data"
        config_dir = tmp_path / "config"

        data_dir.mkdir()
        config_dir.mkdir()

        # Create config files
        (config_dir / "import.yml").write_text("import: config")
        (config_dir / "transform.yml").write_text("transform: config")
        (config_dir / "export.yml").write_text("export: config")

        bootstrap._create_instance_structure(instance_path, data_dir, config_dir)

        # Check that all configs were copied
        assert (instance_path / "config" / "import.yml").exists()
        assert (instance_path / "config" / "transform.yml").exists()
        assert (instance_path / "config" / "export.yml").exists()

    def test_create_instance_structure_creates_readme(self, bootstrap, tmp_path):
        """Test that a README.md file is created in the instance."""
        instance_path = tmp_path / "instance"
        data_dir = tmp_path / "data"
        config_dir = tmp_path / "config"

        data_dir.mkdir()
        config_dir.mkdir()

        bootstrap._create_instance_structure(instance_path, data_dir, config_dir)

        # README should be created
        readme = instance_path / "README.md"
        assert readme.exists()

        content = readme.read_text()
        assert "Niamoto Instance" in content
        assert "Quick Start" in content


class TestDisplayCompletionMessage:
    """Test _display_completion_message method."""

    def test_display_completion_message_shows_success(self, bootstrap, capsys):
        """Test that completion message displays success banner."""
        results = {
            "status": "completed",
            "files_created": ["config/import.yml", "config/transform.yml"],
        }

        bootstrap._display_completion_message(results)

        captured = capsys.readouterr()
        assert "BOOTSTRAP COMPLETE" in captured.out
        assert "🎉" in captured.out

    def test_display_completion_message_shows_next_steps(self, bootstrap, capsys):
        """Test that completion message shows next steps."""
        results = {"status": "completed"}

        bootstrap._display_completion_message(results)

        captured = capsys.readouterr()
        # Should guide user on what to do next
        assert len(captured.out) > 0
