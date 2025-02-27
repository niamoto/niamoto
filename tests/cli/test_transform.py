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


def test_invalid_csv_file(runner):
    """Test validation of invalid CSV file."""
    result = runner.invoke(transform_commands, ["--data", "data.txt"])

    assert result.exit_code == 2


def test_successful_group_transform(runner):
    """Test successful transformation for a specific group."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.transform_data.return_value = None

            result = runner.invoke(transform_commands, ["--group", "taxon"])

            assert result.exit_code == 0
            assert "Processing transformations for group: taxon" in result.output
            mock_service_instance.transform_data.assert_called_once_with(
                group_by="taxon", csv_file=None, recreate_table=True
            )


def test_successful_all_transform(runner):
    """Test successful transformation for all groups."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.transform_data.return_value = None

            result = runner.invoke(transform_commands)

            assert result.exit_code == 0
            assert "Processing all transformation groups" in result.output
            mock_service_instance.transform_data.assert_called_once_with(
                group_by=None, csv_file=None, recreate_table=True
            )


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
            mock_service_instance.transform_data.side_effect = ProcessError(
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
                mock_service_instance.transform_data.return_value = None

                result = runner.invoke(
                    transform_commands, ["--group", "taxon", "--data", "data.csv"]
                )

                assert result.exit_code == 0
                assert "Processing transformations for group: taxon" in result.output
                mock_service_instance.transform_data.assert_called_once_with(
                    group_by="taxon", csv_file="data.csv", recreate_table=True
                )
