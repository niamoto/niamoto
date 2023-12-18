from typing import Any

required_columns = {
    "taxon": ["id_family", "id_genus", "id_species", "id_infra"],
    # add other tables and their required columns here
}


def validate_data(data: Any, table_name: str) -> bool:
    """
    Validate the data based on the table name and required columns.

    Args:
        data (pd.DataFrame): The data to be validated.
        table_name (str): The name of the table to validate against.

    Returns:
        bool: True if the data is valid, False otherwise.
    """
    if data.empty:
        return False

    if table_name in required_columns and not all(
        col in data.columns for col in required_columns[table_name]
    ):
        return False

    return True
