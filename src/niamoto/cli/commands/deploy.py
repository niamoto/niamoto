# commands/deploy.py

"""
Commands for deploying generated content to various platforms.
"""

import click
import os
import subprocess

from ..utils.console import print_success, print_error
from niamoto.common.config import Config


@click.group(name="deploy")
def deploy_commands():
    """Commands for deploying generated content."""
    pass


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
def deploy_to_github(repo: str, branch: str) -> None:
    """Deploy to GitHub Pages."""
    try:
        config = Config()
        output_dir = config.get("output_paths", "site")

        os.chdir(output_dir)

        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "checkout", "-b", branch], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Deploy to GitHub Pages"], check=True)
        subprocess.run(["git", "remote", "add", "origin", repo], check=True)
        subprocess.run(["git", "push", "-f", "origin", branch], check=True)

        print_success(f"Deployed to GitHub Pages on branch: {branch}")

    except Exception as e:
        print_error(f"GitHub Pages deployment failed: {str(e)}")
        raise click.Abort()
