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
            "deploy", "Output directory not found", details={"output_dir": output_dir}
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
@error_handler(log=True, raise_error=False, console_output=True)
def deploy_to_github(repo: str, branch: str) -> None:
    """Deploy to GitHub Pages."""
    config = Config()
    output_dir = get_output_dir(config)

    if not output_dir or not os.path.exists(output_dir):
        raise CommandError(
            "github", "Output directory not found", details={"output_dir": output_dir}
        )

    os.chdir(output_dir)

    git_commands = [
        ["git", "init"],
        ["git", "checkout", "-b", branch],
        ["git", "add", "."],
        ["git", "commit", "-m", "Deploy to GitHub Pages"],
        ["git", "remote", "add", "origin", repo],
        ["git", "push", "-f", "origin", branch],
    ]

    try:
        for cmd in git_commands:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        print_success(f"Deployed to GitHub Pages on branch: {branch}")

    except subprocess.CalledProcessError as e:
        raise CommandError(
            "github",
            f"Git command failed: {e.cmd}",
            details={"command": " ".join(e.cmd), "output": e.output, "error": e.stderr},
        )


@deploy_commands.command(name="netlify")
@click.option(
    "--site-id",
    required=True,
    help="Netlify site ID",
)
@error_handler(log=True, raise_error=False, console_output=True)
def deploy_to_netlify(site_id: str) -> None:
    """Deploy to Netlify."""
    config = Config()
    output_dir = get_output_dir(config)

    # Check if Netlify CLI is installed
    try:
        version_check = subprocess.run(
            ["netlify", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        print_success(f"Using Netlify CLI version: {version_check.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise CommandError(
            "netlify",
            "Netlify CLI not found. Please install it with: npm install -g netlify-cli",
            details={"setup": "https://docs.netlify.com/cli/get-started/"},
        )

    # Check if the site ID exists
    try:
        site_check = subprocess.run(
            ["netlify", "sites:list"],
            check=True,
            capture_output=True,
            text=True
        )
        if site_id not in site_check.stdout:
            raise CommandError(
                "netlify",
                f"Site ID '{site_id}' not found in your Netlify account",
                details={"available_sites": site_check.stdout}
            )
    except subprocess.CalledProcessError as e:
        raise CommandError(
            "netlify",
            "Failed to verify site ID",
            details={"error": e.stderr}
        )

    # Deploy to Netlify with more verbose output
    deploy_cmd = [
        "netlify", "deploy",
        "--prod",
        "--dir", output_dir,
        "--site", site_id,
        "--message", f"Deploy from CLI at {datetime.now().isoformat()}"
    ]
    try:

        deploy_result = subprocess.run(
            deploy_cmd,
            check=True,
            capture_output=True,
            text=True
        )

        print_success(f"Successfully deployed to Netlify site: {site_id}")

        # Extract and display the deployment URL
        for line in deploy_result.stdout.split("\n"):
            if "Website URL:" in line or "Unique Deploy URL:" in line:
                print_success(f"Deployment URL: {line.split(':')[1].strip()}")

    except subprocess.CalledProcessError as e:
        raise CommandError(
            "netlify",
            "Netlify deployment failed",
            details={
                "command": " ".join(deploy_cmd),
                "output": e.stdout,
                "error": e.stderr,
                "exit_code": e.returncode
            }
        )
