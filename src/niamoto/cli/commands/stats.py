"""
Commands for displaying statistics about the Niamoto database.
"""

from typing import Dict, Any, Optional
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseError
from niamoto.common.utils.error_handler import error_handler
from ..utils.console import print_info, print_error


@click.command(name="stats")
@click.option(
    "--group",
    type=str,
    help="Show statistics for a specific group (taxon, plot, shape, etc.).",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed statistics including top items.",
)
@click.option(
    "--export",
    type=click.Path(),
    help="Export statistics to a file (JSON or CSV).",
)
@click.option(
    "--suggestions",
    is_flag=True,
    help="Show suggested queries for data exploration.",
)
@error_handler(log=True, raise_error=True)
def stats_command(
    group: Optional[str], detailed: bool, export: Optional[str], suggestions: bool
) -> None:
    """
    Display statistics about the data in your Niamoto database.

    Shows counts, distributions, and other insights about your ecological data.

    Examples:
        niamoto stats                    # Show general statistics
        niamoto stats --detailed         # Show detailed statistics with top items
        niamoto stats --group taxon      # Show statistics for a specific group
        niamoto stats --export stats.json # Export statistics to a file
    """
    try:
        config = Config()
        db_path = config.database_path

        if not db_path or not Path(db_path).exists():
            print_error("Database not found. Please run 'niamoto init' first.")
            return

        db = Database(db_path)

        # Get statistics based on options
        if group:
            stats = get_group_statistics(db, group, detailed)
            display_group_statistics(stats, group, detailed)
        else:
            stats = get_general_statistics(db, detailed)
            display_general_statistics(stats, detailed)

        # Export if requested
        if export:
            export_statistics(stats, export)
            print_info(f"Statistics exported to {export}")

        # Show suggestions if requested
        if suggestions:
            show_data_exploration_suggestions(db)

    except DatabaseError as e:
        print_error(f"Database error: {str(e)}")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")


def get_general_statistics(db: Database, detailed: bool = False) -> Dict[str, Any]:
    """Get general statistics about all data in the database."""
    stats = {}

    # Get all tables in the database
    try:
        result = db.execute_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        all_tables = [row[0] for row in result]
    except Exception:
        all_tables = []

    # Count records in main reference tables
    main_ref_tables = {
        "taxon_ref": "Reference Taxa",
        "plot_ref": "Reference Plots",
        "shape_ref": "Reference Shapes",
        "occurrences": "Occurrences",
    }

    for table_name, display_name in main_ref_tables.items():
        if table_name in all_tables:
            try:
                result = db.execute_sql(f"SELECT COUNT(*) FROM {table_name}")
                count = result.scalar()
                stats[display_name] = count
            except Exception:
                stats[display_name] = 0

    # Count generated tables (from transforms)
    generated_tables = [t for t in all_tables if t in ["taxon", "plot", "shape"]]
    if generated_tables:
        stats["Generated Tables"] = {}
        for table in generated_tables:
            try:
                result = db.execute_sql(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                stats["Generated Tables"][table.capitalize()] = count
            except Exception:
                stats["Generated Tables"][table.capitalize()] = 0

    # Get shape types dynamically (only if shape_ref exists and has type column)
    if "shape_ref" in all_tables:
        try:
            result = db.execute_sql("PRAGMA table_info(shape_ref)")
            columns = [row[1] for row in result]
            if "type" in columns:
                result = db.execute_sql(
                    "SELECT type, COUNT(*) as count FROM shape_ref WHERE type IS NOT NULL GROUP BY type ORDER BY count DESC"
                )
                shape_types = {row.type: row.count for row in result}
                if shape_types:
                    stats["Shape Types"] = shape_types
        except Exception:
            pass

    if detailed:
        # Try to get top families - check if family column exists
        if "occurrences" in all_tables:
            try:
                result = db.execute_sql("PRAGMA table_info(occurrences)")
                columns = [row[1] for row in result]
                if "family" in columns:
                    result = db.execute_sql("""
                        SELECT family, COUNT(*) as count
                        FROM occurrences
                        WHERE family IS NOT NULL
                        GROUP BY family
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    families = [(row.family, row.count) for row in result]
                    if families:
                        stats["Top Families"] = families
            except Exception:
                pass

        # Try to get elevation statistics - check if elevation column exists
        if "occurrences" in all_tables:
            try:
                result = db.execute_sql("PRAGMA table_info(occurrences)")
                columns = [row[1] for row in result]
                if "elevation" in columns:
                    result = db.execute_sql("""
                        SELECT
                            MIN(elevation) as min_elev,
                            MAX(elevation) as max_elev,
                            AVG(elevation) as avg_elev,
                            COUNT(elevation) as count_with_elev
                        FROM occurrences
                        WHERE elevation IS NOT NULL
                    """)
                    row = result.first()
                    if row and row.min_elev is not None:
                        stats["Elevation Range"] = {
                            "Min": f"{row.min_elev:.0f}m",
                            "Max": f"{row.max_elev:.0f}m",
                            "Average": f"{row.avg_elev:.0f}m",
                            "Records with elevation": f"{row.count_with_elev:,}",
                        }
            except Exception:
                pass

        # Get interesting numerical statistics from occurrences
        if "occurrences" in all_tables:
            try:
                result = db.execute_sql("PRAGMA table_info(occurrences)")
                columns = [row[1] for row in result]
                numerical_cols = []

                # Check for common numerical columns
                common_numerical = ["dbh", "height", "wood_density", "rainfall"]
                for col in common_numerical:
                    if col in columns:
                        numerical_cols.append(col)

                if numerical_cols:
                    stats["Numerical Data"] = {}
                    for col in numerical_cols:
                        result = db.execute_sql(f"""
                            SELECT
                                COUNT({col}) as count_non_null,
                                MIN({col}) as min_val,
                                MAX({col}) as max_val,
                                AVG({col}) as avg_val
                            FROM occurrences
                            WHERE {col} IS NOT NULL
                        """)
                        row = result.first()
                        if row and row.count_non_null > 0:
                            stats["Numerical Data"][col] = {
                                "Count": f"{row.count_non_null:,}",
                                "Range": f"{row.min_val:.2f} - {row.max_val:.2f}",
                                "Average": f"{row.avg_val:.2f}",
                            }
            except Exception:
                pass

    return stats


def get_group_statistics(
    db: Database, group: str, detailed: bool = False
) -> Dict[str, Any]:
    """Get statistics for a specific group."""
    stats = {}

    # Map group names to table names
    table_map = {
        "taxon": "taxon_ref",
        "plot": "plot_ref",
        "shape": "shape_ref",
        "occurrence": "occurrences",
    }

    table_name = table_map.get(group, f"{group}_stats")

    try:
        # Get count
        result = db.execute_sql(f"SELECT COUNT(*) FROM {table_name}")
        stats["Total Count"] = result.scalar()

        # Get column information
        result = db.execute_sql(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in result]
        stats["Columns"] = len(columns)

        if detailed:
            stats["Column Names"] = columns

            # For taxon data, get rank distribution
            if group == "taxon":
                result = db.execute_sql("""
                    SELECT rank_name as rank, COUNT(*) as count
                    FROM taxon_ref
                    WHERE rank_name IS NOT NULL
                    GROUP BY rank_name
                    ORDER BY count DESC
                """)
                stats["Rank Distribution"] = {row.rank: row.count for row in result}

            # For shape data, get type distribution
            elif group == "shape":
                result = db.execute_sql("""
                    SELECT type, COUNT(*) as count
                    FROM shape_ref
                    WHERE type IS NOT NULL
                    GROUP BY type
                    ORDER BY count DESC
                """)
                stats["Types"] = [(row.type, row.count) for row in result]

    except Exception as e:
        stats["Error"] = str(e)

    return stats


def display_general_statistics(stats: Dict[str, Any], detailed: bool) -> None:
    """Display general statistics in a formatted table."""
    console = Console()

    # Main counts table
    table = Table(
        title="Niamoto Database Statistics",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
    )
    table.add_column("Data Type", style="green")
    table.add_column("Count", justify="right", style="yellow")

    # Display main reference data counts first
    main_data_keys = [
        "Reference Taxa",
        "Reference Plots",
        "Reference Shapes",
        "Occurrences",
    ]
    for key in main_data_keys:
        if key in stats:
            table.add_row(key, f"{stats[key]:,}")

    # Display generated tables count if present
    if "Generated Tables" in stats:
        for table_name, count in stats["Generated Tables"].items():
            table.add_row(f"Generated {table_name}", f"{count:,}")

    console.print(table)

    # Shape types if present
    if stats.get("Shape Types"):
        shape_table = Table(
            title="\nShape Types",
            show_header=True,
            header_style="bold cyan",
            box=box.SIMPLE,
        )
        shape_table.add_column("Type", style="green")
        shape_table.add_column("Count", justify="right", style="yellow")

        for shape_type, count in stats["Shape Types"].items():
            shape_table.add_row(shape_type, f"{count:,}")

        console.print(shape_table)

    # Detailed statistics
    if detailed:
        if stats.get("Top Families"):
            family_table = Table(
                title="\nTop 10 Families",
                show_header=True,
                header_style="bold cyan",
                box=box.SIMPLE,
            )
            family_table.add_column("Family", style="green")
            family_table.add_column("Count", justify="right", style="yellow")

            for family, count in stats["Top Families"]:
                family_table.add_row(family, f"{count:,}")

            console.print(family_table)

        if stats.get("Elevation Range"):
            console.print("\n[bold cyan]Elevation Range:[/bold cyan]")
            for key, value in stats["Elevation Range"].items():
                console.print(f"  {key}: {value}")

        if stats.get("Numerical Data"):
            console.print("\n[bold cyan]Numerical Data Summary:[/bold cyan]")
            for field_name, field_stats in stats["Numerical Data"].items():
                console.print(f"  [green]{field_name.upper()}:[/green]")
                for key, value in field_stats.items():
                    console.print(f"    {key}: {value}")


def display_group_statistics(stats: Dict[str, Any], group: str, detailed: bool) -> None:
    """Display statistics for a specific group."""
    console = Console()

    table = Table(
        title=f"{group.capitalize()} Statistics",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
    )
    table.add_column("Metric", style="green")
    table.add_column("Value", justify="right", style="yellow")

    for key, value in stats.items():
        if key not in ["Column Names", "Rank Distribution", "Categories", "Error"]:
            table.add_row(key, f"{value:,}")

    console.print(table)

    if "Error" in stats:
        print_error(f"Error accessing {group} data: {stats['Error']}")
        return

    if detailed:
        if "Rank Distribution" in stats:
            rank_table = Table(
                title="\nRank Distribution",
                show_header=True,
                header_style="bold cyan",
                box=box.SIMPLE,
            )
            rank_table.add_column("Rank", style="green")
            rank_table.add_column("Count", justify="right", style="yellow")

            for rank, count in stats["Rank Distribution"].items():
                rank_table.add_row(rank, f"{count:,}")

            console.print(rank_table)

        if "Types" in stats:
            type_table = Table(
                title="\nTypes",
                show_header=True,
                header_style="bold cyan",
                box=box.SIMPLE,
            )
            type_table.add_column("Type", style="green")
            type_table.add_column("Count", justify="right", style="yellow")

            for type_name, count in stats["Types"]:
                type_table.add_row(type_name, f"{count:,}")

            console.print(type_table)


def show_data_exploration_suggestions(db: Database) -> None:
    """Show suggested queries and exploration tips based on the actual database schema."""
    console = Console()

    console.print("\n[bold cyan]🔍 Data Exploration Suggestions[/bold cyan]")
    console.print(
        "Based on your database schema, here are some useful queries and exploration ideas:"
    )

    try:
        # Get all tables
        result = db.execute_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        all_tables = [row[0] for row in result]

        # Check occurrences table structure for custom suggestions
        if "occurrences" in all_tables:
            result = db.execute_sql("PRAGMA table_info(occurrences)")
            occ_columns = [row[1] for row in result]

            console.print("\n[green]📊 Occurrences Data Exploration:[/green]")

            # Suggest column exploration
            console.print(f"  • Your occurrences table has {len(occ_columns)} columns")
            console.print(
                "  • View all columns: [yellow]niamoto stats --group occurrence --detailed[/yellow]"
            )

            # Suggest specific queries based on available columns
            interesting_columns = []

            # Look for family-like columns
            family_cols = [
                col
                for col in occ_columns
                if "fam" in col.lower() or col.lower() == "family"
            ]
            if family_cols:
                family_col = family_cols[0]
                interesting_columns.append(family_col)
                console.print(
                    f"  • Top families: [yellow]SELECT {family_col}, COUNT(*) FROM occurrences GROUP BY {family_col} ORDER BY COUNT(*) DESC LIMIT 10[/yellow]"
                )

            # Look for elevation-like columns
            elevation_cols = [
                col
                for col in occ_columns
                if "elev" in col.lower() or "altitude" in col.lower()
            ]
            if elevation_cols:
                elev_col = elevation_cols[0]
                interesting_columns.append(elev_col)
                console.print(
                    f"  • Elevation distribution: [yellow]SELECT MIN({elev_col}), MAX({elev_col}), AVG({elev_col}) FROM occurrences[/yellow]"
                )

            # Look for numerical columns
            numerical_cols = []
            common_numerical = [
                "dbh",
                "height",
                "wood_density",
                "rainfall",
                "latitude",
                "longitude",
                "stem_diameter",
                "ddlat",
                "ddlon",
            ]
            for col in common_numerical:
                if col in occ_columns:
                    numerical_cols.append(col)

            if numerical_cols:
                console.print(f"  • Found numerical data: {', '.join(numerical_cols)}")
                console.print(
                    f"  • Explore ranges: [yellow]SELECT MIN({numerical_cols[0]}), MAX({numerical_cols[0]}) FROM occurrences[/yellow]"
                )

        # Reference tables exploration
        ref_tables = ["taxon_ref", "plot_ref", "shape_ref"]
        available_refs = [t for t in ref_tables if t in all_tables]

        if available_refs:
            console.print("\n[green]📚 Reference Data Exploration:[/green]")
            for ref_table in available_refs:
                result = db.execute_sql(f"SELECT COUNT(*) FROM {ref_table}")
                count = result.scalar()
                console.print(f"  • {ref_table}: {count:,} records")
                console.print(f"    [yellow]SELECT * FROM {ref_table} LIMIT 5[/yellow]")

        # Generated tables (from transforms)
        generated_tables = [t for t in all_tables if t in ["taxon", "plot", "shape"]]
        if generated_tables:
            console.print("\n[green]🔄 Generated Analysis Tables:[/green]")
            for table in generated_tables:
                result = db.execute_sql(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                console.print(
                    f"  • {table}: {count:,} records (generated from transforms)"
                )
                console.print(f"    [yellow]SELECT * FROM {table} LIMIT 5[/yellow]")

        # Advanced exploration suggestions
        console.print("\n[green]🚀 Advanced Exploration Ideas:[/green]")

        if "occurrences" in all_tables and "taxon_ref" in all_tables:
            console.print("  • Join occurrences with taxonomy:")
            console.print(
                "    [yellow]SELECT tr.full_name, COUNT(*) FROM occurrences o JOIN taxon_ref tr ON o.taxon_ref_id = tr.id GROUP BY tr.full_name[/yellow]"
            )

        if "occurrences" in all_tables and "plot_ref" in all_tables:
            console.print("  • Plot-based analysis:")
            console.print(
                "    [yellow]SELECT pr.locality, COUNT(*) FROM occurrences o JOIN plot_ref pr ON o.plot_ref_id = pr.id GROUP BY pr.locality[/yellow]"
            )

        # Configuration-based suggestions
        console.print("\n[green]⚙️ Configuration Exploration:[/green]")
        console.print(
            "  • View your transform configuration: [yellow]cat config/transform.yml[/yellow]"
        )
        console.print(
            "  • View your export configuration: [yellow]cat config/export.yml[/yellow]"
        )
        console.print("  • Re-run transformations: [yellow]niamoto transform[/yellow]")
        console.print(
            "  • Generate web pages: [yellow]niamoto export web_pages[/yellow]"
        )

        # Export suggestions
        console.print("\n[green]📤 Export Your Analysis:[/green]")
        console.print(
            "  • Export current stats to JSON: [yellow]niamoto stats --export stats.json[/yellow]"
        )
        console.print(
            "  • Export detailed stats: [yellow]niamoto stats --detailed --export detailed_stats.csv[/yellow]"
        )

    except Exception as e:
        console.print(f"[red]Error generating suggestions: {e}[/red]")


def export_statistics(stats: Dict[str, Any], filepath: str) -> None:
    """Export statistics to a file (JSON or CSV)."""
    from pathlib import Path
    import json

    path = Path(filepath)

    if path.suffix.lower() == ".json":
        # Convert any non-serializable objects
        serializable_stats = {}
        for key, value in stats.items():
            if isinstance(value, list) and value and isinstance(value[0], tuple):
                # Convert list of tuples to dict
                serializable_stats[key] = {item[0]: item[1] for item in value}
            else:
                serializable_stats[key] = value

        with open(path, "w") as f:
            json.dump(serializable_stats, f, indent=2)

    elif path.suffix.lower() == ".csv":
        import csv

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Metric", "Value"])

            for key, value in stats.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        writer.writerow([key, sub_key, sub_value])
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, tuple):
                            writer.writerow([key, item[0], item[1]])
                else:
                    writer.writerow(["General", key, value])
    else:
        raise ValueError(f"Unsupported export format: {path.suffix}")
