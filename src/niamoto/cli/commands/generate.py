# commands/generate.py

"""
Commands for generating static content from Niamoto data.
"""

import click
from typing import Optional

from ..utils.console import print_success, print_error
from niamoto.core.services.generator import GeneratorService
from niamoto.common.config import Config


@click.group(name="generate")
def generate_commands():
    """Commands for generating static content."""
    pass


@generate_commands.command(name="site")
@click.option(
    "--group",
    type=str,
    help="Group to generate content for (e.g., taxon, plot).",
)
def generate_content(group: Optional[str]) -> None:
    """Generate static website content."""
    try:
        config = Config()
        generator = GeneratorService(config)
        generator.generate_content(group)
        print_success("Content generated successfully")

    except Exception as e:
        print_error(f"Content generation failed: {str(e)}")
        raise click.Abort()
