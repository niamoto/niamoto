import unittest
import pandas as pd
from niamoto.data_importer.data_validator import validate_data


class TestValidateData(unittest.TestCase):
    def test_validate_data_success(self):
        data = pd.DataFrame(
            {
                "id_family": [1, 2],
                "id_genus": [3, 4],
                "id_species": [5, 6],
                "id_infra": [7, 8],
            }
        )
        result = validate_data(data, "taxon")
        self.assertTrue(result)

    def test_validate_data_missing_columns(self):
        data = pd.DataFrame({"id_family": [1, 2], "id_genus": [3, 4]})
        result = validate_data(data, "taxon")
        self.assertFalse(result)

    def test_validate_data_empty_dataframe(self):
        data = pd.DataFrame()
        result = validate_data(data, "taxon")
        self.assertFalse(result)

    def test_validate_data_nonexistent_table(self):
        data = pd.DataFrame(
            {
                "id_family": [1, 2],
                "id_genus": [3, 4],
                "id_species": [5, 6],
                "id_infra": [7, 8],
            }
        )
        result = validate_data(data, "nonexistent_table")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
