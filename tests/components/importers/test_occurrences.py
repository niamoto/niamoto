import os
import unittest
from niamoto.core.components.importers.occurrences import OccurrenceImporter


class TestOccurrenceImporter(unittest.TestCase):
    """
    The TestOccurrenceImporter class provides test cases for the OccurrenceImporter class.
    """

    def setUp(self):
        """
        Setup method for the test cases. It is automatically called before each test case.
        """
        self.db_path = "tests/test_data/data/db/test.db"
        self.importer = OccurrenceImporter(self.db_path)
        self.csv_file = "tests/test_data/data/sources/mock_occurrences.csv"
        self.taxon_id_column = "id_taxonref"

        # Create a test CSV file
        with open(self.csv_file, "w") as f:
            f.write(
                '"id_source","source","original_name","family","taxaname","taxonref","rank","dbh","height","flower","fruit","month_obs","wood_density","leaf_sla","bark_thickness","leaf_area","leaf_thickness","leaf_ldmc","strate","elevation","rainfall","holdridge","province","in_forest","in_um","is_tree","id_taxonref","id_family","id_genus","id_species","id_infra","id_rank","geo_pt","plot"\n'
            )
            f.write(
                '67918,occ_ncpippn,Garcinia densiflora,Clusiaceae,Garcinia densiflora,Garcinia densiflora Pierre,Species,12.7,"9.95",false,false,2,"","","","","","","2",503,1750,2,PN,true,false,true,3434,14756,791,3434,"",21,POINT (165.111632 -21.133673),Forêt Plate P26\n'
            )

        # Create the taxon_ref table
        import duckdb

        con = duckdb.connect(self.db_path)
        con.execute(
            "CREATE TABLE IF NOT EXISTS taxon_ref (id BIGINT PRIMARY KEY, name VARCHAR)"
        )
        # con.execute("INSERT INTO taxon_ref (id, name) VALUES (3434, 'Garcinia densiflora Pierre')")
        con.close()

    def tearDown(self):
        """
        Teardown method for the test cases. It is automatically called after each test case.
        """
        # Delete the test database
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        # Delete the test CSV file
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    def test_import_occurrences(self):
        """
        Test case for the import_occurrences method of the OccurrenceImporter class.
        """
        result = self.importer.import_occurrences(self.csv_file, self.taxon_id_column)
        self.assertEqual(result, "Total occurrences imported: 1")

    def test_import_valid_occurrences(self):
        """
        Test case for the import_valid_occurrences method of the OccurrenceImporter class.
        """
        result = self.importer.import_valid_occurrences(
            self.csv_file, self.taxon_id_column, "geo_pt"
        )
        self.assertEqual(result, "Total valid occurrences imported: 0")


if __name__ == "__main__":
    unittest.main()
