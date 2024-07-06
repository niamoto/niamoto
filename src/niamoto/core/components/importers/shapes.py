import logging
import os
import tempfile
import zipfile
from typing import List

import fiona
from pyproj import Transformer, CRS
from shapely import Polygon, MultiPolygon, Point, LineString
from shapely.geometry import shape

from niamoto.common.database import Database
from niamoto.core.models import ShapeRef


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
        # Ensure the logs directory exists
        log_directory = "logs"
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        # Configure logging to write to a file in the logs directory
        log_file_path = os.path.join(log_directory, "shape_import.log")
        logging.basicConfig(
            filename=log_file_path,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def import_from_config(self, shapes_config: List[dict]) -> str:
        """
        Import shape data from various geospatial files based on the configuration.

        Args:
            shapes_config (list): A list of dictionaries containing shape information.

        Returns:
            str: A message indicating the success of the import operation.

        Raises:
            Exception: If an error occurs during the import operation.
        """
        try:
            for shape_info in shapes_config:
                file_path = shape_info['path']
                id_field = shape_info['id_field']
                name_field = shape_info['name_field']
                shape_type = shape_info['name']

                # Create a temporary directory to extract the files
                with tempfile.TemporaryDirectory() as tmpdirname:
                    if file_path.endswith('.zip'):
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(tmpdirname)
                        for root, dirs, files in os.walk(tmpdirname):
                            for file in files:
                                if file.endswith(
                                        ('.gpkg', '.shp', '.geojson', '.json', '.tab', '.mif', '.mid', '.gdb')):
                                    file_path = os.path.join(root, file)
                                    break
                            if file_path != shape_info['path']:
                                break

                    with fiona.open(file_path, 'r') as src:
                        # Get the source CRS
                        src_crs = CRS.from_string(src.crs_wkt)
                        # Define the target CRS
                        dst_crs = CRS.from_epsg(4326)

                        # Create a transformer
                        transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

                        for feature in src:
                            geom = shape(feature['geometry'])

                            # Convert the 3D geometry to 2D if necessary and transform the coordinates
                            geom_wgs84 = self.transform_geometry(geom, transformer)

                            # Convert the geometry to WKT
                            geom_wkt = geom_wgs84.wkt

                            properties = feature['properties']
                            label = properties.get(name_field)
                            shape_id = properties.get(id_field)

                            # Validate the properties
                            if not isinstance(label, str) or not isinstance(shape_id, (int, str)):
                                logging.warning(f"Skipping feature due to invalid properties: {properties} for {shape_info['name']}")
                                continue

                            if label and geom_wkt:
                                existing_shape = (
                                    self.db.session.query(ShapeRef)
                                    .filter_by(label=label, type=shape_type)
                                    .scalar()
                                )

                                if not existing_shape:
                                    new_shape = ShapeRef(
                                        label=label,
                                        type=shape_type,
                                        location=geom_wkt,
                                    )
                                    self.db.session.add(new_shape)
                                else:
                                    # Update the existing shape
                                    existing_shape.location = geom_wkt

            self.db.session.commit()
            return "Shape data imported successfully."

        except Exception as e:
            self.db.session.rollback()
            logging.error(f"Error during shapes data import: {e}")
            raise e
        finally:
            self.db.close_db_session()

    def transform_geometry(self, geom, transformer):
        if isinstance(geom, Point):
            return self.transform_point(geom, transformer)
        elif isinstance(geom, LineString):
            return self.transform_linestring(geom, transformer)
        elif isinstance(geom, Polygon):
            return self.transform_polygon(geom, transformer)
        elif isinstance(geom, MultiPolygon):
            return MultiPolygon([self.transform_polygon(poly, transformer) for poly in geom.geoms])
        else:
            raise ValueError(f"Unsupported geometry type: {type(geom)}")

    @staticmethod
    def transform_point(point: Point, coord_transformer: Transformer) -> Point:
        x, y = point.x, point.y
        x, y = coord_transformer.transform(xx=x, yy=y)
        return Point(x, y)

    def transform_linestring(self, linestring: LineString, transformer) -> LineString:
        return LineString([self.transform_point(Point(x, y), transformer) for x, y, *_ in linestring.coords])

    def transform_polygon(self, polygon, transformer):
        exterior = self.transform_linestring(LineString(polygon.exterior.coords), transformer)
        interiors = [self.transform_linestring(LineString(interior.coords), transformer) for interior in
                     polygon.interiors]
        return Polygon(exterior, interiors)
