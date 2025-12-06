#!/usr/bin/env python3
"""
Query DuckDB database utility script.

This script provides a convenient way to inspect and query the Niamoto DuckDB database
during development and debugging.

Examples:
    # Execute a query
    uv run python scripts/query_db.py "SELECT * FROM taxon LIMIT 5"

    # List all tables
    uv run python scripts/query_db.py --list-tables

    # Describe a table schema
    uv run python scripts/query_db.py --describe taxon

    # Interactive SQL REPL
    uv run python scripts/query_db.py --interactive

    # Use a different database file
    uv run python scripts/query_db.py --db /path/to/db.duckdb "SELECT COUNT(*) FROM taxon"
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from niamoto.common.database import Database
from sqlalchemy import text
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()


def get_default_db_path() -> str:
    """Get the default database path from test-instance."""
    default_path = (
        Path(__file__).parent.parent
        / "test-instance"
        / "niamoto-nc"
        / "db"
        / "niamoto.duckdb"
    )
    if not default_path.exists():
        console.print(
            f"[yellow]Warning: Default database not found at {default_path}[/yellow]"
        )
    return str(default_path)


def list_tables(db: Database) -> None:
    """List all tables in the database."""
    try:
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        if not tables:
            console.print("[yellow]No tables found in database[/yellow]")
            return

        table = Table(
            title="Database Tables", show_header=True, header_style="bold magenta"
        )
        table.add_column("Table Name", style="cyan")
        table.add_column("Row Count", justify="right", style="green")

        for table_name in sorted(tables):
            try:
                with db.engine.connect() as connection:
                    result = connection.execute(
                        text(f'SELECT COUNT(*) FROM "{table_name}"')
                    )
                    count = result.fetchone()[0]
                    table.add_row(table_name, str(count))
            except Exception as e:
                table.add_row(table_name, f"[red]Error: {str(e)}[/red]")

        console.print(table)
        console.print(f"\n[green]Total: {len(tables)} tables[/green]")
    except Exception as e:
        console.print(f"[red]Error listing tables: {str(e)}[/red]")


def describe_table(db: Database, table_name: str) -> None:
    """Describe the schema of a table."""
    try:
        columns = db.get_table_columns(table_name)

        if not columns:
            console.print(
                f"[yellow]Table '{table_name}' not found or has no columns[/yellow]"
            )
            return

        # Get column details
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        table_columns = inspector.get_columns(table_name)

        table = Table(
            title=f"Table: {table_name}", show_header=True, header_style="bold magenta"
        )
        table.add_column("Column", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Nullable", style="green")
        table.add_column("Default", style="blue")

        for col in table_columns:
            table.add_row(
                col["name"],
                str(col["type"]),
                "Yes" if col.get("nullable", True) else "No",
                str(col.get("default", "")),
            )

        console.print(table)

        # Get row count
        with db.engine.connect() as connection:
            result = connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.fetchone()[0]
            console.print(f"\n[green]Total rows: {count:,}[/green]")

    except Exception as e:
        console.print(f"[red]Error describing table '{table_name}': {str(e)}[/red]")


def execute_query(db: Database, query: str, limit: Optional[int] = None) -> None:
    """Execute a SQL query and display results."""
    try:
        # Add LIMIT if not present and limit is specified
        if limit and "LIMIT" not in query.upper():
            query = f"{query.rstrip(';')} LIMIT {limit}"

        # Show the query
        console.print(
            Panel(
                Syntax(query, "sql", theme="monokai"),
                title="Query",
                border_style="blue",
            )
        )

        with db.engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()

            if not rows:
                console.print("[yellow]Query returned no results[/yellow]")
                return

            # Create table
            table = Table(show_header=True, header_style="bold magenta")

            for col in columns:
                table.add_column(str(col), style="cyan")

            for row in rows:
                table.add_row(
                    *[str(val) if val is not None else "[dim]NULL[/dim]" for val in row]
                )

            console.print(table)
            console.print(f"\n[green]Rows returned: {len(rows):,}[/green]")

    except Exception as e:
        console.print(f"[red]Error executing query: {str(e)}[/red]")


def interactive_mode(db: Database) -> None:
    """Enter interactive SQL REPL mode."""
    console.print(
        Panel.fit(
            "[bold cyan]Niamoto DuckDB Interactive Query Tool[/bold cyan]\n"
            "Commands:\n"
            "  .tables          - List all tables\n"
            "  .describe <name> - Describe table schema\n"
            "  .quit or .exit   - Exit interactive mode\n"
            "  Any SQL query    - Execute the query",
            border_style="blue",
        )
    )

    while True:
        try:
            query = console.input("\n[bold green]sql>[/bold green] ").strip()

            if not query:
                continue

            # Handle special commands
            if query in [".quit", ".exit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            elif query == ".tables":
                list_tables(db)
            elif query.startswith(".describe "):
                table_name = query.split(maxsplit=1)[1]
                describe_table(db, table_name)
            else:
                # Execute SQL query
                execute_query(db, query, limit=100)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use .quit or .exit to exit[/yellow]")
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Query and inspect Niamoto DuckDB database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("query", nargs="?", help="SQL query to execute")

    parser.add_argument(
        "--db",
        default=get_default_db_path(),
        help="Path to DuckDB database file (default: test-instance/niamoto-nc/db/niamoto.duckdb)",
    )

    parser.add_argument(
        "--list-tables", action="store_true", help="List all tables in the database"
    )

    parser.add_argument(
        "--describe", metavar="TABLE", help="Describe the schema of a table"
    )

    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enter interactive SQL REPL mode",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of rows returned (default: no limit, or 100 in interactive mode)",
    )

    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Open database in read-only mode (useful if another process has it locked)",
    )

    args = parser.parse_args()

    # Validate database path
    db_path = Path(args.db)
    if not db_path.exists():
        console.print(f"[red]Error: Database file not found: {db_path}[/red]")
        sys.exit(1)

    # Connect to database
    try:
        console.print(f"[blue]Connecting to database: {db_path}[/blue]")
        db = Database(str(db_path), read_only=args.read_only)
        console.print("[green]✓ Connected successfully[/green]\n")
    except Exception as e:
        console.print(f"[red]Error connecting to database: {str(e)}[/red]")
        console.print(
            "[yellow]Tip: Try using --read-only if the database is locked by another process[/yellow]"
        )
        sys.exit(1)

    # Execute commands
    if args.list_tables:
        list_tables(db)
    elif args.describe:
        describe_table(db, args.describe)
    elif args.interactive:
        interactive_mode(db)
    elif args.query:
        execute_query(db, args.query, limit=args.limit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
