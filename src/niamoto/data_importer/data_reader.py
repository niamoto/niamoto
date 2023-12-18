import csv
import pandas as pd
from typing import Any


class DataReader:
    """
    A class that provides static methods for reading data files into Pandas DataFrames.
    """

    @staticmethod
    def read_csv_file(file_path: str) -> Any:
        """
        Reads a CSV file into a Pandas DataFrame.

        Parameters:
            file_path (str): The path to the CSV file.

        Returns:
            pd.DataFrame: The data read from the CSV file.

        Raises:
            Exception: If reading the CSV file fails.
        """
        try:
            # Open the file and read the first line to determine the separator
            with open(file_path, "r", encoding="utf-8") as file:
                dialect = csv.Sniffer().sniff(file.readline())
                file.seek(0)  # Reset file read position to the start
                sep = dialect.delimiter

            # Read the CSV file with the detected separator
            data = pd.read_csv(file_path, sep=sep, low_memory=False)
            return data

        except Exception as e:
            raise e


# Example usage:
# reader = DataReader()
# csv_data = DataReader.read_csv_file('path/to/file.csv')
# excel_data = DataReader.read_excel_file('path/to/file.xlsx')
# json_data = DataReader.read_json_file('path/to/file.json')
