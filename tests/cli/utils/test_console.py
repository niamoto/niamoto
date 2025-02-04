"""Test console utilities."""

import pytest
from unittest.mock import patch
from rich.table import Table

from niamoto.cli.utils.console import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_table,
    console,
)


@pytest.fixture
def mock_console():
    """Mock console for testing."""
    with patch("niamoto.cli.utils.console.console") as mock:
        yield mock


def test_print_success(mock_console):
    """Test success message printing."""
    message = "Operation successful"
    print_success(message)
    mock_console.print.assert_called_once_with(f"[>] {message}", style="italic green")


def test_print_error(mock_console):
    """Test error message printing."""
    message = "An error occurred"
    print_error(message)
    mock_console.print.assert_called_once_with(f"[x] {message}", style="bold red")


def test_print_warning(mock_console):
    """Test warning message printing."""
    message = "Warning message"
    print_warning(message)
    mock_console.print.assert_called_once_with(f"[!] {message}", style="yellow")


def test_print_info(mock_console):
    """Test info message printing."""
    message = "Information message"
    print_info(message)
    mock_console.print.assert_called_once_with(message, style="blue")


def test_print_table_empty_data(mock_console):
    """Test table printing with empty data."""
    data = []
    title = "Empty Table"
    print_table(data, title)
    mock_console.print.assert_called_once()
    table = mock_console.print.call_args[0][0]
    assert isinstance(table, Table)
    assert table.title == title


def test_print_table_with_data(mock_console):
    """Test table printing with data."""
    data = [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
    title = "People"

    print_table(data, title)

    mock_console.print.assert_called_once()
    table = mock_console.print.call_args[0][0]

    assert isinstance(table, Table)
    assert table.title == title

    # Check that the table has the correct columns
    assert len(table.columns) == 2
    assert table.columns[0].header == "name"
    assert table.columns[1].header == "age"
    assert table.columns[0].style == "cyan"
    assert table.columns[1].style == "cyan"


def test_console_instance():
    """Test that console is properly instantiated."""
    from rich.console import Console

    assert isinstance(console, Console)
