"""
Module for importing plot data from GeoPackage files into the database.
"""

from pathlib import Path
from typing import Optional, Any

import geopandas as gpd
import pandas as pd
from shapely import GEOSException
from shapely.validation import explain_validity
from shapely.wkt import loads

from niamoto.common.database import Database
from niamoto.core.models import PlotRef
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    FileReadError,
    DataValidationError,
    DatabaseError,
)
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
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
        self.db_path = db.db_path

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
            DataValidationError: If data is invalid (including invalid geometry)
            DatabaseError: If database operations fail
            PlotImportError: If import operation fails
        """
        # Validate that the file exists
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
            from shapely.errors import GEOSException

            # Si l'exception mentionne "LinearRing" (ou ressemble à une GEOSException), transformer en DataValidationError
            if (
                isinstance(e, GEOSException)
                or "linearring" in str(e).lower()
                or "illegalargumentexception" in str(e).lower()
            ):
                raise DataValidationError("Invalid geometry", [{"error": str(e)}])
            else:
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

        # Process data and import plots
        try:
            imported_count = self._process_plots_data(
                plots_data, identifier, location_field
            )
        except Exception as e:
            from shapely.errors import GEOSException

            if isinstance(e, GEOSException) or "linearring" in str(e).lower():
                raise DataValidationError("Invalid geometry", [{"error": str(e)}])
            else:
                raise

        # Return success message with just the filename, not the full path
        return f"{imported_count} plots imported from {Path(file_path).name}."

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
            DataValidationError: If data is invalid
            DatabaseError: If database operations fail
        """
        imported_count = 0
        with self.db.session() as session:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            )
            with progress:
                task = progress.add_task(
                    "[green]Importing plots...", total=len(plots_data)
                )
                for _, row in plots_data.iterrows():
                    # Appel direct, sans try/except, pour que l'exception se propage
                    if self._import_plot(session, row, identifier):
                        imported_count += 1
                    progress.update(task, advance=1)
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    from sqlalchemy.exc import SQLAlchemyError

                    if isinstance(e, SQLAlchemyError):
                        raise DatabaseError(
                            "Database error during plot import",
                            details={"error": str(e)},
                        )
                    raise
        return imported_count

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
            DataValidationError: If geometry is invalid or data is malformed
            DatabaseError: If database operations fail
        """
        # Récupérer et vérifier la géométrie
        geometry = row.geometry
        if (
            geometry is None
            or pd.isna(geometry)
            or (hasattr(geometry, "is_empty") and geometry.is_empty)
        ):
            raise DataValidationError(
                "Missing geometry", [{"error": "No geometry data"}]
            )

        # Valider l'identifiant du plot
        plot_id = row[identifier]
        if not isinstance(plot_id, (int, str)):
            raise DataValidationError(
                "Invalid plot identifier type",
                [{"error": f"Expected int or str, got {type(plot_id).__name__}"}],
            )
        try:
            plot_id = int(plot_id)
        except ValueError:
            raise DataValidationError(
                "Invalid plot identifier value",
                [{"error": f"Value '{plot_id}' cannot be converted to int"}],
            )

        # Valider le champ 'locality'
        locality = row.get("locality")
        if locality is None or pd.isna(locality):
            raise DataValidationError(
                "Invalid locality", [{"error": "Locality cannot be null or empty"}]
            )
        locality = str(locality).strip()
        if not locality or locality.lower() == "none":
            raise DataValidationError(
                "Invalid locality",
                [{"error": "Locality cannot be null, empty or 'None'"}],
            )

        # Vérifier explicitement la validité de la géométrie avant conversion
        try:
            if not geometry.is_valid:
                from shapely.validation import explain_validity

                error_msg = explain_validity(geometry)
                raise DataValidationError("Invalid geometry", [{"error": error_msg}])
        except Exception as e:
            # Au cas où geometry.is_valid lance une GEOSException
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])

        # Convertir la géométrie en WKT (cette opération devrait maintenant être sûre)
        try:
            from shapely.wkt import dumps

            wkt_geometry = dumps(geometry)
        except Exception as e:
            from shapely.errors import GEOSException

            if isinstance(e, GEOSException):
                raise DataValidationError(
                    "Invalid geometry in conversion", [{"error": str(e)}]
                )
            else:
                raise

        # Optionnel : on peut appeler validate_geometry pour des vérifications complémentaires
        self.validate_geometry(wkt_geometry)

        # Vérifier la présence d'un plot existant
        existing_plot = (
            session.query(PlotRef)
            .filter_by(id_locality=plot_id, locality=locality)
            .first()
        )
        if not existing_plot:
            plot = PlotRef(
                id=plot_id,
                id_locality=plot_id,
                locality=locality,
                geometry=wkt_geometry,
            )
            session.add(plot)
            session.flush()
            return True

        return False

    @staticmethod
    def validate_geometry(wkt_geometry: Optional[str]) -> None:
        """
        Validate WKT geometry.

        Args:
            wkt_geometry: WKT geometry string to validate

        Raises:
            DataValidationError: If geometry is invalid
        """
        if not wkt_geometry:
            raise DataValidationError(
                "Empty geometry", [{"error": "Empty geometry string"}]
            )
        try:
            # Charger la géométrie depuis le WKT
            geom = loads(wkt_geometry)
        except GEOSException as e:
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])
        except Exception as e:
            raise DataValidationError(
                "Failed to validate geometry", [{"error": str(e)}]
            )

        # Vérifier si la géométrie est vide
        try:
            if geom.is_empty:
                raise DataValidationError(
                    "Empty geometry", [{"error": "Empty geometry object"}]
                )
        except Exception as e:
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])

        # Vérifier la validité de la géométrie
        try:
            if not geom.is_valid:
                error_msg = explain_validity(geom)
                raise DataValidationError("Invalid geometry", [{"error": error_msg}])
        except GEOSException as e:
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])
        except Exception as e:
            raise DataValidationError(
                "Failed to validate geometry", [{"error": str(e)}]
            )
