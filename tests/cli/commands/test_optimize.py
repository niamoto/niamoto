"""Tests for optimize command."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from niamoto.cli.commands.optimize import optimize_command


class TestOptimizeCommand:
    """Test optimize command."""

    def test_optimize_with_explicit_db_path(self, tmp_path):
        """Test optimize command with explicit database path."""
        runner = CliRunner()
        db_file = tmp_path / "test.db"
        db_file.touch()

        with patch("niamoto.cli.commands.optimize.Database") as mock_db_class:
            mock_db = MagicMock()
            mock_db_class.return_value = mock_db

            result = runner.invoke(optimize_command, ["--db-path", str(db_file)])

            assert result.exit_code == 0
            assert "Optimizing database" in result.output
            assert "Database optimization completed successfully" in result.output

            # Verify Database was initialized with optimize=True
            mock_db_class.assert_called_once_with(str(db_file), optimize=True)
            mock_db.optimize_all_tables.assert_called_once()
            mock_db.optimize_database.assert_called_once()

    def test_optimize_without_db_path_uses_config(self, tmp_path):
        """Test optimize command without db path uses configuration."""
        runner = CliRunner()
        db_file = tmp_path / "niamoto.db"
        db_file.touch()

        with patch("niamoto.cli.commands.optimize.Config") as mock_config_class:
            with patch("niamoto.cli.commands.optimize.Database") as mock_db_class:
                mock_config = MagicMock()
                mock_config.database_path = str(db_file)
                mock_config_class.return_value = mock_config
                mock_db = MagicMock()
                mock_db_class.return_value = mock_db

                result = runner.invoke(optimize_command)

                assert result.exit_code == 0
                mock_config_class.assert_called_once()
                mock_db.optimize_all_tables.assert_called_once()

    def test_optimize_config_error(self):
        """Test optimize command when config cannot be loaded."""
        runner = CliRunner()

        with patch("niamoto.cli.commands.optimize.Config") as mock_config_class:
            mock_config_class.side_effect = Exception("Config error")

            result = runner.invoke(optimize_command)

            assert result.exit_code == 1
            assert "Error loading configuration" in result.output

    def test_optimize_database_not_found(self, tmp_path):
        """Test optimize command when database file is removed after validation."""
        runner = CliRunner()
        db_file = tmp_path / "temp.db"
        db_file.touch()  # Create file first to pass Click validation

        # Mock Path.exists to return False after Click validates it
        with patch("niamoto.cli.commands.optimize.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            result = runner.invoke(optimize_command, ["--db-path", str(db_file)])

            assert result.exit_code == 1
            assert "Database not found" in result.output

    def test_optimize_with_stats(self, tmp_path):
        """Test optimize command with --show-stats option."""
        runner = CliRunner()
        db_file = tmp_path / "test.db"
        db_file.touch()

        with patch("niamoto.cli.commands.optimize.Database") as mock_db_class:
            mock_db = MagicMock()
            mock_db.get_database_stats.return_value = {
                "database_size_mb": 10.5,
                "table_count": 15,
                "index_count": 20,
                "cache_size": -64000,
                "journal_mode": "wal",
            }
            mock_db_class.return_value = mock_db

            result = runner.invoke(
                optimize_command, ["--db-path", str(db_file), "--show-stats"]
            )

            assert result.exit_code == 0
            assert "Database Statistics" in result.output
            assert "10.5 MB" in result.output
            assert "15" in result.output  # table count
            assert "20" in result.output  # index count
            assert "WAL mode enabled" in result.output
            assert "Large cache configured" in result.output
            assert "well-indexed" in result.output

    def test_optimize_stats_with_delete_mode(self, tmp_path):
        """Test stats display when journal mode is not WAL."""
        runner = CliRunner()
        db_file = tmp_path / "test.db"
        db_file.touch()

        with patch("niamoto.cli.commands.optimize.Database") as mock_db_class:
            mock_db = MagicMock()
            mock_db.get_database_stats.return_value = {
                "database_size_mb": 5.2,
                "table_count": 10,
                "index_count": 8,
                "cache_size": -16000,
                "journal_mode": "delete",
            }
            mock_db_class.return_value = mock_db

            result = runner.invoke(
                optimize_command, ["--db-path", str(db_file), "--show-stats"]
            )

            assert result.exit_code == 0
            assert "Consider enabling WAL mode" in result.output
            assert "Consider increasing cache size" in result.output
            assert "may benefit from additional indexes" in result.output

    def test_optimize_database_error(self, tmp_path):
        """Test optimize command when database optimization fails."""
        runner = CliRunner()
        db_file = tmp_path / "test.db"
        db_file.touch()

        with patch("niamoto.cli.commands.optimize.Database") as mock_db_class:
            mock_db = MagicMock()
            mock_db.optimize_all_tables.side_effect = Exception("Optimization failed")
            mock_db_class.return_value = mock_db

            result = runner.invoke(optimize_command, ["--db-path", str(db_file)])

            assert result.exit_code == 1
            assert "Error during optimization" in result.output
            assert "Optimization failed" in result.output
