import unittest
from unittest.mock import Mock, patch
from niamoto.core.services.importer import ImporterService
import os
import tempfile
from tests.common.base_test import NiamotoTestCase


class TestImporterService(NiamotoTestCase):
    def setUp(self):
        # Create a temporary directory for config to avoid creating at project root
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")

        # Create a mock database and set up the ImporterService
        self.mock_db = Mock()
        with (
            patch(
                "niamoto.core.services.importer.Database",
                return_value=self.mock_db,
                autospec=True,
            ),
            patch("niamoto.core.components.imports.taxons.Config") as mock_config,
        ):
            # Mock Config to prevent creating config directory at project root
            mock_config.return_value.plugins_dir = self.config_dir
            self.importer_service = ImporterService("mock_db_path")

    def tearDown(self):
        """Clean up test fixtures and stop all patches."""
        from unittest import mock
        import shutil

        # Clean up temporary directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

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
    @patch("niamoto.core.services.importer.TaxonomyImporter.import_taxonomy")
    def test_import_taxonomy(
        self,
        mock_import_taxonomy,
        mock_exists,
    ):
        # Test the import_taxonomy method
        mock_exists.return_value = True
        mock_import_taxonomy.return_value = (
            "6 taxons extracted and imported from occurrences.csv."
        )

        hierarchy_config = {
            "levels": [
                {"name": "family", "column": "tax_fam"},
                {"name": "genus", "column": "tax_gen"},
                {"name": "species", "column": "tax_sp_level"},
            ],
            "taxon_id_column": "idtax_individual_f",
        }

        result = self.importer_service.import_taxonomy(
            "occurrences.csv", hierarchy_config
        )
        self.assertEqual(
            result, "6 taxons extracted and imported from occurrences.csv."
        )

    @patch("pathlib.Path.exists")
    @patch("niamoto.core.services.importer.TaxonomyImporter.import_taxonomy")
    def test_import_taxonomy_with_api_config(
        self,
        mock_import_taxonomy,
        mock_exists,
    ):
        # Test the import_taxonomy method with API configuration
        mock_exists.return_value = True
        mock_import_taxonomy.return_value = (
            "6 taxons extracted and imported from occurrences.csv."
        )

        hierarchy_config = {
            "levels": [
                {"name": "family", "column": "tax_fam"},
                {"name": "genus", "column": "tax_gen"},
            ],
            "taxon_id_column": "idtax_individual_f",
        }

        api_config = {
            "enabled": True,
            "plugin": "test_api",
        }

        result = self.importer_service.import_taxonomy(
            "occurrences.csv", hierarchy_config, api_config
        )
        self.assertEqual(
            result, "6 taxons extracted and imported from occurrences.csv."
        )
        # Check that the taxonomy importer was called with correct arguments
        # The path will be converted to absolute, so we check the other args
        call_args = mock_import_taxonomy.call_args[0]
        self.assertTrue(
            call_args[0].endswith("occurrences.csv")
        )  # Path ends with filename
        self.assertEqual(call_args[1], hierarchy_config)
        self.assertEqual(call_args[2], api_config)

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
    @patch("niamoto.core.components.imports.plots.PlotImporter.import_plots")
    def test_import_plots(self, mock_plot_importer_import_plots, mock_exists):
        # Test the import_plots method
        mock_exists.return_value = True
        mock_plot_importer_import_plots.return_value = "Plots import successful"

        result = self.importer_service.import_plots(
            "mock_file.gpkg", "plot_id", "location", locality_field="locality_name"
        )
        self.assertEqual(result, "Plots import successful")
        mock_plot_importer_import_plots.assert_called_once_with(
            "mock_file.gpkg",
            "plot_id",
            "location",
            locality_field="locality_name",
            link_field=None,
            occurrence_link_field=None,
            hierarchy_config=None,
        )

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
