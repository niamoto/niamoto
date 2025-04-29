"""Tests for the deploy commands in the Niamoto CLI."""

import os
from unittest import mock
import subprocess
import pytest
from click.testing import CliRunner

from niamoto.cli.commands.deploy import deploy_to_github, deploy_to_netlify


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_config(runner):
    """Create a mock configuration with a valid output directory."""
    with mock.patch("niamoto.cli.commands.deploy.Config") as mock_cfg:
        # Create a temporary directory for testing
        with runner.isolated_filesystem():
            os.makedirs("output/web")
            mock_cfg.return_value.get_export_config = {
                "web": os.path.abspath("output/web")
            }
            try:
                yield mock_cfg
            finally:
                # Clean up any remaining files/directories
                if os.path.exists("output"):
                    import shutil

                    shutil.rmtree("output", ignore_errors=True)


def test_successful_github_deploy(runner, mock_config):
    """Test successful deployment to GitHub Pages."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        # Mock the branch check to return non-zero (branch doesn't exist)
        def run_command(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "git" and cmd[1] == "rev-parse":
                return mock.Mock(returncode=1)  # Branch doesn't exist
            return mock.Mock(returncode=0)

        mock_run.side_effect = run_command

        result = runner.invoke(
            deploy_to_github, ["--repo", "https://github.com/user/repo.git"]
        )

        assert result.exit_code == 0
        assert "Deployed to GitHub Pages" in result.output

        # Convert each command to a string for more reliable comparison
        called_commands = [" ".join(call[0][0]) for call in mock_run.call_args_list]

        # Verify specific commands
        assert "git init" in called_commands
        assert "git config user.name Niamoto Bot" in called_commands
        assert "git config user.email bot@niamoto.org" in called_commands
        assert (
            "git remote add origin https://github.com/user/repo.git" in called_commands
        )

        # Check for either checkout -b or checkout --orphan (either might be used)
        checkout_commands = [cmd for cmd in called_commands if "git checkout" in cmd]
        checkout_branch_found = any("gh-pages" in cmd for cmd in checkout_commands)
        assert checkout_branch_found, (
            f"No checkout command with gh-pages found in: {checkout_commands}"
        )

        assert "git add ." in called_commands
        assert any("git commit" in cmd for cmd in called_commands)
        assert "git push -f origin gh-pages" in called_commands


def test_successful_netlify_deploy(runner, mock_config):
    """Test successful deployment to Netlify."""
    with mock.patch("subprocess.run") as mock_run:
        # Mock version check
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "netlify-cli 1.0.0\n"

        # Mock site check
        def run_command(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "netlify":
                if cmd[1] == "--version":
                    return mock.Mock(returncode=0, stdout="netlify-cli 1.0.0\n")
                elif cmd[1] == "sites:list":
                    return mock.Mock(returncode=0, stdout="my-site-id")
                elif cmd[1] == "deploy":
                    return mock.Mock(
                        returncode=0,
                        stdout="Website URL: https://my-site.netlify.app\n",
                    )
            return mock.Mock(returncode=0, stdout="")

        mock_run.side_effect = run_command

        result = runner.invoke(deploy_to_netlify, ["--site-id", "my-site-id"])

        assert result.exit_code == 0
        assert "Successfully deployed to Netlify" in result.output
        assert "Deployment URL:" in result.output


def test_missing_output_dir(runner):
    """Test error when output directory is missing."""
    with mock.patch("niamoto.cli.commands.deploy.Config") as mock_config:
        # Mock get_export_config as a property
        mock_config.return_value.get_export_config = {"web": "nonexistent"}

        with runner.isolated_filesystem():
            result = runner.invoke(
                deploy_to_github, ["--repo", "https://github.com/user/repo.git"]
            )

            assert result.exit_code == 1
            assert "Output directory not found" in result.output


def test_git_command_error(runner, mock_config):
    """Test error handling when git command fails."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["git", "push"], output="", stderr="fatal: remote error"
        )

        result = runner.invoke(
            deploy_to_github, ["--repo", "https://github.com/user/repo.git"]
        )

        assert result.exit_code == 1
        assert "Git command failed" in result.output


def test_netlify_command_error(runner, mock_config):
    """Test error handling when netlify command fails."""
    with mock.patch("subprocess.run") as mock_run:

        def run_command(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "netlify":
                if cmd[1] == "--version":
                    return mock.Mock(returncode=0, stdout="netlify-cli 1.0.0\n")
                elif cmd[1] == "sites:list":
                    return mock.Mock(returncode=0, stdout="other-site-id")
                elif cmd[1] == "deploy":
                    raise subprocess.CalledProcessError(
                        returncode=1,
                        cmd=["netlify", "deploy"],
                        output="",
                        stderr="Error: Invalid site ID",
                    )
            return mock.Mock(returncode=0, stdout="")

        mock_run.side_effect = run_command

        result = runner.invoke(deploy_to_netlify, ["--site-id", "invalid-id"])

        assert result.exit_code == 1
        assert "Site ID 'invalid-id' not found" in result.output


def test_netlify_cli_not_found(runner, mock_config):
    """Test error when Netlify CLI is not installed."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        result = runner.invoke(deploy_to_netlify, ["--site-id", "my-site-id"])

        assert result.exit_code == 1
        assert "Netlify CLI not found" in result.output


def test_custom_branch_github_deploy(runner, mock_config):
    """Test GitHub deployment with custom branch."""
    with mock.patch("subprocess.run") as mock_run:
        # Mock the branch check to return non-zero (branch doesn't exist)
        def run_command(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "git" and cmd[1] == "rev-parse":
                return mock.Mock(returncode=1)  # Branch doesn't exist
            return mock.Mock(returncode=0)

        mock_run.side_effect = run_command

        result = runner.invoke(
            deploy_to_github,
            ["--repo", "https://github.com/user/repo.git", "--branch", "custom-branch"],
        )

        assert result.exit_code == 0
        assert "Deployed to GitHub Pages" in result.output

        # Convert commands to strings for more reliable comparison
        called_commands = [" ".join(call[0][0]) for call in mock_run.call_args_list]

        # Verify branch name is used in commands
        checkout_commands = [cmd for cmd in called_commands if "git checkout" in cmd]
        checkout_branch_found = any("custom-branch" in cmd for cmd in checkout_commands)
        assert checkout_branch_found, (
            f"No checkout command with custom-branch found in: {checkout_commands}"
        )

        assert "git push -f origin custom-branch" in called_commands
