import csv
from typing import Tuple, List, Dict, Any

import pandas as pd

from niamoto.core.components.importers.occurrences import OccurrenceImporter
from niamoto.core.components.importers.plots import PlotImporter
from niamoto.core.components.importers.taxonomy import TaxonomyImporter
from niamoto.core.components.importers.shapes import ShapeImporter
from niamoto.common.database import Database
from niamoto.core.utils.logging_utils import setup_logging


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
        self.logger = setup_logging(component_name="importer_service")
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.occurrence_importer = OccurrenceImporter(self.db)
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
        separator = self._detect_separator(file_path)
        try:
            if self._validate_csv_format(file_path, separator, ranks):
                return self.taxonomy_importer.import_from_csv(file_path, ranks)
            else:
                return "CSV file format is incorrect. Please ensure it contains the required standard fields."
        except Exception as e:
            self.logger.error(f"Error importing taxonomy data: {e}")
            return "An error occurred during taxonomy data import."

    @staticmethod
    def _detect_separator(file_path: str) -> str:
        """
        Detect the separator used in the CSV file.

        Args:
            file_path (str): The path to the CSV file.

        Returns:
            str: The detected separator.
        """
        with open(file_path, "r") as file:
            first_line = file.readline()
            dialect = csv.Sniffer().sniff(first_line)
            return str(dialect.delimiter)

    def _validate_csv_format(
        self, file_path: str, separator: str, ranks: Tuple[str, ...]
    ) -> bool:
        """
        Validate the format of the CSV file to ensure it contains the required standard fields and ranks.

        Args:
            file_path (str): The path to the CSV file to be validated.
            separator (str): The separator used in the CSV file.
            ranks (Tuple[str, ...]): The ranks to be validated.

        Returns:
            bool: True if the CSV file contains the required standard fields and ranks, False otherwise.
        """
        required_fields = {"id_taxon", "full_name", "authors"}
        required_fields.update(ranks)

        try:
            df = pd.read_csv(file_path, sep=separator, on_bad_lines="warn")
        except pd.errors.ParserError as e:
            self.logger.error(f"Error reading CSV file: {e}")
            return False

        csv_fields = set(df.columns)
        if not required_fields.issubset(csv_fields):
            missing_fields = required_fields - csv_fields
            self.logger.error(
                f"Missing required fields in CSV file: {', '.join(missing_fields)}"
            )
            return False
        return True

    def import_occurrences(
        self, csvfile: str, taxon_id_column: str, location_column: str
    ) -> str:
        """
        Import occurrences data from a CSV file.

        Args:
            csvfile (str): The path to the CSV file to be imported.
            taxon_id_column (str): The name of the column in the CSV file that contains the taxon IDs.
            location_column (str): The name of the column in the CSV file that contains the location data.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.occurrence_importer.import_valid_occurrences(
            csvfile, taxon_id_column, location_column
        )

    def import_plots(
        self, gpkg_path: str, plot_identifier: str, location_field: str
    ) -> str:
        """
        Import plot data from a GeoPackage file.

        Args:
            gpkg_path (str): The path to the GeoPackage file to be imported.
            plot_identifier (str): The name of the column in the GeoPackage file that contains the plot identifiers.
            location_field (str): The name of the column in the GeoPackage file that contains the location data.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.plot_importer.import_from_gpkg(
            gpkg_path, plot_identifier, location_field
        )

    def import_occurrence_plot_links(self, csvfile: str) -> str:
        """
        Import occurrence-plot links from a CSV file.

        Args:
            csvfile (str): The path to the CSV file to be imported.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.occurrence_importer.import_occurrence_plot_links(csvfile)

    def import_shapes(self, shapes_config: List[Dict[str, Any]]) -> str:
        """
        Import shape data from the configuration.

        Args:
            shapes_config (list): A list of dictionaries containing shape information.

        Returns:
            str: A message indicating the status of the import operation.
        """
        return self.shape_importer.import_from_config(shapes_config)
