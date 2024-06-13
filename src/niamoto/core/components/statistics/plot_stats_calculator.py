import math
import time
from collections import Counter
from typing import List, Dict, Any, Hashable, Union

import pandas as pd
from rich.progress import track
from sqlalchemy import Table, MetaData, Column, Integer

from niamoto.core.models import PlotRef, TaxonRef
from .statistics_calculator import StatisticsCalculator


def calculate_basal_area(occurrences: List[Dict[Hashable, Any]]) -> float:
    """
    Calculate the basal area of the plot.

    Args:
        occurrences (List[Dict[Hashable, Any]]): The occurrences to calculate statistics for.

    Returns:
        float: The basal area of the plot.
    """
    total_basal_area = 0.0
    for occ in occurrences:
        dbh = occ.get('dbh', 0)
        if dbh > 0:
            basal_area = math.pi * (dbh / 2) ** 2 / 10000  # Convert to m²
            total_basal_area += basal_area
    return round(total_basal_area, 2)


def calculate_shannon_index(occurrences: List[Dict[Hashable, Any]], taxon_dict: Dict[int, TaxonRef]) -> float:
    """
    Calculate the Shannon diversity index.

    Args:
        occurrences (List[Dict[Hashable, Any]]): The occurrences to calculate statistics for.
        taxon_dict (Dict[int, TaxonRef]): The dictionary of all taxons.

    Returns:
        float: The Shannon diversity index.
    """
    species_counts = Counter()
    for occ in occurrences:
        taxon_id = occ.get('taxon_ref_id')
        if taxon_id and taxon_id in taxon_dict:
            taxon = taxon_dict[taxon_id]
            if taxon.rank_name.lower() in ['id_species', 'id_infra']:
                species_counts[taxon_id] += 1

    total_individuals = sum(species_counts.values())
    shannon_index = -sum(
        (count / total_individuals) * math.log(count / total_individuals) for count in species_counts.values())
    return round(shannon_index, 2)


def calculate_pielou_evenness(occurrences: List[Dict[Hashable, Any]], taxon_dict: Dict[int, TaxonRef]) -> float:
    """
    Calculate the Pielou evenness index.

    Args:
        occurrences (List[Dict[Hashable, Any]]): The occurrences to calculate statistics for.
        taxon_dict (Dict[int, TaxonRef]): The dictionary of all taxons.

    Returns:
        float: The Pielou evenness index.
    """
    shannon_index = calculate_shannon_index(occurrences, taxon_dict)
    species_counts = Counter()
    for occ in occurrences:
        taxon_id = occ.get('taxon_ref_id')
        if taxon_id and taxon_id in taxon_dict:
            taxon = taxon_dict[taxon_id]
            if taxon.rank_name.lower() in ['id_species', 'id_infra']:
                species_counts[taxon_id] += 1

    species_richness = len(species_counts)
    if species_richness > 1:
        pielou_evenness = shannon_index / math.log(species_richness)
        return round(pielou_evenness, 2)
    return 0.0


def calculate_simpson_index(occurrences: List[Dict[Hashable, Any]], taxon_dict: Dict[int, TaxonRef]) -> float:
    """
    Calculate the Simpson diversity index.

    Args:
        occurrences (List[Dict[Hashable, Any]]): The occurrences to calculate statistics for.
        taxon_dict (Dict[int, TaxonRef]): The dictionary of all taxons.

    Returns:
        float: The Simpson diversity index.
    """
    species_counts = Counter()
    for occ in occurrences:
        taxon_id = occ.get('taxon_ref_id')
        if taxon_id and taxon_id in taxon_dict:
            taxon = taxon_dict[taxon_id]
            if taxon.rank_name.lower() in ['id_species', 'id_infra']:
                species_counts[taxon_id] += 1

    total_individuals = sum(species_counts.values())
    simpson_index = 1 - sum((count / total_individuals) ** 2 for count in species_counts.values())
    return round(simpson_index, 2)


def calculate_biomass(occurrences: List[Dict[Hashable, Any]], a: float = 0.0509, b: float = 2.5) -> float:
    """
    Calculate the biomass of the plot in tonnes per hectare.

    Args:
        occurrences (List[Dict[Hashable, Any]]): The occurrences to calculate statistics for.
        a (float): The coefficient for the allometric equation.
        b (float): The exponent for the allometric equation.

    Returns:
        float: The biomass of the plot in tonnes per hectare.
    """
    total_biomass_kg = 0.0
    for occ in occurrences:
        dbh = occ.get('dbh', 0)
        if dbh > 0:
            # DBH should be in cm for the formula
            biomass = a * (dbh ** b)
            total_biomass_kg += biomass

    # Convert biomass to tonnes
    total_biomass_tonnes = total_biomass_kg / 1000

    # Since each plot is 1 hectare, biomass in tonnes per hectare is the same as total biomass in tonnes
    return round(total_biomass_tonnes, 2)


class PlotStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for plots.

    Inherits from:
        StatisticsCalculator
    """

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
            plot (PlotRef): The plot to process.
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
            self.console.print(f"Failed to process plot {plot.id}: {e}", style="bold red")

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
        plot = self.db.session.query(PlotRef).filter(PlotRef.id_locality == group_id).first()

        # Iterate over fields in the mapping
        for field, field_config in self.fields.items():
            source_field = field_config.get("source_field")

            if source_field is None:
                # Special field without source_field (ex: total_occurrences)
                if field_config.get("transformations"):
                    for transformation in field_config.get("transformations", []):
                        if transformation.get("name") == "count":
                            stats[field] = len(group_occurrences)
                            break

            elif field == "plot_area" and plot:
                # Special case for plot_area
                stats[field] = {
                    "type": "Point",
                    "coordinates": self.extract_coordinates_from_geometry(plot.geometry)
                }

            elif source_field in df_occurrences.columns:
                # Binary field (ex: um_occurrences)
                if field_config.get("field_type") == "BOOLEAN":
                    value_counts = df_occurrences[source_field].value_counts()
                    stats[f"{field}_true"] = value_counts.get(True, 0)
                    stats[f"{field}_false"] = value_counts.get(False, 0)

                # Geolocation field (ex: occurrence_location)
                # elif field_config.get("field_type") == "GEOGRAPHY":
                #     coordinates = self.extract_coordinates(df_occurrences)
                #     stats[f"{field}"] = {
                #         "type": "MultiPoint",
                #         "coordinates": coordinates,
                #     }

                else:
                    # Other fields
                    field_values = df_occurrences[source_field]
                    field_values = field_values[
                        (field_values != 0) & (field_values.notnull())
                        ]

                    # Calculate transformations
                    transformations = field_config.get("transformations", [])
                    if transformations:
                        for transformation in transformations:
                            transform_name = transformation.get("name")
                            if hasattr(pd.Series, transform_name) and len(field_values) > 0:
                                transform_func = getattr(pd.Series, transform_name)
                                transform_result = transform_func(field_values)
                                if isinstance(transform_result, pd.Series):
                                    stats[f"{field}_{transform_name}"] = transform_result.round(2)
                                else:
                                    stats[f"{field}_{transform_name}"] = round(transform_result, 2)

                    # Calculate bins
                    bins_config = field_config.get("bins")
                    if bins_config:
                        bins = bins_config["values"]
                        if bins and len(field_values) > 0:
                            bin_percentages = self.calculate_bins(field_values.tolist(), bins)
                            stats[f"{field}_bins"] = bin_percentages

        # Add group-specific stats
        specific_stats = self.calculate_specific_stats(group_id, group_occurrences)
        stats.update(specific_stats)

        return stats

    @staticmethod
    def extract_coordinates_from_geometry(geometry: str) -> List[float]:
        """
        Extract coordinates from geometry string.

        Args:
            geometry (str): The geometry string.

        Returns:
            List[float]: The coordinates.
        """
        coordinates = geometry.replace("POINT (", "").replace(")", "").split()
        return [float(coord) for coord in coordinates]

    def get_plot_occurrences(self, plot_id: int) -> list[dict[Hashable, Any]]:
        """
        Get plot occurrences.

        Args:
            plot_id (int): The plot ID to get occurrences for.

        Returns:
            list[dict[Hashable, Any]]: The plot occurrences.
        """
        occurrences_plots = Table(
            'occurrences_plots', MetaData(),
            Column('id_occurrence', Integer, primary_key=True),
            Column('id_plot', Integer, primary_key=True)
        )

        occurrence_ids = (
            self.db.session.query(occurrences_plots.c.id_occurrence)
            .filter(occurrences_plots.c.id_plot == plot_id)
            .all()
        )
        occurrence_ids = [op[0] for op in occurrence_ids]
        return [occ for occ in self.occurrences if occ[self.identifier] in occurrence_ids]

    def calculate_specific_stats(
            self, plot_id: int, plot_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate specific statistics for a plot.

        Args:
            plot_id (int): The plot id.
            plot_occurrences (list[dict[Hashable, Any]]): The plot occurrences.

        Returns:
            Dict[str, Any]: The specific statistics.
        """
        taxon_ids = {occ.get('taxon_ref_id') for occ in plot_occurrences if occ.get('taxon_ref_id')}
        taxons = self.db.session.query(TaxonRef).filter(TaxonRef.id.in_(taxon_ids)).all()
        taxon_dict = {taxon.id: taxon for taxon in taxons}

        specific_stats = {
            'top_family': self.calculate_top_families(plot_occurrences, 10),
            'top_species': self.calculate_top_species(plot_occurrences, 10),
            'basal_area': calculate_basal_area(plot_occurrences),
            'shannon': calculate_shannon_index(plot_occurrences, taxon_dict),
            'pielou': calculate_pielou_evenness(plot_occurrences, taxon_dict),
            'simpson': calculate_simpson_index(plot_occurrences, taxon_dict),
            'biomass': calculate_biomass(plot_occurrences)
        }
        return specific_stats

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

