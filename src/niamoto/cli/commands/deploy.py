"""
Commands for deploying generated content to various platforms.
"""

import os
import subprocess
from datetime import datetime

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import CommandError
from niamoto.common.utils import error_handler
from ..utils.console import print_success


@click.group(name="deploy")
def deploy_commands():
    """Deploy generated content using [yellow]config.yml[/yellow]."""
    pass


def get_output_dir(config: Config) -> str:
    """
    Retrieve the output directory from the configuration and verify its existence.

    Args:
        config (Config): The configuration object.

    Returns:
        str: The path to the output directory.

    Raises:
        CommandError: If the output directory is not found or invalid.
    """
    output_dir = config.get_export_config.get("web")
    if not output_dir or not os.path.exists(output_dir):
        raise CommandError(
            command="deploy",
            message="Output directory not found",
            details={"output_dir": output_dir},
        )
    return output_dir


@deploy_commands.command(name="github")
@click.option(
    "--repo",
    required=True,
    help="GitHub repository URL",
)
@click.option(
    "--branch",
    default="gh-pages",
    help="Branch to deploy to",
)
@click.option(
    "--name",
    default="Niamoto Bot",
    help="Git commit author name",
)
@click.option(
    "--email",
    default="bot@niamoto.org",
    help="Git commit author email",
)
@error_handler(log=True, raise_error=True)
def deploy_to_github(repo: str, branch: str, name: str, email: str) -> None:
    """Deploy to GitHub Pages."""
    config = Config()
    output_dir = get_output_dir(config)

    os.chdir(output_dir)

    # Check if git is already initialized
    is_git_repo = os.path.isdir(os.path.join(output_dir, ".git"))

    try:
        # Initialize git if needed
        if not is_git_repo:
            subprocess.run(["git", "init"], check=True, capture_output=True, text=True)
            print_success("Initialized new git repository")
        else:
            print_success("Using existing git repository")

        # Configure git user identity for this repository
        subprocess.run(
            ["git", "config", "user.name", name],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.email", email],
            check=True,
            capture_output=True,
            text=True,
        )
        print_success(f"Configured git identity: {name} <{email}>")

        # Configure git remotes
        try:
            subprocess.run(
                ["git", "remote", "remove", "origin"],
                check=False,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            # It's okay if removing origin fails (might not exist)
            pass

        subprocess.run(
            ["git", "remote", "add", "origin", repo],
            check=True,
            capture_output=True,
            text=True,
        )

        # Check if branch exists locally
        branch_exists = (
            subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                check=False,
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )

        # Switch to the target branch or create it
        if branch_exists:
            subprocess.run(
                ["git", "checkout", branch], check=True, capture_output=True, text=True
            )
            print_success(f"Switched to existing branch: {branch}")
        else:
            # Create a new branch (handle both new repos and existing repos)
            try:
                subprocess.run(
                    ["git", "checkout", "-b", branch],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError:
                # If the checkout fails, try creating from HEAD
                subprocess.run(
                    ["git", "checkout", "--orphan", branch],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                # Remove all files from the index
                subprocess.run(
                    ["git", "rm", "-rf", "."],
                    check=False,
                    capture_output=True,
                    text=True,
                )

            print_success(f"Created new branch: {branch}")

        # Stage all files
        subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)

        # Commit changes (allow empty commits to support re-running the command)
        commit_result = subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"Deploy to GitHub Pages at {datetime.now().isoformat()}",
                "--allow-empty",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        # If nothing to commit, that's okay
        if commit_result.returncode != 0:
            # Check if it's just a "nothing to commit" message
            if (
                "nothing to commit" in commit_result.stderr
                or "nothing to commit" in commit_result.stdout
            ):
                print_success("No changes to commit")
            else:
                # Some other error occurred
                commit_result.check_returncode()  # Will raise with proper error
        else:
            print_success("Committed changes")

        # Force push to branch
        subprocess.run(
            ["git", "push", "-f", "origin", branch],
            check=True,
            capture_output=True,
            text=True,
        )

        print_success(f"Deployed to GitHub Pages on branch: {branch}")

    except subprocess.CalledProcessError as e:
        raise CommandError(
            command="github",
            message=f"Git command failed: {e.cmd}",
            details={
                "command": " ".join(e.cmd),
                "output": e.stdout,
                "error": e.stderr,
                "exit_code": e.returncode,
            },
        )


@deploy_commands.command(name="netlify")
@click.option(
    "--site-id",
    required=True,
    help="Netlify site ID",
)
@error_handler(log=True, raise_error=True)
def deploy_to_netlify(site_id: str) -> None:
    """Deploy to Netlify."""
    config = Config()
    output_dir = get_output_dir(config)

    # Check if Netlify CLI is installed
    try:
        version_check = subprocess.run(
            ["netlify", "--version"], check=True, capture_output=True, text=True
        )
        print_success(f"Using Netlify CLI version: {version_check.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise CommandError(
            command="netlify",
            message="Netlify CLI not found. Please install it with: npm install -g netlify-cli",
            details={"setup": "https://docs.netlify.com/cli/get-started/"},
        )

    # Check if the site ID exists
    try:
        site_check = subprocess.run(
            ["netlify", "sites:list"], check=True, capture_output=True, text=True
        )
        if site_id not in site_check.stdout:
            raise CommandError(
                command="netlify",
                message=f"Site ID '{site_id}' not found in your Netlify account",
                details={"available_sites": site_check.stdout},
            )
    except subprocess.CalledProcessError as e:
        raise CommandError(
            command="netlify",
            message="Failed to verify site ID",
            details={"error": e.stderr},
        )

    # Deploy to Netlify with more verbose output
    deploy_cmd = [
        "netlify",
        "deploy",
        "--prod",
        "--dir",
        output_dir,
        "--site",
        site_id,
        "--message",
        f"Deploy from CLI at {datetime.now().isoformat()}",
    ]
    try:
        deploy_result = subprocess.run(
            deploy_cmd, check=True, capture_output=True, text=True
        )

        print_success(f"Successfully deployed to Netlify site: {site_id}")

        # Extract and display the deployment URL
        for line in deploy_result.stdout.split("\n"):
            if "Website URL:" in line or "Unique Deploy URL:" in line:
                print_success(f"Deployment URL: {line.split(':')[1].strip()}")

    except subprocess.CalledProcessError as e:
        raise CommandError(
            command="netlify",
            message="Netlify deployment failed",
            details={
                "command": " ".join(deploy_cmd),
                "output": e.stdout,
                "error": e.stderr,
                "exit_code": e.returncode,
            },
        )
