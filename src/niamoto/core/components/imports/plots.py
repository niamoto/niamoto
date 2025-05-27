"""
Module for importing plot data from GeoPackage files into the database.
"""

from pathlib import Path
from typing import Optional, Any, Dict

import geopandas as gpd
import pandas as pd
import csv
from shapely import GEOSException
from shapely.validation import explain_validity
from shapely.wkt import loads
from shapely.ops import unary_union

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
        self.link_field = "locality"  # Default field in plot_ref
        self.occurrence_link_field = "plot_name"  # Default field in occurrences

    def set_link_field(self, field_name: str) -> None:
        """
        Set the field name to use for linking plots with occurrences.

        Args:
            field_name: Name of the field in plot_ref table to match with occurrence_link_field in occurrences
        """
        self.link_field = field_name

    def set_occurrence_link_field(self, field_name: str) -> None:
        """
        Set the field name in occurrences table to use for linking with plots.

        Args:
            field_name: Name of the field in occurrences table to match with link_field in plot_ref
        """
        self.occurrence_link_field = field_name

    @error_handler(log=True, raise_error=True)
    def import_plots(
        self,
        file_path: str,
        identifier: str,
        location_field: str,
        locality_field: str,
        link_occurrences: bool = True,
        link_field: Optional[str] = None,
        occurrence_link_field: Optional[str] = None,
        hierarchy_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Import plot data from GeoPackage or CSV file.

        Args:
            file_path: Path to the file
            identifier: Plot identifier column name
            location_field: Location field column name (containing geometry)
            locality_field: Field for locality name (required for CSV)
            link_occurrences: Whether to link occurrences to plots after import
            link_field: Field to use for linking in plot_ref
            occurrence_link_field: Field to use for linking in occurrences
            hierarchy_config: Configuration for hierarchical import (optional)
                Example: {
                    "enabled": True,
                    "levels": ["plot_name", "locality_name", "country"],
                    "aggregate_geometry": True
                }

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data is invalid
            DatabaseError: If database operations fail
        """
        if link_field:
            self.link_field = link_field

        if occurrence_link_field:
            self.occurrence_link_field = occurrence_link_field

        # Validate that the file exists
        file_path = str(Path(file_path).resolve())
        if not Path(file_path).exists():
            raise FileReadError(file_path, "File not found")

        # Determine file type based on extension
        file_ext = Path(file_path).suffix.lower()

        # Load and validate data based on file type
        try:
            if file_ext == ".gpkg":
                return self.import_from_gpkg(
                    file_path,
                    identifier,
                    location_field,
                    link_occurrences=link_occurrences,
                    link_field=link_field,
                    occurrence_link_field=occurrence_link_field,
                )
            elif file_ext == ".csv":
                return self.import_from_csv(
                    file_path,
                    identifier,
                    location_field,
                    locality_field,
                    link_occurrences=link_occurrences,
                    link_field=link_field,
                    occurrence_link_field=occurrence_link_field,
                    hierarchy_config=hierarchy_config,
                )
            else:
                raise DataValidationError(
                    "Unsupported file format",
                    [
                        {
                            "error": f"File extension {file_ext} not supported. Use .gpkg or .csv"
                        }
                    ],
                )
        except Exception as e:
            # Re-raise specific errors
            if isinstance(e, (FileReadError, DataValidationError, DatabaseError)):
                raise
            # Convert generic errors to validation errors where appropriate
            if "geometry" in str(e).lower():
                raise DataValidationError("Invalid geometry", [{"error": str(e)}])
            raise

    @error_handler(log=True, raise_error=True)
    def import_from_csv(
        self,
        csv_path: str,
        identifier: str,
        location_field: str,
        locality_field: str,
        link_occurrences: bool = True,
        link_field: Optional[str] = None,
        occurrence_link_field: Optional[str] = None,
        hierarchy_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Import plot data from CSV.

        Args:
            csv_path: Path to CSV file
            identifier: Plot identifier column name
            location_field: Column containing geometry data (WKT or WKB)
            locality_field: Column containing locality name
            link_occurrences: Whether to link occurrences to plots after import
            link_field: Field name to use for linking in plot_ref
            occurrence_link_field: Field name to use for linking in occurrences table

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data is invalid
            DatabaseError: If database operations fail
        """
        if link_field:
            self.link_field = link_field

        if occurrence_link_field:
            self.occurrence_link_field = occurrence_link_field

        # Validate that the file exists
        file_path = str(Path(csv_path).resolve())
        if not Path(file_path).exists():
            raise FileReadError(file_path, "CSV file not found")

        # Load and validate data
        try:
            # Detect CSV delimiter
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    sample = f.read(1024)
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
                except Exception:
                    # Default to comma if detection fails
                    delimiter = ","

            # Read the CSV file
            df = pd.read_csv(file_path, delimiter=delimiter)

            # Validate required columns
            required_cols = {identifier, location_field, locality_field}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                raise DataValidationError(
                    "Missing required columns",
                    [{"field": col, "error": "Column missing"} for col in missing_cols],
                )

            # Parse geometry from the location_field
            geometries = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    geom_str = str(row[location_field])

                    # Try parsing as WKT first (e.g., "POINT (165.27731323 -21.17780113)")
                    try:
                        from shapely.wkt import loads as wkt_loads

                        geom = wkt_loads(geom_str)
                        geometries.append(geom)
                        continue
                    except Exception:
                        # If WKT fails, try as WKB
                        try:
                            from shapely.wkb import loads as wkb_loads

                            # Handle hex string with or without 0x prefix
                            hex_str = geom_str
                            if hex_str.startswith("0x"):
                                hex_str = hex_str[2:]
                            geom = wkb_loads(bytes.fromhex(hex_str))
                            geometries.append(geom)
                            continue
                        except Exception:
                            # Both parsing methods failed
                            errors.append(
                                {
                                    "row": idx,
                                    "value": geom_str,
                                    "error": "Failed to parse geometry",
                                }
                            )
                            geometries.append(None)
                except Exception as e:
                    errors.append(
                        {
                            "row": idx,
                            "value": str(row.get(location_field, "N/A")),
                            "error": str(e),
                        }
                    )
                    geometries.append(None)

            # If we had errors parsing geometries, report them
            if errors:
                # Only show first few errors to avoid overwhelming output
                raise DataValidationError(
                    "Failed to parse geometries",
                    errors[:5]
                    + (
                        [{"error": f"... and {len(errors) - 5} more errors"}]
                        if len(errors) > 5
                        else []
                    ),
                )

            # Create a GeoDataFrame with the parsed geometries
            gdf = gpd.GeoDataFrame(df, geometry=geometries)

            # Process data and import plots
            if hierarchy_config and hierarchy_config.get("enabled", False):
                imported_count = self._process_hierarchical_plots_data(
                    gdf, identifier, locality_field, hierarchy_config
                )
            else:
                imported_count = self._process_plots_data(
                    gdf, identifier, locality_field
                )

            # Link occurrences to plots if requested
            linked_occurrences = 0
            if link_occurrences:
                linked_occurrences = self.link_occurrences_to_plots()

            # Return success message
            result_message = (
                f"{imported_count} plots imported from {Path(file_path).name}."
            )
            if link_occurrences:
                result_message += f" {linked_occurrences} occurrences linked to plots."
            return result_message

        except Exception as e:
            # Re-raise specific error types
            if isinstance(e, (FileReadError, DataValidationError, DatabaseError)):
                raise

            # For geometry-related errors
            from shapely.errors import GEOSException

            if isinstance(e, GEOSException) or "geometry" in str(e).lower():
                raise DataValidationError("Invalid geometry", [{"error": str(e)}])
            else:
                raise DataValidationError(
                    "Failed to import plots from CSV", [{"error": str(e)}]
                )

    @error_handler(log=True, raise_error=True)
    def import_from_gpkg(
        self,
        gpkg_path: str,
        identifier: str,
        location_field: str,
        link_occurrences: bool = True,
        link_field: Optional[str] = None,
        occurrence_link_field: Optional[str] = None,
    ) -> str:
        """
        Import plot data from GeoPackage.

        Args:
            gpkg_path: Path to GeoPackage file
            identifier: Plot identifier column name
            location_field: Location field column name
            link_occurrences: Whether to link occurrences to plots after import
            link_field: Field name to use for linking in plot_ref (defaults to 'locality')
            occurrence_link_field: Field name to use for linking in occurrences table (defaults to 'plot_name')

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data is invalid (including invalid geometry)
            DatabaseError: If database operations fail
            PlotImportError: If import operation fails
        """
        if link_field:
            self.link_field = link_field

        if occurrence_link_field:
            self.occurrence_link_field = occurrence_link_field

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

        # Link occurrences to plots if requested
        linked_occurrences = 0
        if link_occurrences:
            linked_occurrences = self.link_occurrences_to_plots()

        # Return success message with just the filename, not the full path
        result_message = f"{imported_count} plots imported from {Path(file_path).name}."
        if link_occurrences:
            result_message += f" {linked_occurrences} occurrences linked to plots."
        return result_message

    @error_handler(log=True, raise_error=True)
    def _process_plots_data(
        self, plots_data: gpd.GeoDataFrame, identifier: str, locality_field: str = None
    ) -> int:
        """
        Process and import plot data.

        Args:
            plots_data: GeoDataFrame containing plot data
            identifier: Plot identifier column
            locality_field: Field containing locality name (optional)

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
                    # Use locality_field if provided
                    if self._import_plot(session, row, identifier, locality_field):
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

    def _import_plot(
        self,
        session: Any,
        row: pd.Series,
        identifier: str,
        locality_field: Optional[str] = None,
    ) -> bool:
        """
        Import a single plot.

        Args:
            session: Database session
            row: Plot data row as GeoSeries
            identifier: Plot identifier column
            locality_field: Field containing locality name (optional)

        Returns:
            True if plot was imported, False if skipped

        Raises:
            DataValidationError: If geometry is invalid or data is malformed
            DatabaseError: If database operations fail
        """
        # Get geometry from the GeoDataFrame's geometry column
        geometry = row.geometry
        if (
            geometry is None
            or pd.isna(geometry)
            or (hasattr(geometry, "is_empty") and geometry.is_empty)
        ):
            raise DataValidationError(
                "Missing geometry", [{"error": "No geometry data"}]
            )

        # Validate plot identifier
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

        # Get locality from the specified field or use the identifier field
        locality_field = locality_field or "locality"
        if locality_field in row:
            locality = row[locality_field]
        else:
            # Fallback to using the identifier if locality field doesn't exist
            locality = row[identifier]

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

        # Validate geometry
        try:
            if not geometry.is_valid:
                from shapely.validation import explain_validity

                error_msg = explain_validity(geometry)
                raise DataValidationError("Invalid geometry", [{"error": error_msg}])
        except Exception as e:
            # Handle GEOSException or other validation errors
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])

        # Convert geometry to WKT
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

        # Additional geometry validation
        self.validate_geometry(wkt_geometry)

        # Check for existing plot
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
            # Load geometry from WKT
            geom = loads(wkt_geometry)
        except GEOSException as e:
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])
        except Exception as e:
            raise DataValidationError(
                "Failed to validate geometry", [{"error": str(e)}]
            )

        # Check if the geometry is empty
        try:
            if geom.is_empty:
                raise DataValidationError(
                    "Empty geometry", [{"error": "Empty geometry object"}]
                )
        except Exception as e:
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])

        # Check the validity of the geometry
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

    @error_handler(log=True, raise_error=True)
    def link_occurrences_to_plots(self) -> int:
        """
        Link occurrences to plots based on configured fields.

        This method links occurrences to plots by matching the occurrence_link_field
        in the occurrences table with the link_field in the plot_ref table.

        Returns:
            int: Number of occurrences linked to plots

        Raises:
            DatabaseError: If database operations fail
        """
        try:
            # Ensure plot_ref_id column exists
            self._ensure_plot_ref_id_column_exists()

            # First, check if the occurrence_link_field exists in the occurrences table
            check_column_query = f"""
                SELECT COUNT(*) FROM pragma_table_info('occurrences')
                WHERE name = '{self.occurrence_link_field}'
            """
            column_exists = self.db.execute_sql(check_column_query, fetch=True)
            column_count = self._extract_count_from_result(column_exists)

            if column_count == 0:
                raise DatabaseError(
                    f"Field '{self.occurrence_link_field}' does not exist in occurrences table",
                    details={
                        "error": f"The configured field '{self.occurrence_link_field}' was not found in the occurrences table"
                    },
                )

            # Use a direct JOIN to update all occurrences at once
            try:
                # This version uses a JOIN in the UPDATE statement (works in SQLite)
                bulk_update_query = f"""
                    UPDATE occurrences
                    SET plot_ref_id = (
                        SELECT plot_ref.id
                        FROM plot_ref
                        WHERE TRIM(LOWER(plot_ref.{self.link_field})) = TRIM(LOWER(occurrences.{self.occurrence_link_field}))
                        LIMIT 1
                    )
                    WHERE occurrences.{self.occurrence_link_field} IS NOT NULL
                    AND (occurrences.plot_ref_id IS NULL OR occurrences.plot_ref_id != (
                        SELECT plot_ref.id
                        FROM plot_ref
                        WHERE TRIM(LOWER(plot_ref.{self.link_field})) = TRIM(LOWER(occurrences.{self.occurrence_link_field}))
                        LIMIT 1
                    ))
                """
                result = self.db.execute_sql(bulk_update_query)
                affected_rows = result.rowcount if hasattr(result, "rowcount") else 0

                if affected_rows > 0:
                    return affected_rows

            except Exception:
                # If bulk update fails, try a different approach
                pass

            # If bulk update didn't work, try a different approach
            # Find all matches first
            match_query = f"""
                SELECT o.id as occurrence_id, p.id as plot_id
                FROM occurrences o
                JOIN plot_ref p ON TRIM(LOWER(o.{self.occurrence_link_field})) = TRIM(LOWER(p.{self.link_field}))
                WHERE o.{self.occurrence_link_field} IS NOT NULL
                AND (o.plot_ref_id IS NULL OR o.plot_ref_id != p.id)
            """
            matches = self.db.execute_sql(match_query, fetch=True)

            if not matches or not hasattr(matches, "__iter__"):
                return 0

            # Convert matches to a list of tuples (occurrence_id, plot_id)
            match_list = []
            for match in matches:
                if hasattr(match, "__iter__") and len(match) >= 2:
                    match_list.append((match[0], match[1]))

            if not match_list:
                return 0

            total_linked = 0

            # Process matches in batches
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task(
                    "[green]Linking occurrences to plots...", total=len(match_list)
                )

                batch_size = 100
                for i in range(0, len(match_list), batch_size):
                    batch = match_list[i : i + batch_size]

                    for occurrence_id, plot_id in batch:
                        try:
                            # Update each occurrence individually
                            update_query = """
                                UPDATE occurrences
                                SET plot_ref_id = ?
                                WHERE id = ? AND (plot_ref_id IS NULL OR plot_ref_id != ?)
                            """
                            result = self.db.execute_sql(
                                update_query, params=(plot_id, occurrence_id, plot_id)
                            )
                            affected_rows = (
                                result.rowcount if hasattr(result, "rowcount") else 0
                            )
                            total_linked += affected_rows

                            progress.update(task, advance=1)
                        except Exception:
                            progress.update(task, advance=1)

            return total_linked

        except Exception as e:
            from sqlalchemy.exc import SQLAlchemyError

            if isinstance(e, SQLAlchemyError):
                raise DatabaseError(
                    "Database error during occurrence linking",
                    details={"error": str(e)},
                )
            raise

    def _extract_count_from_result(self, result):
        """
        Extract a count value from a database query result.
        Handles different return types including sqlalchemy.engine.row.Row.

        Args:
            result: The result from a database query

        Returns:
            int: The extracted count value
        """
        try:
            # Handle sqlalchemy.engine.row.Row objects
            if hasattr(result, "__iter__") and not isinstance(
                result, (list, tuple, str)
            ):
                try:
                    return int(result[0])
                except (IndexError, TypeError, ValueError):
                    return 0

            # Handle integer results
            elif isinstance(result, int):
                return result

            # Handle list/tuple results
            elif isinstance(result, (list, tuple)):
                if len(result) == 0:
                    return 0

                # Handle nested lists/tuples
                if isinstance(result[0], (list, tuple)):
                    if len(result[0]) == 0:
                        return 0
                    try:
                        return int(result[0][0])
                    except (TypeError, ValueError):
                        return 0
                else:
                    try:
                        return int(result[0])
                    except (TypeError, ValueError):
                        return 0

            # Default case
            return 0

        except Exception:
            return 0

    @error_handler(log=True, raise_error=True)
    def link_occurrences_by_plot_name(self, plot_link_value: str) -> int:
        """
        Link occurrences to a specific plot by a linking value.

        Args:
            plot_link_value: Value that matches the link_field in plot_ref

        Returns:
            int: Number of occurrences linked

        Raises:
            DatabaseError: If database operations fail
            DataValidationError: If plot not found
        """
        try:
            self._ensure_plot_ref_id_column_exists()

            # Check if the occurrence_link_field exists in the occurrences table
            check_column_query = f"""
                SELECT COUNT(*) FROM pragma_table_info('occurrences')
                WHERE name = '{self.occurrence_link_field}'
            """
            column_exists = self.db.execute_sql(check_column_query, fetch=True)
            column_count = self._extract_count_from_result(column_exists)

            if column_count == 0:
                raise DatabaseError(
                    f"Field '{self.occurrence_link_field}' does not exist in occurrences table",
                    details={
                        "error": f"The configured field '{self.occurrence_link_field}' was not found in the occurrences table"
                    },
                )

            # Find the plot by the configured link field (case-insensitive)
            plot_query = f"""
                SELECT id FROM plot_ref
                WHERE TRIM(LOWER({self.link_field})) = TRIM(LOWER(?))
                LIMIT 1
            """
            result = self.db.execute_sql(
                plot_query, params=(plot_link_value,), fetch=True
            )

            if not result:
                raise DataValidationError(
                    "Plot not found",
                    [
                        {
                            "error": f"No plot found with {self.link_field} '{plot_link_value}'"
                        }
                    ],
                )

            # Extract plot_id
            if hasattr(result, "__iter__") and not isinstance(
                result, (list, tuple, str)
            ):
                plot_id = result[0]
            elif isinstance(result, (list, tuple)) and len(result) > 0:
                if isinstance(result[0], (list, tuple)) and len(result[0]) > 0:
                    plot_id = result[0][0]
                else:
                    plot_id = result[0]
            else:
                plot_id = result

            # Find all occurrences that need to be updated
            match_query = f"""
                SELECT o.id as occurrence_id
                FROM occurrences o
                WHERE TRIM(LOWER(o.{self.occurrence_link_field})) = TRIM(LOWER(?))
                AND (o.plot_ref_id IS NULL OR o.plot_ref_id != ?)
            """
            matches = self.db.execute_sql(
                match_query, params=(plot_link_value, plot_id), fetch=True
            )

            if not matches or not hasattr(matches, "__iter__"):
                return 0

            # Convert matches to a list of occurrence IDs
            occurrence_ids = []
            for match in matches:
                if hasattr(match, "__iter__"):
                    occurrence_ids.append(match[0])
                else:
                    occurrence_ids.append(match)

            if not occurrence_ids:
                return 0

            total_linked = 0

            # Process in batches
            batch_size = 100
            for i in range(0, len(occurrence_ids), batch_size):
                batch = occurrence_ids[i : i + batch_size]

                # Update occurrences in this batch
                placeholders = ", ".join("?" for _ in batch)
                update_query = f"""
                    UPDATE occurrences
                    SET plot_ref_id = ?
                    WHERE id IN ({placeholders})
                    AND (plot_ref_id IS NULL OR plot_ref_id != ?)
                """

                # Create parameters list with plot_id at beginning and end
                params = [plot_id] + batch + [plot_id]

                result = self.db.execute_sql(update_query, params=params)
                affected_rows = result.rowcount if hasattr(result, "rowcount") else 0
                total_linked += affected_rows

            return total_linked

        except Exception as e:
            from sqlalchemy.exc import SQLAlchemyError

            if isinstance(e, SQLAlchemyError):
                raise DatabaseError(
                    "Database error during occurrence linking",
                    details={"error": str(e)},
                )
            if not isinstance(e, DataValidationError):
                raise
            raise

    def _ensure_plot_ref_id_column_exists(self) -> None:
        """
        Ensure that the plot_ref_id column exists in the occurrences table.
        Creates it if it doesn't exist.

        Raises:
            DatabaseError: If database operations fail
        """
        try:
            # Check if the occurrences table exists
            table_query = """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='occurrences'
            """
            tables = self.db.execute_sql(table_query, fetch=True)

            if not tables:
                raise DatabaseError(
                    "Occurrences table does not exist",
                    details={
                        "error": "Cannot add plot_ref_id column to non-existent table"
                    },
                )

            # Check if plot_ref_id column exists
            check_column_query = """
                SELECT COUNT(*) FROM pragma_table_info('occurrences')
                WHERE name = 'plot_ref_id'
            """
            column_exists = self.db.execute_sql(check_column_query, fetch=True)
            column_count = self._extract_count_from_result(column_exists)

            # Create column if it doesn't exist
            if column_count == 0:
                create_column_query = """
                    ALTER TABLE occurrences
                    ADD COLUMN plot_ref_id INTEGER
                """
                self.db.execute_sql(create_column_query)

        except Exception as e:
            from sqlalchemy.exc import SQLAlchemyError

            if isinstance(e, SQLAlchemyError):
                raise DatabaseError(
                    "Database error while ensuring plot_ref_id column exists",
                    details={"error": str(e)},
                )
            raise

    @error_handler(log=True, raise_error=True)
    def _process_hierarchical_plots_data(
        self,
        plots_data: gpd.GeoDataFrame,
        identifier: str,
        locality_field: str,
        hierarchy_config: Dict[str, Any],
    ) -> int:
        """
        Process and import plot data with hierarchical structure.

        Args:
            plots_data: GeoDataFrame containing plot data
            identifier: Plot identifier column
            locality_field: Field containing locality name
            hierarchy_config: Configuration for hierarchy

        Returns:
            Number of imported plots

        Raises:
            DataValidationError: If data is invalid
            DatabaseError: If database operations fail
        """
        imported_count = 0
        levels = hierarchy_config.get(
            "levels", ["plot_name", "locality_name", "country"]
        )
        aggregate_geometry = hierarchy_config.get("aggregate_geometry", True)

        # Validate required columns
        missing_cols = set(levels) - set(plots_data.columns)
        if missing_cols:
            raise DataValidationError(
                "Missing hierarchy columns",
                [{"field": col, "error": "Column missing"} for col in missing_cols],
            )

        # Create dictionaries to store relationships
        country_ids = {}  # country_name -> id
        locality_ids = {}  # (locality_name, country_name) -> id

        with self.db.session() as session:
            # First pass: create higher level entities (countries and localities)
            unique_countries = (
                plots_data[levels[2]].dropna().unique() if len(levels) > 2 else []
            )
            unique_localities = (
                plots_data[[levels[1], levels[2]]].drop_duplicates()
                if len(levels) > 2
                else plots_data[[levels[1]]].drop_duplicates()
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            ) as progress:
                # Import countries
                if len(unique_countries) > 0:
                    task = progress.add_task(
                        "[green]Importing countries...", total=len(unique_countries)
                    )
                    for country in unique_countries:
                        country_id = self._import_hierarchy_level(
                            session,
                            country,
                            "country",
                            plots_data,
                            levels[2],
                            aggregate_geometry,
                        )
                        country_ids[country] = country_id
                        progress.update(task, advance=1)

                # Import localities
                task = progress.add_task(
                    "[green]Importing localities...", total=len(unique_localities)
                )
                for _, loc_row in unique_localities.iterrows():
                    locality_name = loc_row[levels[1]]
                    country_name = loc_row[levels[2]] if len(levels) > 2 else None
                    parent_id = country_ids.get(country_name) if country_name else None

                    locality_id = self._import_hierarchy_level(
                        session,
                        locality_name,
                        "locality",
                        plots_data,
                        levels[1],
                        aggregate_geometry,
                        parent_id=parent_id,
                        filter_by={levels[2]: country_name} if country_name else None,
                    )
                    locality_ids[(locality_name, country_name)] = locality_id
                    progress.update(task, advance=1)

                # Import plots
                task = progress.add_task(
                    "[green]Importing plots...", total=len(plots_data)
                )
                for _, row in plots_data.iterrows():
                    locality_name = row[levels[1]] if len(levels) > 1 else None
                    country_name = row[levels[2]] if len(levels) > 2 else None

                    parent_id = None
                    if locality_name:
                        parent_id = locality_ids.get((locality_name, country_name))

                    if self._import_plot_hierarchical(
                        session, row, identifier, locality_field, parent_id
                    ):
                        imported_count += 1
                    progress.update(task, advance=1)

                try:
                    session.commit()
                    # Update nested set values
                    progress.console.print("[yellow]Updating nested set model...")
                    self._update_nested_set_values(session)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    from sqlalchemy.exc import SQLAlchemyError

                    if isinstance(e, SQLAlchemyError):
                        raise DatabaseError(
                            "Database error during hierarchical plot import",
                            details={"error": str(e)},
                        )
                    raise

        return imported_count

    def _import_hierarchy_level(
        self,
        session: Any,
        name: str,
        level_type: str,
        data: gpd.GeoDataFrame,
        name_column: str,
        aggregate_geometry: bool,
        parent_id: Optional[int] = None,
        filter_by: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Import a hierarchy level (country or locality).

        Args:
            session: Database session
            name: Name of the entity
            level_type: Type of entity ('country' or 'locality')
            data: Full data GeoDataFrame
            name_column: Column containing the name
            aggregate_geometry: Whether to aggregate geometry from children
            parent_id: Parent entity ID
            filter_by: Additional filters for data selection

        Returns:
            ID of the imported entity
        """
        # Check if entity already exists
        existing = (
            session.query(PlotRef)
            .filter_by(locality=name, plot_type=level_type)
            .first()
        )
        if existing:
            return existing.id

        # Filter data for this entity
        mask = data[name_column] == name
        if filter_by:
            for col, val in filter_by.items():
                mask &= data[col] == val
        entity_data = data[mask]

        # Get geometry (aggregate if requested)
        geometry = None
        if aggregate_geometry and len(entity_data) > 0:
            geometries = entity_data.geometry.dropna()
            if len(geometries) > 0:
                try:
                    # Union all geometries
                    unified_geom = unary_union(geometries.tolist())
                    from shapely.wkt import dumps

                    geometry = dumps(unified_geom)
                except Exception as e:
                    print(f"Warning: Failed to aggregate geometry for {name}: {e}")

        # Create entity
        entity = PlotRef(
            id_locality=hash(f"{level_type}_{name}") % 1000000,  # Generate unique ID
            locality=name,
            geometry=geometry,
            plot_type=level_type,
            parent_id=parent_id,
            extra_data={
                "entity_type": level_type,
                "auto_generated": True,
                "child_count": len(entity_data) if level_type != "plot" else None,
            },
        )
        session.add(entity)
        session.flush()
        return entity.id

    def _import_plot_hierarchical(
        self,
        session: Any,
        row: pd.Series,
        identifier: str,
        locality_field: str,
        parent_id: Optional[int] = None,
    ) -> bool:
        """
        Import a single plot with hierarchical structure.

        Args:
            session: Database session
            row: Plot data row
            identifier: Plot identifier column
            locality_field: Field containing locality name
            parent_id: Parent entity ID

        Returns:
            True if plot was imported, False if skipped
        """
        # Get geometry
        geometry = row.geometry
        if (
            geometry is None
            or pd.isna(geometry)
            or (hasattr(geometry, "is_empty") and geometry.is_empty)
        ):
            raise DataValidationError(
                "Missing geometry", [{"error": "No geometry data"}]
            )

        # Validate plot identifier
        plot_id = row[identifier]
        try:
            plot_id = int(plot_id)
        except ValueError:
            raise DataValidationError(
                "Invalid plot identifier value",
                [{"error": f"Value '{plot_id}' cannot be converted to int"}],
            )

        # Get locality
        locality = row[locality_field] if locality_field in row else str(plot_id)
        if not locality or pd.isna(locality):
            raise DataValidationError(
                "Invalid locality", [{"error": "Locality cannot be null or empty"}]
            )
        locality = str(locality).strip()

        # Validate geometry
        try:
            if not geometry.is_valid:
                from shapely.validation import explain_validity

                error_msg = explain_validity(geometry)
                raise DataValidationError("Invalid geometry", [{"error": error_msg}])
        except Exception as e:
            raise DataValidationError("Invalid geometry", [{"error": str(e)}])

        # Convert geometry to WKT
        from shapely.wkt import dumps

        wkt_geometry = dumps(geometry)

        # Check for existing plot
        existing_plot = (
            session.query(PlotRef)
            .filter_by(id_locality=plot_id, locality=locality, plot_type="plot")
            .first()
        )
        if not existing_plot:
            # Extract additional data
            extra_data = {
                "entity_type": "plot",
                "auto_generated": False,
            }
            # Add any extra columns
            for col in row.index:
                if col not in [identifier, locality_field, "geometry"] and pd.notna(
                    row[col]
                ):
                    extra_data[col] = row[col]

            plot = PlotRef(
                id=plot_id,
                id_locality=plot_id,
                locality=locality,
                geometry=wkt_geometry,
                plot_type="plot",
                parent_id=parent_id,
                extra_data=extra_data,
            )
            session.add(plot)
            session.flush()
            return True

        return False

    def _update_nested_set_values(self, session: Any) -> None:
        """
        Update nested set values for hierarchical plots.

        Args:
            session: Database session
        """
        # Reset all nested set values
        session.query(PlotRef).update({"lft": None, "rght": None, "level": None})
        session.flush()

        # Get root nodes (no parent)
        root_nodes = session.query(PlotRef).filter_by(parent_id=None).all()

        counter = 1
        for root in root_nodes:
            counter = self._assign_nested_set_values(session, root, counter, 0)

        session.flush()

    def _assign_nested_set_values(
        self, session: Any, node: PlotRef, counter: int, level: int
    ) -> int:
        """
        Recursively assign nested set values to a node and its children.

        Args:
            session: Database session
            node: Current node
            counter: Current counter value
            level: Current level

        Returns:
            Updated counter value
        """
        # Set left value
        node.lft = counter
        node.level = level
        counter += 1

        # Process children
        children = session.query(PlotRef).filter_by(parent_id=node.id).all()
        for child in children:
            counter = self._assign_nested_set_values(session, child, counter, level + 1)

        # Set right value
        node.rght = counter
        counter += 1

        return counter
