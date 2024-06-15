import pandas as pd
from niamoto.core.models import ShapeRef
from niamoto.common.database import Database


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
                shape_location_wkt = (
                    str(row["shape_location"])
                    if pd.notna(row["shape_location"])
                    else None
                )
                forest_location_wkt = (
                    str(row["forest_location"])
                    if pd.notna(row["forest_location"])
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
                    shape = ShapeRef(
                        label=label,
                        type=type_shape,
                        shape_location=shape_location_wkt,
                        forest_location=forest_location_wkt,
                    )
                    self.db.session.add(shape)
            self.db.session.commit()

            return f"Data from {file_path} imported successfully into table shape_ref."

        except Exception as e:
            self.db.session.rollback()
            raise e
        finally:
            self.db.close_db_session()
