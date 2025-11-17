"""
Generic import commands using the entity registry and typed configurations.
"""

from datetime import datetime

import click

from niamoto.common.config import Config
from niamoto.core.services.importer import ImporterService
from niamoto.common.progress import set_progress_mode
from niamoto.common.utils.emoji import emoji
from ..utils.console import (
    print_error,
    print_info,
    print_start,
    print_success,
)
from ...common.exceptions import (
    ConfigurationError,
    DataImportError,
)
from ...common.utils import error_handler


@click.group(name="import", invoke_without_command=True)
@click.pass_context
@error_handler(log=True, raise_error=True)
def import_commands(ctx):
    """Import data using generic configuration from [yellow]import.yml[/yellow]."""
    # If no sub-command is provided, invoke the "run" command
    if ctx.invoked_subcommand is None:
        ctx.invoke(import_run)


@import_commands.command(name="run")
@click.option(
    "--reset-table/--no-reset-table",
    default=False,
    help="Drop and recreate tables before import",
)
@error_handler(log=True, raise_error=True)
def import_run(reset_table: bool = False) -> None:
    """
    Import all entities from import.yml configuration.

    This command reads the generic entities.references and entities.datasets
    configuration and imports all defined entities.

    Options:
        --reset-table: Drop and recreate tables before import (default: False)
    """
    # Enable progress bars for CLI
    set_progress_mode(use_progress_bar=True)

    start_time = datetime.now()
    print_start("Starting generic entity import")

    try:
        # Load configuration
        config = Config()
        generic_config = config.get_imports_config

        # Initialize importer service
        importer = ImporterService(config.database_path)

        # Import all entities
        result = importer.import_all(generic_config, reset_table=reset_table)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print_success(f"\n{result}")
        print_info(f"\n{emoji('⏱️', '[T]')}  Total duration: {duration:.2f}s")

    except ConfigurationError as e:
        print_error(
            f"Configuration error: {e.message}\n"
            f"Details: {e.details}\n"
            f"Hint: Ensure import.yml follows the entities.references/datasets schema"
        )
        raise
    except Exception as e:
        raise DataImportError(
            message="Import failed",
            details={"error": str(e)},
        ) from e


@import_commands.command(name="reference")
@click.argument("name")
@click.option(
    "--reset-table/--no-reset-table",
    default=False,
    help="Drop and recreate table before import",
)
@error_handler(log=True, raise_error=True)
def import_reference(name: str, reset_table: bool = False) -> None:
    """
    Import a specific reference entity.

    NAME: The reference entity name as defined in import.yml

    Examples:
        niamoto import reference species
        niamoto import reference sites --reset-table
    """
    # Enable progress bars for CLI
    set_progress_mode(use_progress_bar=True)

    print_start(f"Importing reference: {name}")

    try:
        # Load configuration
        config = Config()
        generic_config = config.get_imports_config

        # Get reference config
        if (
            not generic_config.entities
            or name not in generic_config.entities.references
        ):
            raise ConfigurationError(
                config_key=f"entities.references.{name}",
                message=f"Reference '{name}' not found in configuration",
                details={
                    "available_references": list(
                        generic_config.entities.references.keys()
                        if generic_config.entities
                        else []
                    )
                },
            )

        ref_config = generic_config.entities.references[name]

        # Initialize importer and import
        importer = ImporterService(config.database_path)
        result = importer.import_reference(name, ref_config, reset_table=reset_table)

        print_success(f"\n{result}")

    except Exception as e:
        raise DataImportError(
            message=f"Failed to import reference '{name}'",
            details={"error": str(e)},
        ) from e


@import_commands.command(name="dataset")
@click.argument("name")
@click.option(
    "--reset-table/--no-reset-table",
    default=False,
    help="Drop and recreate table before import",
)
@error_handler(log=True, raise_error=True)
def import_dataset(name: str, reset_table: bool = False) -> None:
    """
    Import a specific dataset entity.

    NAME: The dataset entity name as defined in import.yml

    Examples:
        niamoto import dataset observations
        niamoto import dataset measurements --reset-table
    """
    # Enable progress bars for CLI
    set_progress_mode(use_progress_bar=True)

    print_start(f"Importing dataset: {name}")

    try:
        # Load configuration
        config = Config()
        generic_config = config.get_imports_config

        # Get dataset config
        if not generic_config.entities or name not in generic_config.entities.datasets:
            raise ConfigurationError(
                config_key=f"entities.datasets.{name}",
                message=f"Dataset '{name}' not found in configuration",
                details={
                    "available_datasets": list(
                        generic_config.entities.datasets.keys()
                        if generic_config.entities
                        else []
                    )
                },
            )

        ds_config = generic_config.entities.datasets[name]

        # Initialize importer and import
        importer = ImporterService(config.database_path)
        result = importer.import_dataset(name, ds_config, reset_table=reset_table)

        print_success(f"\n{result}")

    except Exception as e:
        raise DataImportError(
            message=f"Failed to import dataset '{name}'",
            details={"error": str(e)},
        ) from e


@import_commands.command(name="list")
@error_handler(log=True, raise_error=True)
def import_list() -> None:
    """
    List all entities defined in import.yml.

    Shows both references and datasets with their configurations.
    """
    try:
        config = Config()
        generic_config = config.get_imports_config

        if not generic_config.entities:
            print_info("No entities configured in import.yml")
            return

        # List references
        if generic_config.entities.references:
            print_info("\n📚 References:")
            for name, ref_config in generic_config.entities.references.items():
                kind = ref_config.kind or "generic"
                path = ref_config.connector.path if ref_config.connector else "N/A"
                print_info(f"  - {name} ({kind}) - {path}")

        # List datasets
        if generic_config.entities.datasets:
            print_info(f"\n{emoji('📊', '[=]')} Datasets:")
            for name, ds_config in generic_config.entities.datasets.items():
                path = ds_config.connector.path if ds_config.connector else "N/A"
                links = len(ds_config.links) if ds_config.links else 0
                print_info(f"  - {name} - {path} ({links} links)")

    except ConfigurationError as e:
        print_error(
            f"Configuration error: {e.message}\n"
            f"Details: {e.details}\n"
            f"Hint: Ensure import.yml follows the entities.references/datasets schema"
        )
        raise


# Keep compatibility alias for `niamoto import all` → `niamoto import run`
@import_commands.command(name="all", hidden=True)
@click.option(
    "--reset-table/--no-reset-table",
    default=False,
    help="Drop and recreate tables before import",
)
@click.pass_context
def import_all(ctx, reset_table: bool = False) -> None:
    """(Deprecated) Use 'niamoto import run' instead."""
    ctx.invoke(import_run, reset_table=reset_table)
