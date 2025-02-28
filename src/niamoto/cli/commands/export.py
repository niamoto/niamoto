# commands/exporter_old.py

"""
Commands for generating static content from Niamoto data.
"""

from typing import Optional

import click

from niamoto.common.config import Config
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.services.exporter_old import ExporterService
from ..utils.console import print_success, print_info


@click.group(name="export", invoke_without_command=True)
@click.option(
    "--group",
    type=str,
    help="Group to generate content for (e.g., taxon, plot, shape).",
)
@click.pass_context
@error_handler(log=True, raise_error=True)
def generate_commands(ctx, group: Optional[str]):
    """Generates static pages using transformed data using [yellow]export.yml[/yellow]."""
    # If no sub-command is provided, invoke the default command (export_pages)
    if ctx.invoked_subcommand is None:
        ctx.invoke(export_pages, group=group)


@generate_commands.command(name="pages")
@click.option(
    "--group",
    type=str,
    help="Group to generate content for (e.g., taxon, plot, shape).",
)
@error_handler(log=True, raise_error=True)
def export_pages(group: Optional[str]) -> None:
    """
    Export data to static pages according to configuration.
    """
    try:
        # Initialize service
        config = Config()
        service = ExporterService(config)

        # Export data
        if group:
            print_info(f"Exporting data for group: {group}")
        else:
            print_info("Exporting all data groups")

        service.export_data(group)

        print_success("Data export completed successfully")
    except Exception:
        # Let the error handler handle the exception
        raise
