"""
Console output utilities for the Niamoto CLI.
Provides consistent formatting for different types of messages.
"""

from rich.console import Console
from typing import Any

console = Console()


def print_success(message: str) -> None:
    """Print a success message in green."""
    console.print(f"[>] {message}", style="italic green")


def print_error(message: str) -> None:
    """Print an error message in red."""
    console.print(f"[x] {message}", style="bold red")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"[!] {message}", style="yellow")


def print_info(message: str) -> None:
    """Print an info message in blue."""
    console.print(f"{message}", style="blue")


def print_table(data: list[dict[str, Any]], title: str) -> None:
    """Print data in a formatted table."""
    from rich.table import Table

    table = Table(title=title)

    # Add columns from the first row keys
    if data:
        for key in data[0].keys():
            table.add_column(key, style="cyan")

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

    # Always print the table, even if empty
    console.print(table)
