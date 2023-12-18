from loguru import logger
from pathlib import Path
import click

# import_api.py

from niamoto.data_importer.data_importer import DataImporter
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseWriteError,
)


def import_data(file_path: str, table_name: str, db_path: str) -> None:
    """
    Import data from the provided file path using the orchestrate_data_import function.

    Parameters:
    - file_path (str): Path to the data file to be imported.
    - table_name (str): Name of the table where the data should be imported.
    - db_path (str): The path to the database.

    Raises:
    - ValueError: If any input is invalid or if the file or directory does not exist.
    - FileNotFoundError: If the file does not exist.
    - IsADirectoryError: If the db_path is not a directory.
    - SpecificException: Specific exceptions related to data importing.

    Returns:
    - result (str): Result or status message after data import operation.
    """

    file = Path(file_path)
    db_file = Path(db_path)

    if not file.is_file():
        raise ValueError(f"File at {file_path} does not exist")

    # Vérifiez si le répertoire parent du fichier de base de données existe
    if not db_file.parent.is_dir():
        raise ValueError(f"Database directory {db_file.parent} does not exist")

    # Si vous voulez vérifier également l'existence du fichier de base de données :
    if not db_file.is_file():
        raise ValueError(f"Database file {db_path} does not exist")

    try:
        data_importer = DataImporter(db_path)
        data_importer.orchestrate_data_import(file_path, table_name)

        click.secho(
            f"Data imported successfully from {file_path} to {table_name}",
            fg="green",
        )

    except (FileReadError, DataValidationError, DatabaseWriteError) as e:
        logger.error(f"Error during data import: {e}")
        raise
