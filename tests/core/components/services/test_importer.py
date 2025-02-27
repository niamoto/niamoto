import unittest
from unittest.mock import Mock, patch
from niamoto.core.services.importer import ImporterService
import os
from tests.common.base_test import NiamotoTestCase


class TestImporterService(NiamotoTestCase):
    def setUp(self):
        # Create a mock database and set up the ImporterService
        self.mock_db = Mock()
        with patch(
            "niamoto.core.services.importer.Database",
            return_value=self.mock_db,
            autospec=True,
        ):
            self.importer_service = ImporterService("mock_db_path")

    def tearDown(self):
        """Clean up test fixtures and stop all patches."""
        from unittest import mock

        # Stop all active patches to prevent MagicMock leaks
        mock.patch.stopall()

    def test_init(self):
        # Test the initialization of ImporterService
        self.assertIsInstance(self.importer_service.db, Mock)
        self.assertIsNotNone(self.importer_service.taxonomy_importer)
        self.assertIsNotNone(self.importer_service.occurrence_importer)
        self.assertIsNotNone(self.importer_service.plot_importer)
        self.assertIsNotNone(self.importer_service.shape_importer)

    @patch("pathlib.Path.exists")
    @patch("niamoto.core.services.importer.ImporterService._detect_separator")
    @patch("niamoto.core.services.importer.ImporterService._validate_csv_format")
    @patch("niamoto.core.services.importer.TaxonomyImporter.import_from_csv")
    def test_import_taxonomy(
        self,
        mock_import_from_csv,
        mock_validate_csv,
        mock_detect_separator,
        mock_exists,
    ):
        # Test the import_taxonomy method
        mock_exists.return_value = True
        mock_detect_separator.return_value = ","
        mock_validate_csv.return_value = set()  # Pas de champs manquants
        mock_import_from_csv.return_value = "Taxonomy import successful"

        result = self.importer_service.import_taxonomy(
            "mock_file.csv", ("genus", "species")
        )
        self.assertEqual(result, "Taxonomy import successful")

    def test_detect_separator(self):
        # Test the _detect_separator method
        with open("test.csv", "w") as f:
            f.write("col1,col2,col3\n")
            f.write("val1,val2,val3\n")

        try:
            result = self.importer_service._detect_separator("test.csv")
            self.assertEqual(result, ",")
        finally:
            os.remove("test.csv")

    @patch("pandas.read_csv")
    def test_validate_csv_format(self, mock_read_csv):
        # Test the _validate_csv_format method
        mock_df = Mock()
        mock_df.columns = ["id_taxon", "full_name", "authors", "genus", "species"]
        mock_read_csv.return_value = mock_df

        missing_fields = self.importer_service._validate_csv_format(
            "mock_file.csv", ",", ("genus", "species")
        )
        # Aucun champ manquant car tous les champs requis sont présents
        self.assertEqual(missing_fields, set())

    @patch("pathlib.Path.exists")
    @patch("niamoto.core.services.importer.OccurrenceImporter.import_valid_occurrences")
    def test_import_occurrences(self, mock_import_valid_occurrences, mock_exists):
        # Test the import_occurrences method
        mock_exists.return_value = True
        mock_import_valid_occurrences.return_value = "Occurrences import successful"

        result = self.importer_service.import_occurrences(
            "mock_file.csv", "taxon_id", "location"
        )
        self.assertEqual(result, "Occurrences import successful")

    @patch("pathlib.Path.exists")
    @patch("niamoto.core.services.importer.PlotImporter.import_from_gpkg")
    def test_import_plots(self, mock_import_from_gpkg, mock_exists):
        # Test the import_plots method
        mock_exists.return_value = True
        mock_import_from_gpkg.return_value = "Plots import successful"

        result = self.importer_service.import_plots(
            "mock_file.gpkg", "plot_id", "location"
        )
        self.assertEqual(result, "Plots import successful")

    @patch("pathlib.Path.exists")
    @patch(
        "niamoto.core.services.importer.OccurrenceImporter.import_occurrence_plot_links"
    )
    def test_import_occurrence_plot_links(
        self, mock_import_occurrence_plot_links, mock_exists
    ):
        # Test the import_occurrence_plot_links method
        mock_exists.return_value = True
        mock_import_occurrence_plot_links.return_value = (
            "Occurrence-plot links import successful"
        )

        result = self.importer_service.import_occurrence_plot_links("mock_file.csv")
        self.assertEqual(result, "Occurrence-plot links import successful")

    @patch("niamoto.core.services.importer.ShapeImporter.import_from_config")
    def test_import_shapes(self, mock_import_from_config):
        # Test the import_shapes method
        mock_import_from_config.return_value = "Shapes import successful"

        shapes_config = [
            {"name": "shape1", "file": "shape1.shp"},
            {"name": "shape2", "file": "shape2.shp"},
        ]
        result = self.importer_service.import_shapes(shapes_config)

        self.assertEqual(result, "Shapes import successful")
        mock_import_from_config.assert_called_once_with(shapes_config)


if __name__ == "__main__":
    unittest.main()
