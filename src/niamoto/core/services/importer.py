"""
Service for importing data into Niamoto.
"""

import csv
from pathlib import Path
from typing import Tuple, List, Dict, Any, Set, Optional

import pandas as pd

from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.core.components.imports.plots import PlotImporter
from niamoto.core.components.imports.taxons import TaxonomyImporter
from niamoto.core.components.imports.shapes import ShapeImporter
from niamoto.common.database import Database
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
        self.taxonomy_importer = TaxonomyImporter(self.db)
        self.occurrence_importer = OccurrenceImporter(self.db)
        self.plot_importer = PlotImporter(self.db)
        self.shape_importer = ShapeImporter(self.db)

    @error_handler(log=True, raise_error=True)
    def import_taxonomy(
        self,
        file_path: str,
        ranks: Tuple[str, ...],
        api_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Import taxonomy data from a CSV file.

        Args:
            file_path: Path to the CSV file
            ranks: Taxonomy ranks to import
            api_config: API configuration for enrichment
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
            ) from e

        # Import the data
        try:
            result = self.taxonomy_importer.import_from_csv(
                file_path, ranks, api_config
            )
            return result
        except Exception as e:
            raise DataImportError(
                f"Failed to import taxonomy data: {str(e)}",
                details={"file": file_path, "error": str(e)},
            ) from e

    @error_handler(log=True, raise_error=True)
    def import_taxonomy_from_occurrences(
        self,
        occurrences_file: str,
        ranks: Tuple[str, ...],
        column_mapping: Dict[str, str],
        api_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extract and import taxonomy data from occurrences.

        Args:
            occurrences_file: Path to occurrences CSV file
            ranks: Taxonomy ranks to import
            column_mapping: Mapping between taxonomy fields and occurrence columns

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            CSVError: If CSV format is invalid
            DataImportError: If import operation fails
        """
        # Validate input parameters
        if not occurrences_file:
            raise ValidationError("occurrences_file", "File path cannot be empty")
        if not ranks:
            raise ValidationError("ranks", "Ranks cannot be empty")

        required_columns = ["taxon_id", "family", "genus", "species"]
        missing_columns = [col for col in required_columns if col not in column_mapping]
        if missing_columns:
            raise ValidationError(
                "column_mapping",
                f"Missing required column mappings: {', '.join(missing_columns)}",
                details={"missing": missing_columns},
            )

        # Validate file exists
        occurrences_file = str(Path(occurrences_file).resolve())
        if not Path(occurrences_file).exists():
            raise FileReadError(
                occurrences_file, "File not found", details={"path": occurrences_file}
            )

        # Import the data
        try:
            result = self.taxonomy_importer.import_from_occurrences(
                occurrences_file, ranks, column_mapping, api_config
            )
            return result
        except Exception as e:
            raise DataImportError(
                f"Failed to extract and import taxonomy from occurrences: {str(e)}",
                details={"file": occurrences_file, "error": str(e)},
            ) from e

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
            ) from e

    @error_handler(log=True, raise_error=True)
    def import_plots(
        self,
        file_path: str,
        plot_identifier: str,
        location_field: str,
        locality_field: str,
        link_field: Optional[str] = None,
        occurrence_link_field: Optional[str] = None,
        hierarchy_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Import plot data from GeoPackage or CSV.

        Args:
            file_path: Path to the file (GeoPackage or CSV)
            plot_identifier: Plot identifier field
            location_field: Location field name (containing geometry)
            locality_field: Field for locality name (mandatory for CSV imports)
            link_field: Field in plot_ref to use for linking with occurrences
            occurrence_link_field: Field in occurrences to use for linking with plots
            hierarchy_config: Configuration for hierarchical import (optional)

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            DataImportError: If import fails
        """
        if not file_path:
            raise ValidationError("file_path", "File path cannot be empty")
        if not plot_identifier:
            raise ValidationError(
                "plot_identifier", "Plot identifier field must be specified"
            )

        if not Path(file_path).exists():
            raise FileReadError(file_path, "File not found")

        try:
            return self.plot_importer.import_plots(
                file_path,
                plot_identifier,
                location_field,
                locality_field=locality_field,
                link_field=link_field,
                occurrence_link_field=occurrence_link_field,
                hierarchy_config=hierarchy_config,
            )
        except Exception as e:
            raise DataImportError(
                "Failed to import plots", details={"error": str(e)}
            ) from e

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
            raise DataImportError(
                "Failed to import shapes", details={"error": str(e)}
            ) from e

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
            with open(file_path, "r", encoding="utf-8") as file:
                first_line = file.readline()
                dialect = csv.Sniffer().sniff(first_line)
                return str(dialect.delimiter)
        except Exception as e:
            raise CSVError(
                file_path, "Failed to detect CSV separator", details={"error": str(e)}
            ) from e

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
            df = pd.read_csv(
                file_path, sep=separator, on_bad_lines="warn", encoding="utf-8"
            )
            csv_fields = set(df.columns)
            return required_fields - csv_fields
        except pd.errors.ParserError as e:
            raise CSVError(
                file_path, "Failed to parse CSV", details={"error": str(e)}
            ) from e
