"""Tests for GUI API context module."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch
import yaml

from niamoto.gui.api import context


@pytest.fixture(autouse=True)
def reset_working_directory():
    """Reset the global working directory before each test."""
    # Store the original value
    original = context._working_directory
    context._working_directory = None

    yield

    # Restore original value after test
    context._working_directory = original


class TestSetWorkingDirectory:
    """Test set_working_directory function."""

    def test_set_working_directory(self, tmp_path):
        """Test setting the working directory."""
        test_dir = tmp_path / "niamoto-project"
        test_dir.mkdir()

        context.set_working_directory(test_dir)

        assert context._working_directory == test_dir

    def test_set_working_directory_updates_global(self, tmp_path):
        """Test that set_working_directory updates the global variable."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        context.set_working_directory(dir1)
        assert context._working_directory == dir1

        context.set_working_directory(dir2)
        assert context._working_directory == dir2


class TestGetWorkingDirectory:
    """Test get_working_directory function."""

    def test_get_working_directory_when_set(self, tmp_path):
        """Test get_working_directory returns set directory."""
        test_dir = tmp_path / "project"
        test_dir.mkdir()

        context.set_working_directory(test_dir)
        result = context.get_working_directory()

        assert result == test_dir

    def test_get_working_directory_from_env_var(self, tmp_path):
        """Test get_working_directory uses NIAMOTO_HOME env var."""
        test_dir = tmp_path / "from-env"
        test_dir.mkdir()

        with patch.dict(os.environ, {"NIAMOTO_HOME": str(test_dir)}):
            result = context.get_working_directory()

        assert result == test_dir

    def test_get_working_directory_fallback_to_cwd(self):
        """Test get_working_directory falls back to cwd."""
        # Make sure no NIAMOTO_HOME is set
        with patch.dict(os.environ, {}, clear=True):
            result = context.get_working_directory()

        assert result == Path.cwd()

    def test_get_working_directory_priority(self, tmp_path):
        """Test that set_working_directory takes priority over env var."""
        dir_set = tmp_path / "set"
        dir_env = tmp_path / "env"
        dir_set.mkdir()
        dir_env.mkdir()

        context.set_working_directory(dir_set)

        with patch.dict(os.environ, {"NIAMOTO_HOME": str(dir_env)}):
            result = context.get_working_directory()

        # Should use the set directory, not the env var
        assert result == dir_set


class TestGetDatabasePath:
    """Test get_database_path function."""

    def test_get_database_path_from_config(self, tmp_path):
        """Test finding database path from config.yml."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_dir = tmp_path / "db"
        db_dir.mkdir()

        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.dump({"database": {"path": "db/niamoto.duckdb"}}))

        db_file = db_dir / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_config_with_absolute_path(self, tmp_path):
        """Test database path with absolute path in config."""
        # Create config
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create database in different location
        db_file = tmp_path / "absolute" / "path" / "niamoto.duckdb"
        db_file.parent.mkdir(parents=True)
        db_file.write_text("fake db")

        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.dump({"database": {"path": str(db_file)}}))

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_fallback_db_duckdb(self, tmp_path):
        """Test fallback to db/niamoto.duckdb."""
        db_dir = tmp_path / "db"
        db_dir.mkdir()
        db_file = db_dir / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_fallback_duckdb_root(self, tmp_path):
        """Test fallback to niamoto.duckdb in root."""
        db_file = tmp_path / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_fallback_data_duckdb(self, tmp_path):
        """Test fallback to data/niamoto.duckdb."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_file = data_dir / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_legacy_sqlite_config(self, tmp_path):
        """Ensure legacy sqlite paths still work when configured."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        db_dir = tmp_path / "db"
        db_dir.mkdir()

        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.dump({"database": {"path": "db/niamoto.db"}}))

        db_file = db_dir / "niamoto.db"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_legacy_sqlite_fallback(self, tmp_path):
        """Ensure sqlite fallback works when DuckDB files are absent."""
        db_dir = tmp_path / "db"
        db_dir.mkdir()
        db_file = db_dir / "niamoto.db"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file

    def test_get_database_path_not_found(self, tmp_path):
        """Test when database file is not found."""
        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result is None

    def test_get_database_path_config_error(self, tmp_path):
        """Test handling of config file errors."""
        # Create invalid config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("invalid: yaml: {{")

        # Create fallback database
        db_dir = tmp_path / "db"
        db_dir.mkdir()
        db_file = db_dir / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        # Should fall back to default location despite config error
        assert result == db_file

    def test_get_database_path_config_without_database_section(self, tmp_path):
        """Test config without database section."""
        # Create config without database section
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text(yaml.dump({"project": {"name": "Test"}}))

        # Create fallback database
        db_dir = tmp_path / "db"
        db_dir.mkdir()
        db_file = db_dir / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        # Should use default path from config (db/niamoto.duckdb)
        assert result == db_file

    def test_get_database_path_empty_config(self, tmp_path):
        """Test with empty config file."""
        # Create empty config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yml"
        config_file.write_text("")

        # Create fallback database
        db_dir = tmp_path / "db"
        db_dir.mkdir()
        db_file = db_dir / "niamoto.duckdb"
        db_file.write_text("fake db")

        context.set_working_directory(tmp_path)
        result = context.get_database_path()

        assert result == db_file


class TestGetConfigPath:
    """Test get_config_path function."""

    def test_get_config_path_simple_filename(self, tmp_path):
        """Test get_config_path with simple filename."""
        context.set_working_directory(tmp_path)
        result = context.get_config_path("transform.yml")

        expected = tmp_path / "config" / "transform.yml"
        assert result == expected

    def test_get_config_path_with_config_prefix(self, tmp_path):
        """Test get_config_path with 'config/' prefix."""
        context.set_working_directory(tmp_path)
        result = context.get_config_path("config/transform.yml")

        expected = tmp_path / "config" / "transform.yml"
        assert result == expected

    def test_get_config_path_different_files(self, tmp_path):
        """Test get_config_path with different config files."""
        context.set_working_directory(tmp_path)

        assert (
            context.get_config_path("import.yml") == tmp_path / "config" / "import.yml"
        )
        assert (
            context.get_config_path("export.yml") == tmp_path / "config" / "export.yml"
        )
        assert (
            context.get_config_path("config.yml") == tmp_path / "config" / "config.yml"
        )

    def test_get_config_path_uses_working_directory(self, tmp_path):
        """Test that get_config_path uses the working directory."""
        dir1 = tmp_path / "project1"
        dir2 = tmp_path / "project2"
        dir1.mkdir()
        dir2.mkdir()

        context.set_working_directory(dir1)
        result1 = context.get_config_path("test.yml")
        assert result1 == dir1 / "config" / "test.yml"

        context.set_working_directory(dir2)
        result2 = context.get_config_path("test.yml")
        assert result2 == dir2 / "config" / "test.yml"
