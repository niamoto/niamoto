import time

from typing import List, Dict, Any, Hashable

from rich.console import Console
from rich.progress import track
from sqlalchemy import select

from .statistics_calculator import StatisticsCalculator
from niamoto.core.models import TaxonRef


class TaxonomyStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for taxonomies.

    Inherits from:
        StatisticsCalculator
    """

    def calculate_taxonomy_stats(self) -> None:
        """
        Calculate statistics for all taxonomies.
        """
        start_time = time.time()

        # Retrieve all taxons from the TaxonRef table in the database
        taxons = self.db.session.query(TaxonRef).all()

        # Initialize the statistics table for storing the calculated statistics for each taxon
        self.initialize_stats_table()

        # Iterate over each taxon retrieved from the database
        for taxon in track(taxons, description="Processing Taxons..."):
            # Process the current taxon by calculating its statistics and updating the statistics table
            self.process_taxon(taxon)

        end_time = time.time()
        total_time = end_time - start_time

        console = Console()
        console.print(
            f"Total processing time: {total_time:.2f} seconds", style="italic blue"
        )

    def process_taxon(self, taxon: TaxonRef) -> None:
        """
        Process a taxon.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to process.
        """
        # Extract the taxon ID value from the Column[int]
        taxon_id = self.db.session.execute(select(taxon.id)).scalar()

        # Check if taxon_id is None
        if taxon_id is None:
            # Handle the case when taxon_id is None
            # You can choose to return or use a default value
            return

        # Retrieve the occurrences for the taxon and its descendants
        taxon_occurrences = self.get_taxon_occurrences(taxon)

        # Check if taxon_occurrences is empty
        if not taxon_occurrences:
            # No occurrences found for the taxon, skip to the next one
            return

        # Calculate the general statistics for each field of the mapping
        stats = self.calculate_stats(taxon_id, taxon_occurrences)

        # Calculate the statistics specific to taxons
        specific_stats = self.calculate_specific_stats(taxon_id, taxon_occurrences)
        stats.update(specific_stats)

        # Create or update the entry in the taxonomy_stats table
        self.create_or_update_stats_entry(taxon_id, stats)

    def get_taxon_occurrences(self, taxon: TaxonRef) -> list[dict[Hashable, Any]]:
        """
        Get taxon occurrences.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to get occurrences for.

        Returns:
            list[dict[Hashable, Any]]: The taxon occurrences.
        """
        # Retrieve the identifiers of the taxon and its descendants
        taxon_ids = self.get_taxon_and_descendant_ids(taxon)

        # Filter the occurrences for the taxon and its descendants
        taxon_occurrences = [
            occ for occ in self.occurrences if occ[self.identifier] in taxon_ids
        ]

        # Return the filtered occurrences
        return taxon_occurrences

    def get_taxon_and_descendant_ids(self, taxon: TaxonRef) -> List[int]:
        """
        Get taxon and descendant ids.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to get ids for.

        Returns:
            List[int]: The taxon and descendant ids.
        """
        # Retrieve the identifiers of the taxon and its descendants using the lft and rght fields
        taxon_ids = (
            self.db.session.query(TaxonRef.id)
            .filter(TaxonRef.lft >= taxon.lft, TaxonRef.rght <= taxon.rght)
            .all()
        )

        # Return a list of taxon identifiers
        return [taxon_id[0] for taxon_id in taxon_ids]

    def calculate_specific_stats(
        self, taxon_id: int, taxon_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate specific statistics for a taxon.

        Args:
            taxon_id (int): The taxon id.
            taxon_occurrences (list[dict[Hashable, Any]]): The taxon occurrences.

        Returns:
            Dict[str, Any]: The specific statistics.
        """
        frequencies = self.calculate_frequencies(taxon_id, taxon_occurrences)
        return frequencies

    def calculate_frequencies(
        self, taxon_id: int, taxon_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate frequencies for a taxon.

        Args:
            taxon_id (int): The taxon id.
            taxon_occurrences (list[dict[Hashable, Any]]): The taxon occurrences.

        Returns:
            Dict[str, Any]: The frequencies.
        """
        frequencies: Dict[str, Any] = {}

        return frequencies
