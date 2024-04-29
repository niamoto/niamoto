import pytest
from niamoto.api.importer import ApiImporter


@pytest.mark.usefixtures("niamoto_home")  # Assure que chaque test utilise cette fixture
class TestApiImporter:
    def test_import_taxons(self, mocker):
        mock_importer_service = mocker.patch("niamoto.api.importer.ImporterService")
        api_importer = ApiImporter()
        mock_importer_service.return_value.import_taxonomy.return_value = (
            "Import successful"
        )

        result = api_importer.import_taxononomy("test.csv", ("species",))

        mock_importer_service.return_value.import_taxonomy.assert_called_once_with(
            "test.csv", ("species",)
        )
        assert result == "Import successful"

    def test_import_plots(self, mocker):
        mock_importer_service = mocker.patch("niamoto.api.importer.ImporterService")
        api_importer = ApiImporter()
        mock_importer_service.return_value.import_plots.return_value = (
            "Import successful"
        )

        result = api_importer.import_plots("test.gpkg")

        mock_importer_service.return_value.import_plots.assert_called_once_with(
            "test.gpkg"
        )
        assert result == "Import successful"

    def test_import_occurrences(self, mocker):
        mock_importer_service = mocker.patch("niamoto.api.importer.ImporterService")
        api_importer = ApiImporter()
        mock_importer_service.return_value.import_occurrences.return_value = (
            "Import successful"
        )

        result = api_importer.import_occurrences("test.csv", "taxon_id")

        mock_importer_service.return_value.import_occurrences.assert_called_once_with(
            "test.csv", "taxon_id"
        )
        assert result == "Import successful"

    def test_import_occurrence_plot_links(self, mocker):
        mock_importer_service = mocker.patch("niamoto.api.importer.ImporterService")
        api_importer = ApiImporter()
        mock_importer_service.return_value.import_occurrence_plot_links.return_value = (
            "Import successful"
        )

        result = api_importer.import_occurrence_plot_links("test.csv")

        mock_importer_service.return_value.import_occurrence_plot_links.assert_called_once_with(
            "test.csv"
        )
        assert result == "Import successful"
