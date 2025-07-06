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
from ..utils.console import (
    print_error,
    print_info,
    print_start,
    print_operation_metrics,
)
from ..utils.metrics import MetricsCollector
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
@click.option(
    "--with-api/--no-api",
    is_flag=True,
    default=None,
    help="Enable/disable API enrichment (default is from config).",
)
@error_handler(log=True, raise_error=True)
def import_taxonomy(
    with_api: Optional[bool] = None,
) -> None:
    """
    Import taxonomy data from occurrences file.

    Uses the configuration from import.yml.

    Options:
    --with-api: Enable API enrichment (default is from config).
    """
    # Get configuration
    config = Config()

    # Get from config
    source_def = validate_source_config(
        config.imports, "taxonomy", ["path", "hierarchy"]
    )
    file_path = source_def.get("path")
    hierarchy_config = source_def.get("hierarchy")

    # Validate file path first
    if not os.path.exists(file_path):
        raise FileError(
            file_path=file_path, message="File not found", details={"path": file_path}
        )

    # Validate hierarchy configuration
    if not hierarchy_config:
        raise ConfigurationError(
            config_key="taxonomy.hierarchy",
            message="Missing hierarchy configuration",
            details={"expected": "hierarchy configuration with levels"},
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

        result = importer.import_taxonomy(file_path, hierarchy_config, api_config)

        print_info(result)

        if api_config and api_config.get("enabled"):
            print_info("Taxonomy data enriched with API information.")

    except FileError as e:
        raise FileError(
            file_path=file_path,
            message=f"File not found or has invalid format: {e}",
            details={"path": file_path},
        ) from e
    except Exception as e:
        raise DataImportError(
            message=str(e),
            details={"file": file_path},
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
    from datetime import datetime

    start_time = datetime.now()

    print_start("Starting full data import")
    config = Config()

    # Collect all import results for summary
    import_results = []

    try:
        # Create a single ImporterService instance to reuse
        importer = ImporterService(config.database_path)
        imports_config = config.imports

        # Import taxonomy
        source_def = validate_source_config(
            imports_config, "taxonomy", ["path", "hierarchy"]
        )
        file_path = source_def.get("path")
        hierarchy_config = source_def.get("hierarchy")

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

        if not hierarchy_config:
            raise ConfigurationError(
                config_key="taxonomy.hierarchy",
                message="Missing hierarchy configuration for taxonomy extraction",
                details={"expected": "hierarchy configuration with levels"},
            )

        result = importer.import_taxonomy(file_path, hierarchy_config, api_config)

        # Collect result for summary
        import_results.append(result)
        # print_info(result)  # Suppress intermediate output

        # Import occurrences
        source_def = validate_source_config(
            imports_config, "occurrences", ["path", "identifier", "location_field"]
        )
        file_path = get_source_path(config, "occurrences")
        taxon_id = source_def.get("identifier")
        location_field = source_def.get("location_field")

        reset_table(config.database_path, "occurrences")
        result = importer.import_occurrences(file_path, taxon_id, location_field)

        # Collect result for summary
        import_results.append(result)

        # Store linking data if available for final summary
        occurrence_importer = importer.occurrence_importer
        if (
            hasattr(occurrence_importer, "last_linking_data")
            and occurrence_importer.last_linking_data
        ):
            import json

            import_results.append(
                f"LINKING_DATA:{json.dumps(occurrence_importer.last_linking_data)}"
            )

        # print_info(result)  # Suppress intermediate output

        # Import plots
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

        # Collect result for summary
        import_results.append(result)
        # print_info(result)  # Suppress intermediate output

        # Import shapes
        shapes_config = imports_config.get("shapes", [])
        if shapes_config and isinstance(shapes_config, list):
            result = importer.import_shapes(shapes_config)

            # Collect result for summary
            import_results.append(result)
        else:
            pass

        end_time = datetime.now()

        # Parse all import results and create metrics
        linking_data = None
        text_results = []

        for result in import_results:
            if isinstance(result, str) and result.startswith("LINKING_DATA:"):
                # Extract linking data
                import json

                linking_data = json.loads(result.replace("LINKING_DATA:", ""))
            else:
                text_results.append(str(result))

        combined_results = "\n".join(text_results)
        import_metrics = MetricsCollector.parse_import_result(
            combined_results, "import"
        )
        import_metrics.start_time = start_time
        import_metrics.end_time = end_time

        # Display the summary using the same system as transform/export
        print_operation_metrics(import_metrics, "import")

        # Add linking statistics if available
        if linking_data:
            from ..utils.console import print_linking_status, print_unlinked_samples

            stats = linking_data["linking_stats"]
            samples = linking_data["unlinked_samples"]

            print_linking_status(
                stats["total"], stats["linked"], stats["failed"], stats["type"]
            )

            if samples:
                print_unlinked_samples(samples, stats["type"])
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
        required_fields: List of required keys for this source (e.g. ["path", "hierarchy"])

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
