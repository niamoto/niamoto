import logging
import os
import tempfile
import zipfile
from typing import List

import fiona
import pandas as pd
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

    def import_from_csv(self, file_path: str) -> str:
        """
        Import shape data from a CSV file.

        Args:
            file_path (str): The path to the CSV file to be imported.

        Returns:
            str: A message indicating the success of the import operation.

        Raises:
            Exception: If an error occurs during the import operation.
        """
        shapes_data = pd.read_csv(file_path)

        try:
            for index, row in shapes_data.iterrows():
                # Ensure the shape_location and forest_location columns are strings
                location_wkt = (
                    str(row["location"])
                    if pd.notna(row["location"])
                    else None
                )

                # Ensure other fields are correctly typed
                label = str(row["label"]) if pd.notna(row["label"]) else None
                type_shape = str(row["type"]) if pd.notna(row["type"]) else None

                existing_shape = (
                    self.db.session.query(ShapeRef)
                    .filter_by(label=label, type=type_shape)
                    .scalar()
                )

                if not existing_shape:
                    shape_ref = ShapeRef(
                        label=label,
                        type=type_shape,
                        location=location_wkt,
                    )
                    self.db.session.add(shape_ref)
            self.db.session.commit()

            return f"Data from {file_path} imported successfully into table shape_ref."

        except Exception as e:
            self.db.session.rollback()
            raise e
        finally:
            self.db.close_db_session()

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

                # Create a temporary directory to extract zip files if necessary
                with tempfile.TemporaryDirectory() as tmpdirname:
                    if file_path.endswith('.zip'):
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            zip_ref.extractall(tmpdirname)
                        # Find the .gpkg or .shp file in the extracted contents
                        for root, dirs, files in os.walk(tmpdirname):
                            for file in files:
                                if file.endswith(
                                        ('.gpkg', '.shp', '.geojson', '.json', '.tab', '.mif', '.mid', '.gdb')):
                                    file_path = os.path.join(root, file)
                                    break
                            if file_path != shape_info['path']:  # If we found a new file_path
                                break

                    with fiona.open(file_path, 'r') as src:
                        for feature in src:
                            geom = shape(feature['geometry'])
                            geom_wkt = geom.wkt
                            properties = feature['properties']
                            label = properties.get(name_field)
                            shape_id = properties.get(id_field)

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

            self.db.session.commit()
            return "Shape data imported successfully."

        except Exception as e:
            self.db.session.rollback()
            logging.error(f"Error during shapes data import: {e}")
            raise e
        finally:
            self.db.close_db_session()
