"""
Commands for transforming and aggregating data in Niamoto.
"""

from typing import Optional
from pathlib import Path

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import (
    ValidationError,
    ConfigurationError,
    FileError,
)
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.services.transformer import TransformerService
from ..utils.console import print_success, print_info, print_warning


@click.group(name="transform", invoke_without_command=True)
@click.option(
    "--group",
    type=str,
    help="Group to transform data for (e.g., 'taxon', 'plot', 'shape').",
)
@click.option(
    "--data",
    type=click.Path(exists=True, dir_okay=False),
    help="Optional data file to use instead of database.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed processing information.",
)
@click.pass_context
@error_handler(log=True, raise_error=True)
def transform_commands(
    ctx: click.Context, group: Optional[str], data: Optional[str], verbose: bool
) -> None:
    """
    Transform and aggregate data according to transform.yml configuration.

    This command processes data following the rules defined in transform.yml,
    which specifies how to group and transform data into useful metrics and
    visualizations.

    Use the --group option to process only a specific group of transforms.
    Use the --data option to use a custom data file.
    Use --verbose for detailed processing information.

    Examples:
        niamoto transform  # Process all groups
        niamoto transform --group taxon  # Process only taxonomy data
        niamoto transform --data my_data.csv  # Use custom data file
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(process_transformations, group=group, data=data, verbose=verbose)


@transform_commands.command(name="list")
@error_handler(log=True, raise_error=True)
def list_configurations() -> None:
    """List all available transformation configurations."""
    try:
        config = Config()
        transforms = config.get_transforms_config()

        if not transforms:
            print_warning("No transformation configurations found in transform.yml")
            return

        print_info("\nAvailable transformation configurations:")
        for transform in transforms:
            group = transform.get("group_by", "unknown")
            source = transform.get("source", {})
            data = source.get("data", "unknown")
            grouping = source.get("grouping", "unknown")
            relation = source.get("relation", {}).get("type", "unknown")
            widgets = len(transform.get("widgets_data", {}))

            print_info(f"\n[bold]{group}[/bold]")
            print_info(f"  Data source: {data}")
            print_info(f"  Grouping: {grouping}")
            print_info(f"  Relation type: {relation}")
            print_info(f"  Widgets: {widgets}")

    except ConfigurationError as e:
        print_warning(f"Error reading configuration: {str(e)}")


@transform_commands.command(name="run")
@click.option(
    "--group",
    type=str,
    help="Group to transform data for (e.g., 'taxon', 'plot', 'shape').",
)
@click.option(
    "--data",
    type=click.Path(exists=True, dir_okay=False),
    help="Optional data file to use instead of database.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed processing information.",
)
@click.option(
    "--recreate-table",
    is_flag=True,
    default=True,
    help="Recreate tables instead of updating them.",
)
@error_handler(log=True, raise_error=True)
def process_transformations(
    group: Optional[str], data: Optional[str], verbose: bool, recreate_table: bool
) -> None:
    """
    Run data transformations based on configuration.

    The transformation process follows these steps:
    1. Load and validate configuration from transform.yml
    2. For each group (or specified group):
        - Load source data
        - Apply grouping based on relation type
        - Calculate metrics and generate visualizations
        - Save results to database
    """
    # Validate inputs
    if data and not data.endswith((".csv", ".xlsx", ".parquet")):
        raise ValidationError(
            field="data",
            message="Unsupported file format",
            details={
                "provided": Path(data).suffix,
                "supported": [".csv", ".xlsx", ".parquet"],
            },
        )

    if data and not Path(data).exists():
        raise FileError(file_path=data, message="Data file not found")

    try:
        config = Config()

        if verbose:
            print_info("Initializing transformer service...")

        service = TransformerService(config.database_path, config)

        # Process transformations
        if group:
            print_info(f"Processing transformations for group: {group}")
        else:
            print_info("Processing all transformation groups")

        service.transform_data(
            group_by=group, csv_file=data, recreate_table=recreate_table
        )

        print_success("Data transformation completed successfully")

    except ConfigurationError as e:
        print_warning(f"Error reading configuration: {str(e)}")


@transform_commands.command(name="check")
@click.option(
    "--group",
    type=str,
    help="Group to check configuration for.",
)
@error_handler(log=True, raise_error=True)
def check_configuration(group: Optional[str]) -> None:
    """
    Check transformation configuration without executing it.

    Validates the transform.yml configuration and reports any issues.
    """
    try:
        config = Config()
        transforms = config.get_transforms_config()

        if not transforms:
            print_warning("No transformation configurations found")
            return

        if group:
            transforms = [t for t in transforms if t.get("group_by") == group]
            if not transforms:
                print_warning(f"No configuration found for group: {group}")
                return

        # Validate each configuration
        service = TransformerService(config.database_path, config)
        for transform in transforms:
            group_by = transform.get("group_by", "unknown")
            print_info(f"\nChecking configuration for {group_by}:")

            try:
                service.validate_configuration(transform)
                print_success(f"Configuration for {group_by} is valid")
            except ValidationError as e:
                print_warning(f"Configuration error in {group_by}: {str(e)}")

    except ConfigurationError as e:
        print_warning(f"Error reading configuration: {str(e)}")
