from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseWriteError,
)
from niamoto.data_importer.data_reader import DataReader
from niamoto.data_importer.data_validator import validate_data
from niamoto.data_importer.data_writer import DataWriter
from loguru import logger
import mimetypes


class DataImporter:
    """
    A class that provides methods for importing data into a database.
    """

    def __init__(self, db_path: str):
        """
        Initialize a DataImporter instance.

        Parameters:
            db_path (str): The path to the database.
        """
        self.data_writer = DataWriter(db_path)

    def orchestrate_data_import(self, file_path: str, table_name: str) -> None:
        """
        Orchestrates the process of importing data from a file to a database table.

        Parameters:
            file_path (str): The path to the data file.
            table_name (str): The name of the table where the data will be imported.

        Raises:
            ValueError: If the file type is unsupported or data validation fails.
        """
        # Determine the file type based on its extension
        mime_type, _ = mimetypes.guess_type(file_path)

        try:
            if mime_type == "text/csv":
                data = DataReader.read_csv_file(file_path)
            else:
                raise FileReadError(f"Unsupported file type: {mime_type}")

            if not validate_data(data, table_name):
                raise DataValidationError("Data validation failed")

            self.data_writer.write_to_db(table_name, data)

        except (FileReadError, DataValidationError, DatabaseWriteError) as e:
            logger.error(f"Error during data import: {e}")
            raise
        except Exception as e:
            # Capture des exceptions inattendues
            logger.error(f"Unexpected error during data import: {e}")
            raise


# Example usage:
# importer = DataImporter('sqlite:///my_database.db')
# importer.orchestrate_data_import('path/to/file.csv', 'table_name')
