"""
CLI command for optimizing the Niamoto database.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from niamoto.common.config import Config
from niamoto.common.database import Database

console = Console()


@click.command(name="optimize")
@click.option(
    "--db-path",
    type=click.Path(exists=True),
    help="Path to the database file. If not provided, uses the configured path.",
)
@click.option(
    "--show-stats",
    is_flag=True,
    help="Show database statistics after optimization.",
)
def optimize_command(db_path: str = None, show_stats: bool = False):
    """
    Optimize the Niamoto database for better performance.

    This command:
    - Applies SQLite PRAGMA optimizations
    - Creates missing indexes on all tables
    - Updates query optimizer statistics
    - Optionally displays database statistics

    Examples:
        niamoto optimize
        niamoto optimize --show-stats
        niamoto optimize --db-path /path/to/database.db
    """

    # Check project structure if no explicit db path
    if not db_path:
        try:
            config = Config()
            db_path = config.database_path
        except Exception as e:
            console.print(f"[red]Error loading configuration:[/red] {str(e)}")
            raise click.Abort()

    if not Path(db_path).exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise click.Abort()

    console.print(f"[cyan]Optimizing database:[/cyan] {db_path}")

    try:
        # Initialize database with optimizations
        db = Database(db_path, optimize=True)

        # Run optimization on all tables
        console.print("\n[yellow]Creating indexes and updating statistics...[/yellow]")
        db.optimize_all_tables()

        # Run additional optimization
        console.print("[yellow]Running database optimization...[/yellow]")
        db.optimize_database()

        console.print(
            "\n[green]✓[/green] Database optimization completed successfully!"
        )

        # Show statistics if requested
        if show_stats:
            console.print("\n[cyan]Database Statistics:[/cyan]")
            stats = db.get_database_stats()

            # Create a nice table for display
            table = Table(title="Database Information", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Size", f"{stats.get('database_size_mb', 'N/A')} MB")
            table.add_row("Tables", str(stats.get("table_count", "N/A")))
            table.add_row("Indexes", str(stats.get("index_count", "N/A")))
            table.add_row("Cache Size", f"{abs(stats.get('cache_size', 0)) // 1024} MB")
            table.add_row("Journal Mode", stats.get("journal_mode", "N/A"))

            console.print(table)

            # Performance tips
            console.print("\n[cyan]Performance Tips:[/cyan]")

            if stats.get("journal_mode") == "wal":
                console.print("✓ WAL mode enabled - better concurrency")
            else:
                console.print("⚠ Consider enabling WAL mode for better concurrency")

            if abs(stats.get("cache_size", 0)) >= 32000:
                console.print("✓ Large cache configured - better performance")
            else:
                console.print("⚠ Consider increasing cache size for better performance")

            if stats.get("index_count", 0) > stats.get("table_count", 0):
                console.print("✓ Tables appear to be well-indexed")
            else:
                console.print("⚠ Some tables may benefit from additional indexes")

    except Exception as e:
        console.print(f"\n[red]Error during optimization:[/red] {str(e)}")
        raise click.Abort()


if __name__ == "__main__":
    optimize_command()
