from typing import Any, Hashable


from niamoto.common.database import Database
from niamoto.core.services.mapper import MapperService
from niamoto.core.components.statistics.taxonomy_stats_calculator import (
    TaxonomyStatsCalculator,
)
from niamoto.core.components.statistics.plot_stats_calculator import PlotStatsCalculator


class StatisticService:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.mapper_service = MapperService(db_path)

    def calculate_statistics(self, occurrences: list[dict[Hashable, Any]]) -> None:
        mapping_data = self.mapper_service.get_mapping()

        for group_config in mapping_data:
            group_by = group_config["group_by"]

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

    def calculate_group_statistics(
        self, occurrences: list[dict[Hashable, Any]], group_by: str
    ) -> None:
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
