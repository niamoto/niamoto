"""
Command modules for the Niamoto CLI.

This module defines and registers all the available commands for the Niamoto
command-line interface (CLI). It serves as the entry point for the CLI
application, combining commands for environment initialization, data import,
data processing, content generation, and deployment.

"""

import click
from .base import RichCLI
from .initialize import init_environment  # Import de la commande unique
from .imports import import_commands
from .transform import transform_commands
from .export import generate_commands
from .deploy import deploy_commands
from .plugins import plugins
from .run import run_pipeline
from .stats import stats_command


def create_cli() -> click.Group:
    """Create and configure the main CLI group with all commands.

    This function initializes the Niamoto command-line interface (CLI)
    by registering the following command groups:
        - `init`: Initializes or resets the environment.
        - `import`: Imports raw data into the system.
        - `transforms`: Transforms and aggregates raw data for analysis.
        - `export`: Generates static content using processed data.
        - `deploy`: Deploys generated content to supported platforms.
        - `plugins`: Lists available plugins in the system.

    Returns:
        click.Group: The root command group for the Niamoto CLI.
    """

    @click.group(cls=RichCLI)
    def cli():
        """Command line interface for Niamoto."""
        pass

    # Register individual commands or command groups
    cli.add_command(init_environment, name="init")
    cli.add_command(import_commands)
    cli.add_command(transform_commands)
    cli.add_command(generate_commands)
    cli.add_command(deploy_commands)
    cli.add_command(plugins)
    cli.add_command(run_pipeline)
    cli.add_command(stats_command)

    return cli
