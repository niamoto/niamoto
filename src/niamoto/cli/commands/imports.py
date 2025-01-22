"""
Commands for importing various types of data into Niamoto.
Handles taxonomy, plots, occurrences and other data imports.
"""

import os
from typing import Optional, Dict, Any

import click

from niamoto.common.config import Config
from niamoto.core.services.importer import ImporterService
from ..utils.console import print_success, print_error, print_info
from ...common.database import Database
from ...common.exceptions import (
    ConfigurationError,
    ValidationError,
    FileError,
    DataImportError,
)
from ...common.utils import error_handler
from ...core.models import Base


@click.group(name="import", invoke_without_command=True)
@click.pass_context
@error_handler(log=True, raise_error=True)
def import_commands(ctx):
    """Import data into Niamoto using the configuration file [yellow]import.yml[/yellow]."""
    # If no sub-command is provided, invoke the "all" command
    if ctx.invoked_subcommand is None:
        ctx.invoke(import_all)


@import_commands.command(name="taxonomy")
@click.argument("csvfile", required=False)
@click.option("--ranks", help="Comma-separated list of ranks in the hierarchy.")
@error_handler(log=True, raise_error=True)
def import_taxonomy(csvfile: Optional[str], ranks: Optional[str]) -> None:
    """
    Import taxonomy data from a CSV file.

    If no file is provided, uses the path from import.yml.
    """
    try:
        config = Config()
        source_def = validate_source_config(
            config.imports, "taxonomy", ["path", "ranks"]
        )

        # Get and validate path
        file_path = csvfile or get_source_path(config, "taxonomy")
        rank_list = (ranks or source_def.get("ranks", "")).split(",")

        if not rank_list:
            raise ValidationError(
                field="ranks",
                message="Ranks must be specified",
                details={"source": source_def},
            )

        # Import data
        importer = ImporterService(config.database_path)
        reset_table(config.database_path, "taxon_ref")

        result = importer.import_taxonomy(file_path, tuple(rank_list))
        print_info(result)

    except Exception as e:
        raise DataImportError(
            message="Taxonomy import failed",
            details={"file": csvfile, "ranks": ranks, "error": str(e)},
        )


@import_commands.command(name="plots")
@click.argument("file", required=False)
@click.option("--id-field", help="Name of the ID field.")
@click.option("--location-field", help="Name of the location field.")
@error_handler(log=True, raise_error=True)
def import_plots(
    file: Optional[str], id_field: Optional[str], location_field: Optional[str]
) -> None:
    """
    Import plot data from a file.

    If no file is provided, uses the path from import.yml.

    Raises:
        ConfigurationError: If configuration is invalid
        ValidationError: If required fields are missing
        FileError: If file is not found or invalid
        DataImportError: If import operation fails
    """
    config = Config()
    sources = config.imports

    source_def = validate_source_config(
        sources, "plots", ["path", "identifier", "location_field"]
    )

    file_path = file or get_source_path(config, "plots")
    id_field = id_field or source_def.get("identifier")
    location_field = location_field or source_def.get("location_field")

    if not id_field or not location_field:
        raise ValidationError(
            field="plots",
            message="Missing required fields",
            details={
                "missing": [
                    f
                    for f, v in [
                        ("id_field", id_field),
                        ("location_field", location_field),
                    ]
                    if not v
                ]
            },
        )

    db_path = config.database_path
    importer = ImporterService(db_path)
    reset_table(db_path, "plot_ref")

    try:
        result = importer.import_plots(file_path, id_field, location_field)
        print_info(result)
    except Exception as e:
        raise DataImportError(
            message="Plot import failed",
            details={
                "file": file_path,
                "id_field": id_field,
                "location_field": location_field,
                "error": str(e),
            },
        )


@import_commands.command(name="occurrences")
@click.argument("csvfile", required=False)
@click.option("--taxon-id", help="Name of the taxon ID field.")
@click.option("--location-field", help="Name of the location field.")
@error_handler(log=True, raise_error=True)
def import_occurrences(
    csvfile: Optional[str], taxon_id: Optional[str], location_field: Optional[str]
) -> None:
    """
    Import occurrence data from a CSV file.

    If no file is provided, uses the path from import.yml.

    Raises:
        ConfigurationError: If configuration is invalid
        ValidationError: If required fields are missing
        FileError: If file is not found or invalid
        DataImportError: If import operation fails
    """
    config = Config()
    sources = config.imports

    source_def = validate_source_config(
        sources, "occurrences", ["path", "identifier", "location_field"]
    )

    file_path = csvfile or get_source_path(config, "occurrences")
    taxon_id = taxon_id or source_def.get("identifier")
    location_field = location_field or source_def.get("location_field")

    if not taxon_id or not location_field:
        raise ValidationError(
            field="occurrences",
            message="Missing required fields",
            details={
                "missing": [
                    f
                    for f, v in [
                        ("taxon_id", taxon_id),
                        ("location_field", location_field),
                    ]
                    if not v
                ]
            },
        )

    db_path = config.database_path
    importer = ImporterService(db_path)
    reset_table(db_path, "occurrences")

    try:
        result = importer.import_occurrences(file_path, taxon_id, location_field)
        print_info(result)
    except Exception as e:
        raise DataImportError(
            message="Occurrences import failed",
            details={
                "file": file_path,
                "taxon_id": taxon_id,
                "location_field": location_field,
                "error": str(e),
            },
        )


@import_commands.command(name="occurrence-plots")
@click.argument("csvfile", required=False)
@error_handler(log=True, raise_error=True)
def import_occurrence_plots(csvfile: Optional[str]) -> None:
    """
    Import occurrence-plot links from a CSV file.

    If no file is provided, uses the path from import.yml.

    Raises:
        ConfigurationError: If configuration is invalid
        ValidationError: If required fields are missing
        FileError: If file is not found or invalid
        DataImportError: If import operation fails
    """
    config = Config()
    sources = config.imports

    validate_source_config(
        sources, "occurrence_plots", ["path", "left_key", "right_key"]
    )

    file_path = csvfile or get_source_path(config, "occurrence_plots")

    db_path = config.database_path
    importer = ImporterService(db_path)
    reset_table(db_path, "occurrences_plots")

    try:
        result = importer.import_occurrence_plot_links(file_path)
        print_info(result)
    except Exception as e:
        raise DataImportError(
            message="Occurrence-plot links import failed",
            details={"file": file_path, "error": str(e)},
        )


@import_commands.command(name="shapes")
@error_handler(log=True, raise_error=True)
def import_shapes() -> None:
    """
    Import shape files defined in import.yml.

    Each shape entry in the configuration should specify a category and path.

    Raises:
        ConfigurationError: If configuration is invalid
        ValidationError: If required fields are missing
        FileError: If any shape file is not found or invalid
        DataImportError: If import operation fails
    """
    config = Config()
    sources = config.imports

    shapes_config = sources.get("shapes", [])
    if not shapes_config or not isinstance(shapes_config, list):
        raise ConfigurationError(
            config_key="shapes",
            message="No shapes configuration found or invalid format",
            details={"expected": "list", "got": type(shapes_config).__name__},
        )

    db_path = config.database_path
    importer = ImporterService(db_path)

    try:
        result = importer.import_shapes(shapes_config)
        print_info(result)
    except Exception as e:
        raise DataImportError(
            message="Shapes import failed",
            details={"shapes_config": shapes_config, "error": str(e)},
        )


@import_commands.command(name="all")
@error_handler(log=True, raise_error=True)
def import_all() -> None:
    """
    Import all data sources from configuration.

    Raises:
        DataImportError: If any import operation fails
    """
    print_info("Starting full data import...")
    ctx = click.get_current_context()

    try:
        # Import taxonomy
        ctx.invoke(import_taxonomy)

        # Import plots
        ctx.invoke(import_plots)

        # Import occurrences
        ctx.invoke(import_occurrences)

        # Import occurrence-plot links
        ctx.invoke(import_occurrence_plots)

        # Import shapes
        ctx.invoke(import_shapes)

        print_success("Data import completed")
    except Exception as e:
        raise DataImportError(
            message="Full import failed", details={"last_step": str(e), "error": str(e)}
        )


@error_handler(log=True, raise_error=True)
def validate_source_config(
    sources: Dict[str, Any], source_name: str, required_fields: list
) -> Dict[str, Any]:
    """
    Validate the presence of a specific source definition (source_name)
    in config.imports and check that all required_fields are present.

    Args:
        sources: The dictionary from config.imports
        source_name: e.g. "taxonomy", "plots"
        required_fields: List of required keys for this source (e.g. ["path", "ranks"])

    Returns:
        The source sub-dict from import.yml

    Raises:
        ConfigurationError: If source is not found in configuration
        ValidationError: If required fields are missing
    """
    source = sources.get(source_name)
    if not source:
        raise ConfigurationError(
            config_key=source_name,
            message=f"Source '{source_name}' not found in configuration",
            details={"required_fields": required_fields},
        )

    missing = [field for field in required_fields if field not in source]
    if missing:
        raise ValidationError(
            field=source_name,
            message=f"Missing required fields: {', '.join(missing)}",
            details={
                "missing_fields": missing,
                "required_fields": required_fields,
                "provided_fields": list(source.keys()),
            },
        )

    return source


@error_handler(log=True, raise_error=True)
def get_source_path(config: Config, source_name: str) -> str:
    """
    Retrieve the path from config.imports[source_name]["path"], ensuring
    it's present and converting it to an absolute path if needed.

    Args:
        config: The combined config object (with config.yml & import.yml loaded).
        source_name: e.g. "taxonomy", "plots", "occurrences", etc.

    Returns:
        A valid absolute path to the source file/directory.

    Raises:
        click.UsageError if path is missing or invalid.
    """
    try:
        imports = config.imports
        source_def = imports.get(source_name, {})
        path = source_def.get("path")

        if not path:
            raise ConfigurationError(
                config_key=f"{source_name}.path",
                message="Path not specified",
                details={"source": source_def},
            )

        if not os.path.isabs(path):
            niamoto_home = config.get_niamoto_home()
            path = os.path.join(niamoto_home, path)

        if not os.path.exists(path):
            raise FileError(
                file_path=path,
                message="Source file not found",
                details={"source_name": source_name},
            )

        return path
    except Exception as e:
        raise ConfigurationError(
            config_key=source_name,
            message="Failed to get source path",
            details={"error": str(e)},
        )


def reset_table(db_path: str, table_name: str) -> None:
    """
    Reset a single table and recreate it using SQLAlchemy models if applicable.

    Args:
        db_path (str): The path to the database file.
        table_name (str): The name of the table to reset.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the reset process.
    """
    db = Database(db_path)

    try:
        db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
    except Exception as e:
        print_error(f"Failed to reset table {table_name}: {str(e)}")

    # Recreate the table using SQLAlchemy models if the model exists
    try:
        engine = db.engine

        if table_name in Base.metadata.tables:
            Base.metadata.create_all(engine, tables=[Base.metadata.tables[table_name]])

    except Exception as e:
        print_error(f"Failed to recreate table {table_name}: {str(e)}")
