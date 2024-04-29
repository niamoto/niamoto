# importer.py

from typing import Tuple
from niamoto.core.components.importers.occurrences import OccurrenceImporter
from niamoto.core.components.importers.plots import PlotImporter
from niamoto.core.components.importers.taxonomy import TaxonomyImporter
from niamoto.common.database import Database


class ImporterService:
    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.occurrence_importer = OccurrenceImporter(db_path)
        self.plot_importer = PlotImporter(self.db)

    def import_taxonomy(self, file_path: str, ranks: Tuple[str, ...]) -> str:
        """
        Import taxonomy data from a CSV file.

        Parameters:
            file_path (str): The path to the CSV file to be imported.
            ranks (tuple): The ranks to be imported.
        """

        return self.taxonomy_importer.import_from_csv(file_path, ranks)

    def import_occurrences(self, csvfile: str, taxon_id_column: str) -> str:
        """Import occurrences data from a CSV file."""
        return self.occurrence_importer.import_valid_occurrences(
            csvfile, taxon_id_column
        )

    def import_plots(self, gpkg_path: str) -> str:
        """Import plot data from a GeoPackage file."""
        return self.plot_importer.import_from_gpkg(gpkg_path)

    def import_occurrence_plot_links(self, csvfile: str) -> str:
        """Import occurrence-plot links from a CSV file."""
        return self.occurrence_importer.import_occurrence_plot_links(csvfile)
