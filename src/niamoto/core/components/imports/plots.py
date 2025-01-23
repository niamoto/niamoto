"""
Module for importing plot data from GeoPackage files into the database.
"""

from pathlib import Path
from typing import Optional, Any

import geopandas as gpd
import pandas as pd
from shapely.wkt import dumps
from sqlalchemy.exc import SQLAlchemyError

from niamoto.common.database import Database
from niamoto.core.models import PlotRef
from niamoto.core.utils.logging_utils import setup_logging
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    PlotImportError,
    FileReadError,
    DataValidationError,
    DatabaseError,
)


class PlotImporter:
    """Class for importing plot data from GeoPackage files."""

    def __init__(self, db: Database):
        """
        Initialize the importer.

        Args:
            db: Database connection
        """
        self.db = db
        self.logger = setup_logging(component_name="import")

    @error_handler(log=True, raise_error=True)
    def import_from_gpkg(
        self, gpkg_path: str, identifier: str, location_field: str
    ) -> str:
        """
        Import plot data from GeoPackage.

        Args:
            gpkg_path: Path to GeoPackage file
            identifier: Plot identifier column name
            location_field: Location field column name

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data is invalid
            DatabaseError: If database operations fail
            PlotImportError: If import operation fails
        """
        try:
            # Validate file exists
            file_path = str(Path(gpkg_path).resolve())
            if not Path(file_path).exists():
                raise FileReadError(file_path, "GeoPackage file not found")

            # Load and validate data
            try:
                plots_data = gpd.read_file(file_path)
                if not isinstance(plots_data, gpd.GeoDataFrame):
                    raise DataValidationError(
                        "Invalid GeoPackage format",
                        [{"error": "File does not contain valid geometric data"}],
                    )
            except Exception as e:
                raise FileReadError(
                    file_path, f"Failed to read GeoPackage file: {str(e)}"
                )

            # Validate required columns
            required_cols = {identifier, location_field, "locality"}
            missing_cols = required_cols - set(plots_data.columns)
            if missing_cols:
                raise DataValidationError(
                    "Missing required columns",
                    [{"field": col, "error": "Column missing"} for col in missing_cols],
                )

            # Import data
            imported_count = self._process_plots_data(
                plots_data, identifier, location_field
            )

            return f"{imported_count} plots imported from {file_path}."

        except Exception as e:
            if isinstance(e, (FileReadError, DataValidationError, DatabaseError)):
                raise
            raise PlotImportError(
                "Failed to import plot data",
                details={"file": gpkg_path, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def _process_plots_data(
        self, plots_data: gpd.GeoDataFrame, identifier: str, location_field: str
    ) -> int:
        """
        Process and import plot data.

        Args:
            plots_data: GeoDataFrame containing plot data
            identifier: Plot identifier column
            location_field: Location field column

        Returns:
            Number of imported plots

        Raises:
            DatabaseError: If database operations fail
        """
        imported_count = 0
        session = self.db.session()

        try:
            # Validate geometry column
            if not plots_data.geometry.name == location_field:
                raise DataValidationError(
                    "Invalid geometry column",
                    [
                        {
                            "error": f"Expected geometry column '{location_field}' not found"
                        }
                    ],
                )

            # Process each plot
            for _, row in plots_data.iterrows():
                try:
                    if self._import_plot(session, row, identifier):
                        imported_count += 1
                except SQLAlchemyError as e:
                    raise DatabaseError(
                        f"Failed to import plot {row[identifier]}",
                        details={"error": str(e)},
                    )

            session.commit()
            return imported_count

        except Exception as e:
            if session:
                session.rollback()
            if isinstance(e, DatabaseError):
                raise
            raise PlotImportError(
                "Failed to process plot data", details={"error": str(e)}
            )
        finally:
            if session:
                session.close()

    def _import_plot(self, session: Any, row: pd.Series, identifier: str) -> bool:
        """
        Import a single plot.

        Args:
            session: Database session
            row: Plot data row as GeoSeries
            identifier: Plot identifier column

        Returns:
            True if plot was imported, False if skipped

        Raises:
            DatabaseError: If database operations fail
            DataValidationError: If geometry is invalid
        """
        try:
            # Accès à la géométrie
            geometry = row.geometry
            if geometry is None:
                raise DataValidationError(
                    "Missing geometry",
                    [{"plot": row[identifier], "error": "No geometry data"}],
                )

            # Extract values
            plot_id = row[identifier]

            # Validate that plot_id is convertible to int
            if not isinstance(plot_id, (int, str)):
                raise DataValidationError(
                    "Invalid plot identifier type",
                    [
                        {
                            "plot": row[identifier],
                            "error": f"Expected int or str, got {type(plot_id).__name__}",
                        }
                    ],
                )

            # Convert to int if possible
            try:
                plot_id = int(plot_id)
            except ValueError:
                raise DataValidationError(
                    "Invalid plot identifier value",
                    [
                        {
                            "plot": row[identifier],
                            "error": f"Value '{plot_id}' cannot be converted to int",
                        }
                    ],
                )

            locality = str(row["locality"])

            wkt_geometry = dumps(geometry)

            # Validate the geometry
            self.validate_geometry(wkt_geometry)

            # Check for existing plot
            existing_plot = (
                session.query(PlotRef)
                .filter_by(id_locality=plot_id, locality=locality)
                .scalar()
            )

            # Add new plot if it doesn't exist
            if not existing_plot:
                plot = PlotRef(
                    id_locality=plot_id,  # Conversion explicite en int
                    locality=locality,
                    geometry=wkt_geometry,
                )
                session.add(plot)
                session.flush()
                return True

            return False

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Database error for plot {row[identifier]}", details={"error": str(e)}
            )

    @staticmethod
    def validate_geometry(wkt_geometry: Optional[str]) -> None:
        """
        Validate WKT geometry.

        Args:
            wkt_geometry: WKT geometry string to validate

        Raises:
            DataValidationError: If geometry is invalid
        """
        if wkt_geometry:
            try:
                from shapely.wkt import loads
                from shapely.validation import explain_validity

                geom = loads(wkt_geometry)
                if not geom.is_valid:
                    raise DataValidationError(
                        "Invalid geometry", [{"error": explain_validity(geom)}]
                    )
            except Exception as e:
                raise DataValidationError(
                    "Failed to validate geometry", [{"error": str(e)}]
                )
