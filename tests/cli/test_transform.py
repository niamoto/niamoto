"""Tests for the transform commands in the Niamoto CLI."""

from unittest import mock
import pytest
from click.testing import CliRunner

from niamoto.cli.commands.transform import transform_commands
from niamoto.common.exceptions import (
    ConfigurationError,
    ProcessError,
    ValidationError,
)


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create a mocked Config instance."""
    with mock.patch("niamoto.cli.commands.transform.Config") as config_mock:
        config_mock.return_value.database_path = "test.db"
        config_mock.return_value.get_transforms_config.return_value = [
            {
                "group_by": "taxon",
                "source": {
                    "data": "occurrences",
                    "grouping": "taxon_id",
                    "relation": {"type": "direct"},
                },
                "widgets_data": {"widget1": {}, "widget2": {}},
            },
            {
                "group_by": "plot",
                "source": {
                    "data": "plots",
                    "grouping": "plot_id",
                    "relation": {"type": "direct"},
                },
                "widgets_data": {"widget1": {}},
            },
        ]
        yield config_mock


def test_invalid_group(runner):
    """Test validation of invalid group parameter."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.get_transforms_config.side_effect = ConfigurationError(
            config_key="transforms",
            message="No configuration found for group: invalid_group",
            details={"available_groups": ["some_group"]},
        )

        result = runner.invoke(transform_commands, ["--group", "invalid_group"])

        assert "No configuration found for group" in result.output


def test_invalid_csv_file(runner):
    """Test validation of invalid CSV file."""
    result = runner.invoke(transform_commands, ["--data", "data.txt"])

    if result.exception:
        print(f"Exception: {result.exception}")

    assert result.exit_code == 2  # Click returns 2 for parameter validation errors
    assert "Invalid value for '--data'" in result.output
    assert "does not exist" in result.output


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


def test_list_command(runner, mock_config):
    """Test the list command for transform configurations."""
    result = runner.invoke(transform_commands, ["list"])

    assert result.exit_code == 0
    assert "Available transformation configurations" in result.output
    assert "taxon" in result.output
    assert "plot" in result.output
    assert "occurrences" in result.output
    assert "plots" in result.output


def test_list_command_no_configs(runner):
    """Test the list command when no configurations are found."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.get_transforms_config.return_value = []

        result = runner.invoke(transform_commands, ["list"])

        assert result.exit_code == 0
        assert "No transformation configurations found" in result.output


def test_check_command_valid(runner, mock_config):
    """Test the check command with valid configurations."""
    with mock.patch(
        "niamoto.cli.commands.transform.TransformerService"
    ) as mock_service:
        mock_service_instance = mock_service.return_value
        mock_service_instance.validate_configuration.return_value = None

        result = runner.invoke(transform_commands, ["check"])

        assert result.exit_code == 0
        assert "Configuration for taxon is valid" in result.output
        assert "Configuration for plot is valid" in result.output
        assert mock_service_instance.validate_configuration.call_count == 2


def test_check_command_invalid(runner, mock_config):
    """Test the check command with invalid configurations."""
    with mock.patch(
        "niamoto.cli.commands.transform.TransformerService"
    ) as mock_service:
        mock_service_instance = mock_service.return_value
        mock_service_instance.validate_configuration.side_effect = [
            None,  # First call succeeds
            ValidationError(
                field="source", message="Invalid source configuration"
            ),  # Second call fails
        ]

        result = runner.invoke(transform_commands, ["check"])

        assert result.exit_code == 0
        assert "Configuration for taxon is valid" in result.output
        assert "Configuration error in plot" in result.output
        assert "Invalid source configuration" in result.output


def test_check_command_specific_group(runner, mock_config):
    """Test the check command with a specific group."""
    with mock.patch(
        "niamoto.cli.commands.transform.TransformerService"
    ) as mock_service:
        mock_service_instance = mock_service.return_value
        mock_service_instance.validate_configuration.return_value = None

        result = runner.invoke(transform_commands, ["check", "--group", "taxon"])

        assert result.exit_code == 0
        assert "Configuration for taxon is valid" in result.output
        assert "plot" not in result.output
        assert mock_service_instance.validate_configuration.call_count == 1


def test_check_command_group_not_found(runner, mock_config):
    """Test the check command with a group that doesn't exist."""
    result = runner.invoke(transform_commands, ["check", "--group", "nonexistent"])

    assert result.exit_code == 0
    assert "No configuration found for group: nonexistent" in result.output


def test_transform_with_verbose(runner):
    """Test transformation with verbose flag."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.transform_data.return_value = None

            result = runner.invoke(transform_commands, ["--verbose"])

            assert result.exit_code == 0
            assert "Initializing transformer service" in result.output
            mock_service_instance.transform_data.assert_called_once_with(
                group_by=None, csv_file=None, recreate_table=True
            )


def test_transform_with_unsupported_file_format(runner):
    """Test transformation with unsupported file format."""
    with runner.isolated_filesystem():
        # Create a test file with unsupported extension
        with open("data.txt", "w") as f:
            f.write("test data")

        result = runner.invoke(transform_commands, ["--data", "data.txt"])

        assert result.exit_code == 1
        # Just check that the error message indicates unsupported format
        # without verifying the exact message content
        assert "Unsupported file format" in result.output


def test_transform_with_nonexistent_file(runner):
    """Test transformation with a file that doesn't exist."""
    result = runner.invoke(transform_commands, ["--data", "nonexistent.csv"])

    assert result.exit_code == 2  # Click validation error
    assert "does not exist" in result.output


def test_run_command_explicit(runner):
    """Test using the explicit 'run' command."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.transform_data.return_value = None

            result = runner.invoke(transform_commands, ["run", "--group", "taxon"])

            assert result.exit_code == 0
            assert "Processing transformations for group: taxon" in result.output
            mock_service_instance.transform_data.assert_called_once_with(
                group_by="taxon", csv_file=None, recreate_table=True
            )


def test_transform_service_success_message(runner):
    """Test that success message is displayed when transformation completes."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.database_path = "test.db"

        with mock.patch(
            "niamoto.cli.commands.transform.TransformerService"
        ) as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.transform_data.return_value = None

            result = runner.invoke(transform_commands)

            assert result.exit_code == 0
            assert "Data transformation completed successfully" in result.output


def test_list_with_config_error(runner):
    """Test list command handling of configuration errors."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.get_transforms_config.side_effect = ConfigurationError(
            config_key="transforms",
            message="Error in configuration",
            details={"file": "transform.yml"},
        )

        result = runner.invoke(transform_commands, ["list"])

        assert result.exit_code == 0
        assert "Error reading configuration" in result.output
        assert "Error in configuration" in result.output


def test_check_with_config_error(runner):
    """Test check command handling of configuration errors."""
    with mock.patch("niamoto.cli.commands.transform.Config") as mock_config:
        mock_config.return_value.get_transforms_config.side_effect = ConfigurationError(
            config_key="transforms",
            message="Error in configuration",
            details={"file": "transform.yml"},
        )

        result = runner.invoke(transform_commands, ["check"])

        assert result.exit_code == 0
        assert "Error reading configuration" in result.output
        assert "Error in configuration" in result.output
