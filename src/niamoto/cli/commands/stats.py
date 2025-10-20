"""
Commands for displaying statistics about the Niamoto database.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import DatabaseError, DatabaseQueryError
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.imports.registry import EntityRegistry, EntityKind, EntityMetadata
from sqlalchemy import inspect

from ..utils.console import print_info, print_error

from string import ascii_letters, digits

_ALLOWED_IDENTIFIER_CHARS = set(ascii_letters + digits + "_- ")
_UNQUOTED_IDENTIFIER_CHARS = set(ascii_letters + digits + "_")


def _quote_identifier(identifier: str) -> str:
    """Safely quote SQL identifiers (tables/columns)."""
    if not identifier:
        raise ValueError("Identifier cannot be empty")

    parts = identifier.split(".")
    quoted_parts: List[str] = []
    needs_quotes_overall = False

    for part in parts:
        if not part:
            raise ValueError(f"Invalid identifier segment in '{identifier}'")
        if any(ch not in _ALLOWED_IDENTIFIER_CHARS for ch in part):
            raise ValueError(f"Invalid characters in identifier '{identifier}'")
        escaped = part.replace('"', '""')
        if any(ch not in _UNQUOTED_IDENTIFIER_CHARS for ch in part):
            needs_quotes_overall = True
        quoted_parts.append(escaped if escaped else part)

    if not needs_quotes_overall:
        return ".".join(quoted_parts)

    return ".".join(f'"{part}"' for part in quoted_parts)


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
        registry = EntityRegistry(db)

        # Get statistics based on options
        if group:
            stats = get_group_statistics(db, registry, group, detailed)
            display_group_statistics(stats, group, detailed)
        else:
            stats = get_general_statistics(db, registry, detailed)
            display_general_statistics(stats, detailed)

        # Export if requested
        if export:
            export_statistics(stats, export)
            print_info(f"Statistics exported to {export}")

        # Show suggestions if requested
        if suggestions:
            show_data_exploration_suggestions(db, registry)

    except DatabaseError as e:
        if not getattr(e, "_handled", False):
            print_error(f"Database error: {str(e)}")
    except Exception as e:
        if not getattr(e, "_handled", False):
            print_error(f"Unexpected error: {str(e)}")


def get_general_statistics(
    db: Database, registry: EntityRegistry, detailed: bool = False
) -> Dict[str, Any]:
    """Get general statistics about all data in the database."""

    stats: Dict[str, Any] = {}
    try:
        all_tables = set(_list_tables(db))
    except Exception:
        all_tables = set()

    references = registry.list_entities(EntityKind.REFERENCE)
    datasets = registry.list_entities(EntityKind.DATASET)

    shape_table = None
    occ_table = None

    for metadata in references:
        table_name = getattr(metadata, "table_name", None)
        if not table_name or table_name not in all_tables:
            continue

        label = metadata.config.get("description") if metadata.config else None
        if not label:
            name_base = (
                metadata.name[:-4] if metadata.name.endswith("_ref") else metadata.name
            )
            label = name_base.replace("_", " ").title()
        display_name = f"Reference {label}".strip()

        try:
            quoted_table = _quote_identifier(table_name)
            result = db.execute_sql(f"SELECT COUNT(*) FROM {quoted_table}")
            count = result.scalar() if result is not None else 0
        except Exception:
            count = 0
        stats[display_name] = count

        if "shape" in metadata.name.lower():
            shape_table = table_name

    for metadata in datasets:
        table_name = getattr(metadata, "table_name", None)
        if not table_name or table_name not in all_tables:
            continue

        label = metadata.config.get("description") if metadata.config else None
        if not label:
            name_base = metadata.name
            label = name_base.replace("_", " ").title()
        display_name = f"Dataset {label}".strip()

        try:
            quoted_table = _quote_identifier(table_name)
            result = db.execute_sql(f"SELECT COUNT(*) FROM {quoted_table}")
            count = result.scalar() if result is not None else 0
        except Exception:
            count = 0
        stats[display_name] = count

        if metadata.name.lower() in {"occurrences", "occurrence"}:
            occ_table = table_name

    generated_tables = [
        table
        for table in all_tables
        if table
        not in {
            m.table_name
            for m in references + datasets
            if getattr(m, "table_name", None)
        }
    ]
    if generated_tables:
        stats["Generated Tables"] = {}
        for table in generated_tables:
            try:
                quoted_table = _quote_identifier(table)
                result = db.execute_sql(f"SELECT COUNT(*) FROM {quoted_table}")
                count = result.scalar() if result is not None else 0
            except Exception:
                count = 0
            stats["Generated Tables"][table] = count

    if shape_table and shape_table in all_tables:
        try:
            columns = db.get_table_columns(shape_table)
            if "type" in columns:
                quoted_table = _quote_identifier(shape_table)
                type_column = _quote_identifier("type")
                result = db.execute_sql(
                    f"SELECT {type_column}, COUNT(*) as count FROM {quoted_table} "
                    f"WHERE {type_column} IS NOT NULL GROUP BY {type_column} ORDER BY count DESC"
                )
                shape_types = {row.type: row.count for row in result}
                if shape_types:
                    stats["Shape Types"] = shape_types
        except Exception:
            pass

    if detailed and occ_table and occ_table in all_tables:
        if occ_table in all_tables:
            try:
                columns = db.get_table_columns(occ_table)
                if "family" in columns:
                    quoted_table = _quote_identifier(occ_table)
                    family_column = _quote_identifier("family")
                    result = db.execute_sql(
                        f"SELECT {family_column}, COUNT(*) as count FROM {quoted_table} "
                        f"WHERE {family_column} IS NOT NULL GROUP BY {family_column} "
                        "ORDER BY count DESC LIMIT 10"
                    )
                    families = [(row.family, row.count) for row in result]
                    if families:
                        stats["Top Families"] = families
            except Exception:
                pass

            try:
                columns = db.get_table_columns(occ_table)
                if "elevation" in columns:
                    quoted_table = _quote_identifier(occ_table)
                    elevation_column = _quote_identifier("elevation")
                    result = db.execute_sql(
                        f"SELECT MIN({elevation_column}) as min_elev, "
                        f"MAX({elevation_column}) as max_elev, "
                        f"AVG({elevation_column}) as avg_elev, "
                        f"COUNT({elevation_column}) as count_with_elev "
                        f"FROM {quoted_table} WHERE {elevation_column} IS NOT NULL"
                    )
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

            try:
                columns = db.get_table_columns(occ_table)
                numerical_cols = [
                    col
                    for col in ["dbh", "height", "wood_density", "rainfall"]
                    if col in columns
                ]
                if numerical_cols:
                    stats["Numerical Data"] = {}
                    quoted_table = _quote_identifier(occ_table)
                    for col in numerical_cols:
                        quoted_column = _quote_identifier(col)
                        result = db.execute_sql(
                            f"SELECT COUNT({quoted_column}) as count_non_null, "
                            f"MIN({quoted_column}) as min_val, "
                            f"MAX({quoted_column}) as max_val, "
                            f"AVG({quoted_column}) as avg_val "
                            f"FROM {quoted_table}"
                        )
                        row = result.first()
                        if row and row.count_non_null:
                            stats["Numerical Data"][col] = {
                                "Count": f"{row.count_non_null:,}",
                                "Range": f"{row.min_val:.2f} - {row.max_val:.2f}",
                                "Average": f"{row.avg_val:.2f}",
                            }
            except Exception:
                pass

    return stats


def get_group_statistics(
    db: Database, registry: EntityRegistry, group: str, detailed: bool = False
) -> Dict[str, Any]:
    """Get statistics for a specific group."""

    stats: Dict[str, Any] = {}
    tables = set(_list_tables(db))

    table_map = {
        "taxon": "taxon_ref",
        "plot": "plot_ref",
        "shape": "shape_ref",
        "occurrence": "occurrences",
    }

    logical_name = table_map.get(group, f"{group}_stats")
    table_name = _resolve_table_name(logical_name, registry)

    if table_name not in tables:
        stats["Error"] = f"Table '{table_name}' not found"
        return stats

    try:
        quoted_table = _quote_identifier(table_name)
        result = db.execute_sql(f"SELECT COUNT(*) FROM {quoted_table}")
        stats["Total Count"] = result.scalar() if result is not None else 0

        columns = db.get_table_columns(table_name)
        stats["Columns"] = len(columns)

        if detailed:
            stats["Column Names"] = columns

            if group == "taxon":
                rank_column = _quote_identifier("rank_name")
                result = db.execute_sql(
                    f"SELECT {rank_column} as rank, COUNT(*) as count FROM {quoted_table} "
                    f"WHERE {rank_column} IS NOT NULL "
                    f"GROUP BY {rank_column} ORDER BY count DESC"
                )
                stats["Rank Distribution"] = {row.rank: row.count for row in result}
            elif group == "shape":
                type_column = _quote_identifier("type")
                result = db.execute_sql(
                    f"SELECT {type_column}, COUNT(*) as count FROM {quoted_table} "
                    f"WHERE {type_column} IS NOT NULL GROUP BY {type_column} ORDER BY count DESC"
                )
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

    reference_entries = {
        key: value for key, value in stats.items() if key.startswith("Reference ")
    }
    dataset_entries = {
        key: value for key, value in stats.items() if key.startswith("Dataset ")
    }

    for key in sorted(reference_entries.keys()):
        table.add_row(key, f"{reference_entries[key]:,}")

    for key in sorted(dataset_entries.keys()):
        table.add_row(key, f"{dataset_entries[key]:,}")

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
        if key not in [
            "Column Names",
            "Rank Distribution",
            "Categories",
            "Error",
            "Types",
        ]:
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


def show_data_exploration_suggestions(db: Database, registry: EntityRegistry) -> None:
    """Show suggested queries and exploration tips based on the current schema."""

    console = Console()
    console.print("\n[bold cyan]🔍 Data Exploration Suggestions[/bold cyan]")
    console.print(
        "Based on your database schema, here are some useful queries and exploration ideas:"
    )

    try:
        all_tables = set(_list_tables(db))
    except Exception:
        all_tables = set()

    dataset_entities = registry.list_entities(EntityKind.DATASET)
    reference_entities = registry.list_entities(EntityKind.REFERENCE)
    occ_entity = _pick_occurrence_entity(registry, dataset_entities)

    if occ_entity and occ_entity.table_name in all_tables:
        label = _format_entity_label(occ_entity.name)
        occ_table = occ_entity.table_name
        columns = db.get_table_columns(occ_table)

        console.print(f"\n[green]📊 {label} Data Exploration:[/green]")
        console.print(f"  • Your {label.lower()} table has {len(columns)} columns")
        console.print(
            "  • View all columns: [yellow]niamoto stats --group occurrence --detailed[/yellow]"
        )

        family_columns = [
            col for col in columns if "fam" in col.lower() or col.lower() == "family"
        ]
        if family_columns:
            family_col = family_columns[0]
            console.print(
                "  • Top families: [yellow]SELECT {col}, COUNT(*) FROM {table} "
                "GROUP BY {col} ORDER BY COUNT(*) DESC LIMIT 10[/yellow]".format(
                    col=family_col, table=occ_table
                )
            )

        elevation_columns = [
            col for col in columns if "elev" in col.lower() or "altitude" in col.lower()
        ]
        if elevation_columns:
            elev_col = elevation_columns[0]
            console.print(
                "  • Elevation distribution: [yellow]SELECT MIN({col}), MAX({col}), "
                "AVG({col}) FROM {table}[/yellow]".format(col=elev_col, table=occ_table)
            )

        numerical_candidates = [
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
        numerical_cols = [col for col in numerical_candidates if col in columns]
        if numerical_cols:
            console.print(f"  • Found numerical data: {', '.join(numerical_cols)}")
            console.print(
                "  • Explore ranges: [yellow]SELECT MIN({col}), MAX({col}) FROM {table}[/yellow]".format(
                    col=numerical_cols[0], table=occ_table
                )
            )

    elif dataset_entities:
        label = _format_entity_label(dataset_entities[0].name)
        console.print(
            f"\n[green]📊 {label} Data Exploration:[/green]\n  • Table not yet available in the current schema"
        )

    available_refs = [
        entity for entity in reference_entities if entity.table_name in all_tables
    ]
    if available_refs:
        console.print("\n[green]📚 Reference Data Exploration:[/green]")
        for entity in available_refs:
            try:
                quoted_table = _quote_identifier(entity.table_name)
                result = db.execute_sql(f"SELECT COUNT(*) FROM {quoted_table}")
                count = result.scalar() if result is not None else 0
            except Exception:
                count = 0
            console.print(f"  • {entity.table_name}: {count:,} records")
            console.print(
                f"    [yellow]SELECT * FROM {entity.table_name} LIMIT 5[/yellow]"
            )

    generated_tables = [t for t in all_tables if t in {"taxon", "plot", "shape"}]
    if generated_tables:
        console.print("\n[green]🔄 Generated Analysis Tables:[/green]")
        for table in generated_tables:
            try:
                quoted_table = _quote_identifier(table)
                result = db.execute_sql(f"SELECT COUNT(*) FROM {quoted_table}")
                count = result.scalar() if result is not None else 0
            except Exception:
                count = 0
            console.print(f"  • {table}: {count:,} records (generated from transforms)")
            console.print(f"    [yellow]SELECT * FROM {table} LIMIT 5[/yellow]")

    console.print("\n[green]🚀 Advanced Exploration Ideas:[/green]")

    if occ_entity and occ_entity.table_name in all_tables:
        taxon_table = _resolve_table_name("taxon_ref", registry)
        if taxon_table in all_tables:
            console.print("  • Join occurrences with taxonomy:")
            console.print(
                "    [yellow]SELECT tr.full_name, COUNT(*) FROM {occ} o "
                "JOIN {tax} tr ON o.taxon_ref_id = tr.id GROUP BY tr.full_name[/yellow]".format(
                    occ=occ_entity.table_name,
                    tax=taxon_table,
                )
            )

        plot_table = _resolve_table_name("plot_ref", registry)
        if plot_table in all_tables:
            console.print("  • Plot-based analysis:")
            console.print(
                "    [yellow]SELECT pr.locality, COUNT(*) FROM {occ} o JOIN {plot} pr "
                "ON o.plot_ref_id = pr.id GROUP BY pr.locality[/yellow]".format(
                    occ=occ_entity.table_name,
                    plot=plot_table,
                )
            )

    console.print("\n[green]⚙️ Configuration Exploration:[/green]")
    console.print(
        "  • View your transform configuration: [yellow]cat config/transform.yml[/yellow]"
    )
    console.print(
        "  • View your export configuration: [yellow]cat config/export.yml[/yellow]"
    )
    console.print("  • Re-run transformations: [yellow]niamoto transform[/yellow]")
    console.print("  • Generate web pages: [yellow]niamoto export web_pages[/yellow]")

    console.print("\n[green]📤 Export Your Analysis:[/green]")
    console.print(
        "  • Export current stats to JSON: [yellow]niamoto stats --export stats.json[/yellow]"
    )
    console.print(
        "  • Export detailed stats: [yellow]niamoto stats --detailed --export detailed_stats.csv[/yellow]"
    )


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


def _list_tables(db: Database) -> List[str]:
    """Return list of table names using SQLAlchemy inspector."""

    try:
        inspector = inspect(db.engine)
        return inspector.get_table_names()
    except Exception:
        return []


def _resolve_table_name(logical_name: str, registry: EntityRegistry) -> str:
    """Resolve a logical entity name to its physical table name."""
    candidates = [logical_name]

    if logical_name.endswith("_ref"):
        base = logical_name[: -len("_ref")]
        candidates.append(base)
        candidates.append(f"{base}s")
        candidates.append(f"{base}es")

    if logical_name.startswith("entity_"):
        candidates.append(logical_name[len("entity_") :])
    if logical_name.startswith("dataset_"):
        candidates.append(logical_name[len("dataset_") :])

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            metadata = registry.get(candidate)
            table_name = getattr(metadata, "table_name", None)
            if table_name:
                return table_name
        except DatabaseQueryError:
            continue

    return logical_name


def _pick_occurrence_entity(
    registry: EntityRegistry, datasets: Optional[List[EntityMetadata]] = None
) -> Optional[EntityMetadata]:
    """Return the dataset entity to use for occurrences-like suggestions."""

    datasets = datasets or registry.list_entities(EntityKind.DATASET)
    for candidate in ("occurrences", "occurrence", "observations"):
        try:
            return registry.get(candidate)
        except DatabaseQueryError:
            continue
    return datasets[0] if datasets else None


def _format_entity_label(name: str) -> str:
    """Return a human readable label for an entity name."""

    return name.replace("_", " ").strip().title() if name else "Entity"
