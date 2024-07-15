"""
commands.py

This module provides a command-line interface (CLI) for Niamoto.
It includes commands for initializing the database and importing data from CSV files.

Using the CLI, users can easily set up the necessary database tables and import data
without directly interacting with the underlying Python code.
"""

import os
import subprocess
import time
from typing import Optional, List

import click
import duckdb
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import box

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.environment import Environment
from niamoto.core.models import Base
from niamoto.core.services.generator import GeneratorService
from niamoto.core.services.importer import ImporterService
from niamoto.core.services.mapper import MapperService
from niamoto.core.services.statistics import StatisticService

NIAMOTO_ASCII_ART = """
┳┓┳┏┓┳┳┓┏┓┏┳┓┏┓
┃┃┃┣┫┃┃┃┃┃ ┃ ┃┃
┛┗┻┛┗┛ ┗┗┛ ┻ ┗┛                                
"""


class RichCLI(click.Group):
    """
    Custom Click Group class that provides a richly formatted CLI interface.
    """

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
        console = Console()
        with console.capture() as capture:
            console.print("[green]" + NIAMOTO_ASCII_ART + "[/green]")
            console.print(
                "\nUsage: niamoto [OPTIONS] COMMAND [ARGS]...\n\n"
                "Command line interface for Niamoto.\n"
                "This CLI provides commands for initializing the database and importing data from CSV files.\n\n"
                "Options:\n"
                "  --help  Show this message and exit.\n\n"
                "Main Commands (in this order, require a complete config.yml file):\n"
            )

        formatter.write(capture.get())

        main_commands = [
            "init",
            "import-all",
            "calculate-statistics",
            "generate-content",
            "deploy-static_files-site",
        ]

        other_commands = [
            cmd for cmd in self.list_commands(ctx) if cmd not in main_commands
        ]

        # Get the list of main commands
        main_commands_info = []
        for cmd_name in main_commands:
            cmd = self.get_command(ctx, cmd_name)
            if cmd is None:
                continue

            # Extract the first line of the docstring as a description
            docstring = cmd.callback.__doc__
            if docstring:
                description = docstring.strip().split("\n")[0]
            else:
                description = "No description provided"

            main_commands_info.append((cmd_name, description))

        # Create the main command table with Rich
        console = Console()
        main_table = Table(show_header=True, header_style="bold magenta")
        main_table.add_column("Command", style="dim")
        main_table.add_column("Description")
        for cmd_name, description in main_commands_info:
            main_table.add_row(cmd_name, description)

        # Capture the output of the main table into a variable
        with console.capture() as capture:
            console.print(main_table)

        # Write the captured output into the formatter
        formatter.write(capture.get())

        # Add other commands section
        if other_commands:
            formatter.write("\nOther Commands:\n")
            other_commands_info = []
            for cmd_name in other_commands:
                cmd = self.get_command(ctx, cmd_name)
                if cmd is None:
                    continue

                # Extract the first line of the docstring as a description
                docstring = cmd.callback.__doc__
                if docstring:
                    description = docstring.strip().split("\n")[0]
                else:
                    description = "No description provided"

                other_commands_info.append((cmd_name, description))

            # Create the other commands table with Rich
            other_table = Table(show_header=True, header_style="bold magenta")
            other_table.add_column("Command", style="dim")
            other_table.add_column("Description")
            for cmd_name, description in other_commands_info:
                other_table.add_row(cmd_name, description)

            # Capture the output of the other table into a variable
            with console.capture() as capture:
                console.print(other_table)

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
        environment = Environment(config_manager)

        if reset:
            click.secho("Resetting the Niamoto environment...", fg="red")
            environment.reset()
        else:
            click.secho(
                "Niamoto environment already exists. Use --reset to remove existing files.",
                fg="yellow",
            )
            return
    else:
        config_manager = Config(config_path, create_default=True)
        environment = Environment(config_manager)
        environment.initialize()

    console.print("🌱 Niamoto initialized.", style="italic green")
    console.rule()

    list_commands(cli, click.get_current_context())


def list_commands(group: click.Group, ctx: click.Context) -> None:
    """
    Display a formatted table of available commands and their descriptions.

    This function iterates over the commands in the provided click.Group and extracts
    the name and description of each command. It then creates a formatted table using
    the rich library to display the commands and their descriptions in a visually
    appealing manner.

    Args:
        group (click.Group): The click.Group object containing the commands to be listed.
        ctx (click.Context): The click context object.

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
    console.print(NIAMOTO_ASCII_ART, style="bold green")

    main_commands = [
        "init",
        "import-all",
        "calculate-statistics",
        "generate-content",
        "deploy-static_files-site",
    ]

    other_commands = [
        cmd for cmd in group.list_commands(ctx) if cmd not in main_commands
    ]

    # Get the list of main commands
    main_commands_info = []
    for cmd_name in main_commands:
        cmd = group.get_command(ctx, cmd_name)
        if cmd is None:
            continue

        # Extract the first line of the docstring as a description
        docstring = cmd.callback.__doc__
        if docstring:
            description = docstring.strip().split("\n")[0]
        else:
            description = "No description provided"

        main_commands_info.append((cmd_name, description))

    # Create the main command table with Rich
    main_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    main_table.add_column("Command", style="dim")
    main_table.add_column("Description")
    for cmd_name, description in main_commands_info:
        main_table.add_row(cmd_name, description)

    console.print("Main Commands:", style="italic underline")
    console.print(main_table)

    # Add other commands section
    if other_commands:
        other_commands_info = []
        for cmd_name in other_commands:
            cmd = group.get_command(ctx, cmd_name)
            if cmd is None:
                continue

            # Extract the first line of the docstring as a description
            docstring = cmd.callback.__doc__
            if docstring:
                description = docstring.strip().split("\n")[0]
            else:
                description = "No description provided"

            other_commands_info.append((cmd_name, description))

        # Create the other commands table with Rich
        other_table = Table(
            show_header=True, header_style="bold magenta", box=box.SIMPLE
        )
        other_table.add_column("Command", style="dim")
        other_table.add_column("Description")
        for cmd_name, description in other_commands_info:
            other_table.add_row(cmd_name, description)

        console.print("Other Commands:", style="italic underline")
        console.print(other_table)


@cli.command(name="import-taxonomy")
@click.argument("csvfile", required=False)
@click.option("--ranks", help="Comma-separated list of ranks in the hierarchy.")
def import_taxonomy(csvfile: str, ranks: str) -> None:
    """
    Import taxonomy data from a CSV file into the database.

    This command reads taxonomic data from the specified CSV file and imports it into the database.
    The CSV file should contain columns corresponding to the taxonomic ranks, such as family, genus, species, etc.
    The `--ranks` option allows you to specify the order of the ranks in the CSV file.

    If the `csvfile` argument is not provided, the command will use the path specified in the configuration file.

    Args:
        csvfile (str, optional): Path to the CSV file containing the taxonomic data to be imported.
                                 If not provided, the path specified in the configuration file will be used.
        ranks (str, optional): Comma-separated list of ranks in the hierarchy, in the order they appear in the CSV file.
                               If not provided, the command will attempt to infer the ranks from the CSV file headers
                               or use the ranks specified in the configuration file.

    Examples:
        $ niamoto import-taxonomy taxonomy.csv
        $ niamoto import-taxonomy taxonomy.csv --ranks=id_family,id_genus,id_species,id_infra
        $ niamoto import-taxonomy

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist and no default path is provided in the configuration.
        ValueError: If the provided ranks do not match the columns in the CSV file.

    Note:
        The CSV file should have a header row specifying the column names.
        The column names should match the ranks specified in the `--ranks` option, if provided.
    """
    config = Config()
    db_path = config.get("database", "path")
    taxonomy_config = config.get("sources", "taxonomy")
    ranks_from_config = taxonomy_config.get("ranks")
    default_csvfile = taxonomy_config.get("path")

    if not csvfile and default_csvfile and os.path.exists(default_csvfile):
        csvfile = default_csvfile

    if not csvfile or not os.path.exists(csvfile):
        raise FileNotFoundError("CSV file not specified or does not exist.")

    ranks = ranks or ranks_from_config
    ranks_tuple = tuple(ranks.split(",")) if ranks else ()

    reset_table(db_path, "taxon_ref")

    data_importer = ImporterService(db_path)
    import_tax_result = data_importer.import_taxonomy(csvfile, ranks_tuple)
    console = Console()
    console.print(import_tax_result, style="italic green")


@cli.command(name="import-plots")
@click.argument("csvfile", required=False)
@click.option(
    "--plot-identifier",
    "-t",
    help="Name of the column in the CSV that corresponds to the plot ID.",
)
@click.option(
    "--location-field",
    "-l",
    help="Name of the column in the CSV that corresponds to the location data.",
)
def import_plots(csvfile: str, plot_identifier: str, location_field: str) -> None:
    """
    Import plot data from a CSV file into the database.

    This command reads plot data from the specified CSV file and imports it into the database.
    The CSV file should contain columns corresponding to the plot data.

    If the `csvfile` argument is not provided, the command will use the path specified in the configuration file.

    Args:
        csvfile (str, optional): Path to the CSV file containing the plot data to be imported.
                                 If not provided, the path specified in the configuration file will be used.
        plot_identifier (str, optional): Name of the column in the CSV file that corresponds to the plot ID.
        location_field (str, optional): Name of the column in the CSV file that corresponds to the location data.

    Examples:
        $ niamoto import-plots plots.csv --plot-identifier=id_location --location-field=geometry
        $ niamoto import-plots plots.csv -t id_location -l geometry
        $ niamoto import-plots -t id_location -l geometry
        $ niamoto import-plots

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist and no default path is provided in the configuration.
        ValueError: If the specified plot identifier column is not found in the CSV file.


    Note:
        - The CSV file should have a header row specifying the column names.
        - The plot identifier column should contain unique identifiers for each plot.
        - The location field column should contain the location data for each plot.
    """
    config = Config()
    db_path = config.get("database", "path")
    plots_config = config.get("sources", "plots")
    default_plot_identifier = plots_config.get("identifier")
    default_location_field = plots_config.get("location_field")
    default_csvfile = plots_config.get("path")

    if not csvfile and default_csvfile and os.path.exists(default_csvfile):
        csvfile = default_csvfile

    if not csvfile or not os.path.exists(csvfile):
        raise FileNotFoundError("CSV file not specified or does not exist.")

    plot_identifier = plot_identifier or default_plot_identifier
    if not plot_identifier:
        raise ValueError("Plot identifier column not specified.")

    location_field = location_field or default_location_field
    if not location_field:
        raise ValueError("Location field column not specified.")

    reset_table(db_path, "plot_ref")

    data_importer = ImporterService(db_path)
    import_plots_result = data_importer.import_plots(
        csvfile, plot_identifier, location_field
    )
    console = Console()
    console.print(import_plots_result, style="italic green")


@cli.command(name="import-occurrences")
@click.argument("csvfile", required=False)
@click.option(
    "--taxon-identifier",
    "-t",
    help="Name of the column in the CSV that corresponds to the taxon ID.",
)
@click.option(
    "--location-field",
    "-l",
    help="Name of the column in the CSV that corresponds to the location data.",
)
def import_occurrences(
    csvfile: str, taxon_identifier: str, location_field: str
) -> None:
    """
    Import occurrence data from a CSV file, analyze it to update the 'mapping' table,
    and link occurrences to their taxons.

    This command reads occurrence data from the specified CSV file, performs an analysis to update the 'mapping' table,
    and establishes links between occurrences and their corresponding taxons based on
    the provided taxon identifier column.

    If the `csvfile` argument is not provided, the command will use the path specified in the configuration file.
    If the `--taxon-identifier` option is not provided, the command will use the taxon identifier
    specified in the configuration file.

    Args:
        csvfile (str, optional): Path to the CSV file containing the occurrence data to be imported and analyzed.
                        If not provided, the path specified in the configuration file will be used.
        taxon_identifier (str, optional): Name of the column in the CSV file that contains the taxon IDs.
                        If not provided, the identifier specified in the configuration file will be used.
       location_field (str, optional): Name of the column in the CSV file that contains the location data.
                        If not provided, the identifier specified in the configuration file will be used.

    Examples:
        $ niamoto import-occurrences occurrences.csv --taxon-identifier=id_taxonref
        $ niamoto import-occurrences occurrences.csv -t id_taxon
        $ niamoto import-occurrences -t id_taxon
        $ niamoto import-occurrences

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist and no default path is provided in the configuration.
        ValueError: If the specified taxon identifier column is not found in the CSV file.
        Exception: If an error occurs during the import process.

    Note:
        - The CSV file should have a header row specifying the column names.
        - The taxon identifier column should contain valid taxon identifiers that match the taxons in the database.
        - The 'mapping' table will be updated based on the analysis of the occurrence data.
    """
    config = Config()
    db_path = config.get("database", "path")
    occurrences_config = config.get("sources", "occurrences")
    default_csvfile = occurrences_config.get("path")
    default_taxon_identifier = occurrences_config.get("identifier")
    default_location_field = occurrences_config.get("location_field")

    if not csvfile and default_csvfile and os.path.exists(default_csvfile):
        csvfile = default_csvfile

    if not csvfile or not os.path.exists(csvfile):
        raise FileNotFoundError("CSV file not specified or does not exist.")

    taxon_identifier = taxon_identifier or default_taxon_identifier
    if not taxon_identifier:
        raise ValueError("Taxon identifier column not specified.")

    location_field = location_field or default_location_field
    if not location_field:
        raise ValueError("Location field column not specified.")

    reset_table(db_path, "occurrences")

    data_importer = ImporterService(db_path)
    import_occ_result = data_importer.import_occurrences(
        csvfile, taxon_identifier, location_field
    )
    console = Console()
    console.print(import_occ_result, style="italic green")


@cli.command(name="import-occurrence-plots")
@click.argument("csvfile", required=False)
def import_occurrence_plot_links(csvfile: str) -> None:
    """
    Import occurrence-plot links from a CSV file.

    This command reads occurrence-plot links from the specified CSV file and imports them into the database.
    The CSV file should contain columns representing the occurrence ID and the corresponding plot ID.

    If the `csvfile` argument is not provided, the command will use the path specified in the configuration file.

    Args:
        csvfile (str, optional): Path to the CSV file containing the occurrence-plot links.
                                 If not provided, the path specified in the configuration file will be used.

    Examples:
        $ niamoto import-occurrence-plots occurrence_plots.csv
        $ niamoto import-occurrence-plots

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified CSV file does not exist and no default path is provided in the configuration.
        ValueError: If the CSV file does not contain the required columns for occurrence-plot links.
        Exception: If an error occurs during the import process.

    Note:
        - The CSV file should have a header row specifying the column names.
        - The required columns in the CSV file are:
            - 'occurrence_id': The ID of the occurrence.
            - 'plot_id': The ID of the plot associated with the occurrence.
        - The occurrence IDs and plot IDs should match the existing occurrences and plots in the database.
    """
    config = Config()
    db_path = config.get("database", "path")
    occurrence_plots_config = config.get("sources", "occurrence-plots")
    default_csvfile = occurrence_plots_config.get("path")

    if not csvfile and default_csvfile and os.path.exists(default_csvfile):
        csvfile = default_csvfile

    if not csvfile or not os.path.exists(csvfile):
        raise FileNotFoundError("CSV file not specified or does not exist.")

    try:
        reset_table(db_path, "occurrences_plots")
        data_importer = ImporterService(db_path)
        import_occ_plot_results = data_importer.import_occurrence_plot_links(csvfile)
        console = Console()
        console.print(import_occ_plot_results, style="italic green")
    except FileNotFoundError as e:
        logger.exception(f"CSV file not found: {e}")
        raise
    except ValueError as e:
        logger.exception(f"Invalid CSV file format: {e}")
        raise
    except Exception as e:
        logger.exception(f"Import failed: {e}")
        raise


@cli.command(name="import-shapes")
def import_shapes() -> None:
    """
    Import shape data from the configuration file into the database.

    This command reads shape data from the configuration file and imports it into the database.
    The configuration file should specify the paths to the shape files along with necessary metadata.

    Returns:
        None

    Raises:
        FileNotFoundError: If any of the specified shape files do not exist.
        ValueError: If the configuration is missing required fields.

    Examples:
        $ niamoto import-shapes

    Note:
        The configuration file should have entries under the 'shapes' section specifying details
        such as the file path, id field, and name field for each shape file.
    """
    config = Config()
    db_path = config.get("database", "path")
    shapes_config = config.get("shapes")

    reset_table(db_path, "shape_ref")

    data_importer = ImporterService(db_path)
    import_shapes_result = data_importer.import_shapes(shapes_config)

    console = Console()
    console.print(import_shapes_result, style="italic green")


@cli.command(name="import-all")
def import_all() -> None:
    """
    Import all data sources as specified in the configuration file.

    This command reads the paths for taxonomy, plots, shapes, occurrences, and occurrence-plot links
    from the configuration file, resets the relevant tables, and imports the data into the database.

    Returns:
        None

    Raises:
        FileNotFoundError: If any of the specified CSV files do not exist.
        ValueError: If any required configurations are missing.
    """
    console = Console()
    config = Config()
    db_path = config.get("database", "path")

    # Reset the tables
    reset_tables(db_path)

    # Import taxonomy
    taxonomy_config = config.get("sources", "taxonomy")
    taxonomy_csvfile = taxonomy_config.get("path")
    taxonomy_ranks = taxonomy_config.get("ranks")
    if not taxonomy_csvfile or not os.path.exists(taxonomy_csvfile):
        raise FileNotFoundError(f"Taxonomy CSV file not found: {taxonomy_csvfile}")
    data_importer = ImporterService(db_path)
    console.print(f"Importing taxonomy from {taxonomy_csvfile}", style="italic green")
    data_importer.import_taxonomy(taxonomy_csvfile, tuple(taxonomy_ranks.split(",")))

    # Import plots
    plots_config = config.get("sources", "plots")
    plots_csvfile = plots_config.get("path")
    plot_identifier = plots_config.get("identifier")
    location_field = plots_config.get("location_field")
    if not plots_csvfile or not os.path.exists(plots_csvfile):
        raise FileNotFoundError(f"Plots CSV file not found: {plots_csvfile}")
    console.print(f"Importing plots from {plots_csvfile}", style="italic green")
    data_importer.import_plots(plots_csvfile, plot_identifier, location_field)

    # Import occurrences
    occurrences_config = config.get("sources", "occurrences")
    occurrences_csvfile = occurrences_config.get("path")
    occurrences_taxon_identifier = occurrences_config.get("identifier")
    occurrences_location_field = occurrences_config.get("location_field")
    if not occurrences_csvfile or not os.path.exists(occurrences_csvfile):
        raise FileNotFoundError(
            f"Occurrences CSV file not found: {occurrences_csvfile}"
        )
    console.print(
        f"Importing occurrences from {occurrences_csvfile}", style="italic green"
    )
    data_importer.import_occurrences(
        occurrences_csvfile, occurrences_taxon_identifier, occurrences_location_field
    )

    # Import occurrence plots
    occurrence_plots_config = config.get("sources", "occurrence-plots")
    occurrence_plots_csvfile = occurrence_plots_config.get("path")
    if not occurrence_plots_csvfile or not os.path.exists(occurrence_plots_csvfile):
        raise FileNotFoundError(
            f"Occurrence plots CSV file not found: {occurrence_plots_csvfile}"
        )
    console.print(
        f"Importing occurrence plots from {occurrence_plots_csvfile}",
        style="italic green",
    )
    data_importer.import_occurrence_plot_links(occurrence_plots_csvfile)

    # Import shapes
    shapes_config = config.get("shapes")
    if not shapes_config:
        raise ValueError("Shapes configuration not found in the config file.")
    data_importer.import_shapes(shapes_config)

    console.print("All data sources imported successfully.", style="bold green")


def reset_table(db_path: str, table_name: str) -> None:
    """
    Reset a single table using DuckDB and recreate it using SQLAlchemy models if applicable.

    Args:
        db_path (str): The path to the DuckDB database file.
        table_name (str): The name of the table to reset.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the reset process.
    """
    console = Console()
    duckdb_connection = duckdb.connect(db_path)  # Connect directly to DuckDB

    try:
        # Drop the table
        duckdb_connection.execute(f"DROP TABLE IF EXISTS {table_name}")

    except Exception as e:
        console.print(f"Error resetting table {table_name}: {e}", style="bold red")
        raise
    finally:
        duckdb_connection.close()

    # Recreate the table using SQLAlchemy models if the model exists
    try:
        db = Database(db_path)
        engine = db.engine

        if table_name in Base.metadata.tables:
            Base.metadata.create_all(engine, tables=[Base.metadata.tables[table_name]])

    except Exception as e:
        console.print(f"Error recreating table {table_name}: {e}", style="bold red")
        raise


def reset_tables(db_path: str) -> None:
    """
    Reset the tables using DuckDB and recreate them using SQLAlchemy models.

    Args:
        db_path (str): The path to the DuckDB database file.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the reset process.
    """
    table_names = [
        "occurrences_plots",
        "occurrences",
        "plot_ref",
        "shape_ref",
        "taxon_ref",
    ]

    console = Console()
    console.print("Initializing database...", style="italic green")

    for table_name in table_names:
        reset_table(db_path, table_name)


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
        config = Config()
        db_path = config.get("database", "path")
        api_mapper = MapperService(db_path)
        if data_source:
            api_mapper.generate_mapping(
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
    "--csv-file",
    type=str,
    help="Path to the CSV file containing the occurrences. If not provided, the source_table_name from the mapping "
    "will be used.",
)
@click.option(
    "--mapping-group",
    type=str,
    help="The specific group to calculate statistics for. If not provided, statistics will be calculated for all "
    "groups.",
)
def calculate_statistics(csv_file: Optional[str], mapping_group: Optional[str]) -> None:
    """
    Calculate statistics based on the mapping file specified in the configuration.

    This command calculates various statistics based on the mapping file defined in the configuration.
    It provides options to calculate statistics for a specific group or for all groups.
    If a CSV file is provided, it will be used as the data source for calculating the statistics.
    Otherwise, the source_table_name from the mapping file will be used.

    Args:
        csv_file (str, optional): Path to the CSV file containing the occurrences.
                                  If not provided, the source_table_name from the mapping will be used.
        mapping_group (str, optional): The specific group to calculate statistics for.
                                  If not provided, statistics will be calculated for all groups.

    Examples:
        $ niamoto calculate-statistics
        $ niamoto calculate-statistics --csv-file occurrences.csv
        $ niamoto calculate-statistics --mapping-group taxon
        $ niamoto calculate-statistics --csv-file plot_occurrences.csv --mapping-group plot

    Raises:
        Exception: If an error occurs during the statistics calculation process.

    Note:
        - If a CSV file is provided, ensure that it has the necessary columns and format for calculating the statistics.
        - The mapping file used for the statistics calculation is specified in the configuration.
    """
    try:
        config = Config()
        db_path = config.get("database", "path")
        data_processor = StatisticService(db_path)
        data_processor.calculate_statistics(csv_file=csv_file, group_by=mapping_group)
        console = Console()
        console.print("Statistics calculated successfully.", style="italic green")
    except Exception as e:
        if "Could not set lock on file" in str(e):
            console = Console()
            console.print(
                "Error: Database is currently locked by another process.",
                style="bold red",
            )
        else:
            console = Console()
            console.print(f"Error while calculating statistics: {e}", style="bold red")


@cli.command(name="generate-content")
@click.option(
    "--mapping-group",
    type=str,
    help="The specific group to generate content for. If not provided, content will be generated for all groups.",
)
def generate_content(mapping_group: Optional[str]) -> None:
    """
    Generate static web pages for each group in the database.

    This command generates static web pages for a specific group or all groups in the database.
    The mapping file used for the content generation is specified in the configuration.

    Args:
        mapping_group (str, optional): The specific group to generate content for.
                                       If not provided, content will be generated for all groups.

    Examples:
        $ niamoto generate-static-content
        $ niamoto generate-static-content --mapping-group taxon
        $ niamoto generate-static-content --mapping-group plot

    Raises:
        Exception: If an error occurs during the content generation process.

    Note:
        - The generated static site files are stored in the configured output directory.
        - The database connection settings are retrieved from the configuration file.
        - The command may take some time to complete, depending on the number of groups in the database.
    """
    try:
        start_time = time.time()
        config = Config()
        generator_service = GeneratorService(config)
        generator_service.generate_content(mapping_group)

        duration = time.time() - start_time
        console = Console()
        console.print(
            f"🌱 Content generation completed in {duration:.2f} seconds.",
            style="italic green",
        )

    except Exception as e:
        console = Console()
        console.print(f"Error while generating static content: {e}", style="bold red")


@cli.command(name="deploy-static-content")
@click.option(
    "--output-dir", default="output", help="Directory containing generated files."
)
@click.option(
    "--provider",
    type=click.Choice(["github", "netlify"]),
    required=True,
    help="Deployment provider (github or netlify).",
)
@click.option(
    "--repo-url", help="GitHub repository URL (required if provider is 'github')."
)
@click.option(
    "--branch", default="main", help="Branch to deploy to (default is 'main')."
)
@click.option("--site-id", help="Netlify site ID (required if provider is 'netlify').")
def deploy(
    output_dir: str, provider: str, repo_url: str, branch: str, site_id: str
) -> None:
    """
    Deploy generated static_site and static_api to the specified provider (GitHub Pages or Netlify).

    Args:
        output_dir (str): Path to the directory containing generated files.
        provider (str): Deployment provider ('github' or 'netlify').
        repo_url (str): GitHub repository URL (required if provider is 'github').
        branch (str): Branch to deploy to (default is 'main').
        site_id (str): Netlify site ID (required if provider is 'netlify').

    Examples:
        $ niamoto deploy --provider=github --output-dir=output --repo-url=https://github.com/username/repo.git
        $ niamoto deploy --provider=netlify --output-dir=output --site-id=your-netlify-site-id
    """
    if provider == "github" and not repo_url:
        raise click.UsageError(
            "The --repo-url option is required when deploying to GitHub Pages."
        )
    if provider == "netlify" and not site_id:
        raise click.UsageError(
            "The --site-id option is required when deploying to Netlify."
        )

    try:
        if provider == "github":
            deploy_to_github(output_dir, repo_url, branch)
        elif provider == "netlify":
            deploy_to_netlify(output_dir, site_id)
        else:
            raise click.UsageError("Unsupported provider specified.")
    except subprocess.CalledProcessError as e:
        console = Console()
        console.print(f"An error occurred while deploying: {e}", style="bold red")


def deploy_to_github(output_dir: str, repo_url: str, branch: str) -> None:
    """
    Deploy generated static_files files to GitHub Pages.

    Args:
        output_dir (str): Path to the directory containing generated files.
        repo_url (str): GitHub repository URL.
        branch (str): Branch to deploy to (default is 'main').

    """
    try:
        os.chdir(output_dir)

        # Initialize git repository if not already initialized
        if not os.path.exists(os.path.join(output_dir, ".git")):
            subprocess.run(["git", "init"], check=True)

        # Check if the remote 'origin' is already set
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True
        )
        if result.returncode != 0:
            subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
        else:
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True)

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Deploy static_files site"], check=True)
        subprocess.run(["git", "push", "--force", "origin", branch], check=True)

        console = Console()
        console.print("Deployment to GitHub Pages successful.", style="italic green")
    except subprocess.CalledProcessError as e:
        console = Console()
        console.print(
            f"An error occurred while deploying to GitHub: {e}", style="bold red"
        )


def deploy_to_netlify(output_dir: str, site_id: str) -> None:
    """
    Deploy generated static_files files to Netlify.

    Args:
        output_dir (str): Path to the directory containing generated files.
        site_id (str): Netlify site ID.

    """
    try:
        subprocess.run(
            ["netlify", "deploy", "--prod", "--dir", output_dir, "--site", site_id],
            check=True,
        )

        console = Console()
        console.print("Deployment to Netlify successful.", style="italic green")
    except subprocess.CalledProcessError as e:
        console = Console()
        console.print(
            f"An error occurred while deploying to Netlify: {e}", style="bold red"
        )


if __name__ == "__main__":
    cli()
