from typing import Any, Optional

from loguru import logger

from niamoto.common.config import Config
from niamoto.core.services.mapper import MapperService


class ApiMapper:
    """
    A class used to map data for the Niamoto project.

    Attributes:
        config (Config): The configuration settings for the Niamoto project.
        db_path (str): The path to the database.
    """

    def __init__(self) -> None:
        """
        Initializes the ApiMapper with the database path.
        """
        self.config = Config()
        self.db_path = self.config.get("database", "path")

    def generate_mapping_from_csv(
        self,
        csvfile: str,
        group_by: str,
        reference_table_name: Optional[str],
        reference_data_path: Optional[str],
    ) -> Any:
        """
        Generates a mapping from a CSV file.

        Args:
            csvfile (str): Path to the CSV file to generate mapping from.
            group_by (str): The type of grouping to generate the mapping for (e.g., taxon, plot, commune).
            reference_table_name (Optional[str]): The name of the reference table in the database.
            reference_data_path (Optional[str]): The path to the reference table file (e.g., GeoPackage).

        Returns:
            Any: Confirmation message.
        """
        try:
            # Initialize the data import service
            mapper_service = MapperService(self.db_path)

            # Call the service to import the taxonomy
            mapper_service.generate_mapping(
                csvfile, group_by, reference_table_name, reference_data_path
            )

            return "Mapping generated"

        except Exception as e:
            logger.exception(f"Error importing 'occurrences' data: {e}")

    def add_new_mapping(self, field: str) -> Any:
        """
        Adds a new mapping to the database.

        Args:
            field (str): New field to be added to the mapping.

        Returns:
            Any: Confirmation message.
        """
        try:
            # Initialize the data import service
            mapper_service = MapperService(self.db_path)

            # Call the service to import the taxonomy
            mapper_service.add_mapping(field)

            return "Mapping added"

        except Exception as e:
            logger.exception(f"Error importing 'occurrences' data: {e}")
