"""
base.py

This module provides the base click group and common utilities for the Niamoto CLI.
It defines the custom formatted CLI interface and shared command functionality.
"""

from typing import List
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
     ^      ^      ^      ^      ^
    ^^^    ^^^    ^^^    ^^^    ^^^
   ^^^^^  ^^^^^  ^^^^^  ^^^^^  ^^^^^
     |      |      |      |      |

  NIAMOTO - Forest Ecology Data Platform
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
        from niamoto.common.bundle import get_base_path, is_frozen

        if is_frozen():
            # In PyInstaller bundle, read from __version__.py
            from niamoto.__version__ import __version__

            return __version__

        pyproject_path = get_base_path() / "pyproject.toml"
        if not pyproject_path.exists():
            raise VersionError(
                message="Version information not found - package not installed and pyproject.toml not found",
                details={"path": str(pyproject_path)},
            )

        try:
            import tomllib  # Python 3.11+

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
        self._format_command_group(ctx, "Commands", self.list_commands(ctx))

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

    # Quick Start section
    console.print("\n[bold yellow]🚀 Quick Start:[/bold yellow]\n")

    quick_start_steps = [
        {
            "title": "Initialize a new project",
            "commands": [
                "niamoto init my-project    # Create new project with GUI",
                "niamoto init              # Initialize in current directory",
                "niamoto init --gui        # Initialize with GUI configuration",
            ],
        },
        {
            "title": "Configure and import your data",
            "commands": [
                "niamoto gui               # Visual configuration interface",
                "niamoto import            # Import all configured sources",
            ],
        },
        {
            "title": "Run the pipeline",
            "commands": [
                "niamoto run               # Import → Transform → Export",
            ],
        },
    ]

    for i, step in enumerate(quick_start_steps, 1):
        console.print(f"[bold cyan]{i}. {step['title']}[/bold cyan]")
        for cmd in step["commands"]:
            console.print(f"[green]   $ {cmd}[/green]")

    # Common Workflows section
    console.print("\n[bold yellow]📋 Common Workflows:[/bold yellow]\n")

    workflows = [
        {
            "icon": "📊",
            "title": "Check your data",
            "command": "niamoto stats             # Overview of your database",
        },
        {
            "icon": "🔄",
            "title": "Update your site",
            "command": "niamoto transform && niamoto export  # Recalculate and regenerate",
        },
        {
            "icon": "🚀",
            "title": "Deploy your site",
            "command": "niamoto deploy github --repo <url>   # Deploy to GitHub Pages",
        },
    ]

    for workflow in workflows:
        console.print(f"[cyan]{workflow['icon']} {workflow['title']}[/cyan]")
        console.print(f"[green]   $ {workflow['command']}[/green]")

    # All Commands reference
    console.print("\n[bold yellow]📖 All Commands:[/bold yellow]\n")

    command_groups = [
        {
            "name": "Setup",
            "commands": "init, gui",
        },
        {
            "name": "Pipeline",
            "commands": "import, transform, export, run",
        },
        {
            "name": "Analysis",
            "commands": "stats, plugins",
        },
        {
            "name": "Deployment",
            "commands": "deploy",
        },
    ]

    for group in command_groups:
        console.print(f"  [cyan]• {group['name']}:[/cyan] {group['commands']}")

    console.print("\n[dim]Run 'niamoto <command> --help' for detailed usage[/dim]")

    # Learn More section
    console.print("\n[bold yellow]💡 Learn More:[/bold yellow]")
    console.print("  📖 Documentation: [link]https://niamoto.readthedocs.io/[/link]")
    console.print("  ❓ Help: niamoto <command> --help")
    console.print("  🐛 Issues: [link]https://github.com/niamoto/niamoto/issues[/link]")


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
