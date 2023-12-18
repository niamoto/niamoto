"""
commands.py

This module provides a command-line interface (CLI) for Niamoto.
It includes commands for initializing the database and importing data from CSV files.

Using the CLI, users can easily set up the necessary database tables and import data
without directly interacting with the underlying Python code.
"""

from loguru import logger
import os
import time
import shutil

import click
import toml
from rich.console import Console
from rich.progress import track
from rich.table import Table
from typing import Any, Dict, Optional
from niamoto.common.config_manager import ConfigManager
from niamoto.api import import_api
from niamoto.db.models.models import Base, Taxon
from niamoto.db.utils.database import Database
from niamoto.db.niamoto_repository import NiamotoRepository
from niamoto.api.site_generator_api import SiteGeneratorAPI
from sqlalchemy import asc


@click.group()
def cli() -> None:
    """
    Command line interface for Niamoto.

    This CLI provides commands for initializing the database and importing data from CSV files.
    """
    pass


@cli.command()
@click.option(
    "--reset", is_flag=True, help="Reset the entire project if it already exists."
)
def init(reset: bool) -> None:
    """
    Initialize or reset the Niamoto environment.

    :param reset: Flag to reset the environment if it already exists.
    """
    config_dir = os.path.join(os.getcwd(), "config")
    config_path = os.path.join(config_dir, "niamoto_config.toml")
    console = Console()
    # Vérifier si la configuration existe déjà
    if os.path.exists(config_path):
        if reset:
            click.secho("Resetting the Niamoto environment...", fg="red")
            reset_environment(config_path)
        else:
            click.secho(
                "Niamoto environment already exists. Use --reset to remove existing files",
                fg="yellow",
            )
            return

    else:
        config = create_default_config()
        create_config_file(config, config_path)
        initialize_environment(config)

    console.print("🌱 Niamoto initialized.", style="italic green")
    console.rule()

    list_commands(cli)


def list_commands(group: click.Group) -> None:
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Command", style="dim", width=20)
    table.add_column("Description")

    for command in group.commands.values():
        docstring = command.callback.__doc__
        if docstring:
            # Extraire la première ligne non vide du docstring
            description = next(
                (line.strip() for line in docstring.split("\n") if line.strip()),
                "No description",
            )
        else:
            description = "No description"

        table.add_row(command.name, description)

    console.print("Available Commands:", style="italic underline")
    console.print(table)


def reset_environment(config_path: str) -> None:
    """
    Reset the Niamoto environment by deleting the existing database, configuration, and web static pages.

    :param config_path: Path to the configuration file.
    """
    config = validate_config(config_path)
    if config is None:
        click.secho("Invalid configuration file. Please check and try again.", fg="red")
        return

    # Supprimer la base de données existante si elle existe
    db_path = config["database"]["path"]
    if os.path.exists(db_path):
        os.remove(db_path)
        click.secho(f"Removed existing database at {db_path}", fg="yellow")

    # Supprimer les fichiers dans le dossier web static_pages
    static_pages_path = os.path.join(os.getcwd(), config["web"]["static_pages"])
    if os.path.exists(static_pages_path):
        shutil.rmtree(static_pages_path)
        click.secho(
            f"Removed existing static pages at {static_pages_path}", fg="yellow"
        )

    # Réinitialiser l'environnement
    initialize_environment(config)


def validate_config(config_path: str) -> Optional[Dict[Any, Any]]:
    """
    Validate the existing configuration file.

    :param config_path: Path to the configuration file.
    :return: A dictionary containing the configuration if valid, None otherwise.
    """
    expected_keys = {
        "database": ["type", "path"],
        "sources": ["csv", "raster"],
        "web": ["static_pages", "api"],
        "logs": ["path"],
    }

    try:
        with open(config_path, "r") as config_file:
            config: Dict[Any, Any] = toml.load(config_file)

        for section, keys in expected_keys.items():
            if section not in config:
                raise ValueError(f"Missing section: {section}")

            for key in keys:
                if key not in config[section] or not config[section][key]:
                    raise ValueError(
                        f"Missing or empty key '{key}' in section '{section}'"
                    )

        return config

    except Exception as e:
        click.secho(f"Error validating configuration file: {e}", fg="red")
        return None


def create_default_config() -> Dict[Any, Any]:
    """
    Create a default configuration dictionary.
    """
    return {
        "database": {"type": "sqlite", "path": "data/db/niamoto.db"},
        "sources": {
            "csv": "data/sources/csv",
            "raster": "data/sources/raster",
        },
        "web": {
            "static_pages": "web/static",
            "api": "web/api",
        },
        "logs": {"path": "logs"},
        "taxonomy": {
            "Family": {"field": "id_family", "parent": ""},
            "Genus": {"field": "id_genus", "parent": "Family"},
            "Species": {"field": "id_species", "parent": "Genus"},
            "Hybrid": {"field": "id_species", "parent": "Genus"},
            "Subspecies": {"field": "id_infra", "parent": "Species"},
            "Variety": {"field": "id_infra", "parent": "Species"},
            "Forma": {"field": "id_infra", "parent": "Species"},
        },
    }


def create_config_file(config: Dict[Any, Any], config_path: str) -> None:
    """
    Create the niamoto_config.toml configuration file.

    :param config: A dictionary containing configuration settings.
    :param config_path: Path to the configuration file.
    """
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as config_file:
        toml.dump(config, config_file)
    click.secho(f"Configuration file created at {config_path}", fg="green")


def initialize_environment(config: Dict[Any, Any]) -> None:
    """
    Initialize the Niamoto environment using settings from the configuration file.

    :param config: A dictionary containing configuration settings.
    """
    # Créer les répertoires nécessaires
    for key in ["sources", "web", "logs"]:
        for path in config[key].values():
            os.makedirs(os.path.join(os.getcwd(), path), exist_ok=True)

    # Initialiser la base de données
    db_path = config["database"]["path"]
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = Database(db_path)
    Base.metadata.create_all(db.engine)
    # click.secho(f"{db_path} database initialized.", fg="green")


@cli.command()
@click.argument("csvfile")
@click.argument("table_name", default="taxon")
def import_data(csvfile: str, table_name: str) -> None:
    """
    Import data from a CSV file into the specified table.

    Parameters:
        csvfile (str): Path to the CSV file containing the data to be imported.
        table_name (str): Name of the database table where the data should be imported.

    This command uses the import_api module to process and insert data from the CSV file.
    """
    # Database connection string
    config_manager = ConfigManager()
    db_path = config_manager.get("database", "path")
    import_csv_data(csvfile, table_name, db_path)


def import_csv_data(csvfile: str, table_name: str, database_path: str) -> None:
    try:
        import_api.import_data(csvfile, table_name, database_path)
    except Exception as e:
        logger.exception(f"Import failed: {e}")


@cli.command()
def generate_static_site() -> None:
    """
    Generates static web pages for each taxon in a database.
    It calls the `generate_pages` function and prints the total time taken to generate all pages.
    """
    generate_pages()


def generate_pages() -> float:
    """
    This function generates static web pages for each taxon in the database.
    It first retrieves all taxons from the database, ordered by their full name.
    Then, it generates a web page for each taxon using the `SiteGeneratorAPI`.
    It also generates a JavaScript file for the taxonomy tree using the `PageGenerator`.
    Finally, it returns the total time taken to generate all pages.
    """
    # Record the start time
    start_time = time.time()

    # Create a ConfigManager instance to manage configuration
    config_manager = ConfigManager()

    # Get the database path from the configuration
    db_path = config_manager.get("database", "path")

    repository = NiamotoRepository(db_path)

    # Get all Taxon entities from the repository, ordered by their full name
    taxons = repository.get_entities(Taxon, order_by=asc(Taxon.full_name))

    site_api = SiteGeneratorAPI(config=config_manager)

    # Generate a page for each taxon
    for taxon in track(taxons, description="Pages generated"):
        site_api.generate_page_for_taxon(taxon)

    # Generate the taxonomy tree
    site_api.generate_taxonomy_tree(taxons)

    repository.close_session()

    duration = time.time() - start_time

    console = Console()
    console.print(
        f"🌱 Generated {len(taxons)} pages in {duration:.2f} seconds.",
        style="italic green",
    )

    return duration


# Entry point for the CLI
if __name__ == "__main__":
    cli()
