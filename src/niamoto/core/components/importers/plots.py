import geopandas as gpd  # type: ignore
from shapely.wkt import dumps  # type: ignore

from niamoto.core.models import PlotRef
from niamoto.common.database import Database


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

    def import_from_gpkg(self, file_path: str) -> str:
        """
        Import plot data from a GeoPackage file.

        Args:
            file_path (str): The path to the GeoPackage file to be imported.

        Returns:
            str: A message indicating the success of the import operation.

        Raises:
            Exception: If an error occurs during the import operation.
        """
        plots_data = gpd.read_file(file_path)

        try:
            for index, row in plots_data.iterrows():
                # Convert Shapely geometry to WKT
                wkt_geometry = dumps(row["geometry"]) if row["geometry"] else None

                existing_plot = (
                    self.db.session.query(PlotRef)
                    .filter_by(id_locality=row["id_locality"], locality=row["locality"])
                    .scalar()
                )

                if not existing_plot:
                    plot = PlotRef(
                        id_locality=row["id_locality"],
                        locality=row["locality"],
                        substrat=row["substrat"],
                        geometry=wkt_geometry,  # Utilisation de la chaîne WKT
                    )
                    self.db.session.add(plot)
            self.db.session.commit()

            return f"Data from {file_path} imported successfully into table plot_ref."

        except Exception as e:
            self.db.session.rollback()
            raise e
        finally:
            self.db.close_db_session()
