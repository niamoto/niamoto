import time
from typing import List, Dict, Any, Hashable

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

        try:
            taxons = self._retrieve_all_taxons()

            self.initialize_stats_table()

            for taxon in track(taxons, description="Processing Taxons..."):
                self.process_taxon(taxon)

        except Exception as e:
            self.console.print(f"An error occurred: {e}", style="bold red")
        finally:
            total_time = time.time() - start_time
            self.console.print(
                f"Total processing time: {total_time:.2f} seconds", style="italic blue"
            )

    def process_taxon(self, taxon: TaxonRef) -> None:
        """
        Process a taxon.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to process.
        """
        try:
            taxon_id = self._extract_taxon_id(taxon)
            if taxon_id is None:
                return

            taxon_occurrences = self.get_taxon_occurrences(taxon)
            if not taxon_occurrences:
                return

            stats = self.calculate_stats(taxon_id, taxon_occurrences)
            specific_stats = self.calculate_specific_stats(taxon_id, taxon_occurrences)
            stats.update(specific_stats)

            self.create_or_update_stats_entry(taxon_id, stats)

        except Exception as e:
            self.console.print(f"Failed to process taxon {taxon.id}: {e}", style="bold red")

    def get_taxon_occurrences(self, taxon: TaxonRef) -> list[dict[Hashable, Any]]:
        """
        Get taxon occurrences.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to get occurrences for.

        Returns:
            list[dict[Hashable, Any]]: The taxon occurrences.
        """
        taxon_ids = self.get_taxon_and_descendant_ids(taxon)
        return [occ for occ in self.occurrences if occ[self.identifier] in taxon_ids]

    def get_taxon_and_descendant_ids(self, taxon: TaxonRef) -> List[int]:
        """
        Get taxon and descendant ids.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to get ids for.

        Returns:
            List[int]: The taxon and descendant ids.
        """
        taxon_ids = (
            self.db.session.query(TaxonRef.id)
            .filter(TaxonRef.lft >= taxon.lft, TaxonRef.rght <= taxon.rght)
            .all()
        )
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
        specific_stats = {'top_species': self.calculate_top_species(taxon_occurrences, 10)}
        return specific_stats

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
        # Logic to calculate frequencies specific to taxon
        return frequencies

    def _retrieve_all_taxons(self) -> List[TaxonRef]:
        """
        Retrieve all taxons from the database.

        Returns:
            List[TaxonRef]: A list of taxon references.
        """
        return self.db.session.query(TaxonRef).all()

    def _extract_taxon_id(self, taxon: TaxonRef) -> int:
        """
        Extract the taxon ID value.

        Args:
            taxon (TaxonRef): The taxon from which to extract the ID.

        Returns:
            int: The taxon ID.
        """
        return self.db.session.execute(select(taxon.id)).scalar()
