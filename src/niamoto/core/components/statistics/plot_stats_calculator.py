from typing import List, Dict, Any, Hashable
from .statistics_calculator import StatisticsCalculator
from ...models import PlotRef


class PlotStatsCalculator(StatisticsCalculator):
    def calculate_plot_stats(self) -> None:
        # Retrieve the unique identifiers of the plots from PlotRef
        plot_ids = self.get_unique_plot_ids()

        for plot_id in plot_ids:
            self.process_group(plot_id)

    def process_group(self, plot_id: int) -> None:
        # Filter the occurrences related to the current plot from the occurrences_plots table
        plot_occurrences = self.get_plot_occurrences(plot_id)

        # Calculate the general statistics for each field of the mapping
        stats = self.calculate_stats(plot_id, plot_occurrences)

        # Calculate the specific statistics for the plots
        specific_stats = self.calculate_specific_stats(plot_id, plot_occurrences)
        stats.update(specific_stats)

        # Create or update the entry in the plot_stats table
        self.create_or_update_stats_entry(plot_id, stats)

    def calculate_specific_stats(
        self, plot_id: int, plot_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        frequencies = self.calculate_frequencies(plot_id, plot_occurrences)
        return frequencies

    def calculate_frequencies(
        self, plot_id: int, plot_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        frequencies: Dict[str, Any] = {}
        # Calculate the specific frequencies for the plots (altitude, rainfall, etc.)
        # ...
        return frequencies

    def get_unique_plot_ids(self) -> List[int]:
        # Retrieve the unique identifiers of the plots from PlotRef
        plot_ids = self.db.session.query(PlotRef.id).all()
        return [plot_id[0] for plot_id in plot_ids]

    def get_plot_occurrences(self, plot_id: int) -> list[dict[Hashable, Any]]:
        occurrence_identifier = self.identifier
        query = f"""
            SELECT o.*
            FROM occurrences o
            JOIN occurrences_plots op ON o.{occurrence_identifier} = op.occurrence_id
            WHERE op.plot_id = {plot_id}
        """
        result = self.db.engine.execute(query)  # type: ignore
        plot_occurrences = [dict(row) for row in result]
        return plot_occurrences
