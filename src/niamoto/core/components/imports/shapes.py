"""
This module contains the ShapeImporter class used to import shape data from various geospatial files into the database.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import tempfile

import fiona
from pyproj import Transformer, CRS
from rich.progress import Progress
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from sqlalchemy.exc import SQLAlchemyError

from niamoto.common.database import Database
from niamoto.core.models import ShapeRef
from niamoto.core.utils.logging_utils import setup_logging
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    ShapeImportError,
    FileReadError,
    DataValidationError,
    DatabaseError,
    ConfigurationError,
)


class ShapeImporter:
    """
    A class used to import shape data from a CSV file into the database.

    Attributes:
        db (Database): The database connection.
    """

    def __init__(self, db: Database):
        """
        Initializes the ShapeImporter with the database connection.

        Args:
            db (Database): The database connection.
        """
        self.db = db
        self.logger = setup_logging(component_name="import")

    @error_handler(log=True, raise_error=True)
    def import_from_config(self, shapes_config: List[Dict[str, Any]]) -> str:
        """
        Import shapes based on configuration.

        Args:
            shapes_config: List of shape configurations

        Returns:
            Success message with import stats

        Raises:
            ConfigurationError: If configuration is invalid
            FileReadError: If files cannot be read
            ShapeImportError: If import fails
            DatabaseError: If database operations fail
        """
        import_stats = {
            "processed": 0,
            "skipped": 0,
            "updated": 0,
            "added": 0,
            "errors": [],
        }

        try:
            # Validate configuration
            self._validate_config(shapes_config)

            # Process each shape configuration
            with Progress() as progress:
                task = progress.add_task(
                    "[green]Importing shapes...", total=len(shapes_config)
                )

                for shape_info in shapes_config:
                    try:
                        self._process_shape_file(shape_info, import_stats)
                    except Exception as e:
                        import_stats["errors"].append(
                            f"Error processing {shape_info.get('category', 'unknown')}: {str(e)}"
                        )
                    finally:
                        progress.update(task, advance=1)

                # Commit changes
                try:
                    self.db.session.commit()
                except SQLAlchemyError as e:
                    raise DatabaseError(
                        "Failed to commit changes", details={"error": str(e)}
                    )

                return self._format_result_message(import_stats)

        except Exception as e:
            self.db.session.rollback()
            if isinstance(e, (ConfigurationError, FileReadError, DatabaseError)):
                raise
            raise ShapeImportError(
                "Failed to import shapes",
                details={"error": str(e), "stats": import_stats},
            )
        finally:
            self.db.close_db_session()

    @staticmethod
    def _validate_config(shapes_config: List[Dict[str, Any]]) -> None:
        """
        Validate shape configuration.

        Args:
            shapes_config: Configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not shapes_config:
            raise ConfigurationError("shapes", "Empty shapes configuration provided")

        required_fields = ["category", "label", "path", "name_field"]
        for shape_info in shapes_config:
            missing_fields = [
                field for field in required_fields if field not in shape_info
            ]
            if missing_fields:
                raise ConfigurationError(
                    "shapes",
                    "Missing required fields",
                    details={"missing_fields": missing_fields, "config": shape_info},
                )

    @error_handler(log=True, raise_error=True)
    def _process_shape_file(
        self, shape_info: Dict[str, Any], import_stats: Dict[str, Any]
    ) -> None:
        """
        Process a single shape file.

        Args:
            shape_info: Shape configuration
            import_stats: Import transforms to update

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data is invalid
            DatabaseError: If database operations fail
        """
        file_path = Path(shape_info["path"])
        if not file_path.exists():
            raise FileReadError(str(file_path), "Shape file not found")

        with tempfile.TemporaryDirectory() as tmp_dir:
            actual_path = self._process_input_file(str(file_path), tmp_dir)

            try:
                with fiona.open(actual_path, "r") as src:
                    if not src.crs_wkt:
                        raise DataValidationError(
                            "Invalid shape file",
                            [{"error": "No CRS found", "file": str(file_path)}],
                        )

                    transformer = self._setup_transformer(src.crs_wkt)
                    self._process_features(src, shape_info, transformer, import_stats)

            except fiona.errors.FionaValueError as e:
                raise DataValidationError(
                    "Invalid shape file format",
                    [{"error": str(e), "file": str(file_path)}],
                )
            except Exception as e:
                if isinstance(e, DataValidationError):
                    raise
                raise ShapeImportError(
                    f"Failed to process {file_path}", details={"error": str(e)}
                )

    @staticmethod
    def _setup_transformer(crs_wkt: str) -> Transformer:
        """
        Set up coordinate transformation.

        Args:
            crs_wkt: Source CRS in WKT format

        Returns:
            Configured transformer

        Raises:
            DataValidationError: If CRS is invalid
        """
        try:
            src_crs = CRS.from_string(crs_wkt)
            dst_crs = CRS.from_epsg(4326)
            return Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        except Exception as e:
            raise DataValidationError("Invalid CRS", [{"error": str(e)}])

    def _process_features(
        self,
        src: Any,
        shape_info: Dict[str, Any],
        transformer: Transformer,
        import_stats: Dict[str, Any],
    ) -> None:
        """
        Process features from shape file.

        Args:
            src: Fiona data source
            shape_info: Shape configuration
            transformer: Coordinate transformer
            import_stats: Import transforms to update

        Raises:
            DatabaseError: If database operations fail
        """
        for feature in src:
            import_stats["processed"] += 1

            try:
                if not self._is_valid_feature(feature):
                    import_stats["skipped"] += 1
                    continue

                geom = shape(feature["geometry"])
                geom_wgs84 = self.transform_geometry(geom, transformer)
                label = self._get_feature_label(feature, shape_info)

                if not label:
                    import_stats["skipped"] += 1
                    continue

                if self._update_or_create_shape(
                    label, shape_info, geom_wgs84, import_stats
                ):
                    import_stats["added"] += 1
                else:
                    import_stats["updated"] += 1

            except Exception as e:
                import_stats["errors"].append(str(e))
                import_stats["skipped"] += 1

    @staticmethod
    def _is_valid_feature(feature: Dict[str, Any]) -> bool:
        """Check if feature has required data."""
        return bool(feature.get("geometry") and feature.get("properties"))

    @staticmethod
    def _get_feature_label(feature: Dict[str, Any], shape_info: Dict[str, Any]) -> str:
        """Get feature label from properties."""
        label = feature["properties"].get(shape_info["name_field"])
        return str(label).strip() if label else ""

    def _update_or_create_shape(
        self,
        label: str,
        shape_info: Dict[str, Any],
        geometry: BaseGeometry,
        import_stats: Dict[str, Any],
    ) -> bool:
        """
        Update or create shape record.

        Returns:
            True if created new, False if updated
        """
        try:
            existing_shape = (
                self.db.session.query(ShapeRef)
                .filter_by(label=label, type=shape_info["category"])
                .scalar()
            )

            if existing_shape:
                existing_shape.location = geometry.wkb.hex()
                return False
            else:
                new_shape = ShapeRef(
                    label=label,
                    type=shape_info["category"],
                    type_label=shape_info["label"],
                    location=geometry.wkb.hex(),
                )
                self.db.session.add(new_shape)
                return True

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Database error for shape {label}", details={"error": str(e)}
            )

    @staticmethod
    def _format_result_message(stats: Dict[str, Any]) -> str:
        """Format import results message."""
        total = stats["added"] + stats["updated"]
        msg = f"{total} shapes imported ("
        msg += f"{stats['added']} new, {stats['updated']} updated)"

        if stats["errors"]:
            msg += "\nErrors encountered:\n"
            msg += "\n".join(f"- {error}" for error in stats["errors"])
        return msg

    @staticmethod
    def _process_input_file(file_path: str, tmp_dir: str) -> str:
        """
        Process input file and return usable path.

        Args:
            file_path: Original file path
            tmp_dir: Temporary directory path

        Returns:
            Processed file path

        Raises:
            FileReadError: If file processing fails
        """
        try:
            if file_path.endswith((".geojson", ".json")):
                with open(file_path, "r") as f:
                    data = json.load(f)
                tmp_path = str(Path(tmp_dir) / Path(file_path).name)
                with open(tmp_path, "w") as f:
                    json.dump(data, f)
                return tmp_path
            return file_path
        except Exception as e:
            raise FileReadError(
                file_path, "Failed to process input file", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def transform_geometry(
        self, geom: BaseGeometry, transformer: Transformer
    ) -> BaseGeometry:
        """Transform geometry to WGS84."""
        if isinstance(geom, Point):
            return self.transform_point(geom, transformer)
        elif isinstance(geom, LineString):
            return self.transform_linestring(geom, transformer)
        elif isinstance(geom, Polygon):
            return MultiPolygon([self.transform_polygon(geom, transformer)])
        elif isinstance(geom, MultiPolygon):
            return MultiPolygon(
                [self.transform_polygon(poly, transformer) for poly in geom.geoms]
            )
        else:
            raise DataValidationError(
                "Invalid geometry type", [{"type": str(type(geom))}]
            )

    @staticmethod
    def transform_point(point: Point, coord_transformer: Transformer) -> Point:
        """
        Transform a point to WGS84.
        Args:
            point (Point): The point to transforms.
            coord_transformer (Transformer): The transformer to use.

        Returns:
            Point: The transformed point.

        """
        x, y = point.x, point.y
        x, y = coord_transformer.transform(xx=x, yy=y)
        return Point(x, y)

    def transform_linestring(
        self, linestring: LineString, transformer: Transformer
    ) -> LineString:
        """
        Transform a linestring to WGS84.
        Args:
            linestring (LineString): The linestring to transforms.
            transformer (Transformer): The transformer to use.

        Returns:
            LineString: The transformed linestring.

        """
        return LineString(
            [
                self.transform_point(Point(x, y), transformer)
                for x, y, *_ in linestring.coords
            ]
        )

    def transform_polygon(self, polygon: Polygon, transformer: Transformer) -> Polygon:
        """
        Transform a polygon to WGS84.
        Args:
            polygon (Polygon): The polygon to transforms.
            transformer (Transformer): The transformer to use.

        Returns:
            Polygon: The transformed polygon.

        """
        exterior = self.transform_linestring(
            LineString(polygon.exterior.coords), transformer
        )
        interiors = [
            self.transform_linestring(LineString(interior.coords), transformer)
            for interior in polygon.interiors
        ]
        return Polygon(exterior, interiors)
