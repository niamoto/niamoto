"""Tests for the transform commands in the Niamoto CLI."""

from unittest import mock
import pytest
from click.testing import CliRunner

from niamoto.cli.commands.transform import transform_commands
from niamoto.common.exceptions import (
    ConfigurationError,
    ProcessError,
)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


def test_invalid_group(runner):
    """Test validation of invalid group parameter."""
    result = runner.invoke(transform_commands, ["--group", "invalid_group"])

    assert result.exit_code == 1
    assert "Invalid group specified" in result.output


def test_invalid_csv_file(runner):
    """Test validation of invalid CSV file."""
    result = runner.invoke(transform_commands, ["--csv-file", "data.txt"])

    assert result.exit_code == 1
    assert "Invalid file format" in result.output


def test_successful_group_transform(runner):
    """Test successful transformation for a specific group."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.calculate_statistics.return_value = None

            result = runner.invoke(transform_commands, ["--group", "taxon"])

            assert result.exit_code == 0
            assert "Transforming data for group: taxon" in result.output
            mock_service_instance.calculate_statistics.assert_called_once_with(
                group_by="taxon", csv_file=None
            )


def test_successful_all_transform(runner):
    """Test successful transformation for all groups."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.calculate_statistics.return_value = None

            result = runner.invoke(transform_commands)

            assert result.exit_code == 0
            assert "Starting full data transformation" in result.output
            assert "All transformations completed successfully" in result.output
            # Verify that calculate_statistics was called for each group
            calls = mock_service_instance.calculate_statistics.call_args_list
            assert len(calls) == 3
            assert calls[0][1]["group_by"] == "taxon"
            assert calls[1][1]["group_by"] == "plot"
            assert calls[2][1]["group_by"] == "shape"


def test_config_error(runner):
    """Test error handling for configuration errors."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.side_effect = ConfigurationError(
            config_key="transform",
            message="Configuration file not found",
            details={"path": "transform.yml"},
        )

        result = runner.invoke(transform_commands, ["--group", "taxon"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output


def test_process_error(runner):
    """Test error handling for processing errors."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.calculate_statistics.side_effect = ProcessError(
                message="Data transforms failed", details={"group": "taxon"}
            )

            result = runner.invoke(transform_commands, ["--group", "taxon"])

            assert result.exit_code == 1
            assert "Data transforms failed" in result.output


def test_transform_with_csv(runner):
    """Test transformation with CSV file input."""
    with runner.isolated_filesystem():
        # Create a test CSV file
        with open("data.csv", "w") as f:
            f.write("species,count\n")
            f.write("test_species,10\n")

        with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
            mock_config.return_value.database_path = "test.db"

            with mock.patch(
                "niamoto.cli.commands.transform.TransformerService"
            ) as mock_service:
                mock_service_instance = mock_service.return_value
                mock_service_instance.calculate_statistics.return_value = None

                result = runner.invoke(
                    transform_commands, ["--group", "taxon", "--csv-file", "data.csv"]
                )

                assert result.exit_code == 0
                assert "Transforming data for group: taxon" in result.output
                mock_service_instance.calculate_statistics.assert_called_once_with(
                    group_by="taxon", csv_file="data.csv"
                )
