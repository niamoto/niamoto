"""
Command modules for the Niamoto CLI.
"""
import click
from .base import RichCLI
from .initialize import initialize_commands
from .import_data import import_commands
from .statistics import statistic_commands
from .generate import generate_commands
from .deploy import deploy_commands


def create_cli() -> click.Group:
    """
    Create and configure the main CLI group with all commands.
    """

    @click.group(cls=RichCLI)
    def cli():
        """Command line interface for Niamoto."""
        pass

    # Register all command groups
    cli.add_command(initialize_commands)
    cli.add_command(import_commands)
    cli.add_command(statistic_commands)
    cli.add_command(generate_commands)
    cli.add_command(deploy_commands)

    return cli
