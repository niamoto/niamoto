"""
base.py

This module provides the base click group and common utilities for the Niamoto CLI.
It defines the custom formatted CLI interface and shared command functionality.
"""

from typing import List
from pathlib import Path
from importlib import metadata
import click
from rich.console import Console
from rich.table import Table
from rich.style import Style
from rich import box


from niamoto.common.exceptions import VersionError, CommandError
from niamoto.common.utils import error_handler

# ASCII art banner for CLI
# NIAMOTO_ASCII_ART = """
#     /\\
#    /  \\    /\\
#   /    \\  /  \\  /\\  /\\
#  /      \\/    \\/  \\/  \\
# ┳┓┳┏┓┳┳┓┏┓┏┳┓┏┓  forest
# ┃┃┃┣┫┃┃┃┃┃ ┃ ┃┃  ecology
# ┛┗┻┛┗┛ ┗┗┛ ┻ ┗┛  data
# """

NIAMOTO_ASCII_ART = """
 ██╗   ██╗██╗ █████╗ ███╗   ███╗ ██████╗ ████████╗ ██████╗
 ███╗  ██║██║██╔══██╗████╗ ████║██╔═══██╗╚══██╔══╝██╔═══██╗
 ████╗ ██║██║███████║██╔████╔██║██║   ██║   ██║   ██║   ██║
 ██╔██╗██║██║██╔══██║██║╚██╔╝██║██║   ██║   ██║   ██║   ██║
 ██║╚████║██║██║  ██║██║ ╚═╝ ██║╚██████╔╝   ██║   ╚██████╔╝
 ╚═╝ ╚═══╝╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝    ╚═╝    ╚═════╝
"""


@error_handler(log=True, raise_error=True)
@error_handler(log=True, raise_error=True)
def get_version_from_pyproject() -> str:
    """
    Gets the version number of Niamoto.
    First tries to get it from the installed package metadata,
    falls back to pyproject.toml if in development mode.

    Returns:
        str: The version string (e.g., '0.3.3')
    """
    try:
        # Try to get version from installed package first
        return metadata.version("niamoto")
    except metadata.PackageNotFoundError:
        # Fallback to pyproject.toml for development mode
        pyproject_path = Path(__file__).resolve().parents[4] / "pyproject.toml"
        if not pyproject_path.exists():
            raise VersionError(
                message="Version information not found - package not installed and pyproject.toml not found",
                details={"path": str(pyproject_path)},
            )

        try:
            # Use appropriate TOML parser based on Python version
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib  # Python 3.10 and earlier

            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)
                version = pyproject_data.get("project", {}).get(
                    "version"
                ) or pyproject_data.get("tool", {}).get("project", {}).get("version")
                if not isinstance(version, str):
                    raise VersionError(
                        message="Version not found or invalid in pyproject.toml",
                        details={"content": pyproject_data},
                    )
                return version
        except Exception as e:
            raise VersionError(
                message="Error reading version from pyproject.toml",
                details={"error": str(e)},
            )


# Get the version of the application
VERSION = get_version_from_pyproject()


class RichCLI(click.Group):
    """
    Custom Click Group class that provides a richly formatted CLI interface.
    Overrides default Click Group behavior to provide custom help formatting
    and command organization.
    """

    def list_commands(self, ctx: click.Context) -> List[str]:
        """
        Return the list of command names as they were added, not sorted.

        Args:
            ctx (click.Context): The click context object.

        Returns:
            list: A list of command names in the order they were added.
        """
        return list(self.commands.keys())

    @error_handler(log=True)
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Override the format_help method to integrate our command table with colors.

        Args:
            ctx (click.Context): The click context object.
            formatter (click.HelpFormatter): The click help formatter object.
        """
        console = Console()
        # Imprimez directement dans la console pour conserver les couleurs
        niamoto_style = Style(color="#5ba250")
        console.print(NIAMOTO_ASCII_ART, style=niamoto_style)
        console.print(
            f"\n[bold]Niamoto CLI, version {VERSION}[/bold]\n"
            "\n[bold yellow]Usage:[/bold yellow] niamoto [OPTIONS] COMMAND [ARGS]...\n\n"
            "Command line interface for Niamoto.\n"
            "This CLI provides commands for managing ecological data through a configurable\n"
            "pipeline system with import, transform, and export stages.\n\n"
            "[bold yellow]Options:[/bold yellow]\n"
            "  --help  [dim]Show this message and exit.[/dim]\n\n"
        )

        # Afficher les commandes principales
        self._format_command_group(ctx, "Main Commands", self.list_commands(ctx))

        # Afficher les Next Steps
        display_next_steps()

    @error_handler(log=True)
    def _format_command_group(
        self,
        ctx: click.Context,
        group_title: str,
        commands: List[str],
    ) -> None:
        """
        Format a group of commands into a rich table with colors.

        Args:
            ctx (click.Context): The click context object
            group_title (str): The title for this group of commands
            commands (List[str]): List of command names to format
        """
        console = Console()
        table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
        table.add_column("Command", style="green")
        table.add_column("Description")

        for cmd_name in commands:
            cmd = self.get_command(ctx, cmd_name)
            if cmd is None:
                continue

            # Extract the first line of the docstring as description
            docstring = cmd.callback.__doc__
            description = (
                docstring.strip().split("\n")[0] if docstring else "No description"
            )

            table.add_row(cmd_name, description)

        # Imprimez directement le tableau dans la console pour conserver les couleurs
        console.print(f"\n[bold yellow]{group_title}[/bold yellow]\n")
        console.print(table)


@error_handler(log=True)
def display_next_steps() -> None:
    """
    Display the "Next Steps" section at the end of the help message.
    """
    console = Console()
    console.print("\n[bold yellow]Get Started:[/bold yellow]\n")

    steps = [
        {
            "title": "Initialize or check your environment",
            "commands": [
                "niamoto init # Initialize the environment (or check the current status)",
                "niamoto init --reset # Reinitialize the database and remove generated files in outputs directory",
            ],
        },
        {
            "title": "Explore available plugins",
            "commands": [
                "niamoto plugins # List all available Niamoto plugins",
                "niamoto plugins --type transformer # List transformer plugins only",
                "niamoto plugins --type loader     # List loader plugins only",
                "niamoto plugins --type exporter   # List exporter plugins only",
                "niamoto plugins --type widget     # List widget plugins only",
            ],
        },
        {
            "title": "Import data",
            "commands": [
                "niamoto import taxonomy <file>     # Import taxonomy data",
                "niamoto import plots <file>        # Import plot data",
                "niamoto import occurrences <file>  # Import occurrence data",
                "niamoto import # Import all sources",
            ],
        },
        {
            "title": "Transform data",
            "commands": [
                "niamoto transform --group <name> # Transform data by configured group",
                "niamoto transform # Transform for all configured groups",
                "# Groups are defined in your transform.yml configuration file",
            ],
        },
        {
            "title": "Export content",
            "commands": [
                "niamoto export web_pages --group <name> # Export static pages by configured group",
                "niamoto export # Export for all configured groups",
                "# Groups are defined in your export.yml configuration file",
            ],
        },
        {
            "title": "Run the complete pipeline",
            "commands": [
                "niamoto run # Run the complete Niamoto data pipeline: import, transform, and export",
                "niamoto run --skip-import     # Run transform and export only",
                "niamoto run --skip-transform  # Run import and export only",
                "niamoto run --skip-export     # Run import and transform only",
            ],
        },
        {
            "title": "Deploy content",
            "commands": [
                "niamoto deploy github --repo <url>     # Deploy to GitHub Pages",
                "niamoto deploy netlify --site-id <id>  # Deploy to Netlify",
            ],
        },
        {
            "title": "Have fun exploring your data and generating insights!",
            "commands": [
                "niamoto stats # Display general statistics about your data",
                "niamoto stats --detailed # Show detailed statistics with top items",
                "niamoto stats --group taxon # Show statistics for a specific group",
                "niamoto stats --suggestions # Get exploration suggestions based on your data",
                "niamoto stats --export stats.json # Export statistics to JSON or CSV",
                "# Explore the generated website in outputs/website/",
            ],
        },
    ]

    for i, step in enumerate(steps, 1):
        console.print(f"[bold cyan]{i}. {step['title']}[/bold cyan]")
        for cmd in step["commands"]:
            if cmd.startswith("#"):
                console.print(f"[dim]{cmd}[/dim]")
            else:
                console.print(f"[green]   $ {cmd}[/green]")

    console.print("\n[bold yellow]Need help?[/bold yellow]")
    console.print("  * Run 'niamoto --help' for available commands")
    console.print("  * Visit https://niamoto.readthedocs.io/ for documentation")


@error_handler(log=True, raise_error=True)
def confirm_action(question: str, default: bool = False) -> bool:
    """
    Ask for user confirmation before proceeding with an action.

    Args:
        question (str): The question to ask
        default (bool): Default response if user just hits enter

    Returns:
        bool: True if user confirmed, False otherwise
    """
    try:
        return click.confirm(question, default=default)
    except click.Abort:
        raise CommandError(
            command="confirm_action",
            message="User aborted the action",
            details={"question": question},
        )
