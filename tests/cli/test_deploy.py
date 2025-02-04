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
            yield mock_cfg


def test_successful_github_deploy(runner, mock_config):
    """Test successful deployment to GitHub Pages."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0

        result = runner.invoke(
            deploy_to_github, ["--repo", "https://github.com/user/repo.git"]
        )

        assert result.exit_code == 0
        assert "Deployed to GitHub Pages" in result.output

        # Verify all git commands were called
        calls = mock_run.call_args_list
        assert len(calls) == 6  # init, checkout, add, commit, remote add, push

        # Verify specific commands
        assert calls[0][0][0] == ["git", "init"]
        assert calls[1][0][0] == ["git", "checkout", "-b", "gh-pages"]
        assert calls[2][0][0] == ["git", "add", "."]
        assert calls[3][0][0] == ["git", "commit", "-m", "Deploy to GitHub Pages"]
        assert calls[4][0][0] == [
            "git",
            "remote",
            "add",
            "origin",
            "https://github.com/user/repo.git",
        ]
        assert calls[5][0][0] == ["git", "push", "-f", "origin", "gh-pages"]


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
        mock_run.return_value.returncode = 0

        result = runner.invoke(
            deploy_to_github,
            ["--repo", "https://github.com/user/repo.git", "--branch", "custom-branch"],
        )

        assert result.exit_code == 0
        assert "Deployed to GitHub Pages" in result.output

        # Verify branch name in commands
        calls = mock_run.call_args_list
        assert ["git", "checkout", "-b", "custom-branch"] in [
            call[0][0] for call in calls
        ]
        assert ["git", "push", "-f", "origin", "custom-branch"] in [
            call[0][0] for call in calls
        ]
