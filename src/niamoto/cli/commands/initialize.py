"""
Commands for initializing and resetting the Niamoto environment.
Handles database initialization, configuration files and environment setup.
"""

import os
import click

from ..utils.console import print_success, print_error, print_warning, print_info
from .base import display_next_steps
from niamoto.common.config import Config
from niamoto.common.environment import Environment
from ...common.exceptions import CommandError, EnvironmentSetupError
from ...common.utils import error_handler


@click.command(name="init")
@click.option(
    "--reset", is_flag=True, help="Reset the environment if it already exists."
)
@error_handler(log=True, raise_error=True)
def init_environment(reset: bool) -> None:
    """
    Initialize or reset the Niamoto environment, and display its status.

    Handles:
      - config.yml (database, logs, outputs)
      - import.yml (data sources)
      - transform.yml
      - export.yml
    """
    try:
        config_dir = get_config_dir()
        environment_exists = os.path.exists(config_dir)

        if environment_exists and reset:
            if not confirm_reset():
                print_warning("Environment reset cancelled by user.")
                return
            reset_environment(config_dir)
        elif not environment_exists:
            initialize_environment(config_dir)

        display_environment_status(config_dir)
        display_next_steps()

    except Exception as e:
        raise CommandError(
            command="init", message="Initialization failed", details={"error": str(e)}
        )


def confirm_reset() -> bool:
    """
    Ask for user confirmation before resetting the environment.

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    click.echo(
        click.style(
            "This will reinitialize the database and remove all generated files in the outputs directory.",
            fg="red",
            bold=True,
        )
    )
    return click.confirm("Are you sure you want to reset?", default=False)


@error_handler(log=True, raise_error=True)
def get_config_dir() -> str:
    """
    Retrieve the path to the configuration directory.

    Returns:
        str: Path to the configuration directory.
    """
    try:
        niamoto_home = Config.get_niamoto_home()
        return os.path.join(niamoto_home, "config")
    except Exception as e:
        raise EnvironmentSetupError(
            message="Failed to get config directory", details={"error": str(e)}
        )


@error_handler(log=True, raise_error=True)
def initialize_environment(config_dir: str) -> None:
    """
    Initialize the Niamoto environment.

    Args:
        config_dir (str): Path to the configuration directory.
    """
    try:
        os.makedirs(config_dir, exist_ok=True)
        environment = Environment(config_dir)
        environment.initialize()
        print_success("Environment initialized successfully.")
    except Exception as e:
        raise EnvironmentSetupError(
            message="Failed to initialize environment",
            details={"config_dir": config_dir, "error": str(e)},
        )


@error_handler(log=True, raise_error=True)
def reset_environment(config_dir: str) -> None:
    """
    Reset the Niamoto environment.

    Args:
        config_dir (str): Path to the configuration directory.
    """
    try:
        environment = Environment(config_dir)
        environment.reset()
        print_success("Environment reset successfully.")
    except Exception as e:
        raise EnvironmentSetupError(
            message="Failed to reset environment",
            details={"config_dir": config_dir, "error": str(e)},
        )


@error_handler(log=True)
def display_environment_status(config_dir: str) -> None:
    """
    Display the current status of the Niamoto environment.

    Args:
        config_dir (str): Path to the configuration directory.
    """
    print_info("Checking environment status...")

    if not os.path.isdir(config_dir):
        print_warning("No 'config' directory found. Environment not initialized.")
        return

    check_config_files(config_dir)
    check_environment_details(Config(config_dir))


@error_handler(log=True)
def check_config_files(config_dir: str) -> None:
    """
    Check if the config files exist in the config directory.
    Args:
        config_dir (str): Path to the configuration directory.
    """
    config_files = {
        "Global config": "config.yml",
        "Import config": "import.yml",
        "Transform config": "transform.yml",
        "Export config": "export.yml",
    }

    for label, filename in config_files.items():
        path = os.path.join(config_dir, filename)
        if os.path.exists(path):
            print_success(f"{label}")
        else:
            print_warning(f"{label} (missing)")


@error_handler(log=True)
def check_environment_details(config: Config) -> None:
    """
    Check additional environment details like database, logs, and outputs.

    Args:
        config (Config): Configuration object.
    """
    try:
        niamoto_home = Config.get_niamoto_home()

        check_path(config.database_path, niamoto_home, "Database", is_file=True)
        check_path(config.logs_path, niamoto_home, "Logs directory")

        for key, out_path in config.get_export_config.items():
            if out_path:
                check_path(out_path, niamoto_home, f"Output directory for {key}")

    except Exception as e:
        print_error(f"Failed to check environment details: {str(e)}")


def check_path(path: str, base_path: str, label: str, is_file: bool = False) -> None:
    """
    Check if a path exists.
    Args:
        path (str): Path to check
        base_path (str): Base path
        label (str): Label
        is_file (bool, optional): If the path is a file. Defaults to False.
    """
    full_path = os.path.join(base_path, path) if not os.path.isabs(path) else path
    exists = os.path.isfile(full_path) if is_file else os.path.exists(full_path)
    if exists:
        print_success(f"{label} found")
    else:
        print_warning(f"{label} not found")
