import geopandas as gpd  # type: ignore
from shapely.wkt import dumps  # type: ignore

from niamoto.core.models import PlotRef
from niamoto.common.database import Database


class PlotImporter:
    def __init__(self, db: Database):
        self.db = db

    def import_from_gpkg(self, file_path: str) -> str:
        """
        Import plot data from a GeoPackage file.

        Args:
            file_path:  The path to the GeoPackage file to be imported.

        Returns:

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
