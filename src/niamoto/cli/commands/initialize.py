"""
Commands for initializing and resetting the Niamoto environment.
Handles database initialization, configuration files and environment setup.
"""

import os
import click
import sys

from ..utils.console import print_success, print_error, print_warning, print_info
from .base import confirm_action
from niamoto.common.config import Config
from niamoto.common.environment import Environment


@click.group(name="init")
def initialize_commands():
    """Commands for initializing and managing the Niamoto environment."""
    pass


@initialize_commands.command(name="setup")
@click.option(
    "--reset", is_flag=True, help="Reset the environment if it already exists."
)
@click.option("--force", is_flag=True, help="Skip confirmation prompts.")
def setup_environment(reset: bool, force: bool) -> None:
    """
    Initialize or reset the Niamoto environment with multiple config files:
      - config.yml (database, logs, outputs)
      - sources.yml (data sources)
      - stats.yml
      - presentation.yml
    """
    try:
        niamoto_home = Config.get_niamoto_home()
        config_dir = os.path.join(niamoto_home, "config")
        environment_exists = os.path.exists(config_dir)

        if environment_exists:
            if not reset:
                print_warning(
                    "Niamoto environment already exists. Use --reset to start fresh."
                )
                display_environment_status()
                return

            if not force and not confirm_action(
                "This will delete all existing data. Continue?"
            ):
                print_warning("Setup cancelled.")
                return

            # Load and reset environment
            environment = Environment(config_dir)
            environment.reset()
            print_success("Environment reset successfully.")

        else:
            # Create new environment
            os.makedirs(config_dir, exist_ok=True)
            environment = Environment(config_dir)
            environment.initialize()
            print_success("Environment initialized successfully.")

        display_environment_status()
        display_next_steps()

    except Exception as e:
        print_error(f"Setup failed: {str(e)}")
        raise click.Abort()


@initialize_commands.command(name="status")
def check_environment() -> None:
    """Display the current status of the Niamoto environment."""
    try:
        display_environment_status()
    except Exception as e:
        print_error(f"Status check failed: {str(e)}")
        raise click.Abort()


def display_environment_status() -> None:
    """Display current status of the Niamoto environment."""
    niamoto_home = Config.get_niamoto_home()
    config_dir = os.path.join(niamoto_home, "config")

    print_info("\nChecking environment status...")

    # Check if config/ directory exists
    if not os.path.isdir(config_dir):
        print_warning("No 'config' directory found. Environment not initialized.")
        return

    # Check config files
    config_files = {
        "Global config (config.yml)": os.path.join(config_dir, "config.yml"),
        "Sources config (sources.yml)": os.path.join(config_dir, "sources.yml"),
        "Stats config (stats.yml)": os.path.join(config_dir, "stats.yml"),
        "Presentation config (presentation.yml)": os.path.join(
            config_dir, "presentation.yml"
        ),
    }

    missing_files = []
    for label, path in config_files.items():
        if os.path.exists(path):
            print_success(f"[OK] {label}")
        else:
            print_warning(f"[MISSING] {label}")
            missing_files.append(label)

    # Check global config
    global_cfg_path = os.path.join(config_dir, "config.yml")
    if not os.path.exists(global_cfg_path):
        print_warning("Cannot load environment details without config.yml.")
        return

    # Check environment configuration
    try:
        config = Config(config_dir)
        db_path = config.database_path
        logs_path = config.logs_path
        outputs = config.output_paths

        # Database check
        full_db_path = (
            os.path.join(niamoto_home, db_path)
            if not os.path.isabs(db_path)
            else db_path
        )
        if os.path.exists(full_db_path):
            print_success("[OK] Database found")
        else:
            print_warning("[MISSING] Database not found")

        # Logs check
        full_logs_path = (
            os.path.join(niamoto_home, logs_path)
            if not os.path.isabs(logs_path)
            else logs_path
        )
        if os.path.exists(full_logs_path):
            print_success("[OK] Logs directory found")
        else:
            print_warning("[MISSING] Logs directory missing")

        # Outputs check
        for key, out_path in outputs.items():
            if not out_path:
                print_warning(f"[ERROR] Output directory for {key} is not set")
                continue
            full_out_path = (
                os.path.join(niamoto_home, out_path)
                if not os.path.isabs(out_path)
                else out_path
            )
            if os.path.exists(full_out_path):
                print_success(f"[OK] Output directory for {key}")
            else:
                print_warning(f"[MISSING] Output directory for {key}")

    except Exception as e:
        print_error(f"Failed to check environment details: {str(e)}")


def display_next_steps() -> None:
    """Display helpful information about next steps."""
    print_info("\nNext Steps:")

    steps = [
        {
            "title": "Review or edit your config files",
            "commands": [
                "# e.g. open config/config.yml, config/sources.yml, etc.",
                "niamoto init status  # Verify your configuration",
            ],
        },
        {
            "title": "Import your data",
            "commands": [
                "niamoto import taxonomy <file>  # Import taxonomy data",
                "niamoto import plots <file>     # Import plot data",
                "niamoto import occurrences <file>  # Import occurrence data",
                "# Or import everything at once:",
                "niamoto import all",
            ],
        },
        {
            "title": "Calculate statistics",
            "commands": [
                "niamoto stats calculate --group taxon",
                "niamoto stats calculate --group plot",
                "niamoto stats calculate --group shape",
            ],
        },
        {
            "title": "Generate and deploy content",
            "commands": [
                "niamoto generate site  # Generate static site",
                "niamoto deploy github --repo <url>  # Deploy to GitHub Pages",
            ],
        },
    ]

    for i, step in enumerate(steps, 1):
        print_info(f"\n{i}. {step['title']}")
        for cmd in step["commands"]:
            if cmd.startswith("#"):
                print_info(f"   {cmd}")
            else:
                print_success(f"   $ {cmd}")

    print_info("\nNeed help?")
    print_info("  * Run 'niamoto --help' for available commands")
    print_info("  * Visit https://docs.niamoto.com for documentation")
    print_info("  * Join our community at https://discord.gg/niamoto")