# src/niamoto/cli/commands/export.py

"""
Commands for generating static content from Niamoto data.
"""

from typing import Optional
from pathlib import Path

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import ConfigurationError, ProcessError
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.services.exporter import ExporterService
from ..utils.console import print_success, print_info, print_error


@click.group(name="export", invoke_without_command=True)
@click.option(
    "--target",
    type=str,
    help="Name of the specific export target to run (defined in config). If omitted, runs all enabled targets.",
)
@click.pass_context
@error_handler(log=True, raise_error=True)
def generate_commands(ctx, target: Optional[str]):
    """Generates static web content based on export configurations."""
    # If no sub-command is provided, invoke the default command (export_pages)
    if ctx.invoked_subcommand is None:
        ctx.invoke(export_pages, target=target)


@generate_commands.command(name="web_pages")
@click.option(
    "--target",
    type=str,
    help="Name of the specific export target to run. If omitted, runs all enabled targets.",
)
@click.option(
    "--group",
    type=str,
    default=None,
    help="Only export pages belonging to this group (e.g., taxon, plot).",
)
@error_handler(log=True, raise_error=True)
def export_pages(target: Optional[str], group: Optional[str]) -> None:
    """
    Export data to static web content according to export target configurations.
    """
    try:
        # Initialize service
        config = Config()
        db_path = config.database_path
        db_path_obj = Path(db_path) if db_path else None

        if not db_path_obj or not db_path_obj.exists():
            print_error(f"Database path not found or configured: {db_path_obj}")
            return

        # Initialize the new ExporterService
        service = ExporterService(db_path=str(db_path_obj), config=config)

        # Run the export process
        if target:
            print_info(f"Running export target: {target}")
        else:
            print_info("Running all enabled export targets...")

        service.run_export(target_name=target, group_filter=group)

        # Success message is handled by the service logging, but we can add a final one here
        print_success("Export process completed.")
    except (ConfigurationError, ProcessError) as e:
        # Handle known Niamoto configuration or processing errors
        print_error(f"Export failed: {e}")
        # Let the error handler potentially re-raise if configured
        raise
    except Exception as e:
        # Catch unexpected errors
        print_error(f"An unexpected error occurred during export: {e}")
        raise
