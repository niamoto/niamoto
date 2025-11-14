"""Tests for common paths module."""

from pathlib import Path

from niamoto.common.paths import PROJECT_ROOT


class TestProjectRoot:
    """Test PROJECT_ROOT constant."""

    def test_project_root_exists(self):
        """Test that PROJECT_ROOT points to an existing directory."""
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()

    def test_project_root_is_path_object(self):
        """Test that PROJECT_ROOT is a Path instance."""
        assert isinstance(PROJECT_ROOT, Path)

    def test_project_root_is_absolute(self):
        """Test that PROJECT_ROOT is an absolute path."""
        assert PROJECT_ROOT.is_absolute()

    def test_project_root_contains_src(self):
        """Test that PROJECT_ROOT is the niamoto package directory."""
        # PROJECT_ROOT should be the src/niamoto directory
        assert PROJECT_ROOT.name == "niamoto"
        # Should contain key modules
        assert (PROJECT_ROOT / "__init__.py").exists()
        assert (PROJECT_ROOT / "cli").exists()
        assert (PROJECT_ROOT / "core").exists()
