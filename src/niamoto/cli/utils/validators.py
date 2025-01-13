"""
Input validation utilities for the Niamoto CLI.
"""
import os
import click
from typing import Optional
import pandas as pd

from niamoto.common.database import Database


def validate_csv_file(
    file_path: str, required_columns: Optional[list[str]] = None
) -> None:
    """
    Validate a CSV file exists and optionally check for required columns.

    Raises:
        click.BadParameter: If validation fails
    """
    if not os.path.exists(file_path):
        raise click.BadParameter(f"File not found: {file_path}")

    if required_columns:
        try:
            df = pd.read_csv(file_path, nrows=0)
            missing = set(required_columns) - set(df.columns)
            if missing:
                raise click.BadParameter(
                    f"Missing required columns: {', '.join(missing)}"
                )
        except Exception as e:
            raise click.BadParameter(f"Invalid CSV file: {str(e)}")


def validate_database_connection(db_path: str) -> None:
    """
    Validate database connection can be established.

    Raises:
        click.BadParameter: If connection fails
    """
    try:
        db = Database(db_path)
        db.engine.connect()
    except Exception as e:
        raise click.BadParameter(f"Database connection failed: {str(e)}")
