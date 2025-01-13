"""
Database utilities for the Niamoto CLI.
"""
import os

from niamoto.cli.utils import print_success, print_error
from niamoto.common.database import Database
from niamoto.core.models import Base


def reset_table(db_path: str, table_name: str) -> None:
    """
    Reset a single table and recreate it using SQLAlchemy models if applicable.

    Args:
        db_path (str): The path to the database file.
        table_name (str): The name of the table to reset.

    Returns:
        None

    Raises:
        Exception: If an error occurs during the reset process.
    """
    db = Database(db_path)

    try:
        db.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
        print_success(f"Reset table: {table_name}")
    except Exception as e:
        print_error(f"Failed to reset table {table_name}: {str(e)}")

    # Recreate the table using SQLAlchemy models if the model exists
    try:
        engine = db.engine

        if table_name in Base.metadata.tables:
            Base.metadata.create_all(engine, tables=[Base.metadata.tables[table_name]])

    except Exception as e:
        print_error(f"Failed to recreate table {table_name}: {str(e)}")


def check_database_exists(db_path: str) -> bool:
    """
    Check if the database file exists and is accessible.
    """
    return os.path.exists(db_path)
