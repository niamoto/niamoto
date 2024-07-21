import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from niamoto.cli import commands
from niamoto.common.config import Config


class TestCommands(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp(prefix="niamoto_test_")
        os.environ["NIAMOTO_HOME"] = self.temp_dir

    def tearDown(self):
        os.environ.pop("NIAMOTO_HOME", None)
        os.rmdir(self.temp_dir)

    @patch('niamoto.cli.commands.Environment')
    @patch('niamoto.cli.commands.Config')
    def test_init(self, mock_config, mock_environment):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(Config, "get_niamoto_home", return_value=temp_dir):
                result = self.runner.invoke(commands.init)
        self.assertEqual(result.exit_code, 0)
        mock_environment.return_value.initialize.assert_called_once()

    @patch('niamoto.cli.commands.ImporterService')
    @patch('niamoto.cli.commands.Config')
    @patch('niamoto.cli.commands.reset_table')
    def test_import_taxonomy(self, mock_reset_table, mock_config, mock_importer_service):
        mock_config.return_value.get.return_value = {
            'path': 'test_taxonomy_path',
            'ranks': 'family,genus,species'
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write('header1,header2,header3\n')
            csv_path = temp_file.name

        try:
            result = self.runner.invoke(commands.import_taxonomy, [csv_path, '--ranks', 'family,genus,species'])
            self.assertEqual(result.exit_code, 0)
            mock_reset_table.assert_called_once()
            mock_importer_service.return_value.import_taxonomy.assert_called_once_with(csv_path, ('family', 'genus', 'species'))
        finally:
            os.unlink(csv_path)

    @patch('niamoto.cli.commands.ImporterService')
    @patch('niamoto.cli.commands.Config')
    @patch('niamoto.cli.commands.reset_table')
    def test_import_plots(self, mock_reset_table, mock_config, mock_importer_service):
        mock_config.return_value.get.return_value = {
            'path': 'test_plots_path',
            'identifier': 'plot_id',
            'location_field': 'geometry'
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write('plot_id,geometry\n')
            csv_path = temp_file.name

        try:
            result = self.runner.invoke(commands.import_plots, [csv_path, '--plot-identifier', 'plot_id', '--location-field', 'geometry'])
            self.assertEqual(result.exit_code, 0)
            mock_reset_table.assert_called_once()
            mock_importer_service.return_value.import_plots.assert_called_once_with(csv_path, 'plot_id', 'geometry')
        finally:
            os.unlink(csv_path)

    @patch('niamoto.cli.commands.ImporterService')
    @patch('niamoto.cli.commands.Config')
    @patch('niamoto.cli.commands.reset_table')
    def test_import_occurrences(self, mock_reset_table, mock_config, mock_importer_service):
        mock_config.return_value.get.return_value = {
            'path': 'test_occurrences_path',
            'identifier': 'taxon_id',
            'location_field': 'location'
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write('taxon_id,location\n')
            csv_path = temp_file.name

        try:
            result = self.runner.invoke(commands.import_occurrences, [csv_path, '--taxon-identifier', 'taxon_id', '--location-field', 'location'])
            self.assertEqual(result.exit_code, 0)
            mock_reset_table.assert_called_once()
            mock_importer_service.return_value.import_occurrences.assert_called_once_with(csv_path, 'taxon_id', 'location')
        finally:
            os.unlink(csv_path)

    @patch('niamoto.cli.commands.ImporterService')
    @patch('niamoto.cli.commands.Config')
    @patch('niamoto.cli.commands.reset_table')
    def test_import_occurrence_plot_links(self, mock_reset_table, mock_config, mock_importer_service):
        mock_config.return_value.get.return_value = {'path': 'test_occurrence_plots_path'}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_file.write('occurrence_id,plot_id\n')
            csv_path = temp_file.name

        try:
            result = self.runner.invoke(commands.import_occurrence_plot_links, [csv_path])
            self.assertEqual(result.exit_code, 0)
            mock_reset_table.assert_called_once()
            mock_importer_service.return_value.import_occurrence_plot_links.assert_called_once_with(csv_path)
        finally:
            os.unlink(csv_path)

    @patch('niamoto.cli.commands.ImporterService')
    @patch('niamoto.cli.commands.Config')
    @patch('niamoto.cli.commands.reset_table')
    def test_import_shapes(self, mock_reset_table, mock_config, mock_importer_service):
        mock_config.return_value.get.return_value = [{'name': 'shape1', 'path': 'shape1.shp'}]
        result = self.runner.invoke(commands.import_shapes)
        self.assertEqual(result.exit_code, 0)
        mock_reset_table.assert_called_once()
        mock_importer_service.return_value.import_shapes.assert_called_once()

    @patch('niamoto.cli.commands.ImporterService')
    @patch('niamoto.cli.commands.Config')
    @patch('niamoto.cli.commands.reset_tables')
    def test_import_all(self, mock_reset_tables, mock_config, mock_importer_service):
        with tempfile.TemporaryDirectory() as temp_dir:
            taxonomy_path = os.path.join(temp_dir, 'taxonomy.csv')
            plots_path = os.path.join(temp_dir, 'plots.csv')
            occurrences_path = os.path.join(temp_dir, 'occurrences.csv')
            occurrence_plots_path = os.path.join(temp_dir, 'occurrence_plots.csv')
            shape_path = os.path.join(temp_dir, 'shape1.shp')

            # Créer des fichiers avec un contenu minimal
            for path in [taxonomy_path, plots_path, occurrences_path, occurrence_plots_path]:
                with open(path, 'w') as f:
                    f.write('header1,header2,header3\n')
                    f.write('data1,data2,data3\n')

            # Créer un fichier shape vide
            open(shape_path, 'a').close()

            # Configurer le mock Config
            mock_config_instance = MagicMock()
            mock_config_instance.get.side_effect = lambda *args: {
                ('database', 'path'): os.path.join(temp_dir, 'test.db'),
                ('sources', 'taxonomy'): {'path': taxonomy_path, 'ranks': 'family,genus,species'},
                ('sources', 'plots'): {'path': plots_path, 'identifier': 'plot_id', 'location_field': 'geometry'},
                ('sources', 'occurrences'): {'path': occurrences_path, 'identifier': 'taxon_id',
                                             'location_field': 'location'},
                ('sources', 'occurrence-plots'): {'path': occurrence_plots_path},
                ('shapes',): [{'name': 'shape1', 'path': shape_path}]
            }.get(args, None)
            mock_config.return_value = mock_config_instance

            # Configurer le mock ImporterService
            mock_importer_instance = MagicMock()
            mock_importer_instance.import_taxonomy.return_value = "Taxonomy import successful"
            mock_importer_instance.import_plots.return_value = "Plots import successful"
            mock_importer_instance.import_occurrences.return_value = "Occurrences import successful"
            mock_importer_instance.import_occurrence_plot_links.return_value = "Occurrence plot links import successful"
            mock_importer_instance.import_shapes.return_value = "Shapes import successful"
            mock_importer_service.return_value = mock_importer_instance

            # Exécuter la commande
            result = self.runner.invoke(commands.import_all)

            print(f"Command output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                print(f"Exception traceback: {result.exc_info}")

            self.assertEqual(result.exit_code, 0,
                             f"Command failed with exit code {result.exit_code}. Error: {result.output}")

            # Vérifier les appels
            mock_reset_tables.assert_called_once()
            mock_importer_instance.import_taxonomy.assert_called_once_with(taxonomy_path,
                                                                           ('family', 'genus', 'species'))
            mock_importer_instance.import_plots.assert_called_once_with(plots_path, 'plot_id', 'geometry')
            mock_importer_instance.import_occurrences.assert_called_once_with(occurrences_path, 'taxon_id', 'location')
            mock_importer_instance.import_occurrence_plot_links.assert_called_once_with(occurrence_plots_path)
            mock_importer_instance.import_shapes.assert_called_once()

    @patch('niamoto.cli.commands.MapperService')
    @patch('niamoto.cli.commands.Config')
    def test_generate_mapping(self, mock_config, mock_mapper_service):
        result = self.runner.invoke(commands.generate_mapping, ['--data-source', 'test.csv', '--mapping-group', 'taxon'])
        self.assertEqual(result.exit_code, 0)
        mock_mapper_service.return_value.generate_mapping.assert_called_once()

    @patch('niamoto.cli.commands.StatisticService')
    @patch('niamoto.cli.commands.Config')
    def test_calculate_statistics(self, mock_config, mock_statistic_service):
        result = self.runner.invoke(commands.calculate_statistics)
        self.assertEqual(result.exit_code, 0)
        mock_statistic_service.return_value.calculate_statistics.assert_called_once()

    @patch('niamoto.cli.commands.GeneratorService')
    @patch('niamoto.cli.commands.Config')
    def test_generate_content(self, mock_config, mock_generator_service):
        result = self.runner.invoke(commands.generate_content)
        self.assertEqual(result.exit_code, 0)
        mock_generator_service.return_value.generate_content.assert_called_once()

    @patch('niamoto.cli.commands.deploy_to_github')
    def test_deploy_to_github(self, mock_deploy_to_github):
        result = self.runner.invoke(commands.deploy, ['--provider', 'github', '--output-dir', 'output', '--repo-url', 'https://github.com/test/repo.git'])
        self.assertEqual(result.exit_code, 0)
        mock_deploy_to_github.assert_called_once()

    @patch('niamoto.cli.commands.deploy_to_netlify')
    def test_deploy_to_netlify(self, mock_deploy_to_netlify):
        result = self.runner.invoke(commands.deploy, ['--provider', 'netlify', '--output-dir', 'output', '--site-id', 'test-site-id'])
        self.assertEqual(result.exit_code, 0)
        mock_deploy_to_netlify.assert_called_once()

if __name__ == '__main__':
    unittest.main()