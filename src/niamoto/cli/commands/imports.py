"""
Commands for importing various types of data into Niamoto.
Handles taxonomy, plots, occurrences and other data imports.
"""

import os
from typing import Optional, Dict, Any

import click
from sqlalchemy.exc import SQLAlchemyError

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
@click.option(
    "--source",
    type=click.Choice(["file", "occurrence"]),
    help="Source of taxonomy data: 'file' (default) or 'occurrence'.",
)
@click.option(
    "--with-api/--no-api",
    is_flag=True,
    default=None,
    help="Enable/disable API enrichment (default is from config).",
)
@error_handler(log=True, raise_error=True)
def import_taxonomy(
    csvfile: Optional[str],
    ranks: Optional[str],
    source: Optional[str] = None,
    with_api: Optional[bool] = None,
) -> None:
    """
    Import taxonomy data from a CSV file or extract from occurrences.

    If no file is provided, uses the path from import.yml.

    Options:
    --source: Specify the source of taxonomy data ('file' or 'occurrence').
    If 'occurrence', taxonomy will be extracted from occurrence data.
    --with-api: Enable API enrichment (default is from config).
    """
    # Get configuration
    config = Config()

    # If using explicit arguments
    if csvfile is not None:
        file_path = csvfile
        rank_list = ranks.split(",") if ranks else []
        tax_source = source or "file"
    else:
        # Get from config
        source_def = validate_source_config(
            config.imports, "taxonomy", ["path", "ranks"]
        )
        file_path = source_def.get("path")
        rank_list = source_def.get("ranks", "").split(",")
        tax_source = source_def.get("source", "file")

    # Validate file path first
    if not os.path.exists(file_path):
        raise FileError(
            file_path=file_path, message="File not found", details={"path": file_path}
        )

    # Validate ranks
    if not rank_list or not any(rank_list):
        raise ValidationError(
            field="taxonomy",
            message="Missing required fields: ranks",
            details={"missing": ["ranks"]},
        )

    api_config = None
    source_def = config.imports.get("taxonomy", {})

    if with_api is not None:  # CLI flag provided
        if with_api:  # CLI flag set to enable
            api_config = source_def.get("api_enrichment", {})
            if not api_config:
                print_error(
                    "API enrichment enabled but no configuration found in import.yml"
                )
            else:
                api_config["enabled"] = True
        else:  # CLI flag set to disable
            api_config = {"enabled": False}
    elif source_def.get("api_enrichment", {}).get(
        "enabled", False
    ):  # Use config file setting
        api_config = source_def.get("api_enrichment", {})
        api_config["enabled"] = True

    # Import data
    try:
        importer = ImporterService(config.database_path)
        reset_table(config.database_path, "taxon_ref")

        if tax_source == "occurrence":
            # Get occurrence columns mapping from config
            occ_columns = source_def.get("occurrence_columns", {})

            if not occ_columns:
                print_error(
                    "Missing occurrence_columns configuration for taxonomy extraction from occurrences"
                )
                print_info("Example configuration:")
                print_info(
                    """
                    taxonomy:
                    type: csv
                    path: "imports/occurrences.csv"
                    source: "occurrence"
                    ranks: "family,genus,species,infra"
                    occurrence_columns:
                        taxon_id: "id_taxonref"
                        family: "family"
                        genus: "genus"
                        species: "species"
                        infra: "infra"
                        authors: "taxonref"
                """
                )
                raise ConfigurationError(
                    config_key="taxonomy.occurrence_columns",
                    message="Missing occurrence columns mapping configuration",
                    details={
                        "expected": "dictionary mapping taxonomy fields to occurrence columns"
                    },
                )

            result = importer.import_taxonomy_from_occurrences(
                file_path, tuple(rank_list), occ_columns, api_config
            )
        else:  # Default to file
            result = importer.import_taxonomy(file_path, tuple(rank_list), api_config)

        print_info(result)

        if api_config and api_config.get("enabled"):
            print_info("Taxonomy data enriched with API information.")

    except FileError as e:
        raise FileError(
            file_path=file_path,
            message=f"File not found or has invalid format: {e}",
            details={"path": file_path, "ranks": ranks},
        ) from e
    except Exception as e:
        raise DataImportError(
            message=str(e),
            details={"file": file_path, "ranks": ranks, "source": tax_source},
        ) from e


@import_commands.command(name="plots")
@click.argument("file", required=False)
@click.option("--id-field", help="Name of the ID field.")
@click.option("--location-field", help="Name of the location field.")
@click.option("--locality-field", help="Name of the locality field.")
@click.option(
    "--link-field", help="Field in plot_ref to use for linking with occurrences."
)
@click.option(
    "--occurrence-link-field",
    help="Field in occurrences to use for linking with plots.",
)
@error_handler(log=True, raise_error=True)
def import_plots(
    file: Optional[str],
    id_field: Optional[str],
    location_field: Optional[str],
    locality_field: Optional[str],
    link_field: Optional[str],
    occurrence_link_field: Optional[str],
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
        sources, "plots", ["path", "identifier", "location_field", "locality_field"]
    )

    file_path = file or get_source_path(config, "plots")
    id_field = id_field or source_def.get("identifier")
    location_field = location_field or source_def.get("location_field")
    locality_field = locality_field or source_def.get("locality_field")
    link_field = link_field or source_def.get("link_field")
    occurrence_link_field = occurrence_link_field or source_def.get(
        "occurrence_link_field"
    )

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

    # Check for hierarchical configuration
    hierarchy_config = source_def.get("hierarchy")

    try:
        result = importer.import_plots(
            file_path,
            id_field,
            location_field,
            locality_field,
            link_field=link_field,
            occurrence_link_field=occurrence_link_field,
            hierarchy_config=hierarchy_config,
        )
        print_info(result)
    except Exception as e:
        raise DataImportError(
            "Failed to import plots",
            details={"error": str(e)},
        ) from e


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
        ) from e


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
        ) from e


@import_commands.command(name="all")
@error_handler(log=True, raise_error=True)
def import_all() -> None:
    """
    Import all data sources from configuration.

    Raises:
        DataImportError: If any import operation fails
    """
    print_info("Starting full data import...")
    config = Config()

    try:
        # Create a single ImporterService instance to reuse
        importer = ImporterService(config.database_path)
        imports_config = config.imports

        # Import taxonomy
        print_info("Importing taxonomy...")
        source_def = validate_source_config(
            imports_config, "taxonomy", ["path", "ranks"]
        )
        file_path = source_def.get("path")
        rank_list = source_def.get("ranks", "").split(",")
        tax_source = source_def.get("source", "file")

        # Validate file path first
        if not os.path.exists(file_path):
            raise FileError(
                file_path=file_path,
                message="File not found",
                details={"path": file_path},
            )

        api_config = None
        if source_def.get("api_enrichment", {}).get("enabled", False):
            api_config = source_def.get("api_enrichment", {})
            api_config["enabled"] = True

        reset_table(config.database_path, "taxon_ref")

        if tax_source == "occurrence":
            occ_columns = source_def.get("occurrence_columns", {})
            if not occ_columns:
                raise ConfigurationError(
                    config_key="taxonomy.occurrence_columns",
                    message="Missing occurrence columns mapping configuration",
                    details={
                        "expected": "dictionary mapping taxonomy fields to occurrence columns"
                    },
                )
            result = importer.import_taxonomy_from_occurrences(
                file_path, tuple(rank_list), occ_columns, api_config
            )
        else:
            result = importer.import_taxonomy(file_path, tuple(rank_list), api_config)
        print_info(result)

        # Import occurrences
        print_info("Importing occurrences...")
        source_def = validate_source_config(
            imports_config, "occurrences", ["path", "identifier", "location_field"]
        )
        file_path = get_source_path(config, "occurrences")
        taxon_id = source_def.get("identifier")
        location_field = source_def.get("location_field")

        reset_table(config.database_path, "occurrences")
        result = importer.import_occurrences(file_path, taxon_id, location_field)
        print_info(result)

        # Import plots
        print_info("Importing plots...")
        source_def = validate_source_config(
            imports_config,
            "plots",
            ["path", "identifier", "location_field", "locality_field"],
        )
        file_path = get_source_path(config, "plots")
        id_field = source_def.get("identifier")
        location_field = source_def.get("location_field")
        locality_field = source_def.get("locality_field")
        link_field = source_def.get("link_field")
        occurrence_link_field = source_def.get("occurrence_link_field")

        reset_table(config.database_path, "plot_ref")

        # Check for hierarchical configuration
        hierarchy_config = source_def.get("hierarchy")

        result = importer.import_plots(
            file_path,
            id_field,
            location_field,
            locality_field,
            link_field=link_field,
            occurrence_link_field=occurrence_link_field,
            hierarchy_config=hierarchy_config,
        )
        print_info(result)

        # Import shapes
        print_info("Importing shapes...")
        shapes_config = imports_config.get("shapes", [])
        if shapes_config and isinstance(shapes_config, list):
            result = importer.import_shapes(shapes_config)
            print_info(result)
        else:
            print_info("No shapes configured, skipping")

        print_success("Data import completed")
    except Exception as e:
        raise DataImportError(
            message="Full import failed", details={"error": str(e)}
        ) from e


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
        ) from e


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
    except SQLAlchemyError as e:
        print_error(f"Failed to reset table {table_name}: {str(e)}")

    # Recreate the table using SQLAlchemy models if the model exists
    try:
        engine = db.engine

        if table_name in Base.metadata.tables:
            Base.metadata.create_all(engine, tables=[Base.metadata.tables[table_name]])

    except SQLAlchemyError as e:
        print_error(f"Failed to recreate table {table_name}: {str(e)}")
