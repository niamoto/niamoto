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
from niamoto.core.imports.registry import EntityKind
from types import SimpleNamespace


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def test_registry(request):
    """Create a test registry with automatic cleanup.

    Usage in tests:
        def test_something(test_registry):
            registry = test_registry()  # or test_registry(mapping={...})
            # Use registry...
            # Cleanup happens automatically
    """
    dbs_to_close = []

    def _make_registry(mapping=None, include_defaults=True):
        registry, db = make_registry(mapping, include_defaults)
        dbs_to_close.append(db)
        return registry

    yield _make_registry

    # Cleanup all databases created during the test
    for db in dbs_to_close:
        db.engine.dispose()


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
        mock_db.engine = Mock()
        mock_db.has_table = Mock(return_value=True)
        mock_db.get_table_columns = Mock(return_value=["id"])
        mock_db_class.return_value = mock_db

        mock_result = Mock()
        mock_result.scalar.return_value = 100
        mock_db.execute_sql.return_value = mock_result

        yield mock_db


@pytest.fixture
def command_registry():
    """Create a real EntityRegistry with in-memory database for testing."""
    from niamoto.common.database import Database
    from niamoto.core.imports.registry import EntityRegistry

    # Create in-memory database
    db = Database(":memory:")
    registry = EntityRegistry(db)

    # Populate with default test data
    for entry in DEFAULT_REGISTRY_ENTRIES:
        registry.register_entity(
            name=entry["name"],
            kind=entry["kind"],
            table_name=entry["table_name"],
            config={},
        )

    # Patch EntityRegistry constructor to return our instance
    with patch("niamoto.cli.commands.stats.EntityRegistry", return_value=registry):
        yield registry

    # Cleanup: Close database connection to prevent ResourceWarning
    db.engine.dispose()


@pytest.fixture
def mock_inspector():
    """Patch SQLAlchemy inspector used by the stats module."""
    with patch("niamoto.cli.commands.stats.inspect") as inspect_mock:
        inspector = MagicMock()
        inspector.get_table_names.return_value = []
        inspect_mock.return_value = inspector
        yield inspector


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


DEFAULT_REGISTRY_ENTRIES = [
    {
        "name": "taxon_ref",
        "table_name": "taxon_ref",
        "kind": EntityKind.REFERENCE,
    },
    {
        "name": "plot_ref",
        "table_name": "plot_ref",
        "kind": EntityKind.REFERENCE,
    },
    {
        "name": "shape_ref",
        "table_name": "shape_ref",
        "kind": EntityKind.REFERENCE,
    },
    {
        "name": "occurrences",
        "table_name": "occurrences",
        "kind": EntityKind.DATASET,
    },
]


def make_registry(mapping=None, include_defaults: bool = True):
    """Create a real EntityRegistry with in-memory database for testing.

    FIXED: Replaced FakeRegistry (~40 lines) with real EntityRegistry.
    This ensures tests match production behavior and reduces maintenance burden.

    WARNING: Caller is responsible for closing the database connection.
    Access via registry.db.close() to prevent ResourceWarning.

    Returns:
        tuple: (registry, db) - Both registry and database for proper cleanup
    """
    from niamoto.common.database import Database
    from niamoto.core.imports.registry import EntityRegistry

    # Create in-memory database
    db = Database(":memory:")
    registry = EntityRegistry(db)

    # Add default entries
    entries = []
    if include_defaults:
        entries.extend(DEFAULT_REGISTRY_ENTRIES)

    # Add custom mapping
    mapping = mapping or {}
    for name, table_name in mapping.items():
        kind = EntityKind.DATASET
        if name.endswith("_ref"):
            kind = EntityKind.REFERENCE
        entries.append({"name": name, "table_name": table_name, "kind": kind})

    # Populate registry
    for entry in entries:
        registry.register_entity(
            name=entry["name"],
            kind=entry["kind"],
            table_name=entry["table_name"],
            config={},
        )

    return registry, db


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
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        command_registry,
        mock_inspector,
    ):
        """Test stats command showing general statistics."""
        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "plot_ref",
            "shape_ref",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "plot_ref" in sql:
                return Mock(scalar=Mock(return_value=500))
            if "shape_ref" in sql:
                return Mock(scalar=Mock(return_value=200))
            if "occurrences" in sql:
                return Mock(scalar=Mock(return_value=5000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = lambda table: ["id"]

        result = runner.invoke(stats_command)

        assert result.exit_code == 0
        assert "Niamoto Database Statistics" in result.output

    def test_stats_command_with_group(
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        command_registry,
        mock_inspector,
    ):
        """Test stats command with specific group."""
        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                return Mock(scalar=Mock(return_value=1000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = (
            lambda table: ["id", "full_name", "rank_name"]
            if table == "taxon_ref"
            else ["id"]
        )

        result = runner.invoke(stats_command, ["--group", "taxon"])

        assert result.exit_code == 0
        assert "Taxon Statistics" in result.output

    def test_stats_command_with_detailed(
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        command_registry,
        mock_inspector,
    ):
        """Test stats command with detailed flag."""
        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "plot_ref",
            "shape_ref",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "FROM taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "FROM plot_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=500))
            if "FROM shape_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=200))
            if "FROM occurrences" in sql and "GROUP" not in sql and "AVG" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            if "FROM shape_ref" in sql and "GROUP BY type" in sql:
                return [
                    SimpleNamespace(type="Forest", count=100),
                    SimpleNamespace(type="River", count=50),
                ]
            if "FROM occurrences" in sql and "GROUP BY family" in sql:
                return [
                    SimpleNamespace(family="Myrtaceae", count=500),
                    SimpleNamespace(family="Lauraceae", count=300),
                ]
            if "AVG(elevation)" in sql:
                row = SimpleNamespace(
                    min_elev=0,
                    max_elev=1000,
                    avg_elev=500,
                    count_with_elev=4000,
                )
                return Mock(first=Mock(return_value=row))
            if "AVG(dbh)" in sql and "COUNT(dbh)" in sql:
                row = SimpleNamespace(
                    count_non_null=3000,
                    min_val=5.0,
                    max_val=150.0,
                    avg_val=45.5,
                )
                return Mock(first=Mock(return_value=row))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect

        def get_columns(table: str):
            if table == "shape_ref":
                return ["id", "type"]
            if table == "occurrences":
                return ["id", "family", "elevation", "dbh"]
            return ["id"]

        mock_database.get_table_columns.side_effect = get_columns

        result = runner.invoke(stats_command, ["--detailed"])

        assert result.exit_code == 0
        assert "Niamoto Database Statistics" in result.output

    def test_stats_command_with_export_json(
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        tmp_path,
        command_registry,
        mock_inspector,
    ):
        """Test stats command with JSON export."""
        export_file = tmp_path / "stats.json"

        # Mock database responses
        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                return Mock(scalar=Mock(return_value=1000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect

        result = runner.invoke(stats_command, ["--export", str(export_file)])

        assert result.exit_code == 0
        assert export_file.exists()
        assert "Statistics exported to" in result.output

        # Check JSON content
        with open(export_file) as f:
            data = json.load(f)
            assert "Reference Taxon" in data
            assert data["Reference Taxon"] == 1000

    def test_stats_command_with_export_csv(
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        tmp_path,
        command_registry,
        mock_inspector,
    ):
        """Test stats command with CSV export."""
        export_file = tmp_path / "stats.csv"

        # Mock database responses
        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                return Mock(scalar=Mock(return_value=1000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect

        result = runner.invoke(stats_command, ["--export", str(export_file)])

        assert result.exit_code == 0
        assert export_file.exists()

        # Check CSV content
        with open(export_file) as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert rows[0] == ["Category", "Metric", "Value"]
            assert ["General", "Reference Taxon", "1000"] in rows

    def test_stats_command_with_suggestions(
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        command_registry,
        mock_inspector,
    ):
        """Test stats command with suggestions flag."""
        mock_inspector.get_table_names.return_value = ["taxon_ref", "occurrences"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "FROM taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "FROM occurrences" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = (
            lambda table: ["id", "family", "elevation", "dbh"]
            if table == "occurrences"
            else ["id"]
        )

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

    def test_get_general_statistics_basic(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test getting basic general statistics."""
        # Mock responses
        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "plot_ref",
            "shape_ref",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "plot_ref" in sql:
                return Mock(scalar=Mock(return_value=500))
            if "shape_ref" in sql:
                return Mock(scalar=Mock(return_value=200))
            if "occurrences" in sql:
                return Mock(scalar=Mock(return_value=5000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        registry = test_registry()

        stats = get_general_statistics(mock_database, registry)

        assert stats["Reference Taxon"] == 1000
        assert stats["Reference Plot"] == 500
        assert stats["Reference Shape"] == 200
        assert stats["Dataset Occurrences"] == 5000

    def test_get_general_statistics_with_generated_tables(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test getting statistics including generated tables."""
        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "taxon",
            "plot",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "occurrences" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            if "FROM taxon" in sql:
                return Mock(scalar=Mock(return_value=800))
            if "FROM plot" in sql:
                return Mock(scalar=Mock(return_value=400))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        registry = test_registry()

        stats = get_general_statistics(mock_database, registry)

        assert "Generated Tables" in stats
        assert stats["Generated Tables"]["taxon"] == 800
        assert stats["Generated Tables"]["plot"] == 400

    def test_get_general_statistics_detailed(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test getting detailed general statistics."""
        mock_inspector.get_table_names.return_value = ["occurrences"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "occurrences" in sql and "GROUP" not in sql and "AVG" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            if "GROUP BY family" in sql:
                return [
                    SimpleNamespace(family="Myrtaceae", count=500),
                    SimpleNamespace(family="Lauraceae", count=300),
                ]
            if "AVG(elevation)" in sql:
                row = SimpleNamespace(
                    min_elev=0,
                    max_elev=1000,
                    avg_elev=500,
                    count_with_elev=4000,
                )
                return Mock(first=Mock(return_value=row))
            if "AVG(dbh)" in sql:
                row = SimpleNamespace(
                    count_non_null=3000,
                    min_val=5.0,
                    max_val=150.0,
                    avg_val=45.5,
                )
                return Mock(first=Mock(return_value=row))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect

        def get_columns(table: str):
            if table == "occurrences":
                return ["id", "family", "elevation", "dbh"]
            return ["id"]

        mock_database.get_table_columns.side_effect = get_columns
        registry = test_registry({"occurrences": "occurrences"})

        stats = get_general_statistics(mock_database, registry, detailed=True)

        assert "Top Families" in stats
        assert stats["Top Families"][0] == ("Myrtaceae", 500)
        assert "Elevation Range" in stats
        assert stats["Elevation Range"]["Min"] == "0m"
        assert stats["Elevation Range"]["Max"] == "1000m"
        assert "Numerical Data" in stats
        assert "dbh" in stats["Numerical Data"]

    def test_get_general_statistics_handles_errors(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test that get_general_statistics handles database errors gracefully."""
        # First query succeeds, subsequent queries fail
        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                raise Exception("Query failed")
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        registry = test_registry()

        stats = get_general_statistics(mock_database, registry)

        # Should have empty stats but not crash
        assert stats["Reference Taxon"] == 0

    def test_get_general_statistics_table_list_fails(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test when the initial table list query fails."""
        # Table list query fails
        mock_inspector.get_table_names.side_effect = Exception("Cannot inspect")
        registry = test_registry()

        stats = get_general_statistics(mock_database, registry)

        # Should return empty stats
        assert stats == {}


class TestGetGroupStatistics:
    """Test the get_group_statistics function."""

    def test_get_group_statistics_taxon(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test getting statistics for taxon group."""
        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql:
                return Mock(scalar=Mock(return_value=1000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = (
            lambda table: ["id", "full_name", "rank_name"]
            if table == "taxon_ref"
            else ["id"]
        )
        registry = test_registry()

        stats = get_group_statistics(mock_database, registry, "taxon")

        assert stats["Total Count"] == 1000
        assert stats["Columns"] == 3

    def test_get_group_statistics_taxon_detailed(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test getting detailed statistics for taxon group."""
        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "GROUP BY rank_name" in sql:
                # SQL uses "as value" alias, so mocks must return .value attribute
                return [
                    SimpleNamespace(value="species", count=800),
                    SimpleNamespace(value="genus", count=150),
                    SimpleNamespace(value="family", count=50),
                ]
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = (
            lambda table: ["id", "full_name", "rank_name"]
            if table == "taxon_ref"
            else ["id"]
        )
        registry = test_registry()

        stats = get_group_statistics(mock_database, registry, "taxon", detailed=True)

        assert "Column Names" in stats
        assert "rank_name" in stats["Column Names"]
        assert "Rank Distribution" in stats
        assert stats["Rank Distribution"]["species"] == 800

    def test_get_group_statistics_shape_detailed(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test getting detailed statistics for shape group."""
        mock_inspector.get_table_names.return_value = ["shape_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "shape_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=200))
            if "GROUP BY type" in sql:
                # SQL uses "as value" alias, so mocks must return .value attribute
                return [
                    SimpleNamespace(value="Forest", count=100),
                    SimpleNamespace(value="River", count=50),
                    SimpleNamespace(value="Road", count=50),
                ]
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = (
            lambda table: ["id", "type", "name"] if table == "shape_ref" else ["id"]
        )
        registry = test_registry()

        stats = get_group_statistics(mock_database, registry, "shape", detailed=True)

        assert "Types" in stats
        assert stats["Types"]["Forest"] == 100

    def test_get_group_statistics_error_handling(
        self, mock_database, mock_inspector, test_registry
    ):
        """Test error handling in get_group_statistics."""
        mock_inspector.get_table_names.return_value = []
        registry = test_registry()

        stats = get_group_statistics(mock_database, registry, "invalid_group")

        assert "Error" in stats
        assert "not found" in stats["Error"]


class TestDisplayFunctions:
    """Test the display functions."""

    def test_display_general_statistics(self, capsys):
        """Test displaying general statistics."""
        stats = {
            "Reference Taxon": 1000,
            "Reference Plot": 500,
            "Dataset Occurrences": 5000,
            "Generated Tables": {
                "taxon": 800,
                "plot": 400,
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
            "Reference Taxon": 1000,
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
            "Types": {
                "Forest": 100,
                "River": 50,
                "Road": 30,
                "Building": 20,
            },
        }

        display_group_statistics(stats, "shape", detailed=True)

        captured = capsys.readouterr()
        assert "Shape Statistics" in captured.out
        assert "Types" in captured.out
        assert "Forest" in captured.out
        assert "100" in captured.out


class TestShowDataExplorationSuggestions:
    """Test the show_data_exploration_suggestions function."""

    def test_show_suggestions_basic(
        self, mock_database, mock_inspector, capsys, test_registry
    ):
        """Test showing basic data exploration suggestions."""
        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "plot_ref",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "FROM taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "FROM plot_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=500))
            if "FROM occurrences" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect

        def get_columns(table: str):
            if table == "occurrences":
                return ["id", "family", "elevation", "dbh"]
            return ["id"]

        mock_database.get_table_columns.side_effect = get_columns

        registry = test_registry()

        show_data_exploration_suggestions(mock_database, registry)

        captured = capsys.readouterr()
        assert "Data Exploration Suggestions" in captured.out
        assert "Occurrences Data Exploration" in captured.out
        assert "Top families" in captured.out
        assert "Elevation distribution" in captured.out
        assert "Reference Data Exploration" in captured.out

    def test_show_suggestions_with_generated_tables(
        self, mock_database, mock_inspector, capsys, test_registry
    ):
        """Test showing suggestions with generated tables."""
        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "taxon",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "FROM taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "FROM taxon" in sql:
                return Mock(scalar=Mock(return_value=800))
            if "FROM occurrences" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = lambda table: ["id"]
        registry = test_registry()

        show_data_exploration_suggestions(mock_database, registry)

        captured = capsys.readouterr()
        assert "Generated Analysis Tables" in captured.out
        assert "generated from transforms" in captured.out

    def test_show_suggestions_error_handling(
        self, mock_database, mock_inspector, capsys, test_registry
    ):
        """Test error handling in suggestions."""
        mock_inspector.get_table_names.side_effect = Exception("Database error")
        registry = test_registry()

        show_data_exploration_suggestions(mock_database, registry)

        captured = capsys.readouterr()
        assert "Data Exploration Suggestions" in captured.out


class TestExportStatistics:
    """Test the export_statistics function."""

    def test_export_statistics_json(self, tmp_path):
        """Test exporting statistics to JSON."""
        stats = {
            "Reference Taxon": 1000,
            "Top Families": [("Myrtaceae", 500), ("Lauraceae", 300)],
            "Shape Types": {"Forest": 100, "River": 50},
        }

        export_file = tmp_path / "stats.json"
        export_statistics(stats, str(export_file))

        assert export_file.exists()

        with open(export_file) as f:
            data = json.load(f)
            assert data["Reference Taxon"] == 1000
            assert (
                data["Top Families"]["Myrtaceae"] == 500
            )  # Converted from list of tuples
            assert data["Shape Types"]["Forest"] == 100

    def test_export_statistics_csv(self, tmp_path):
        """Test exporting statistics to CSV."""
        stats = {
            "Reference Taxon": 1000,
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
            assert ["General", "Reference Taxon", "1000"] in rows
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
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        tmp_path,
        command_registry,
        mock_inspector,
    ):
        """Test full flow with all options."""
        export_file = tmp_path / "full_stats.json"

        mock_inspector.get_table_names.return_value = [
            "taxon_ref",
            "plot_ref",
            "shape_ref",
            "occurrences",
        ]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "FROM taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "FROM plot_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=500))
            if "FROM shape_ref" in sql and "GROUP" not in sql and "GROUP BY" not in sql:
                return Mock(scalar=Mock(return_value=200))
            if "FROM occurrences" in sql and "GROUP" not in sql and "AVG" not in sql:
                return Mock(scalar=Mock(return_value=5000))
            if "FROM shape_ref" in sql and "GROUP BY type" in sql:
                return [SimpleNamespace(type="Forest", count=100)]
            if "FROM occurrences" in sql and "GROUP BY family" in sql:
                return [SimpleNamespace(family="Myrtaceae", count=500)]
            if "AVG(elevation)" in sql:
                row = SimpleNamespace(
                    min_elev=0,
                    max_elev=1000,
                    avg_elev=500,
                    count_with_elev=4000,
                )
                return Mock(first=Mock(return_value=row))
            if "AVG(dbh)" in sql:
                row = SimpleNamespace(
                    count_non_null=3000,
                    min_val=5.0,
                    max_val=150.0,
                    avg_val=45.5,
                )
                return Mock(first=Mock(return_value=row))
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect

        def get_columns(table: str):
            if table == "shape_ref":
                return ["id", "type"]
            if table == "occurrences":
                return ["id", "family", "elevation", "dbh"]
            return ["id"]

        mock_database.get_table_columns.side_effect = get_columns

        result = runner.invoke(
            stats_command, ["--detailed", "--export", str(export_file), "--suggestions"]
        )

        assert result.exit_code == 0
        assert "Niamoto Database Statistics" in result.output
        assert "Statistics exported to" in result.output
        assert "Data Exploration Suggestions" in result.output
        assert export_file.exists()

    def test_stats_command_group_with_export(
        self,
        runner,
        mock_config,
        mock_database,
        mock_path,
        tmp_path,
        command_registry,
        mock_inspector,
    ):
        """Test group statistics with export."""
        export_file = tmp_path / "taxon_stats.csv"

        mock_inspector.get_table_names.return_value = ["taxon_ref"]

        def execute_sql_side_effect(sql: str, *args, **kwargs):
            if "taxon_ref" in sql and "GROUP" not in sql:
                return Mock(scalar=Mock(return_value=1000))
            if "GROUP BY rank_name" in sql:
                return [SimpleNamespace(rank="species", count=800)]
            return Mock(scalar=Mock(return_value=0))

        mock_database.execute_sql.side_effect = execute_sql_side_effect
        mock_database.get_table_columns.side_effect = (
            lambda table: ["id", "full_name", "rank_name"]
            if table == "taxon_ref"
            else ["id"]
        )

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
