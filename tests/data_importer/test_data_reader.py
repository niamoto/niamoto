import unittest
from unittest.mock import patch, mock_open
import pandas as pd
from niamoto.data_importer.data_reader import DataReader


class TestDataReader(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="col1,col2\nval1,val2")
    @patch("pandas.read_csv")
    def test_read_csv_file(self, mock_read_csv, mock_file):
        # Arrange
        file_path = "mock_file.csv"
        mock_read_csv.return_value = pd.DataFrame({"col1": ["val1"], "col2": ["val2"]})

        # Act
        result = DataReader.read_csv_file(file_path)

        # Assert
        mock_read_csv.assert_called_once()
        self.assertIsInstance(result, pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
