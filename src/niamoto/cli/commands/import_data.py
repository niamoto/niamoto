"""
Commands for importing various types of data into Niamoto.
Handles taxonomy, plots, occurrences and other data imports.
"""

import os
from typing import Optional, Dict, Any

import click

from ..utils.console import print_success, print_error, print_info
from ..utils.validators import validate_csv_file
from ..utils.database import reset_table
from niamoto.common.config import Config  # The updated Config class
from niamoto.core.services.importer import ImporterService


def validate_source_config(
    sources: Dict[str, Any], source_name: str, required_fields: list
) -> Dict[str, Any]:
    """
    Validate the presence of a specific source definition (source_name)
    in config.sources and check that all required_fields are present.

    Args:
        sources: The dictionary from config.sources
        source_name: e.g. "taxonomy", "plots"
        required_fields: List of required keys for this source (e.g. ["path", "ranks"])

    Returns:
        The source sub-dict from sources.yml

    Raises:
        click.UsageError: If configuration is invalid or missing required fields
    """
    source = sources.get(source_name)
    if not source:
        raise click.UsageError(
            f"No configuration found for source '{source_name}' in sources.yml"
        )

    missing = [field for field in required_fields if field not in source]
    if missing:
        raise click.UsageError(
            f"Missing required fields for '{source_name}': {', '.join(missing)}"
        )

    return source


def get_source_path(config: Config, source_name: str) -> str:
    """
    Retrieve the path from config.sources[source_name]["path"], ensuring
    it's present and converting it to an absolute path if needed.

    Args:
        config: The combined config object (with config.yml & sources.yml loaded).
        source_name: e.g. "taxonomy", "plots", "occurrences", etc.

    Returns:
        A valid absolute path to the source file/directory.

    Raises:
        click.UsageError if path is missing or invalid.
    """
    # Pull the entire sources dictionary
    sources = config.sources
    source_def = sources.get(source_name, {})
    path = source_def.get("path")

    if not path:
        raise click.UsageError(f"No path specified for '{source_name}' in sources.yml")

    # Convert to absolute path if it's relative
    if not os.path.isabs(path):
        niamoto_home = config.get_niamoto_home()
        path = os.path.join(niamoto_home, path)

    if not os.path.exists(path):
        raise click.UsageError(f"Path not found for '{source_name}': {path}")

    return path


@click.group(name="import")
def import_commands():
    """Commands for importing data into Niamoto."""
    pass


@import_commands.command(name="taxonomy")
@click.argument("csvfile", required=False)
@click.option("--ranks", help="Comma-separated list of ranks in the hierarchy.")
def import_taxonomy(csvfile: Optional[str], ranks: Optional[str]) -> None:
    """
    Import taxonomy data from a CSV file.

    If no file is provided, uses the path from sources.yml.
    """
    try:
        # Load the multi-file config (which includes config.yml + sources.yml)
        config = Config()
        sources = config.sources

        source_def = validate_source_config(sources, "taxonomy", ["path", "ranks"])
        # If user didn't provide a CSV file, we get path from sources.yml
        if not csvfile:
            csvfile = get_source_path(config, "taxonomy")

        # Ranks from either CLI or sources.yml
        ranks = ranks or source_def.get("ranks")
        if not ranks:
            raise click.UsageError(
                "Ranks must be specified (either via --ranks or in sources.yml)"
            )

        # Validate the CSV structure
        validate_csv_file(csvfile, ranks.split(","))

        # Database path from config.yml
        db_path = config.database_path
        importer = ImporterService(db_path)

        # Drop and recreate table in DB
        reset_table(db_path, "taxon_ref")

        result = importer.import_taxonomy(csvfile, tuple(ranks.split(",")))
        print_success(result)

    except Exception as e:
        print_error(f"Taxonomy import failed: {str(e)}")
        raise click.Abort()


@import_commands.command(name="plots")
@click.argument("file", required=False)
@click.option("--id-field", help="Name of the ID field.")
@click.option("--location-field", help="Name of the location field.")
def import_plots(
    file: Optional[str], id_field: Optional[str], location_field: Optional[str]
) -> None:
    """Import plot data."""
    try:
        config = Config()
        sources = config.sources

        source_def = validate_source_config(
            sources, "plots", ["path", "identifier", "location_field"]
        )

        if not file:
            file = get_source_path(config, "plots")

        id_field = id_field or source_def.get("identifier")
        location_field = location_field or source_def.get("location_field")

        db_path = config.database_path
        importer = ImporterService(db_path)
        reset_table(db_path, "plot_ref")

        result = importer.import_plots(file, id_field, location_field)
        print_success(result)

    except Exception as e:
        print_error(f"Plot import failed: {str(e)}")
        raise click.Abort()


@import_commands.command(name="occurrences")
@click.argument("csvfile", required=False)
@click.option("--taxon-id", help="Name of the taxon ID field.")
@click.option("--location-field", help="Name of the location field.")
def import_occurrences(
    csvfile: Optional[str], taxon_id: Optional[str], location_field: Optional[str]
) -> None:
    """Import occurrence data."""
    try:
        config = Config()
        sources = config.sources

        source_def = validate_source_config(
            sources, "occurrences", ["path", "identifier", "location_field"]
        )

        if not csvfile:
            csvfile = get_source_path(config, "occurrences")

        taxon_id = taxon_id or source_def.get("identifier")
        location_field = location_field or source_def.get("location_field")

        db_path = config.database_path
        importer = ImporterService(db_path)
        reset_table(db_path, "occurrences")

        result = importer.import_occurrences(csvfile, taxon_id, location_field)
        print_success(result)

    except Exception as e:
        print_error(f"Occurrences import failed: {str(e)}")
        raise click.Abort()


@import_commands.command(name="occurrence-plots")
@click.argument("csvfile", required=False)
def import_occurrence_plots(csvfile: Optional[str]) -> None:
    """Import occurrence-plot links."""
    try:
        config = Config()
        sources = config.sources

        source_def = validate_source_config(
            sources, "occurrence_plots", ["path", "left_key", "right_key"]
        )

        if not csvfile:
            csvfile = get_source_path(config, "occurrence_plots")

        db_path = config.database_path
        importer = ImporterService(db_path)
        reset_table(db_path, "occurrences_plots")

        result = importer.import_occurrence_plot_links(csvfile)
        print_success(result)

    except Exception as e:
        print_error(f"Occurrence-plot links import failed: {str(e)}")
        raise click.Abort()


@import_commands.command(name="shapes")
def import_shapes() -> None:
    """Import shape files defined in sources.yml (e.g. multiple categories)."""
    try:
        config = Config()
        sources = config.sources

        # Suppose shapes are a list under sources["shapes"], each with {category, path, etc.}
        shapes_config = sources.get("shapes", [])
        if not shapes_config or not isinstance(shapes_config, list):
            raise click.UsageError(
                "No shapes configuration found in sources.yml under 'shapes'"
            )

        db_path = config.database_path
        importer = ImporterService(db_path)
        # reset_table(db_path, "shape_ref")

        result = importer.import_shapes(shapes_config)
        print_success(result)

    except Exception as e:
        print_error(f"Shapes import failed: {str(e)}")
        raise click.Abort()


@import_commands.command(name="all")
def import_all() -> None:
    """Import all data sources from configuration."""
    try:
        print_info("Starting full data import...")

        # Reuse context to sequentially call sub-commands
        ctx = click.get_current_context()

        ctx.invoke(import_taxonomy)
        print_info("Taxonomy import completed")

        ctx.invoke(import_plots)
        print_info("Plots import completed")

        ctx.invoke(import_occurrences)
        print_info("Occurrences import completed")

        ctx.invoke(import_occurrence_plots)
        print_info("Occurrence-plot links import completed")

        ctx.invoke(import_shapes)
        print_info("Shapes import completed")

        print_success("All data imported successfully")

    except Exception as e:
        print_error(f"Full import failed: {str(e)}")
        raise click.Abort()
