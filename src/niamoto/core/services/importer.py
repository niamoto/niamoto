from typing import Tuple
from niamoto.core.components.importers.occurrences import OccurrenceImporter
from niamoto.core.components.importers.plots import PlotImporter
from niamoto.core.components.importers.taxonomy import TaxonomyImporter
from niamoto.core.components.importers.shapes import ShapeImporter
from niamoto.common.database import Database


class ImporterService:
    """
    The ImporterService class provides methods to import taxonomy, occurrences, plots, and shapes data.
    """

    def __init__(self, db_path: str):
        """
        Initializes a new instance of the ImporterService with a given database path.

        Args:
            db_path (str): The path to the database file.
        """
        self.db = Database(db_path)
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.occurrence_importer = OccurrenceImporter(db_path)
        self.plot_importer = PlotImporter(self.db)
        self.shape_importer = ShapeImporter(self.db)

    def import_taxonomy(self, file_path: str, ranks: Tuple[str, ...]) -> str:
        """
        Import taxonomy data from a CSV file.

        Args:
            file_path (str): The path to the CSV file to be imported.
            ranks (tuple): The ranks to be imported.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.taxonomy_importer.import_from_csv(file_path, ranks)

    def import_occurrences(
        self, csvfile: str, taxon_id_column: str, location_column: str
    ) -> str:
        """
        Import occurrences data from a CSV file.

        Args:
            csvfile (str): The path to the CSV file to be imported.
            taxon_id_column (str): The name of the column in the CSV file that contains the taxon IDs.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.occurrence_importer.import_valid_occurrences(
            csvfile, taxon_id_column, location_column
        )

    def import_plots(self, gpkg_path: str) -> str:
        """
        Import plot data from a GeoPackage file.

        Args:
            gpkg_path (str): The path to the GeoPackage file to be imported.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.plot_importer.import_from_gpkg(gpkg_path)

    def import_occurrence_plot_links(self, csvfile: str) -> str:
        """
        Import occurrence-plot links from a CSV file.

        Args:
            csvfile (str): The path to the CSV file to be imported.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.occurrence_importer.import_occurrence_plot_links(csvfile)

    def import_shapes(self, csvfile: str) -> str:
        """
        Import shape data from a CSV file.

        Args:
            csvfile (str): The path to the CSV file to be imported.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.shape_importer.import_from_csv(csvfile)
