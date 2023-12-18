import unittest
from unittest.mock import patch
from niamoto.data_importer.data_importer import DataImporter
from niamoto.common.exceptions import FileReadError


class TestDataImporter(unittest.TestCase):
    @patch("niamoto.data_importer.data_importer.DataWriter")
    @patch("niamoto.data_importer.data_importer.DataReader")
    @patch("niamoto.data_importer.data_importer.validate_data")
    def test_orchestrate_data_import_csv(
        self, mock_validate_data, mock_data_reader, mock_data_writer
    ):
        # Arrange for CSV file
        mock_db_path = "mock_db_path"
        mock_file_path = "mock_file_path.csv"
        mock_table_name = "mock_table_name"
        mock_data = [{"column1": "data1"}]
        mock_data_reader.read_csv_file.return_value = mock_data
        mock_validate_data.return_value = True

        # Act
        importer = DataImporter(mock_db_path)
        importer.orchestrate_data_import(mock_file_path, mock_table_name)

        # Assert
        mock_data_reader.read_csv_file.assert_called_once_with(mock_file_path)
        mock_validate_data.assert_called_once_with(mock_data, mock_table_name)
        mock_data_writer.return_value.write_to_db.assert_called_once_with(
            mock_table_name, mock_data
        )

    @patch("niamoto.data_importer.data_importer.DataWriter")
    @patch("niamoto.data_importer.data_importer.DataReader")
    @patch("niamoto.data_importer.data_importer.validate_data")
    def test_orchestrate_data_import_unsupported_type(
        self, mock_validate_data, mock_data_reader, mock_data_writer
    ):
        # Arrange for unsupported file type
        mock_db_path = "mock_db_path"
        mock_file_path = "mock_file_path.unsupported"
        mock_table_name = "mock_table_name"

        # Act & Assert
        importer = DataImporter(mock_db_path)
        with self.assertRaises(FileReadError):
            importer.orchestrate_data_import(mock_file_path, mock_table_name)

        mock_data_reader.read_csv_file.assert_not_called()
        mock_validate_data.assert_not_called()
        mock_data_writer.return_value.write_to_db.assert_not_called()


if __name__ == "__main__":
    unittest.main()
