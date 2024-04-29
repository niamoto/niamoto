from loguru import logger
from typing import Any, Tuple
from niamoto.core.services.importer import ImporterService
from niamoto.common.config import Config


class ApiImporter:
    def __init__(self) -> None:
        """
        Initialize the ImportAPI with the database path.

        Parameters:
        - db_path (str): The path to the database.
        """
        self.config = Config()
        self.db_path = self.config.get("database", "path")

    def import_taxononomy(self, csvfile: str, ranks: Tuple[str, ...]) -> Any:
        """
        Import taxonomu data using DataImportService.

        Parameters:
            csvfile (str): Path to the CSV file to be imported.
            ranks (tuple): The ranks to be imported.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the taxonomy
            import_tax_results = data_import_service.import_taxonomy(csvfile, ranks)

            # Confirmation message
            return import_tax_results

        except Exception as e:
            logger.exception(f"Error importing 'occurrences' data: {e}")

    def import_plots(self, gpkg_path: str) -> Any:
        """
        Import plot data from the provided GeoPackage file path.

        Parameters:
        - gpkg_path (str): Path to the GeoPackage file to be imported.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the plots
            import_plot_results = data_import_service.import_plots(gpkg_path)

            # Confirmation message
            return import_plot_results

        except Exception as e:
            logger.error(f"Error during plot data import: {e}")

    def import_occurrences(self, csvfile: str, taxon_id_column: str) -> Any:
        """
        Import occurrences data using DataImportService.

        Parameters:
            taxon_id_column: Name of the column in the CSV that corresponds to the taxon ID.
            csvfile (str): Path to the CSV file to be imported.
        """
        try:
            # Initialize the data import service
            data_import_service = ImporterService(self.db_path)

            # Call the service to import the occurrences
            import_occ_result = data_import_service.import_occurrences(
                csvfile, taxon_id_column
            )

            # Confirmation message
            return import_occ_result

        except Exception as e:
            logger.exception(f"Error importing 'occurrences' data: {e}")

    def import_occurrence_plot_links(self, csvfile: str) -> Any:
        """
        Import occurrence-plot links from a CSV file.

        Parameters:
        - csvfile (str): Path to the CSV file to be imported.
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
            logger.exception(f"Error importing 'occurrence-plot' links: {e}")
