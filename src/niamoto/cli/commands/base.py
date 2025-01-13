"""
base.py

This module provides the base click group and common utilities for the Niamoto CLI.
It defines the custom formatted CLI interface and shared command functionality.
"""

import click
from rich.console import Console
from rich.table import Table
from rich import box
from typing import List

# ASCII art banner for CLI
NIAMOTO_ASCII_ART = """
┳┓┳┏┓┳┳┓┏┓┏┳┓┏┓
┃┃┃┣┫┃┃┃┃┃ ┃ ┃┃
┛┗┻┛┗┛ ┗┗┛ ┻ ┗┛                                
"""


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

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Override the format_help method to integrate our command table.

        Args:
            ctx (click.Context): The click context object.
            formatter (click.HelpFormatter): The click help formatter object.
        """
        console = Console()
        with console.capture() as capture:
            console.print("[green]" + NIAMOTO_ASCII_ART + "[/green]")
            console.print(
                "\nUsage: niamoto [OPTIONS] COMMAND [ARGS]...\n\n"
                "Command line interface for Niamoto.\n"
                "This CLI provides commands for managing taxonomy data, plots, occurrences\n"
                "and generating static content.\n\n"
                "Options:\n"
                "  --help  Show this message and exit.\n\n"
                "Main Commands:\n"
            )

        formatter.write(capture.get())

        # Define main commands in preferred order
        main_commands = [
            "init",
            "import-all",
            "calculate-statistics",
            "generate-content",
            "deploy-static-site",
        ]

        # Get other commands that are not in main_commands
        other_commands = [
            cmd for cmd in self.list_commands(ctx) if cmd not in main_commands
        ]

        # Format and display main commands
        self._format_command_group(ctx, formatter, "Main Commands", main_commands)

        # Format and display other commands if any exist
        if other_commands:
            self._format_command_group(ctx, formatter, "Other Commands", other_commands)

    def _format_command_group(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
        group_title: str,
        commands: List[str],
    ) -> None:
        """
        Format a group of commands into a rich table.

        Args:
            ctx (click.Context): The click context object
            formatter (click.HelpFormatter): The formatter to write to
            group_title (str): The title for this group of commands
            commands (List[str]): List of command names to format
        """
        console = Console()
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("Command", style="dim")
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

        with console.capture() as capture:
            console.print(table)

        formatter.write(capture.get())


def print_success(message: str) -> None:
    """
    Print a success message in green with a checkmark.

    Args:
        message (str): The message to print
    """
    console = Console()
    console.print(f"✓ {message}", style="italic green")


def print_error(message: str) -> None:
    """
    Print an error message in red with an X.

    Args:
        message (str): The message to print
    """
    console = Console()
    console.print(f"✗ {message}", style="bold red")


def print_warning(message: str) -> None:
    """
    Print a warning message in yellow with an exclamation mark.

    Args:
        message (str): The message to print
    """
    console = Console()
    console.print(f"! {message}", style="yellow")


def print_info(message: str) -> None:
    """
    Print an info message in blue with an info symbol.

    Args:
        message (str): The message to print
    """
    console = Console()
    console.print(f"ℹ {message}", style="blue")


def confirm_action(question: str, default: bool = False) -> bool:
    """
    Ask for user confirmation before proceeding with an action.

    Args:
        question (str): The question to ask
        default (bool): Default response if user just hits enter

    Returns:
        bool: True if user confirmed, False otherwise
    """
    return click.confirm(question, default=default)
