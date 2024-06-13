from typing import Any, Optional, Hashable

import pandas as pd
import sqlalchemy
from loguru import logger
from niamoto.common.config import Config
from niamoto.core.services.mapper import MapperService
from niamoto.core.services.statistics import StatisticService


class ApiStatistics:
    """
    A class used to calculate and retrieve statistics for the Niamoto project.

    Attributes:
        config (Config): The configuration settings for the Niamoto project.
        db_path (str): The path to the database.
    """

    def __init__(self) -> None:
        """
        Initializes the ApiStatistics with the database path.
        """
        self.config = Config()
        self.db_path = self.config.get("database", "path")

    def calculate_group_statistics(
        self, group_by: str, csv_file: Optional[str] = None
    ) -> None:
        """
        Calculates group statistics using the StatisticService.

        Args:
            group_by (str): The type of grouping to calculate the statistics for (e.g., taxon, plot, commune).
            csv_file (Optional[str]): Path to the CSV file to be used for calculating statistics.
        """
        try:
            statistic_service = StatisticService(self.db_path)
            occurrences = self.get_occurrences(group_by, csv_file)
            statistic_service.calculate_group_statistics(occurrences, group_by)
        except Exception as e:
            logger.exception(
                f"Error calculating statistics for group '{group_by}': {e}"
            )

    def calculate_all_statistics(self, csv_file: Optional[str] = None) -> None:
        """
        Calculates all statistics using the StatisticService.

        Args:
            csv_file (Optional[str]): Path to the CSV file to be used for calculating statistics.
        """
        try:
            statistic_service = StatisticService(self.db_path)
            occurrences = self.get_occurrences(None, csv_file)
            statistic_service.calculate_statistics(occurrences)
        except Exception as e:
            logger.exception(f"Error calculating statistics: {e}")

    def get_occurrences(
        self, group_by: Optional[str], csv_file: Optional[str]
    ) -> list[dict[Hashable, Any]]:
        """
        Retrieves occurrences either from a CSV file or from the database.

        Args:
            group_by (Optional[str]): The type of grouping to retrieve the occurrences for (e.g., taxon, plot, commune).
            csv_file (Optional[str]): Path to the CSV file to be used for retrieving occurrences.

        Returns:
            list[dict[Hashable, Any]]: A list of occurrences.
        """
        if csv_file:
            # Load occurrences from the specified CSV file
            occurrences = self.load_occurrences_from_csv(csv_file)
        else:
            # Retrieve the target table name from the mapping
            mapper_service = MapperService(self.db_path)
            if group_by:
                group_config = mapper_service.get_group_config(group_by)
                source_table_name = group_config.get("source_table_name")
            else:
                mapping = mapper_service.get_mapping()
                source_table_name = mapping[0].get("source_table_name")

            # Retrieve the occurrences from the target table
            occurrences = self.load_occurrences_from_database(source_table_name)

        return occurrences

    @staticmethod
    def load_occurrences_from_csv(csv_file: str) -> list[dict[Hashable, Any]]:
        """
        Loads occurrences from a CSV file.

        Args:
            csv_file (str): Path to the CSV file to be loaded.

        Returns:
            list[dict[Hashable, Any]]: A list of occurrences.
        """
        # Read the CSV file using pandas
        df = pd.read_csv(csv_file)

        # Convert the DataFrame into a list of dictionaries
        occurrences = df.to_dict("records")

        return occurrences

    def load_occurrences_from_database(
        self, table_name: Optional[Any]
    ) -> list[dict[Hashable, Any]]:
        """
        Loads occurrences from the database.

        Args:
            table_name (Optional[Any]): The name of the table in the database to load occurrences from.

        Returns:
            list[dict[Hashable, Any]]: A list of occurrences.
        """
        # Create a connection to the database
        engine = sqlalchemy.create_engine(f"duckdb:///{self.db_path}")

        # Execute a SQL query to retrieve all occurrences from the specified table
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

        # Convert the DataFrame into a list of dictionaries
        occurrences = df.to_dict("records")

        return occurrences
