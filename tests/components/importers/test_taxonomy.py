import os
import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

from niamoto.common.database import Database
from niamoto.core.components.imports.taxons import TaxonomyImporter


class TestTaxonomyImporter(unittest.TestCase):
    """
    The TestTaxonomyImporter class provides test cases for the TaxonomyImporter class.
    """

    def setUp(self):
        """
        Setup method for the test cases. It is automatically called before each test case.
        """
        self.db = MagicMock(spec=Database)
        self.importer = TaxonomyImporter(self.db)
        self.csv_file = "tests/test_data/data/sources/mock_taxonomy.csv"
        self.ranks = ("id_family", "id_genus", "id_species", "id_infra")

        # Create a test CSV file
        os.makedirs(os.path.dirname(self.csv_file), exist_ok=True)
        with open(self.csv_file, "w") as f:
            f.write(
                "id_taxon,full_name,rank_name,id_family,id_genus,id_species,id_infra,authors\n"
            )
            f.write("1,Famille1,id_family,1,,,,\n")
            f.write("2,Genre1,id_genus,1,2,,,Auteur1\n")
            f.write("3,Espece1,id_species,1,2,3,,Auteur2\n")
            f.write("4,Infra1,id_infra,1,2,3,4,Auteur3\n")

    def tearDown(self):
        """
        Teardown method for the test cases. It is automatically called after each test case.
        """
        # Delete the test CSV file
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    def test_import_from_csv(self):
        """
        Test case for the import_from_csv method of the TaxonomyImporter class.
        """
        with patch.object(
            self.importer, "_prepare_dataframe"
        ) as mock_prepare_dataframe, patch.object(
            self.importer, "_process_dataframe"
        ) as mock_process_dataframe:
            mock_prepare_dataframe.return_value = pd.DataFrame(
                {"id_taxon": [1]}
            )  # Retourner un DataFrame non vide avec une colonne "id_taxon"
            result = self.importer.import_from_csv(self.csv_file, self.ranks)
            mock_prepare_dataframe.assert_called_once()  # Vérifier que la méthode a été appelée une fois
            mock_process_dataframe.assert_called_once()
            self.assertEqual(
                result, f"Taxonomy data imported successfully from {self.csv_file}"
            )

    def test_prepare_dataframe(self):
        """
        Test case for the _prepare_dataframe method of the TaxonomyImporter class.
        """
        df = pd.read_csv(self.csv_file)
        result_df = self.importer._prepare_dataframe(df, self.ranks)
        expected_df = pd.DataFrame(
            {
                "id_taxon": [1, 2, 3, 4],
                "full_name": ["Famille1", "Genre1", "Espece1", "Infra1"],
                "rank_name": ["id_family", "id_genus", "id_species", "id_infra"],
                "id_family": [1, 1, 1, 1],
                "id_genus": [np.nan, 2, 2, 2],
                "id_species": [np.nan, np.nan, 3, 3],
                "id_infra": [np.nan, np.nan, np.nan, 4],
                "authors": [np.nan, "Auteur1", "Auteur2", "Auteur3"],
                "rank": ["id_family", "id_genus", "id_species", "id_infra"],
                "parent_id": [np.nan, 1, 2, 3],
            }
        )

        # Trier les DataFrames par la colonne "id_taxon"
        result_df.sort_values("id_taxon", inplace=True)
        expected_df.sort_values("id_taxon", inplace=True)

        # Réinitialiser les index des DataFrames
        result_df.reset_index(drop=True, inplace=True)
        expected_df.reset_index(drop=True, inplace=True)

        pd.testing.assert_frame_equal(result_df, expected_df, check_dtype=False)

    def test_get_rank(self):
        """
        Test case for the _get_rank method of the TaxonomyImporter class.
        """
        row = {
            "id_taxon": 1,
            "id_family": 1,
            "id_genus": None,
            "id_species": None,
            "id_infra": None,
        }
        self.assertEqual(self.importer._get_rank(row, self.ranks), "id_family")

        row = {
            "id_taxon": 2,
            "id_family": 1,
            "id_genus": 2,
            "id_species": None,
            "id_infra": None,
        }
        self.assertEqual(self.importer._get_rank(row, self.ranks), "id_genus")

        row = {
            "id_taxon": 3,
            "id_family": 1,
            "id_genus": 2,
            "id_species": 3,
            "id_infra": None,
        }
        self.assertEqual(self.importer._get_rank(row, self.ranks), "id_species")

        row = {
            "id_taxon": 4,
            "id_family": 1,
            "id_genus": 2,
            "id_species": 3,
            "id_infra": 4,
        }
        self.assertEqual(self.importer._get_rank(row, self.ranks), "id_infra")

    def test_get_parent_id(self):
        """
        Test case for the _get_parent_id method of the TaxonomyImporter class.
        """
        row = {
            "id_taxon": 1,
            "id_family": 1,
            "id_genus": None,
            "id_species": None,
            "id_infra": None,
        }
        self.assertIsNone(self.importer._get_parent_id(row, self.ranks))

        row = {
            "id_taxon": 2,
            "id_family": 1,
            "id_genus": 2,
            "id_species": None,
            "id_infra": None,
        }
        self.assertEqual(self.importer._get_parent_id(row, self.ranks), 1)

        row = {
            "id_taxon": 3,
            "id_family": 1,
            "id_genus": 2,
            "id_species": 3,
            "id_infra": None,
        }
        self.assertEqual(self.importer._get_parent_id(row, self.ranks), 2)

        row = {
            "id_taxon": 4,
            "id_family": 1,
            "id_genus": 2,
            "id_species": 3,
            "id_infra": 4,
        }
        self.assertEqual(self.importer._get_parent_id(row, self.ranks), 3)


if __name__ == "__main__":
    unittest.main()
