"""
This module contains the ShapeImporter class used to import shape data from various geospatial files into the database.
"""
import json
import logging
import os
import tempfile
import zipfile
from typing import List, Dict, Any

import fiona  # type: ignore
from pyproj import Transformer, CRS
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon

from rich.console import Console
from rich.progress import Progress
from shapely.geometry.base import BaseGeometry

from niamoto.common.database import Database
from niamoto.core.models import ShapeRef
from niamoto.core.utils.logging_utils import setup_logging


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
        self.logger = setup_logging(component_name="shapes_import")

    def import_from_config(self, shapes_config: List[Dict[str, Any]]) -> str:
        """
        Import shape data from various geospatial files based on the configuration.

        Args:
            shapes_config (list): A list of dictionaries containing shape information.

        Returns:
            str: A message indicating the success of the import operation.

        Raises:
            ValueError: If configuration is invalid or required files are missing
            FileNotFoundError: If specified files cannot be found
            Exception: For other import operation errors
        """
        console = Console()
        import_stats = {
            "processed": 0,
            "skipped": 0,
            "updated": 0,
            "added": 0,
            "errors": [],
        }

        try:
            # Validate config structure
            if not shapes_config:
                raise ValueError("Empty shapes configuration provided")

            for shape_info in shapes_config:
                required_fields = ["category", "label", "path", "name_field"]
                missing_fields = [
                    field for field in required_fields if field not in shape_info
                ]
                if missing_fields:
                    raise ValueError(
                        f"Missing required fields in config: {', '.join(missing_fields)}"
                    )

            with Progress(console=console) as progress:
                task = progress.add_task(
                    "[green]Importing shapes...", total=len(shapes_config)
                )

                for shape_info in shapes_config:
                    try:
                        shape_category = shape_info["category"]
                        shape_category_label = shape_info["label"]
                        file_path = shape_info["path"]
                        name_field = shape_info["name_field"]

                        # Check if file exists
                        if not os.path.exists(file_path):
                            raise FileNotFoundError(f"File not found: {file_path}")

                        # Create a temporary directory to extract the files
                        with tempfile.TemporaryDirectory() as tmpdirname:
                            actual_file_path = self._process_input_file(
                                file_path, tmpdirname
                            )

                            # Validate the file can be opened with fiona
                            try:
                                with fiona.open(actual_file_path, "r") as src:
                                    # Get and validate CRS
                                    if not src.crs_wkt:
                                        raise ValueError(
                                            f"No CRS found in file: {actual_file_path}"
                                        )

                                    src_crs = CRS.from_string(src.crs_wkt)
                                    dst_crs = CRS.from_epsg(4326)
                                    transformer = Transformer.from_crs(
                                        src_crs, dst_crs, always_xy=True
                                    )

                                    # Process features
                                    for feature in src:
                                        import_stats["processed"] += 1

                                        try:
                                            if not feature.get("geometry"):
                                                import_stats["errors"].append(
                                                    "Missing geometry in feature"
                                                )
                                                import_stats["skipped"] += 1
                                                continue

                                            geom = shape(feature["geometry"])
                                            geom_wgs84 = self.transform_geometry(
                                                geom, transformer
                                            )
                                            geom_wkt = geom_wgs84.wkt

                                            properties = feature["properties"]
                                            if not properties:
                                                import_stats["errors"].append(
                                                    "No properties found in feature"
                                                )
                                                import_stats["skipped"] += 1
                                                continue

                                            label = properties.get(name_field)
                                            label = (
                                                str(label)
                                                if label is not None
                                                else None
                                            )

                                            if (
                                                not isinstance(label, str)
                                                or not label.strip()
                                            ):
                                                import_stats["errors"].append(
                                                    f"Invalid or empty label in feature: {properties}"
                                                )
                                                import_stats["skipped"] += 1
                                                continue

                                            if geom_wkt:
                                                existing_shape = (
                                                    self.db.session.query(ShapeRef)
                                                    .filter_by(
                                                        label=label, type=shape_category
                                                    )
                                                    .scalar()
                                                )

                                                if not existing_shape:
                                                    new_shape = ShapeRef(
                                                        label=label,
                                                        type=shape_category,
                                                        type_label=shape_category_label,
                                                        location=geom_wkt,
                                                    )
                                                    self.db.session.add(new_shape)
                                                    import_stats["added"] += 1
                                                else:
                                                    existing_shape.location = geom_wkt
                                                    import_stats["updated"] += 1

                                        except Exception as feat_error:
                                            import_stats["errors"].append(
                                                f"Error processing feature: {str(feat_error)}"
                                            )
                                            import_stats["skipped"] += 1

                            except fiona.errors.DriverError as e:
                                raise ValueError(
                                    f"Unable to open file {actual_file_path}: {str(e)}"
                                )

                    except Exception as shape_error:
                        import_stats["errors"].append(
                            f"Error processing shape {shape_category}: {str(shape_error)}"
                        )
                    finally:
                        progress.update(task, advance=1)

                self.db.session.commit()

                # Prepare result message
                result_message = (
                    f"Import completed:\n"
                    f"- Processed: {import_stats['processed']} features\n"
                    f"- Added: {import_stats['added']} new shapes\n"
                    f"- Updated: {import_stats['updated']} existing shapes\n"
                    f"- Skipped: {import_stats['skipped']} invalid entries\n"
                )
                if import_stats["errors"]:
                    result_message += "\nErrors encountered:\n"
                    result_message += "\n".join(
                        f"- {error}" for error in import_stats["errors"]
                    )

                return result_message

        except Exception as e:
            self.db.session.rollback()
            logging.error(f"Error during shapes data import: {e}")
            raise
        finally:
            self.db.close_db_session()

    @staticmethod
    def _process_input_file(file_path: str, tmp_dir: str) -> str:
        """
        Process the input file and return the actual path to use.

        Args:
            file_path (str): Original file path
            tmp_dir (str): Temporary directory path

        Returns:
            str: Actual file path to use
        """
        if file_path.endswith(".zip"):
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)
            actual_path = next(
                (
                    os.path.join(root, file)
                    for root, _, files in os.walk(tmp_dir)
                    for file in files
                    if file.endswith(
                        (
                            ".gpkg",
                            ".shp",
                            ".geojson",
                            ".json",
                            ".tab",
                            ".mif",
                            ".mid",
                            ".gdb",
                        )
                    )
                ),
                None,
            )
            if not actual_path:
                raise ValueError(f"No valid geospatial file found in zip: {file_path}")
            return actual_path

        elif file_path.endswith((".geojson", ".json")):
            # Fix JSON formatting if needed
            with open(file_path, "r") as f:
                data = json.load(f)
            tmp_path = os.path.join(tmp_dir, os.path.basename(file_path))
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            return tmp_path

        return file_path

    def transform_geometry(
        self, geom: BaseGeometry, transformer: Transformer
    ) -> BaseGeometry:
        """
        Transform the geometry to WGS84 and ensure it is a MultiPolygon.

        Args:
            geom (BaseGeometry): The geometry to transform.
            transformer (Transformer): The transformer to use.

        Returns:
            BaseGeometry: The transformed geometry as MultiPolygon.

        """
        if isinstance(geom, Point):
            return self.transform_point(geom, transformer)
        elif isinstance(geom, LineString):
            return self.transform_linestring(geom, transformer)
        elif isinstance(geom, Polygon):
            # Convert Polygon to MultiPolygon by wrapping it in a MultiPolygon
            return MultiPolygon([self.transform_polygon(geom, transformer)])
        elif isinstance(geom, MultiPolygon):
            return MultiPolygon(
                [self.transform_polygon(poly, transformer) for poly in geom.geoms]
            )
        else:
            raise ValueError(f"Unsupported geometry type: {type(geom)}")

    @staticmethod
    def transform_point(point: Point, coord_transformer: Transformer) -> Point:
        """
        Transform a point to WGS84.
        Args:
            point (Point): The point to transform.
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
            linestring (LineString): The linestring to transform.
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
            polygon (Polygon): The polygon to transform.
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
