from typing import Any, Hashable, Optional

import pandas as pd
import sqlalchemy

from loguru import logger

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.core.components.statistics.shape_stats_calculator import (
    ShapeStatsCalculator,
)
from niamoto.core.components.statistics.taxonomy_stats_calculator import (
    TaxonomyStatsCalculator,
)
from niamoto.core.components.statistics.plot_stats_calculator import PlotStatsCalculator


class StatisticService:
    """
    The StatisticService class provides methods to calculate statistics.
    """

    def __init__(self, db_path: str, config: Config):
        """
        Initializes a new instance of the StatisticService.

        Args:
            db_path (str): The path to the database file.
            config (Config): The configuration instance.
        """
        self.db_path = db_path
        self.db = Database(db_path)
        self.config = config

    def calculate_statistics(
        self, csv_file: Optional[str] = None, group_by: Optional[str] = None
    ) -> None:
        """
        Calculates statistics based on configuration.

        Args:
            group_by (str): The type of grouping (e.g., taxon, plot, shape).
            csv_file (Optional[str]): Optional CSV file path to use instead of configured source.
        """
        try:
            # Get occurrences data
            occurrences = self.get_occurrences(group_by, csv_file)

            # Get stats configuration
            stats_config = self.config.get_stats_config()

            if group_by:
                # Calculate for specific group
                group_stats = next(
                    (g for g in stats_config if g["group_by"] == group_by), None
                )
                if group_stats:
                    self.calculate_group_statistics(occurrences, group_stats)
            else:
                # Calculate for all groups
                for group_stats in stats_config:
                    self.calculate_group_statistics(occurrences, group_stats)

        except Exception as e:
            logger.exception(f"Error calculating statistics: {e}")

    def get_occurrences(
        self, group_by: Optional[str], csv_file: Optional[str]
    ) -> list[dict[Hashable, Any]]:
        """
        Retrieves occurrences data.

        Args:
            group_by (Optional[str]): Optional group by parameter.
            csv_file (Optional[str]): Optional CSV file path.

        Returns:
            list[dict[Hashable, Any]]: List of occurrences.
        """
        if csv_file:
            return self.load_occurrences_from_csv(csv_file)

        # Get source path from configuration
        source_config = self.config.data_sources.get("occurrences", {})
        source_path = source_config.get("path")

        if not source_path:
            raise ValueError("No occurrence source path configured")

        return self.load_occurrences_from_csv(source_path)

    def calculate_group_statistics(
        self, occurrences: list[dict[Hashable, Any]], group_config: dict
    ) -> None:
        """
        Calculate statistics for a group based on configuration.

        Args:
            occurrences (list[dict[Hashable, Any]]): The occurrences data.
            group_config (dict): Configuration for the group.
        """
        group_by = group_config["group_by"]

        if group_by == "taxon":
            taxon_calculator = TaxonomyStatsCalculator(
                self.db, occurrences, group_config
            )
            taxon_calculator.calculate_taxonomy_stats()
        elif group_by == "plot":
            plot_calculator = PlotStatsCalculator(self.db, occurrences, group_config)
            plot_calculator.calculate_plot_stats()
        elif group_by == "shape":
            shape_calculator = ShapeStatsCalculator(self.db, occurrences, group_config)
            shape_calculator.calculate_shape_stats()

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
        engine = sqlalchemy.create_engine(f"sqlite:///{self.db_path}")

        # Execute a SQL query to retrieve all occurrences from the specified table
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

        # Convert the DataFrame into a list of dictionaries
        occurrences = df.to_dict("records")

        return occurrences
