# commands/exporter.py

"""
Commands for generating static content from Niamoto data.
"""

from typing import Optional

import click

from niamoto.common.config import Config
from niamoto.common.exceptions import (
    ConfigurationError,
    ValidationError,
    GenerationError,
    TemplateError,
)
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.services.exporter import ExporterService
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
    Generate static website content.

    Args:
        group: Optional group to generate content for (e.g., taxon, plot)

    Raises:
        ConfigurationError: If configuration is invalid or export.yml is missing
        ValidationError: If group parameter is invalid
        TemplateError: If template processing fails
        OutputError: If file generation fails
        GenerationError: If content generation fails
    """
    config = Config()

    # Validate transforms configuration
    if not config.exports:
        raise ConfigurationError(
            config_key="transforms",
            message="Missing or empty transforms configuration",
            details={"file": "export.yml"},
        )

    # Validate group if provided
    if group and group.lower() not in ["taxon", "plot", "shape"]:
        raise ValidationError(
            field="group",
            message="Invalid group specified",
            details={"provided": group, "allowed_values": ["taxon", "plot", "shape"]},
        )

    try:
        generator = ExporterService(config)

        if group:
            print_info(f"Generating static pages for group: {group}")
            generator.export_data(group)
        else:
            print_info("Starting full pages generation...")
            for group in ["taxon", "plot", "shape"]:
                print_info(f"Generating static pages for group: {group}")
                generator.export_data(group)

        print_success("Static pages generation completed")

    except TemplateError as e:
        # Re-raise template errors with more context
        raise TemplateError(
            template_name=str(e.template_name),
            message="Template processing failed",
            details={"group": group, "error": str(e)},
        )
    except Exception as e:
        # Handle other generation errors
        raise GenerationError(
            message="Content generation failed",
            details={"group": group, "error": str(e)},
        )
