import time
from collections import Counter
from typing import List, Dict, Any, Hashable, Union

import geopandas as gpd
import pandas as pd
from rich.progress import track
from sqlalchemy import Table, MetaData, Column, Integer

from niamoto.common.database import Database
from niamoto.core.models import PlotRef, TaxonRef
from .statistics_calculator import StatisticsCalculator
from ...services.mapper import MapperService


class PlotStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for plots.

    Inherits from:
        StatisticsCalculator
    """

    def __init__(
        self,
        db: Database,
        mapper_service: MapperService,
        occurrences: list[dict[Hashable, Any]],
        group_by: str,
    ):
        super().__init__(db, mapper_service, occurrences, group_by)
        self.plot_identifier = self.mapper_service.get_source_identifier("plots")
        self.plots_data = self.load_plots_data()

    def load_plots_data(self) -> pd.DataFrame:
        plots_path = self.mapper_service.get_source_path("plots")
        gdf = gpd.read_file(plots_path)
        return gdf

    def calculate_plot_stats(self) -> None:
        """
        Calculate statistics for all plots.
        """
        start_time = time.time()

        try:
            plots = self._retrieve_all_plots()

            self.initialize_stats_table()

            for plot in track(plots, description="Processing Plots..."):
                self.process_plot(plot)

        except Exception as e:
            self.console.print(f"An error occurred: {e}", style="bold red")
        finally:
            total_time = time.time() - start_time
            self.console.print(
                f"Total processing time: {total_time:.2f} seconds", style="italic blue"
            )

    def process_plot(self, plot: PlotRef) -> None:
        """
        Process a plot.

        Args:
            plot ('niamoto.core.models.models.PlotRef'): The plot to process.
        """
        try:
            plot_id = self._extract_plot_id(plot)
            if plot_id is None:
                return

            plot_occurrences = self.get_plot_occurrences(plot_id)
            if not plot_occurrences:
                return

            stats = self.calculate_stats(plot_id, plot_occurrences)

            self.create_or_update_stats_entry(plot_id, stats)

        except Exception as e:
            self.console.print(
                f"Failed to process plot {plot.id}: {e}", style="bold red"
            )

    def calculate_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a group.

        Args:
            group_id (int): The group id.
            group_occurrences (list[dict[Hashable, Any]]): The group occurrences.

        Returns:
            Dict[str, Any]: The statistics.
        """
        stats: Dict[str, Union[int, Dict[str, Any], pd.Series[Any], float]] = {}

        # Convert occurrences to pandas DataFrame
        df_occurrences = pd.DataFrame(group_occurrences)

        # Retrieve the plot object using group_id
        plot = (
            self.db.session.query(PlotRef)
            .filter(PlotRef.id_locality == group_id)
            .first()
        )
        plot_data = (
            self.plots_data[self.plots_data[self.plot_identifier] == group_id].iloc[0]
            if plot
            else None
        )

        # Iterate over fields in the mapping
        for field, field_config in self.fields.items():
            source_field = field_config.get("source_field")
            source = field_config.get("source")
            transformations = field_config.get("transformations", [])

            if source_field is None:
                # Special field without source_field (ex: total_occurrences)
                if transformations:
                    for transformation in transformations:
                        transform_name = transformation.get("name")
                        if transform_name == "count":
                            stats[field] = len(group_occurrences)
                            break
                        elif transform_name == "top":
                            stats[field] = self.calculate_top_items(
                                group_occurrences, field_config
                            )

            elif source == "occurrences":
                # Binary field (ex: um_occurrences)
                if (
                    field_config.get("field_type") == "BOOLEAN"
                    and source_field in df_occurrences.columns
                ):
                    value_counts = df_occurrences[source_field].value_counts()
                    stats[f"{field}_true"] = value_counts.get(True, 0)
                    stats[f"{field}_false"] = value_counts.get(False, 0)

                # Geolocation field (ex: occurrence_location)
                elif (
                    field_config.get("field_type") == "GEOGRAPHY"
                    and source_field in df_occurrences.columns
                ):
                    coordinates = self.extract_coordinates(df_occurrences, source_field)
                    stats[field] = {
                        "type": "MultiPoint",
                        "coordinates": coordinates,
                    }

                else:
                    # Other fields
                    field_values = df_occurrences[source_field]
                    field_values = field_values[
                        (field_values != 0) & (field_values.notnull())
                    ]

                    # Calculate transformations
                    if transformations:
                        for transformation in transformations:
                            transform_name = transformation.get("name")
                            field_name = (
                                f"{field}_{transform_name}"
                                if transform_name
                                else f"{field}"
                            )

                            if (
                                hasattr(pd.Series, transform_name)
                                and len(field_values) > 0
                            ):
                                transform_func = getattr(pd.Series, transform_name)
                                transform_result = transform_func(field_values)
                                if isinstance(transform_result, pd.Series):
                                    stats[field_name] = transform_result.round(2)
                                else:
                                    stats[field_name] = round(transform_result, 2)

                    # Calculate bins
                    bins_config = field_config.get("bins")
                    if bins_config:
                        bins = bins_config["values"]
                        if bins and len(field_values) > 0:
                            bin_percentages = self.calculate_bins(
                                field_values.tolist(), bins
                            )
                            stats[f"{field}_bins"] = bin_percentages

            elif source == "plots" and plot_data is not None:
                if source_field:
                    if field_config.get("field_type") == "GEOGRAPHY":
                        stats[field] = self.extract_coordinates_from_geometry(
                            plot_data[source_field]
                        )
                    else:
                        stats[field] = plot_data[source_field]
                else:
                    stats[field] = plot_data[field]

        return stats

    def extract_coordinates_from_geometry(self, geometry: Any) -> Dict[str, Any]:
        """
        Extract coordinates from GeoDataFrame geometry.

        Args:
            geometry (Any): The geometry object.

        Returns:
            Dict[str, Any]: The type of geometry and the coordinates.
        """
        if geometry.geom_type == "Point":
            return {"type": "Point", "coordinates": [geometry.x, geometry.y]}
        elif geometry.geom_type == "LineString":
            return {
                "type": "LineString",
                "coordinates": [[point.x, point.y] for point in geometry.coords],
            }
        elif geometry.geom_type == "Polygon":
            return {
                "type": "Polygon",
                "coordinates": [
                    [[point.x, point.y] for point in ring.coords]
                    for ring in geometry.interiors
                ],
            }
        else:
            return {"type": "Unknown", "coordinates": []}

    def get_plot_occurrences(self, plot_id: int) -> list[dict[Hashable, Any]]:
        """
        Get plot occurrences.

        Args:
            plot_id (int): The plot ID to get occurrences for.

        Returns:
            list[dict[Hashable, Any]]: The plot occurrences.
        """
        occurrences_plots = Table(
            "occurrences_plots",
            MetaData(),
            Column("id_occurrence", Integer, primary_key=True),
            Column("id_plot", Integer, primary_key=True),
        )

        occurrence_ids = (
            self.db.session.query(occurrences_plots.c.id_occurrence)
            .filter(occurrences_plots.c.id_plot == plot_id)
            .all()
        )
        occurrence_ids = [op[0] for op in occurrence_ids]
        return [
            occ for occ in self.occurrences if occ[self.identifier] in occurrence_ids
        ]

    def _retrieve_all_plots(self) -> List[PlotRef]:
        """
        Retrieve all plots from the database.

        Returns:
            List[PlotRef]: A list of plot references.
        """
        return self.db.session.query(PlotRef).all()

    @staticmethod
    def _extract_plot_id(plot: PlotRef) -> int:
        """
        Extract the plot ID value.

        Args:
            plot (PlotRef): The plot from which to extract the ID.

        Returns:
            int: The plot ID.
        """
        return plot.id_locality

    def calculate_top_values(
        self, plot_occurrences: list[dict[Hashable, Any]], field_config: dict
    ) -> dict:
        """
        Calculate the top values based on the configuration.

        Args:
            plot_occurrences (list[dict[Hashable, Any]]): The plot occurrences.
            field_config (dict): The field configuration.

        Returns:
            dict: The top values.
        """
        target_ranks = field_config["transformations"][0]["target_ranks"]
        count = field_config["transformations"][0]["count"]

        counts = Counter()
        for occ in plot_occurrences:
            taxon_id = occ.get("taxon_ref_id")
            if taxon_id:
                taxon = self.db.session.query(TaxonRef).get(taxon_id)
                if taxon and taxon.rank_name in target_ranks:
                    counts[taxon.full_name] += 1

        top_values = counts.most_common(count)
        return {f"{rank}": value for rank, value in top_values}

    @staticmethod
    def calculate_bins(values: List[float], bins: List[float]) -> dict[str, float]:
        """
        Categorizes the field data into specified bins and calculates the frequencies for each category.
        The frequencies are then converted to percentages and returned as a dictionary.

        Args:
            values (List[float]): The list of field values.
            bins (List[int]): The list of bins to categorize the data.

        Returns:
            dict[Any, Any]: A dictionary containing the frequencies of the field data categories as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        # Convert the list of values to a pandas Series
        data = pd.Series(values)

        # Distribute the data into categories
        binned_data = pd.cut(data.dropna(), bins=bins, right=False)

        # Calculate the frequencies for each category
        data_counts = binned_data.value_counts(sort=False, normalize=True)

        # Convert to percentages
        data_percentages = data_counts.apply(
            lambda x: round(x * 100, 2) if not pd.isna(x) else 0.0
        )

        # Convert to dictionary
        return {
            str(interval.left): percentage
            for interval, percentage in data_percentages.items()
            if isinstance(interval, pd.Interval)
        }
