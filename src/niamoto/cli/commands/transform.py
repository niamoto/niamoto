"""
Commands for transforming and aggregating data in Niamoto.
"""

from typing import Optional

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import ValidationError, ProcessError
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.services.transformer import TransformerService
from ..utils.console import print_success, print_info


@click.group(name="transform", invoke_without_command=True)
@click.option(
    "--group",
    type=str,
    help="Group to transforms data for (e.g., taxon, plot).",
)
@click.option(
    "--csv-file",
    type=str,
    help="Optional CSV file with occurrence data.",
)
@click.pass_context
@error_handler(log=True, raise_error=True)
def transform_commands(ctx, group: Optional[str], csv_file: Optional[str]) -> None:
    """
    Transforms and aggregates raw data using [yellow]transform.yml[/yellow] and [yellow]import.yml[/yellow].

    This command processes data for a specific group (e.g., taxon or plot),
    optionally using a provided CSV file as input.

    Raises:
        ConfigurationError: If configuration files are invalid
        ValidationError: If group parameter is invalid
        FileError: If CSV file is not found or invalid
        ProcessError: If transforms operation fails
    """
    # Validate group if provided
    if group and group.lower() not in ["taxon", "plot", "shape"]:
        raise ValidationError(
            field="group",
            message="Invalid group specified",
            details={"provided": group, "allowed_values": ["taxon", "plot", "shape"]},
        )

    # Validate CSV file if provided
    if csv_file and not csv_file.endswith(".csv"):
        raise ValidationError(
            field="csv_file",
            message="Invalid file format",
            details={"provided": csv_file, "expected": "CSV file"},
        )

    # If no sub-command is provided, invoke the default command
    if ctx.invoked_subcommand is None:
        if group:
            ctx.invoke(process_transformations, group=group, csv_file=csv_file)
        else:
            ctx.invoke(transform_all)


@transform_commands.command(name="run")
@click.option(
    "--group",
    type=str,
    help="Group to transforms data for (e.g., taxon, plot).",
)
@click.option(
    "--csv-file",
    type=str,
    help="Optional CSV file with occurrence data.",
)
@error_handler(log=True, raise_error=True)
def process_transformations(group: Optional[str], csv_file: Optional[str]) -> None:
    """
    Calculate transforms for a specified group.

    Args:
        group: Group to process data for (e.g., taxon, plot)
        csv_file: Optional path to CSV file with occurrence data

    Raises:
        ConfigurationError: If configuration is invalid
        ValidationError: If parameters are invalid
        FileError: If CSV file is not found or invalid
        ProcessError: If calculation fails
        DataTransformError: If data transforms operation fails
    """
    config = Config()

    try:
        # Initialize service
        service = TransformerService(config.database_path, config)

        # Calculate statistics
        print_info(f"Transforming data for group: {group or 'all'}")
        service.calculate_statistics(group_by=group, csv_file=csv_file)
        print_success("Data transformation completed")

    except Exception as e:
        raise ProcessError(
            message="Data transforms failed",
            details={"group": group, "csv_file": csv_file, "error": str(e)},
        )


@transform_commands.command(name="all")
@error_handler(log=True, raise_error=True)
def transform_all() -> None:
    """
    Transform all data according to configuration.

    Processes taxonomy, plot and shape data sequentially.
    """
    print_info("Starting full data transformation...")
    config = Config()

    try:
        # Initialize service
        service = TransformerService(config.database_path, config)

        # Transform taxonomy data
        service.calculate_statistics(group_by="taxon")

        # Transform plot data
        service.calculate_statistics(group_by="plot")

        # Transform shape data
        service.calculate_statistics(group_by="shape")

        print_success("All transformations completed successfully")

    except Exception as e:
        raise ProcessError(
            message="Full transformation failed", details={"error": str(e)}
        )
