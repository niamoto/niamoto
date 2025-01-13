from typing import List, Tuple
import pandas as pd
from loguru import logger


def analyze_csv_data_types(csv_file: str) -> List[Tuple[str, str]]:
    """
    Analyze the data types of columns in a CSV file.

    Args:
        csv_file (str): Path to the CSV file to be analyzed.

    Returns:
        List[Tuple[str, str]]: A list of tuples with column names and types.
    """
    try:
        # Read the CSV file with pandas
        df = pd.read_csv(
            csv_file, nrows=1000
        )  # Read first 1000 rows for type inference

        # Map pandas dtypes to SQLite types
        type_mapping = {
            "int64": "INTEGER",
            "float64": "REAL",
            "object": "TEXT",
            "bool": "INTEGER",
            "datetime64[ns]": "TEXT",
            "category": "TEXT",
        }

        types_info = []
        for column in df.columns:
            pandas_type = str(df[column].dtype)
            sqlite_type = type_mapping.get(pandas_type, "TEXT")
            types_info.append((column, sqlite_type))

        return types_info
    except Exception as e:
        logger.exception(f"Error analyzing CSV file: {e}")
        raise ValueError("Unable to analyze CSV file") from e


def is_sqlite_type_numeric(sqlite_type: str) -> bool:
    """
    Check if a SQLite data type is numeric.

    Args:
        sqlite_type (str): The data type of the column in SQLite.

    Returns:
        bool: True if the type is numeric, False otherwise.
    """
    numeric_types = [
        "INTEGER",
        "REAL",
        "DECIMAL",
        "NUMERIC",
    ]
    return sqlite_type.upper() in numeric_types
