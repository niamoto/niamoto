"""
Service for importing data into Niamoto.
"""

import csv
from pathlib import Path
from typing import Tuple, List, Dict, Any, Set

import pandas as pd

from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.core.components.imports.plots import PlotImporter
from niamoto.core.components.imports.taxons import TaxonomyImporter
from niamoto.core.components.imports.shapes import ShapeImporter
from niamoto.common.database import Database
from niamoto.common.utils.logging_utils import setup_logging
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    FileReadError,
    CSVError,
    DataImportError,
    ValidationError,
)


class ImporterService:
    """
    Service providing methods to import taxonomy, occurrences, plots, and shapes data.
    """

    def __init__(self, db_path: str):
        """
        Initialize the ImporterService.

        Args:
            db_path: Path to the database file
        """
        self.db = Database(db_path)
        self.logger = setup_logging(component_name="import")
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.occurrence_importer = OccurrenceImporter(self.db)
        self.plot_importer = PlotImporter(self.db)
        self.shape_importer = ShapeImporter(self.db)

    @error_handler(log=True, raise_error=True)
    def import_taxonomy(self, file_path: str, ranks: Tuple[str, ...]) -> str:
        """
        Import taxonomy data from a CSV file.

        Args:
            file_path: Path to the CSV file
            ranks: Taxonomy ranks to import

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            CSVError: If CSV format is invalid
            DataImportError: If import operation fails
        """
        # Validate input parameters
        if not file_path:
            raise ValidationError("file_path", "File path cannot be empty")
        if not ranks:
            raise ValidationError("ranks", "Ranks cannot be empty")

        # Validate file exists
        file_path = str(Path(file_path).resolve())
        if not Path(file_path).exists():
            raise FileReadError(
                file_path, "File not found", details={"path": file_path}
            )

        # Detect separator and validate format
        try:
            separator = self._detect_separator(file_path)
            missing_fields = self._validate_csv_format(file_path, separator, ranks)
            if missing_fields:
                raise CSVError(
                    file_path,
                    "Invalid CSV format",
                    details={"missing_fields": missing_fields},
                )
        except Exception as e:
            raise CSVError(
                file_path, "Failed to validate CSV file", details={"error": str(e)}
            )

        # Import the data
        try:
            result = self.taxonomy_importer.import_from_csv(file_path, ranks)
            return result
        except Exception as e:
            raise DataImportError(
                f"Failed to import taxonomy data: {str(e)}",
                details={"file": file_path, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def import_occurrences(
        self, csvfile: str, taxon_id_column: str, location_column: str
    ) -> str:
        """
        Import occurrences data.

        Args:
            csvfile: Path to CSV file
            taxon_id_column: Name of taxon ID column
            location_column: Name of location column

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            DataImportError: If import fails
        """
        if not csvfile:
            raise ValidationError("csvfile", "CSV file path cannot be empty")
        if not taxon_id_column:
            raise ValidationError(
                "taxon_id_column", "Taxon ID column must be specified"
            )
        if not location_column:
            raise ValidationError(
                "location_column", "Location column must be specified"
            )

        if not Path(csvfile).exists():
            raise FileReadError(csvfile, "File not found")

        try:
            return self.occurrence_importer.import_valid_occurrences(
                csvfile, taxon_id_column, location_column
            )
        except Exception as e:
            raise DataImportError(
                "Failed to import occurrences", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def import_plots(
        self, gpkg_path: str, plot_identifier: str, location_field: str
    ) -> str:
        """
        Import plot data.

        Args:
            gpkg_path: Path to GeoPackage file
            plot_identifier: Plot identifier field
            location_field: Location field name

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            DataImportError: If import fails
        """
        if not gpkg_path:
            raise ValidationError("gpkg_path", "GeoPackage path cannot be empty")
        if not plot_identifier:
            raise ValidationError(
                "plot_identifier", "Plot identifier field must be specified"
            )

        if not Path(gpkg_path).exists():
            raise FileReadError(gpkg_path, "File not found")

        try:
            return self.plot_importer.import_from_gpkg(
                gpkg_path, plot_identifier, location_field
            )
        except Exception as e:
            raise DataImportError("Failed to import plots", details={"error": str(e)})

    @error_handler(log=True, raise_error=True)
    def import_occurrence_plot_links(self, csvfile: str) -> str:
        """
        Import occurrence-plot links.

        Args:
            csvfile: Path to CSV file

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            DataImportError: If import fails
        """
        if not csvfile:
            raise ValidationError("csvfile", "CSV file path cannot be empty")

        if not Path(csvfile).exists():
            raise FileReadError(csvfile, "File not found")

        try:
            return self.occurrence_importer.import_occurrence_plot_links(csvfile)
        except Exception as e:
            raise DataImportError(
                "Failed to import occurrence-plot links", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def import_shapes(self, shapes_config: List[Dict[str, Any]]) -> str:
        """
        Import shape data.

        Args:
            shapes_config: List of shape configurations

        Returns:
            Success message

        Raises:
            ValidationError: If config is invalid
            DataImportError: If import fails
        """
        if not shapes_config:
            raise ValidationError(
                "shapes_config", "Shapes configuration cannot be empty"
            )

        try:
            return self.shape_importer.import_from_config(shapes_config)
        except Exception as e:
            raise DataImportError("Failed to import shapes", details={"error": str(e)})

    def _detect_separator(self, file_path: str) -> str:
        """
        Detect CSV separator.

        Args:
            file_path: Path to CSV file

        Returns:
            Detected separator

        Raises:
            CSVError: If separator cannot be detected
        """
        try:
            with open(file_path, "r", encoding='utf-8') as file:
                first_line = file.readline()
                dialect = csv.Sniffer().sniff(first_line)
                return str(dialect.delimiter)
        except Exception as e:
            raise CSVError(
                file_path, "Failed to detect CSV separator", details={"error": str(e)}
            )

    def _validate_csv_format(
        self, file_path: str, separator: str, ranks: Tuple[str, ...]
    ) -> Set[str]:
        """
        Validate CSV format.

        Args:
            file_path: Path to CSV file
            separator: CSV separator
            ranks: Required ranks

        Returns:
            Set of missing fields if any

        Raises:
            CSVError: If CSV format is invalid
        """
        required_fields = {"id_taxon", "full_name", "authors"} | set(ranks)

        try:
            df = pd.read_csv(file_path, sep=separator, on_bad_lines="warn", encoding='utf-8')
            csv_fields = set(df.columns)
            return required_fields - csv_fields
        except pd.errors.ParserError as e:
            raise CSVError(file_path, "Failed to parse CSV", details={"error": str(e)})
