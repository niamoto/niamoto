"""
Service for importing data into Niamoto.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from niamoto.core.components.imports.occurrences import OccurrenceImporter
from niamoto.core.components.imports.plots import PlotImporter
from niamoto.core.components.imports.taxons import TaxonomyImporter
from niamoto.core.components.imports.shapes import ShapeImporter
from niamoto.common.database import Database
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    FileReadError,
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
        occurrences_file: str,
        hierarchy_config: Dict[str, Any],
        api_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extract and import taxonomy data from occurrences.

        Args:
            occurrences_file: Path to occurrences CSV file
            hierarchy_config: Hierarchical configuration with levels
            api_config: API configuration for enrichment

        Returns:
            Success message

        Raises:
            ValidationError: If parameters are invalid
            FileReadError: If file cannot be read
            DataImportError: If import operation fails
        """
        # Validate input parameters
        if not occurrences_file:
            raise ValidationError("occurrences_file", "File path cannot be empty")
        if not hierarchy_config:
            raise ValidationError(
                "hierarchy_config", "Hierarchy configuration cannot be empty"
            )

        # Validate file exists
        occurrences_file = str(Path(occurrences_file).resolve())
        if not Path(occurrences_file).exists():
            raise FileReadError(
                occurrences_file, "File not found", details={"path": occurrences_file}
            )

        # Import the data
        try:
            result = self.taxonomy_importer.import_taxonomy(
                occurrences_file, hierarchy_config, api_config
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
