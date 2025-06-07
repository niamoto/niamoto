"""
Tests for the base CLI module.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock
from importlib import metadata

from niamoto.cli.commands.base import (
    get_version_from_pyproject,
    RichCLI,
    display_next_steps,
    confirm_action,
)
from niamoto.common.exceptions import VersionError


def test_get_version_from_pyproject_success(tmp_path, monkeypatch):
    """Test successful version retrieval from pyproject.toml"""

    # Mock metadata.version to raise PackageNotFoundError
    def mock_version(name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", mock_version)

    # Create a mock pyproject.toml with a valid version
    mock_content = """
[tool.project]
version = "1.0.0"
    """
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(mock_content)

    # Mock the path resolution to return our mock file
    def mock_get_pyproject_path(*args, **kwargs):
        return pyproject_path

    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(Path, "__truediv__", lambda self, other: pyproject_path)

    version = get_version_from_pyproject()
    assert version == "1.0.0"


def test_get_version_from_pyproject_file_not_found(tmp_path, monkeypatch):
    """Test version retrieval when pyproject.toml doesn't exist"""

    # Mock metadata.version to raise PackageNotFoundError
    def mock_version(name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", mock_version)

    # Mock the path resolution to return a non-existent file
    pyproject_path = tmp_path / "nonexistent.toml"

    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(Path, "__truediv__", lambda self, other: pyproject_path)

    # In test environment, we're not exiting but raising the exception
    with pytest.raises(VersionError):
        get_version_from_pyproject()


def test_get_version_from_pyproject_invalid_content(tmp_path, monkeypatch):
    """Test version retrieval with invalid pyproject.toml content"""

    # Mock metadata.version to raise PackageNotFoundError
    def mock_version(name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", mock_version)

    # Create a mock pyproject.toml with invalid content
    mock_content = """
[tool]
# No version information
    """
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(mock_content)

    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(Path, "__truediv__", lambda self, other: pyproject_path)

    # In test environment, we're not exiting but raising the exception
    with pytest.raises(VersionError):
        get_version_from_pyproject()


class TestRichCLI:
    @pytest.fixture
    def cli(self):
        """Create a RichCLI instance for testing"""
        cli = RichCLI()

        @cli.command()
        def test_command():
            """Test command description"""
            pass

        return cli

    def test_list_commands(self, cli):
        """Test that list_commands returns commands in order of addition"""
        ctx = MagicMock()
        commands = cli.list_commands(ctx)
        assert commands == ["test-command"]  # Click converts underscores to hyphens

    def test_format_help(self, cli):
        """Test help formatting includes required sections"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Check that important sections are present in the output
        output = result.output
        assert "Niamoto CLI, version" in output
        assert "Usage:" in output
        assert "Main Commands" in output
        assert "Get Started:" in output


def test_display_next_steps(capsys):
    """Test that display_next_steps outputs expected sections"""
    display_next_steps()
    captured = capsys.readouterr()

    # Verify key sections are present
    assert "Get Started:" in captured.out
    assert "Initialize or check your environment" in captured.out
    assert "Import data" in captured.out
    assert "Transform data" in captured.out
    assert "Export content" in captured.out
    assert "Deploy content" in captured.out


def test_display_next_steps_includes_stats_commands(capsys):
    """Test that display_next_steps includes the stats command and its options"""
    display_next_steps()
    captured = capsys.readouterr()

    # Remove line breaks and extra spaces for more reliable matching
    output = captured.out.replace("\n", " ").replace("  ", " ")

    # Verify the stats exploration section is present
    assert "Have fun exploring your data and generating insights!" in captured.out

    # Verify specific stats commands are present (checking for key parts)
    assert "niamoto stats" in output
    assert "--detailed" in output
    assert "--group taxon" in output
    assert "--suggestions" in output
    assert "--export stats.json" in output
    assert "Display general statistics about your data" in output
    assert "Get exploration suggestions based on your data" in output


@patch("click.confirm")
def test_confirm_action_yes(mock_confirm):
    """Test confirm_action when user confirms"""
    mock_confirm.return_value = True
    assert confirm_action("Proceed?") is True
    mock_confirm.assert_called_once_with("Proceed?", default=False)


@patch("click.confirm")
def test_confirm_action_no(mock_confirm):
    """Test confirm_action when user declines"""
    mock_confirm.return_value = False
    assert confirm_action("Proceed?") is False
    mock_confirm.assert_called_once_with("Proceed?", default=False)


@patch("click.confirm")
def test_confirm_action_default(mock_confirm):
    """Test confirm_action with default values"""
    # Test with default=True
    mock_confirm.return_value = True
    assert confirm_action("Proceed?", default=True) is True
    mock_confirm.assert_called_with("Proceed?", default=True)

    # Test with default=False
    mock_confirm.return_value = False
    assert confirm_action("Proceed?", default=False) is False
    mock_confirm.assert_called_with("Proceed?", default=False)
