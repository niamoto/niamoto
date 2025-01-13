"""
This module contains the PlotImporter class, which is used to import plot data from a GeoPackage file into the database.
"""
import geopandas as gpd  # type: ignore
from shapely.wkt import dumps

from niamoto.common.database import Database
from niamoto.core.models import PlotRef
from niamoto.core.utils.logging_utils import setup_logging


class PlotImporter:
    """
    A class used to import plot data from a GeoPackage file into the database.

    Attributes:
        db (Database): The database connection.
    """

    def __init__(self, db: Database):
        """
        Initializes the PlotImporter with the database connection.

        Args:
            db (Database): The database connection.
        """
        self.db = db
        self.logger = setup_logging(component_name="plots_import")

    def import_from_gpkg(
        self, gpkg_path: str, identifier: str, location_field: str
    ) -> str:
        """
        Import plot data from a GeoPackage file.

        Args:
            gpkg_path (str): The path to the GeoPackage file to be imported.
            identifier (str): The name of the column in the GeoPackage that corresponds to the plot ID.
            location_field (str): The name of the column in the GeoPackage that corresponds to the location data.

        Returns:
            str: A message indicating the success of the import operation.

        Raises:
            Exception: If an error occurs during the import operation.
        """
        plots_data = gpd.read_file(gpkg_path)

        try:
            for index, row in plots_data.iterrows():
                # Convert Shapely geometry to WKT
                wkt_geometry = (
                    dumps(row[location_field]) if row[location_field] else None
                )

                existing_plot = (
                    self.db.session.query(PlotRef)
                    .filter_by(id=row[identifier], locality=row["locality"])
                    .scalar()
                )

                if not existing_plot:
                    plot = PlotRef(
                        id_locality=row[identifier],
                        locality=row["locality"],
                        geometry=wkt_geometry,
                    )
                    self.db.session.add(plot)

            self.db.session.commit()
            return f"Data from {gpkg_path} imported successfully into table plot_ref."

        except Exception as e:
            self.db.session.rollback()
            raise e
        finally:
            self.db.close_db_session()
