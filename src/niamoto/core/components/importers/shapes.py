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
            Exception: If an error occurs during the import operation.
        """
        console = Console()
        try:
            with Progress(console=console) as progress:
                task = progress.add_task(
                    "[green]Importing shapes...", total=len(shapes_config)
                )

                for shape_info in shapes_config:
                    shape_category = shape_info["category"]
                    shape_category_label = shape_info["label"]
                    file_path = shape_info["path"]
                    name_field = shape_info["name_field"]

                    # Create a temporary directory to extract the files
                    with tempfile.TemporaryDirectory() as tmpdirname:
                        if file_path.endswith(".zip"):
                            with zipfile.ZipFile(file_path, "r") as zip_ref:
                                zip_ref.extractall(tmpdirname)
                            file_path = next(
                                (
                                    os.path.join(root, file)
                                    for root, _, files in os.walk(tmpdirname)
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
                                shape_info["path"],
                            )
                        # If the file is GeoJSON, try to fix the formatting
                        if file_path.endswith((".geojson", ".json")):
                            with open(file_path, "r") as f:
                                data = json.load(f)
                            with open(file_path, "w") as f:
                                json.dump(data, f)

                        with fiona.open(file_path, "r") as src:
                            # Get the source CRS
                            src_crs = CRS.from_string(src.crs_wkt)
                            # Define the target CRS
                            dst_crs = CRS.from_epsg(4326)

                            # Create a transformer
                            transformer = Transformer.from_crs(
                                src_crs, dst_crs, always_xy=True
                            )

                            for feature in src:
                                geom = shape(feature["geometry"])

                                # Convert the 3D geometry to 2D if necessary and transform the coordinates
                                geom_wgs84 = self.transform_geometry(geom, transformer)

                                # Convert the geometry to WKT
                                geom_wkt = geom_wgs84.wkt

                                properties = feature["properties"]
                                label = properties.get(name_field)
                                label = str(label) if label is not None else None

                                # Validate the properties
                                if not isinstance(label, str):
                                    logging.warning(
                                        f"Skipping feature due to invalid properties: {properties} for "
                                        f"{name_field}"
                                    )
                                    continue

                                if label and geom_wkt:
                                    existing_shape = (
                                        self.db.session.query(ShapeRef)
                                        .filter_by(label=label, type=shape_category)
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
                                    else:
                                        # Update the existing shape
                                        existing_shape.location = geom_wkt

                    progress.update(task, advance=1)

            self.db.session.commit()
            return "Shape data imported successfully."

        except Exception as e:
            self.db.session.rollback()
            logging.error(f"Error during shapes data import: {e}")
            raise e
        finally:
            self.db.close_db_session()

    def transform_geometry(
        self, geom: BaseGeometry, transformer: Transformer
    ) -> BaseGeometry:
        """
        Transform the geometry to WGS84.
        Args:
            geom (BaseGeometry): The geometry to transform.
            transformer (Transformer): The transformer to use.

        Returns:
            BaseGeometry: The transformed geometry.

        """
        if isinstance(geom, Point):
            return self.transform_point(geom, transformer)
        elif isinstance(geom, LineString):
            return self.transform_linestring(geom, transformer)
        elif isinstance(geom, Polygon):
            return self.transform_polygon(geom, transformer)
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
