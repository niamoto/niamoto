from typing import Any, Hashable, Optional

import pandas as pd
import sqlalchemy

from loguru import logger
from niamoto.common.database import Database
from niamoto.core.components.statistics.shape_stats_calculator import (
    ShapeStatsCalculator,
)
from niamoto.core.services.mapper import MapperService
from niamoto.core.components.statistics.taxonomy_stats_calculator import (
    TaxonomyStatsCalculator,
)
from niamoto.core.components.statistics.plot_stats_calculator import PlotStatsCalculator


class StatisticService:
    """
    The StatisticService class provides methods to calculate statistics.
    """

    def __init__(self, db_path: str):
        """
        Initializes a new instance of the StatisticService with a given database path.

        Args:
            db_path (str): The path to the database file.
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.mapper_service = MapperService(db_path)

    def calculate_statistics(
        self, csv_file: Optional[str] = None, group_by: Optional[str] = None
    ) -> None:
        """
        Calculates group statistics using the StatisticService.

        Args:
            group_by (str): The type of grouping to calculate the statistics for (e.g., taxon, plot, shape).
            csv_file (Optional[str]): Path to the CSV file to be used for calculating statistics.
        """
        try:
            occurrences = self.get_occurrences(group_by, csv_file)
            mapping_data = self.mapper_service.get_aggregations()

            if group_by:
                # Calculate statistics for the specified group_by
                self.calculate_group_statistics(occurrences, group_by)
            else:
                # Calculate statistics for all group_by in the configuration
                for group_config in mapping_data:
                    group_by = group_config["group_by"]
                    self.calculate_group_statistics(occurrences, group_by)
        except Exception as e:
            logger.exception(f"Error calculating statistics: {e}")

    def calculate_group_statistics(
        self, occurrences: list[dict[Hashable, Any]], group_by: Optional[str]
    ) -> None:
        """
        Calculate group statistics for a given list of occurrences and a group by parameter.

        Args:
            occurrences (list[dict[Hashable, Any]]): The list of occurrences to calculate statistics for.
            group_by (str): The parameter to group the occurrences by.
        """
        group_config = self.mapper_service.get_group_config(group_by)

        if group_config:
            if group_by == "taxon":
                taxon_calculator = TaxonomyStatsCalculator(
                    self.db, self.mapper_service, occurrences, group_by
                )
                taxon_calculator.calculate_taxonomy_stats()
            elif group_by == "plot":
                plot_calculator = PlotStatsCalculator(
                    self.db, self.mapper_service, occurrences, group_by
                )
                plot_calculator.calculate_plot_stats()
            elif group_by == "shape":
                shape_calculator = ShapeStatsCalculator(
                    self.db, self.mapper_service, occurrences, group_by
                )
                shape_calculator.calculate_shape_stats()

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
                mapping = mapper_service.get_aggregations()
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
