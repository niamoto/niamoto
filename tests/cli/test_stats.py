"""
Tests for the stats command module.
"""

import json
import csv
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from click.testing import CliRunner

from niamoto.cli.commands.stats import (
    stats_command,
    get_general_statistics,
    get_group_statistics,
    display_general_statistics,
    display_group_statistics,
    show_data_exploration_suggestions,
    export_statistics,
)


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock Config class."""
    with patch("niamoto.cli.commands.stats.Config") as mock_config:
        mock_config.return_value.database_path = "/mock/db/path.db"
        yield mock_config


@pytest.fixture
def mock_database():
    """Mock Database class."""
    with patch("niamoto.cli.commands.stats.Database") as mock_db_class:
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        # Mock execute_sql for general queries
        mock_result = Mock()
        mock_result.scalar.return_value = 100
        mock_db.execute_sql.return_value = mock_result

        yield mock_db


@pytest.fixture
def mock_path():
    """Mock Path class."""
    with patch("niamoto.cli.commands.stats.Path") as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance
        mock_path_class.side_effect = (
            lambda x: mock_path_instance if x == "/mock/db/path.db" else Path(x)
        )
        yield mock_path_class


class TestStatsCommand:
    """Test the stats command."""

    def test_stats_command_help(self, runner):
        """Test that the stats command help works correctly."""
        result = runner.invoke(stats_command, ["--help"])
        assert result.exit_code == 0
        assert "Display statistics about the data" in result.output
        assert "--group" in result.output
        assert "--detailed" in result.output
        assert "--export" in result.output
        assert "--suggestions" in result.output

    def test_stats_command_database_not_found(self, runner, mock_config):
        """Test stats command when database doesn't exist."""
        with patch("niamoto.cli.commands.stats.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            result = runner.invoke(stats_command)

            assert result.exit_code == 0
            assert "Database not found" in result.output

    def test_stats_command_general_statistics(
        self, runner, mock_config, mock_database, mock_path
    ):
        """Test stats command showing general statistics."""
        # Mock table list
        mock_result = Mock()
        mock_result.__iter__ = Mock(
            return_value=iter(
                [("taxon_ref",), ("plot_ref",), ("shape_ref",), ("occurrences",)]
            )
        )
        mock_database.execute_sql.side_effect = [
            mock_result,  # Table list query
            Mock(scalar=Mock(return_value=1000)),  # taxon_ref count
            Mock(scalar=Mock(return_value=500)),  # plot_ref count
            Mock(scalar=Mock(return_value=200)),  # shape_ref count
            Mock(scalar=Mock(return_value=5000)),  # occurrences count
        ]

        result = runner.invoke(stats_command)

        assert result.exit_code == 0
        assert "Niamoto Database Statistics" in result.output

    def test_stats_command_with_group(
        self, runner, mock_config, mock_database, mock_path
    ):
        """Test stats command with specific group."""
        # Mock for group statistics
        mock_database.execute_sql.side_effect = [
            Mock(scalar=Mock(return_value=1000)),  # Count query
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # PRAGMA table_info
                            (0, "id", "INTEGER", 0, None, 1),
                            (1, "full_name", "TEXT", 0, None, 0),
                            (2, "rank_name", "TEXT", 0, None, 0),
                        ]
                    )
                )
            ),
        ]

        result = runner.invoke(stats_command, ["--group", "taxon"])

        assert result.exit_code == 0
        assert "Taxon Statistics" in result.output

    def test_stats_command_with_detailed(
        self, runner, mock_config, mock_database, mock_path
    ):
        """Test stats command with detailed flag."""
        # Mock complex responses for detailed statistics
        mock_database.execute_sql.side_effect = [
            # Table list
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            ("taxon_ref",),
                            ("plot_ref",),
                            ("shape_ref",),
                            ("occurrences",),
                        ]
                    )
                )
            ),
            # Basic counts
            Mock(scalar=Mock(return_value=1000)),  # taxon_ref
            Mock(scalar=Mock(return_value=500)),  # plot_ref
            Mock(scalar=Mock(return_value=200)),  # shape_ref
            Mock(scalar=Mock(return_value=5000)),  # occurrences
            # Shape types (PRAGMA table_info)
            Mock(
                __iter__=Mock(
                    return_value=iter([(0, "id", "INTEGER"), (1, "type", "TEXT")])
                )
            ),
            # Shape type counts
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            Mock(type="Forest", count=100),
                            Mock(type="River", count=50),
                        ]
                    )
                )
            ),
            # Occurrences columns for families
            Mock(
                __iter__=Mock(
                    return_value=iter([(0, "id", "INTEGER"), (1, "family", "TEXT")])
                )
            ),
            # Top families
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            Mock(family="Myrtaceae", count=500),
                            Mock(family="Lauraceae", count=300),
                        ]
                    )
                )
            ),
        ]

        result = runner.invoke(stats_command, ["--detailed"])

        assert result.exit_code == 0
        assert "Niamoto Database Statistics" in result.output

    def test_stats_command_with_export_json(
        self, runner, mock_config, mock_database, mock_path, tmp_path
    ):
        """Test stats command with JSON export."""
        export_file = tmp_path / "stats.json"

        # Mock database responses
        mock_database.execute_sql.side_effect = [
            Mock(__iter__=Mock(return_value=iter([("taxon_ref",)]))),
            Mock(scalar=Mock(return_value=1000)),
        ]

        result = runner.invoke(stats_command, ["--export", str(export_file)])

        assert result.exit_code == 0
        assert export_file.exists()
        assert "Statistics exported to" in result.output

        # Check JSON content
        with open(export_file) as f:
            data = json.load(f)
            assert "Reference Taxa" in data
            assert data["Reference Taxa"] == 1000

    def test_stats_command_with_export_csv(
        self, runner, mock_config, mock_database, mock_path, tmp_path
    ):
        """Test stats command with CSV export."""
        export_file = tmp_path / "stats.csv"

        # Mock database responses
        mock_database.execute_sql.side_effect = [
            Mock(__iter__=Mock(return_value=iter([("taxon_ref",)]))),
            Mock(scalar=Mock(return_value=1000)),
        ]

        result = runner.invoke(stats_command, ["--export", str(export_file)])

        assert result.exit_code == 0
        assert export_file.exists()

        # Check CSV content
        with open(export_file) as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert rows[0] == ["Category", "Metric", "Value"]
            assert ["General", "Reference Taxa", "1000"] in rows

    def test_stats_command_with_suggestions(
        self, runner, mock_config, mock_database, mock_path
    ):
        """Test stats command with suggestions flag."""
        # Mock for suggestions
        mock_database.execute_sql.side_effect = [
            # General stats queries
            Mock(__iter__=Mock(return_value=iter([("taxon_ref",)]))),
            Mock(scalar=Mock(return_value=1000)),
            # Suggestions queries
            Mock(__iter__=Mock(return_value=iter([("taxon_ref",), ("occurrences",)]))),
            # Occurrences columns
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            (0, "id", "INTEGER"),
                            (1, "family", "TEXT"),
                            (2, "elevation", "REAL"),
                        ]
                    )
                )
            ),
        ]

        result = runner.invoke(stats_command, ["--suggestions"])

        assert result.exit_code == 0
        assert "Data Exploration Suggestions" in result.output
        assert "Occurrences Data Exploration" in result.output

    def test_stats_command_database_error(self, runner, mock_config, mock_path):
        """Test stats command handling database errors."""
        # Make the Database constructor fail
        with patch("niamoto.cli.commands.stats.Database") as mock_db_class:
            mock_db_class.side_effect = Exception("Database connection failed")

            result = runner.invoke(stats_command)

            # The command catches the error and prints it, but doesn't exit with error code
            assert result.exit_code == 0
            assert "Unexpected error: Database connection failed" in result.output


class TestStatsCommandEdgeCases:
    """Test edge cases for stats command."""

    def test_stats_command_with_database_error_exception(
        self, runner, mock_config, mock_path
    ):
        """Test stats command when database raises DatabaseError."""
        from niamoto.common.exceptions import DatabaseError

        with patch("niamoto.cli.commands.stats.Database") as mock_db_class:
            mock_db_class.side_effect = DatabaseError("Connection lost")

            result = runner.invoke(stats_command)

            assert result.exit_code == 0
            assert "Database error: Connection lost" in result.output


class TestGetGeneralStatistics:
    """Test the get_general_statistics function."""

    def test_get_general_statistics_basic(self, mock_database):
        """Test getting basic general statistics."""
        # Mock responses
        mock_database.execute_sql.side_effect = [
            # Table list
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            ("taxon_ref",),
                            ("plot_ref",),
                            ("shape_ref",),
                            ("occurrences",),
                        ]
                    )
                )
            ),
            # Counts
            Mock(scalar=Mock(return_value=1000)),  # taxon_ref
            Mock(scalar=Mock(return_value=500)),  # plot_ref
            Mock(scalar=Mock(return_value=200)),  # shape_ref
            Mock(scalar=Mock(return_value=5000)),  # occurrences
        ]

        stats = get_general_statistics(mock_database)

        assert stats["Reference Taxa"] == 1000
        assert stats["Reference Plots"] == 500
        assert stats["Reference Shapes"] == 200
        assert stats["Occurrences"] == 5000

    def test_get_general_statistics_with_generated_tables(self, mock_database):
        """Test getting statistics including generated tables."""
        mock_database.execute_sql.side_effect = [
            # Table list including generated tables
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [("taxon_ref",), ("taxon",), ("plot",), ("occurrences",)]
                    )
                )
            ),
            # Reference counts
            Mock(scalar=Mock(return_value=1000)),  # taxon_ref
            Mock(scalar=Mock(return_value=5000)),  # occurrences
            # Generated table counts
            Mock(scalar=Mock(return_value=800)),  # taxon
            Mock(scalar=Mock(return_value=400)),  # plot
        ]

        stats = get_general_statistics(mock_database)

        assert "Generated Tables" in stats
        assert stats["Generated Tables"]["Taxon"] == 800
        assert stats["Generated Tables"]["Plot"] == 400

    def test_get_general_statistics_detailed(self, mock_database):
        """Test getting detailed general statistics."""
        mock_database.execute_sql.side_effect = [
            # Table list
            Mock(__iter__=Mock(return_value=iter([("occurrences",)]))),
            Mock(scalar=Mock(return_value=5000)),  # occurrences count
            # Check columns for families
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            (0, "id", "INTEGER"),
                            (1, "family", "TEXT"),
                            (2, "elevation", "REAL"),
                            (3, "dbh", "REAL"),
                        ]
                    )
                )
            ),
            # Top families
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            Mock(family="Myrtaceae", count=500),
                            Mock(family="Lauraceae", count=300),
                        ]
                    )
                )
            ),
            # Check columns for elevation
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            (0, "id", "INTEGER"),
                            (1, "elevation", "REAL"),
                        ]
                    )
                )
            ),
            # Elevation stats
            Mock(
                first=Mock(
                    return_value=Mock(
                        min_elev=0, max_elev=1000, avg_elev=500, count_with_elev=4000
                    )
                )
            ),
            # Check columns for numerical data
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            (0, "id", "INTEGER"),
                            (1, "dbh", "REAL"),
                        ]
                    )
                )
            ),
            # DBH stats
            Mock(
                first=Mock(
                    return_value=Mock(
                        count_non_null=3000, min_val=5.0, max_val=150.0, avg_val=45.5
                    )
                )
            ),
        ]

        stats = get_general_statistics(mock_database, detailed=True)

        assert "Top Families" in stats
        assert stats["Top Families"][0] == ("Myrtaceae", 500)
        assert "Elevation Range" in stats
        assert stats["Elevation Range"]["Min"] == "0m"
        assert stats["Elevation Range"]["Max"] == "1000m"
        assert "Numerical Data" in stats
        assert "dbh" in stats["Numerical Data"]

    def test_get_general_statistics_handles_errors(self, mock_database):
        """Test that get_general_statistics handles database errors gracefully."""
        # First query succeeds, subsequent queries fail
        mock_database.execute_sql.side_effect = [
            Mock(__iter__=Mock(return_value=iter([("taxon_ref",)]))),
            Exception("Query failed"),
        ]

        stats = get_general_statistics(mock_database)

        # Should have empty stats but not crash
        assert stats["Reference Taxa"] == 0

    def test_get_general_statistics_table_list_fails(self, mock_database):
        """Test when the initial table list query fails."""
        # Table list query fails
        mock_database.execute_sql.side_effect = Exception("Cannot query tables")

        stats = get_general_statistics(mock_database)

        # Should return empty stats
        assert stats == {}


class TestGetGroupStatistics:
    """Test the get_group_statistics function."""

    def test_get_group_statistics_taxon(self, mock_database):
        """Test getting statistics for taxon group."""
        mock_database.execute_sql.side_effect = [
            Mock(scalar=Mock(return_value=1000)),  # Count
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Columns
                            (0, "id", "INTEGER"),
                            (1, "full_name", "TEXT"),
                            (2, "rank_name", "TEXT"),
                        ]
                    )
                )
            ),
        ]

        stats = get_group_statistics(mock_database, "taxon")

        assert stats["Total Count"] == 1000
        assert stats["Columns"] == 3

    def test_get_group_statistics_taxon_detailed(self, mock_database):
        """Test getting detailed statistics for taxon group."""
        mock_database.execute_sql.side_effect = [
            Mock(scalar=Mock(return_value=1000)),  # Count
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Columns
                            (0, "id", "INTEGER"),
                            (1, "full_name", "TEXT"),
                            (2, "rank_name", "TEXT"),
                        ]
                    )
                )
            ),
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Rank distribution
                            Mock(rank="species", count=800),
                            Mock(rank="genus", count=150),
                            Mock(rank="family", count=50),
                        ]
                    )
                )
            ),
        ]

        stats = get_group_statistics(mock_database, "taxon", detailed=True)

        assert "Column Names" in stats
        assert "rank_name" in stats["Column Names"]
        assert "Rank Distribution" in stats
        assert stats["Rank Distribution"]["species"] == 800

    def test_get_group_statistics_shape_detailed(self, mock_database):
        """Test getting detailed statistics for shape group."""
        mock_database.execute_sql.side_effect = [
            Mock(scalar=Mock(return_value=200)),  # Count
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Columns
                            (0, "id", "INTEGER"),
                            (1, "type", "TEXT"),
                            (2, "name", "TEXT"),
                        ]
                    )
                )
            ),
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Type distribution
                            Mock(type="Forest", count=100),
                            Mock(type="River", count=50),
                            Mock(type="Road", count=50),
                        ]
                    )
                )
            ),
        ]

        stats = get_group_statistics(mock_database, "shape", detailed=True)

        assert "Types" in stats
        assert ("Forest", 100) in stats["Types"]

    def test_get_group_statistics_error_handling(self, mock_database):
        """Test error handling in get_group_statistics."""
        mock_database.execute_sql.side_effect = Exception("Table not found")

        stats = get_group_statistics(mock_database, "invalid_group")

        assert "Error" in stats
        assert "Table not found" in stats["Error"]


class TestDisplayFunctions:
    """Test the display functions."""

    def test_display_general_statistics(self, capsys):
        """Test displaying general statistics."""
        stats = {
            "Reference Taxa": 1000,
            "Reference Plots": 500,
            "Occurrences": 5000,
            "Generated Tables": {
                "Taxon": 800,
                "Plot": 400,
            },
            "Shape Types": {
                "Forest": 100,
                "River": 50,
            },
        }

        display_general_statistics(stats, detailed=False)

        captured = capsys.readouterr()
        assert "Niamoto Database Statistics" in captured.out
        assert "1,000" in captured.out  # Formatted number
        assert "Shape Types" in captured.out

    def test_display_general_statistics_detailed(self, capsys):
        """Test displaying detailed general statistics."""
        stats = {
            "Reference Taxa": 1000,
            "Top Families": [
                ("Myrtaceae", 500),
                ("Lauraceae", 300),
            ],
            "Elevation Range": {
                "Min": "0m",
                "Max": "1000m",
                "Average": "500m",
            },
            "Numerical Data": {
                "dbh": {
                    "Count": "3,000",
                    "Range": "5.00 - 150.00",
                    "Average": "45.50",
                }
            },
        }

        display_general_statistics(stats, detailed=True)

        captured = capsys.readouterr()
        assert "Top 10 Families" in captured.out
        assert "Myrtaceae" in captured.out
        assert "Elevation Range" in captured.out
        assert "Numerical Data Summary" in captured.out

    def test_display_group_statistics(self, capsys):
        """Test displaying group statistics."""
        stats = {
            "Total Count": 1000,
            "Columns": 10,
            "Rank Distribution": {
                "species": 800,
                "genus": 150,
                "family": 50,
            },
        }

        display_group_statistics(stats, "taxon", detailed=True)

        captured = capsys.readouterr()
        assert "Taxon Statistics" in captured.out
        assert "1,000" in captured.out
        assert "Rank Distribution" in captured.out
        assert "species" in captured.out

    def test_display_group_statistics_with_error(self, capsys):
        """Test displaying group statistics with error."""
        stats = {
            "Total Count": 0,
            "Error": "Table not found",
        }

        display_group_statistics(stats, "invalid", detailed=False)

        captured = capsys.readouterr()
        assert "Error accessing invalid data" in captured.out

    def test_display_group_statistics_with_types(self, capsys):
        """Test displaying group statistics with types (for shape group)."""
        stats = {
            "Total Count": 200,
            "Columns": 5,
            "Types": [
                ("Forest", 100),
                ("River", 50),
                ("Road", 30),
                ("Building", 20),
            ],
        }

        display_group_statistics(stats, "shape", detailed=True)

        captured = capsys.readouterr()
        assert "Shape Statistics" in captured.out
        assert "Types" in captured.out
        assert "Forest" in captured.out
        assert "100" in captured.out


class TestShowDataExplorationSuggestions:
    """Test the show_data_exploration_suggestions function."""

    def test_show_suggestions_basic(self, mock_database, capsys):
        """Test showing basic data exploration suggestions."""
        mock_database.execute_sql.side_effect = [
            # Table list
            Mock(
                __iter__=Mock(
                    return_value=iter([("taxon_ref",), ("plot_ref",), ("occurrences",)])
                )
            ),
            # Occurrences columns
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            (0, "id", "INTEGER"),
                            (1, "family", "TEXT"),
                            (2, "elevation", "REAL"),
                            (3, "dbh", "REAL"),
                        ]
                    )
                )
            ),
            # Ref table counts
            Mock(scalar=Mock(return_value=1000)),  # taxon_ref
            Mock(scalar=Mock(return_value=500)),  # plot_ref
        ]

        show_data_exploration_suggestions(mock_database)

        captured = capsys.readouterr()
        assert "Data Exploration Suggestions" in captured.out
        assert "Occurrences Data Exploration" in captured.out
        assert "Top families" in captured.out
        assert "Elevation distribution" in captured.out
        assert "Reference Data Exploration" in captured.out

    def test_show_suggestions_with_generated_tables(self, mock_database, capsys):
        """Test showing suggestions with generated tables."""
        mock_database.execute_sql.side_effect = [
            # Table list
            Mock(
                __iter__=Mock(
                    return_value=iter([("taxon_ref",), ("taxon",), ("occurrences",)])
                )
            ),
            # Occurrences columns
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            (0, "id", "INTEGER"),
                        ]
                    )
                )
            ),
            # Ref table count
            Mock(scalar=Mock(return_value=1000)),
            # Generated table count
            Mock(scalar=Mock(return_value=800)),
        ]

        show_data_exploration_suggestions(mock_database)

        captured = capsys.readouterr()
        assert "Generated Analysis Tables" in captured.out
        assert "generated from transforms" in captured.out

    def test_show_suggestions_error_handling(self, mock_database, capsys):
        """Test error handling in suggestions."""
        mock_database.execute_sql.side_effect = Exception("Database error")

        show_data_exploration_suggestions(mock_database)

        captured = capsys.readouterr()
        assert "Error generating suggestions" in captured.out


class TestExportStatistics:
    """Test the export_statistics function."""

    def test_export_statistics_json(self, tmp_path):
        """Test exporting statistics to JSON."""
        stats = {
            "Reference Taxa": 1000,
            "Top Families": [("Myrtaceae", 500), ("Lauraceae", 300)],
            "Shape Types": {"Forest": 100, "River": 50},
        }

        export_file = tmp_path / "stats.json"
        export_statistics(stats, str(export_file))

        assert export_file.exists()

        with open(export_file) as f:
            data = json.load(f)
            assert data["Reference Taxa"] == 1000
            assert (
                data["Top Families"]["Myrtaceae"] == 500
            )  # Converted from list of tuples
            assert data["Shape Types"]["Forest"] == 100

    def test_export_statistics_csv(self, tmp_path):
        """Test exporting statistics to CSV."""
        stats = {
            "Reference Taxa": 1000,
            "Shape Types": {"Forest": 100, "River": 50},
            "Top Families": [("Myrtaceae", 500), ("Lauraceae", 300)],
        }

        export_file = tmp_path / "stats.csv"
        export_statistics(stats, str(export_file))

        assert export_file.exists()

        with open(export_file) as f:
            reader = csv.reader(f)
            rows = list(reader)

            assert rows[0] == ["Category", "Metric", "Value"]
            assert ["General", "Reference Taxa", "1000"] in rows
            assert ["Shape Types", "Forest", "100"] in rows
            assert ["Top Families", "Myrtaceae", "500"] in rows

    def test_export_statistics_unsupported_format(self, tmp_path):
        """Test exporting to unsupported format raises error."""
        stats = {"test": 123}
        export_file = tmp_path / "stats.txt"

        with pytest.raises(ValueError) as exc_info:
            export_statistics(stats, str(export_file))

        assert "Unsupported export format" in str(exc_info.value)


class TestIntegration:
    """Integration tests for the stats command."""

    def test_stats_command_full_flow(
        self, runner, mock_config, mock_database, mock_path, tmp_path
    ):
        """Test full flow with all options."""
        export_file = tmp_path / "full_stats.json"

        # Mock comprehensive database responses
        mock_database.execute_sql.side_effect = [
            # General stats queries
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            ("taxon_ref",),
                            ("plot_ref",),
                            ("shape_ref",),
                            ("occurrences",),
                        ]
                    )
                )
            ),
            Mock(scalar=Mock(return_value=1000)),  # taxon_ref
            Mock(scalar=Mock(return_value=500)),  # plot_ref
            Mock(scalar=Mock(return_value=200)),  # shape_ref
            Mock(scalar=Mock(return_value=5000)),  # occurrences
            # Shape types
            Mock(__iter__=Mock(return_value=iter([(0, "type", "TEXT")]))),
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            Mock(type="Forest", count=100),
                        ]
                    )
                )
            ),
            # Detailed stats
            Mock(__iter__=Mock(return_value=iter([(0, "family", "TEXT")]))),
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [
                            Mock(family="Myrtaceae", count=500),
                        ]
                    )
                )
            ),
            # Suggestions queries
            Mock(__iter__=Mock(return_value=iter([("occurrences",)]))),
            Mock(__iter__=Mock(return_value=iter([(0, "family", "TEXT")]))),
        ]

        result = runner.invoke(
            stats_command, ["--detailed", "--export", str(export_file), "--suggestions"]
        )

        assert result.exit_code == 0
        assert "Niamoto Database Statistics" in result.output
        assert "Statistics exported to" in result.output
        assert "Data Exploration Suggestions" in result.output
        assert export_file.exists()

    def test_stats_command_group_with_export(
        self, runner, mock_config, mock_database, mock_path, tmp_path
    ):
        """Test group statistics with export."""
        export_file = tmp_path / "taxon_stats.csv"

        mock_database.execute_sql.side_effect = [
            Mock(scalar=Mock(return_value=1000)),  # Count
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Columns
                            (0, "id", "INTEGER"),
                            (1, "full_name", "TEXT"),
                        ]
                    )
                )
            ),
            Mock(
                __iter__=Mock(
                    return_value=iter(
                        [  # Rank distribution
                            Mock(rank="species", count=800),
                        ]
                    )
                )
            ),
        ]

        result = runner.invoke(
            stats_command,
            ["--group", "taxon", "--detailed", "--export", str(export_file)],
        )

        assert result.exit_code == 0
        assert export_file.exists()

        # Check CSV content
        with open(export_file) as f:
            content = f.read()
            assert "Total Count" in content
            assert "1000" in content
