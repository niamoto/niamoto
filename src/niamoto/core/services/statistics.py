from typing import Any, Hashable


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
        self.db = Database(db_path)
        self.mapper_service = MapperService(db_path)

    def calculate_statistics(self, occurrences: list[dict[Hashable, Any]]) -> None:
        """
        Calculate statistics for a given list of occurrences.

        Args:
            occurrences (list[dict[Hashable, Any]]): The list of occurrences to calculate statistics for.
        """
        mapping_data = self.mapper_service.get_mapping()

        for group_config in mapping_data:
            group_by = group_config["group_by"]
            # TODO: Remove this check once all group_by parameters are implemented
            if group_by != "shape":
                self.calculate_group_statistics(occurrences, group_by)

    def calculate_group_statistics(
        self, occurrences: list[dict[Hashable, Any]], group_by: str
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
