from typing import Any

from niamoto.data_processor.taxon.processor import TaxonDataProcessor


class DataWriter:
    """
    A class that provides methods for writing data to a database.
    """

    def __init__(self, db_path: str):
        """
        Initialize a DataWriter instance.

        Parameters:
            db_path (str): The path to the database.
        """
        self.taxon_data_processor = TaxonDataProcessor(db_path)

    def write_to_db(self, table_name: str, data: Any) -> None:
        """
        Writes data to a specified table in the database.

        Parameters:
            table_name (str): The name of the table to write to.
            data (pd.DataFrame): The data to write.

        Notes:
            - If the table name is 'taxon', special processing is applied.
            - Otherwise, data is directly written to the table.
        """
        if table_name == "taxon":
            # Process and write taxon data using the TaxonDataProcessor class
            self.taxon_data_processor.process_and_write_taxon_data(data)


# Example usage:
# writer = DataWriter('path/to/my_database.db')
# writer.write_to_db('some_table', some_dataframe)
