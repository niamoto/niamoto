"""
commands.py

This module provides a command-line interface (CLI) for Niamoto.
It includes commands for initializing the database and importing data from CSV files.

Using the CLI, users can easily set up the necessary database tables and import data
without directly interacting with the underlying Python code.
"""

import os
import time
from typing import Optional, List

import click
from loguru import logger
from rich.console import Console
from rich.progress import track
from rich.table import Table
from sqlalchemy import asc, text

from niamoto.api import StaticContentGenerator, ApiImporter, ApiMapper
from niamoto.api.statistics import ApiStatistics
from niamoto.common.config import Config
from niamoto.common.environment import Environment
from niamoto.core.models import TaxonRef
from niamoto.core.repositories.niamoto_repository import NiamotoRepository
from niamoto.core.services.mapper import MapperService


class RichCLI(click.Group):
    def list_commands(self, ctx: click.Context) -> List[str]:
        """
        Return the list of command names as they were added, not sorted.

        This method overrides the default behavior of click.Group to return the command names
        in the order they were added, instead of sorting them alphabetically.

        Args:
            ctx (click.Context): The click context object.

        Returns:
            list: A list of command names in the order they were added.
        """
        return list(self.commands.keys())

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Override the format_help method to integrate our command table.

        This method customizes the help message displayed when the user runs the CLI with the --help option.
        It includes a custom usage message, a description of the CLI, available options, and a table of available commands.

        Args:
            ctx (click.Context): The click context object.
            formatter (click.HelpFormatter): The click help formatter object.

        Returns:
            None

        Note:
            - The custom help message is written to the formatter using the write method.
            - The available commands are retrieved using the list_commands method.
            - The command table is created using the rich library's Table class.
            - The output of the command table is captured and written to the formatter.
        """
        # Display the custom help message
        formatter.write(
            "Usage: niamoto [OPTIONS] COMMAND [ARGS]...\n\n"
            "Command line interface for Niamoto.\n"
            "This CLI provides commands for initializing the database and importing data from CSV files.\n\n"
            "Options:\n"
            "  --help  Show this message and exit.\n\n"
            "Available Commands:\n"
        )

        # Get the list of commands
        commands = self.list_commands(ctx)
        commands_info = []
        for cmd_name in commands:
            cmd = self.get_command(ctx, cmd_name)
            if cmd is None:
                continue

            # Extract the first line of the docstring as a description
            docstring = cmd.callback.__doc__
            if docstring:
                description = docstring.strip().split("\n")[0]
            else:
                description = "No description provided"

            commands_info.append((cmd_name, description))

        # Create the command table with Rich
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Command", style="dim")
        table.add_column("Description")
        for cmd_name, description in commands_info:
            table.add_row(cmd_name, description)

        # Capture the output of the table into a variable
        with console.capture() as capture:
            console.print(table)

        # Write the captured output into the formatter
        formatter.write(capture.get())


@click.group(cls=RichCLI)
def cli() -> None:
    """
    Command line interface for Niamoto.

    This CLI provides commands for initializing the database and importing data from CSV files.

    The `cli` function serves as the entry point for the Niamoto command line interface.
    It is decorated with `@click.group` to define it as a Click command group.

    The `cls` parameter is set to `RichCLI`, which is a custom class that inherits from `click.Group`.
    This allows for customization of the CLI behavior and appearance.

    Returns:
        None

    Example:
        To run the Niamoto CLI, use the following command:
        $ niamoto [OPTIONS] COMMAND [ARGS]...

    Note:
        - The docstring of the `cli` function provides a brief description of the Niamoto CLI.
        - The `pass` statement is used as a placeholder since the `cli` function doesn't have any body.
        - The actual commands and their implementations are defined separately using the `@cli.command()` decorator.
    """
    pass


@cli.command()
@click.option(
    "--reset", is_flag=True, help="Reset the entire project if it already exists."
)
def init(reset: bool) -> None:
    """
    Initialize or reset the Niamoto environment.

    This command sets up the necessary configuration files and directories for the Niamoto project.
    If the environment already exists, it provides an option to reset the project and start fresh.

    Args:
        reset (bool): Flag to reset the environment if it already exists.

    Examples:
        $ niamoto init
        $ niamoto init --reset

    Returns:
        None

    Raises:
        None

    Note:
        - If the Niamoto environment already exists and the `--reset` flag is not provided, the command will abort and display a warning message.
        - If the `--reset` flag is provided and the environment exists, the command will reset the environment by removing existing files and reinitializing the project.
        - If the Niamoto environment does not exist, the command will initialize a new environment with default configuration settings.
    """
    console = Console()
    niamoto_home = Config.get_niamoto_home()
    config_path = os.path.join(niamoto_home, "config.yml")

    if os.path.exists(config_path):
        config_manager = Config(config_path)
        environment = Environment(config_manager.config)

        if reset:
            click.secho("Resetting the Niamoto environment...", fg="red")
            environment.reset()
        else:
            click.secho(
                "Niamoto environment already exists. Use --reset to remove existing files",
                fg="yellow",
            )
            return
    else:
        config_manager = Config(config_path, create_default=True)
        environment = Environment(config_manager.config)
        environment.initialize()

    console.print("🌱 Niamoto initialized.", style="italic green")
    console.rule()

    list_commands(cli)


def list_commands(group: click.Group) -> None:
    """
    Display a formatted table of available commands and their descriptions.

    This function iterates over the commands in the provided click.Group and extracts
    the name and description of each command. It then creates a formatted table using
    the rich library to display the commands and their descriptions in a visually
    appealing manner.

    Args:
        group (click.Group): The click.Group object containing the commands to be listed.

    Returns:
        None

    Example:
        list_commands(cli)

    Note:
        - The function assumes that each command has a docstring that provides a description.
        - If a command lacks a docstring or the docstring is empty, the description will be set to "No description".
        - The table is formatted with a header row and two columns: "Command" and "Description".
        - The "Command" column has a fixed width of 20 characters and is styled with a "dim" color.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Command", style="dim", width=20)
    table.add_column("Description")

    for command in group.commands.values():
        docstring = command.callback.__doc__
        if docstring:
            # Extract the first non-empty line of the docstring
            description = next(
                (line.strip() for line in docstring.split("\n") if line.strip()),
                "No description",
            )
        else:
            description = "No description"

        table.add_row(command.name, description)

    console.print("Available Commands:", style="italic underline")
    console.print(table)


@cli.command(name="import-taxonomy")
@click.argument("csvfile")
@click.option("--ranks", help="Comma-separated list of ranks in the hierarchy.")
def import_taxonomy(csvfile: str, ranks: str) -> None:
    """
    Import taxonomy data from a CSV file into the database.

    This command reads taxonomic data from the specified CSV file and imports it into the database.
    The CSV file should contain columns corresponding to the taxonomic ranks, such as family, genus, species, etc.
    The `--ranks` option allows you to specify the order of the ranks in the CSV file.

    Args:
        csvfile (str): Path to the CSV file containing the taxonomic data to be imported.
        ranks (str): Comma-separated list of ranks in the hierarchy, in the order they appear in the CSV file.
                     If not provided, the command will attempt to infer the ranks from the CSV file headers.

    Examples:
        $ niamoto import-taxonomy taxonomy.csv
        $ niamoto import-taxonomy taxonomy.csv --ranks=id_family,id_genus,id_species,id_infra

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist.
        ValueError: If the provided ranks do not match the columns in the CSV file.

    Note:
        The CSV file should have a header row specifying the column names.
        The column names should match the ranks specified in the `--ranks` option, if provided.
    """
    ranks_tuple = tuple(ranks.split(",")) if ranks else ()
    data_importer = ApiImporter()
    import_tax_result = data_importer.import_taxononomy(csvfile, ranks_tuple)
    console = Console()
    console.print(import_tax_result, style="italic green")


@cli.command(name="import-plots")
@click.argument("gpkg_file")
def import_plots(gpkg_file: str) -> None:
    """
    Import plot data from a GeoPackage file into the plot_ref table.

    This command reads plot data from the specified GeoPackage file and imports it into the plot_ref table in the database.
    The GeoPackage file should contain a layer with plot geometries and associated attributes.

    Args:
        gpkg_file (str): Path to the GeoPackage file containing the plot data.

    Examples:
        $ niamoto import-plots plots.gpkg

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified GeoPackage file does not exist.
        ValueError: If the GeoPackage file does not contain a valid plot layer.
        Exception: If an error occurs during the import process.

    Note:
        The plot layer in the GeoPackage file should have a specific structure and attributes.
        Refer to the documentation for the required structure of the plot layer.
    """
    try:
        api_importer = ApiImporter()
        import_plot_results = api_importer.import_plots(gpkg_file)
        console = Console()
        console.print(import_plot_results, style="italic green")
    except FileNotFoundError as e:
        logger.exception(f"GeoPackage file not found: {e}")
    except ValueError as e:
        logger.exception(f"Invalid GeoPackage file: {e}")
    except Exception as e:
        logger.exception(f"Import failed: {e}")


@cli.command(name="import-occurrences")
@click.argument("csvfile")
@click.option(
    "--taxon-id-column",
    "-t",
    required=True,
    help="Name of the column in the CSV that corresponds to the taxon ID.",
)
def import_occurrences(csvfile: str, taxon_id_column: str) -> None:
    """
    Import occurrence data from a CSV file, analyze it to update the 'mapping' table, and link occurrences to their taxons.

    This command reads occurrence data from the specified CSV file, performs an analysis to update the 'mapping' table,
    and establishes links between occurrences and their corresponding taxons based on the provided taxon ID column.

    Args:
        csvfile (str): Path to the CSV file containing the occurrence data to be imported and analyzed.
        taxon_id_column (str): Name of the column in the CSV file that contains the taxon IDs.

    Examples:
        $ niamoto import-occurrences occurrences.csv --taxon-id-column=id_taxonref
        $ niamoto import-occurrences occurrences.csv -t taxon_id

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist.
        ValueError: If the specified taxon ID column is not found in the CSV file.
        Exception: If an error occurs during the import process.

    Note:
        - The CSV file should have a header row specifying the column names.
        - The taxon ID column should contain valid taxon identifiers that match the taxons in the database.
        - The 'mapping' table will be updated based on the analysis of the occurrence data.
    """
    data_importer = ApiImporter()
    import_occ_result = data_importer.import_occurrences(csvfile, taxon_id_column)
    console = Console()
    console.print(import_occ_result, style="italic green")


@cli.command(name="import-occurrence-plots")
@click.argument("csvfile")
def import_occurrence_plot_links(csvfile: str) -> None:
    """
    Import occurrence-plot links from a CSV file.

    This command reads occurrence-plot links from the specified CSV file and imports them into the database.
    The CSV file should contain columns representing the occurrence ID and the corresponding plot ID.

    Args:
        csvfile (str): Path to the CSV file containing the occurrence-plot links.

    Examples:
        $ niamoto import-occurrence-plots occurrence_plots.csv

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist.
        ValueError: If the CSV file does not contain the required columns for occurrence-plot links.
        Exception: If an error occurs during the import process.

    Note:
        - The CSV file should have a header row specifying the column names.
        - The required columns in the CSV file are:
            - 'occurrence_id': The ID of the occurrence.
            - 'plot_id': The ID of the plot associated with the occurrence.
        - The occurrence IDs and plot IDs should match the existing occurrences and plots in the database.
    """
    try:
        api_importer = ApiImporter()
        import_occ_plot_results = api_importer.import_occurrence_plot_links(csvfile)
        console = Console()
        console.print(import_occ_plot_results, style="italic green")
    except FileNotFoundError as e:
        logger.exception(f"CSV file not found: {e}")
    except ValueError as e:
        logger.exception(f"Invalid CSV file format: {e}")
    except Exception as e:
        logger.exception(f"Import failed: {e}")


@cli.command(name="generate-mapping")
@click.option(
    "--data-source",
    type=str,
    help="Path to the CSV file to generate mapping from.",
)
@click.option(
    "--mapping-group",
    type=str,
    required=True,
    help="The type of grouping to generate the mapping for (e.g., taxon, plot, commune).",
)
@click.option(
    "--reference-table-name",
    type=str,
    help="The name of the reference table in the database.",
)
@click.option(
    "--reference-data-path",
    type=str,
    help="The path to the reference table file (e.g., GeoPackage).",
)
def generate_mapping(
    data_source: str,
    mapping_group: str,
    reference_table_name: Optional[str],
    reference_data_path: Optional[str],
) -> None:
    """
    Generate a mapping from a CSV file based on the specified grouping criteria.

    This command generates a mapping between the data in the CSV file and the specified grouping criteria.
    It allows for the creation of mappings based on different entities such as taxon, plot, or commune.
    If a reference table and data path are provided, they will be used to enhance the mapping process.

    Args:
        data_source (str): Path to the CSV file containing the data to generate the mapping from.
        mapping_group (str): The type of grouping to generate the mapping for (e.g., taxon, plot, commune).
        reference_table_name (str, optional): The name of the reference table in the database.
        reference_data_path (str, optional): The path to the reference table file (e.g., GeoPackage).

    Examples:
        $ niamoto generate-mapping --data-source occurrences.csv --mapping-group taxon --reference-table-name taxon_ref
        $ niamoto generate-mapping --data-source plot_data.csv --mapping-group plot --reference-table-name plot_ref --reference-data-path plot_ref.gpkg

    Raises:
        click.UsageError: If no CSV file is provided to generate the mapping from.
        Exception: If an error occurs during the mapping generation process.

    Note:
        - The CSV file should have a header row specifying the column names.
        - The mapping group should correspond to a valid entity type (e.g., taxon, plot, commune).
        - If a reference table and data path are provided, ensure that they are valid and accessible.
    """
    try:
        api_mapper = ApiMapper()
        if data_source:
            api_mapper.generate_mapping_from_csv(
                data_source, mapping_group, reference_table_name, reference_data_path
            )
        else:
            raise click.UsageError(
                "Please provide a CSV file to generate mapping from."
            )
    except click.UsageError as e:
        console = Console()
        console.print(f"Usage error: {e}", style="bold red")
    except Exception as e:
        console = Console()
        console.print(f"Error while generating mapping: {e}", style="bold red")


@cli.command(name="calculate-statistics")
@click.option(
    "--mapping-group",
    type=str,
    help="The specific group to calculate statistics for. If not provided, statistics will be calculated for all groups.",
)
@click.option(
    "--csv-file",
    type=str,
    help="Path to the CSV file containing the occurrences. If not provided, the target_table_name from the mapping will be used.",
)
def calculate_statistics(mapping_group: Optional[str], csv_file: Optional[str]) -> None:
    """
    Calculate statistics based on the mapping file specified in the configuration.

    This command calculates various statistics based on the mapping file defined in the configuration.
    It provides options to calculate statistics for a specific group or for all groups.
    If a CSV file is provided, it will be used as the data source for calculating the statistics.
    Otherwise, the target_table_name from the mapping file will be used.

    Args:
        mapping_group (str, optional): The specific group to calculate statistics for.
                                  If not provided, statistics will be calculated for all groups.
        csv_file (str, optional): Path to the CSV file containing the occurrences.
                                  If not provided, the target_table_name from the mapping will be used.

    Examples:
        $ niamoto calculate-statistics
        $ niamoto calculate-statistics --mapping-group taxon
        $ niamoto calculate-statistics --csv-file occurrences.csv
        $ niamoto calculate-statistics --mapping-group plot --csv-file plot_occurrences.csv

    Raises:
        Exception: If an error occurs during the statistics calculation process.

    Note:
        - If a CSV file is provided, ensure that it has the necessary columns and format for calculating the statistics.
        - The mapping file used for the statistics calculation is specified in the configuration.
    """
    try:
        api_statistics = ApiStatistics()
        if mapping_group:
            api_statistics.calculate_group_statistics(mapping_group, csv_file)
        else:
            api_statistics.calculate_all_statistics(csv_file)
        console = Console()
        console.print("Statistics calculated successfully.", style="italic green")
    except Exception as e:
        console = Console()
        console.print(f"Error while calculating statistics: {e}", style="bold red")


@cli.command(name="generate-static-site")
def generate_static_site() -> None:
    """
    Generate static web pages for each taxon in the database.

    This command retrieves all taxons from the database, ordered by their full name,
    and generates a static web page for each taxon using the `SiteGeneratorAPI`.
    It also generates a JavaScript file for the taxonomy tree using the `PageGenerator`.

    The generated static site includes individual pages for each taxon, displaying relevant
    information and data associated with the taxon. The taxonomy tree JavaScript file
    provides an interactive hierarchical representation of the taxonomic structure.

    Examples:
        $ niamoto generate-static-site

    Returns:
        None

    Note:
        - The generated static site files are stored in the configured output directory.
        - The database connection settings are retrieved from the configuration file.
        - The command may take some time to complete, depending on the number of taxons in the database.
    """
    # Record the start time
    start_time = time.time()

    # Create a ConfigManager instance to manage configuration
    config_manager = Config()

    # Get the database path from the configuration
    db_path = config_manager.get("database", "path")

    repository = NiamotoRepository(db_path)

    # Get all Taxon entities from the repository, ordered by their full name
    taxons = repository.get_entities(TaxonRef, order_by=asc(TaxonRef.full_name))

    content_generator = StaticContentGenerator(config=config_manager)

    mapping_service = MapperService(db_path)
    mapping_group = mapping_service.get_group_config("taxon")
    # Generate a page for each taxon
    for taxon in track(taxons, description="Pages generated"):
        with repository.db.engine.connect() as connection:
            result = connection.execute(
                text("SELECT * FROM taxon_stats WHERE taxon_id = :taxon_id"),
                {"taxon_id": taxon.id},
            )
            taxon_stats_row = result.fetchone()

            if taxon_stats_row:
                taxon_stats_dict = dict(zip(result.keys(), taxon_stats_row))
            else:
                taxon_stats_dict = {}

            content_generator.generate_page_for_taxon(
                taxon, taxon_stats_dict, mapping_group
            )

    # Generate the taxonomy tree
    content_generator.generate_taxonomy_tree(taxons)

    repository.close_session()
    duration = time.time() - start_time
    console = Console()
    console.print(
        f"🌱 Generated {len(taxons)} pages in {duration:.2f} seconds.",
        style="italic green",
    )


if __name__ == "__main__":
    cli()
