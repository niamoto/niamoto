from typing import List, Tuple
import duckdb
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
        con = duckdb.connect()
        con.execute(
            f"CREATE TEMPORARY TABLE temp_csv AS SELECT * FROM READ_CSV_AUTO('{csv_file}')"
        )
        types_info = con.execute("DESCRIBE temp_csv").fetchall()
        con.close()
        return [(col_info[0], col_info[1]) for col_info in types_info]
    except Exception as e:
        logger.exception(f"Error analyzing CSV file with DuckDB: {e}")
        raise ValueError("Unable to analyze CSV file") from e


def is_duckdb_type_numeric(duckdb_type: str) -> bool:
    """
    Check if a DuckDB data type is numeric.

    Args:
        duckdb_type (str): The data type of the column in DuckDB.

    Returns:
        bool: True if the type is numeric, False otherwise.
    """
    numeric_types = [
        "TINYINT",
        "SMALLINT",
        "INTEGER",
        "BIGINT",
        "HUGEINT",
        "UTINYINT",
        "USMALLINT",
        "UINTEGER",
        "UBIGINT",
        "UHUGEINT",
        "DECIMAL",
        "REAL",
        "DOUBLE",
    ]
    return duckdb_type.upper() in numeric_types
