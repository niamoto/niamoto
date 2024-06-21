from loguru import logger
from typing import Any, Tuple
from niamoto.core.services.importer import ImporterService
from niamoto.common.config import Config


class ApiImporter:
    """
    A class used to import data for the Niamoto project.

    Attributes:
        config (Config): The configuration settings for the Niamoto project.
        db_path (str): The path to the database.
    """

    def __init__(self) -> None:
        """
        Initializes the ApiImporter with the database path.
        """
        self.config = Config()
        self.db_path = self.config.get("database", "path")

    def import_taxonomy(self, csvfile: str, ranks: Tuple[str, ...]) -> Any:
        """
        Imports taxonomy data using DataImportService.

        Args:
            csvfile (str): Path to the CSV file to be imported.
            ranks (Tuple[str, ...]): The ranks to be imported.

        Returns:
            Any: The results of the import operation.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the taxonomy
            import_tax_results = data_import_service.import_taxonomy(csvfile, ranks)

            # Confirmation message
            return import_tax_results

        except Exception as e:
            logger.error(f"Error during taxonomy data import: {e}")

    def import_plots(self, gpkg_path: str, plot_identifier: str, location_field: str) -> Any:
        """
        Imports plot data from the provided GeoPackage file path.

        Args:
            gpkg_path (str): Path to the GeoPackage file to be imported.
            plot_identifier (str): The name of the column in the GeoPackage that corresponds to the plot ID.
            location_field (str): The name of the column in the GeoPackage that corresponds to the location data.

        Returns:
            Any: The results of the import operation.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the plots
            import_plot_results = data_import_service.import_plots(gpkg_path, plot_identifier, location_field)

            # Confirmation message
            return import_plot_results

        except Exception as e:
            logger.error(f"Error during plot data import: {e}")

    def import_occurrences(
        self, csvfile: str, taxon_identifier: str, location_field: str
    ) -> Any:
        """
        Imports occurrences data using DataImportService.

        Args:
            csvfile (str): Path to the CSV file to be imported.
            taxon_identifier (str): The name of the column in the CSV file that contains the taxon IDs.
            location_field (str): The name of the column in the CSV file that contains the location data.

        Returns:
            Any: The results of the import operation.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the occurrences
            import_occ_result = data_import_service.import_occurrences(
                csvfile, taxon_identifier, location_field
            )

            # Confirmation message
            return import_occ_result

        except Exception as e:
            logger.error(f"Error during occurrences data import: {e}")

    def import_occurrence_plot_links(self, csvfile: str) -> Any:
        """
        Imports occurrence-plot links from a CSV file.

        Args:
            csvfile (str): The path to the CSV file to be imported.

        Returns:
            Any: The results of the import operation.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the occurrence-plot links
            import_opl_results = data_import_service.import_occurrence_plot_links(
                csvfile
            )

            # Confirmation message
            return import_opl_results

        except Exception as e:
            logger.error(f"Error during occurrence-plot data import: {e}")

    def import_shapes(self, csvfile: str) -> Any:
        """
        Imports shape data from a CSV file.

        Args:
            csvfile (str): Path to the CSV file to be imported.

        Returns:
            Any: The results of the import operation.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the shapes
            import_shapes_result = data_import_service.import_shapes(csvfile)

            # Confirmation message
            return import_shapes_result

        except Exception as e:
            logger.error(f"Error during shapes data import: {e}")
