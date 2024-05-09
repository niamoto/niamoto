import os
import tempfile
import shutil
import unittest
from unittest import mock
from click.testing import CliRunner
from niamoto.cli import commands
from niamoto.common.config import Config


class TestCommands(unittest.TestCase):
    """
    The TestCommands class provides test cases for the commands in the CLI.
    """

    def setUp(self):
        """
        Setup method for the test cases. It is automatically called before each test case.
        """
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp(prefix="niamoto_test_")
        os.environ["NIAMOTO_HOME"] = self.temp_dir

    def tearDown(self):
        """
        Teardown method for the test cases. It is automatically called after each test case.
        """
        os.environ.pop("NIAMOTO_HOME", None)
        shutil.rmtree(self.temp_dir)

    @mock.patch("niamoto.cli.commands.Console")
    @mock.patch("niamoto.cli.commands.Environment")
    @mock.patch("niamoto.cli.commands.Config")
    @mock.patch("niamoto.cli.commands.list_commands")
    def test_init_new_environment(
        self, mock_list_commands, mock_config, mock_environment, mock_console
    ):
        """
        Test case for the 'init' command of the CLI.

        Args:
            mock_list_commands: A mock for the list_commands function.
            mock_config: A mock for the Config class.
            mock_environment: A mock for the Environment class.
            mock_console: A mock for the Console class.
        """
        # Create a temporary directory for the configuration file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure the path of the configuration file in the temporary directory
            config_path = os.path.join(temp_dir, "config.yml")

            # Patch the get_niamoto_home method of Config to return the temporary directory
            with mock.patch.object(Config, "get_niamoto_home", return_value=temp_dir):
                # Configure the mock Config to return the path of the temporary configuration file
                mock_config.return_value.config_path = config_path

                # Execute the 'init' command without any options
                result = self.runner.invoke(commands.init)

            # Verify that the command has exited with the exit code 0
            self.assertEqual(result.exit_code, 0)

            # Verify that 'Environment' has been called with the configuration object
            mock_environment.assert_called_once_with(mock_config.return_value.config)

            # Verify that 'Environment.initialize' has been called
            mock_environment.return_value.initialize.assert_called_once()

            # Verify that 'Console.print' has been called with the initialization message
            mock_console.return_value.print.assert_any_call(
                "🌱 Niamoto initialized.", style="italic green"
            )

            mock_console.return_value.rule.assert_called_once()

            mock_list_commands.assert_called_once_with(commands.cli)

    @mock.patch("niamoto.cli.commands.Console")
    @mock.patch("niamoto.cli.commands.Table")
    def test_list_commands(self, mock_table, mock_console):
        """
        Test case for the 'list_commands' function of the CLI.

        Args:
            mock_table: A mock for the Table class.
            mock_console: A mock for the Console class.
        """
        # Create a mock group with two commands
        mock_group = mock.MagicMock()
        command1 = mock.MagicMock()
        command1.name = "command1"
        command1.callback.__doc__ = "description1"
        command2 = mock.MagicMock()
        command2.name = "command2"
        command2.callback.__doc__ = "description2"
        mock_group.commands.values.return_value = [command1, command2]

        # Call the 'list_commands' function with the mock group
        commands.list_commands(mock_group)

        # Verify that 'Console' and 'Table' have been called once
        mock_console.assert_called_once()
        mock_table.assert_called_once()

        # Print out the calls to the 'add_row' method
        print(mock_table.return_value.add_row.call_args_list)

        # Verify that 'Table.add_column' has been called twice
        mock_table.return_value.add_row.assert_any_call("command1", "description1")
        mock_table.return_value.add_row.assert_any_call("command2", "description2")

    @mock.patch("niamoto.cli.commands.ApiImporter")
    @mock.patch("niamoto.cli.commands.Console")
    def test_import_occurrences(self, mock_console, mock_api_importer):
        """
        Test case for the 'import-occurrences' command of the CLI.

        Args:
            mock_console: A mock for the Console class.
            mock_api_importer: A mock for the ApiImporter class.
        """
        mock_result = mock.MagicMock()
        mock_result.__str__.side_effect = lambda: "Import successful"
        mock_api_importer.return_value.import_occurrences.return_value = mock_result

        result = self.runner.invoke(
            commands.cli,
            ["import-occurrences", "test.csv", "--taxon-id-column", "taxon_id"],
        )

        self.assertEqual(result.exit_code, 0)

    @mock.patch("niamoto.cli.commands.ApiImporter")
    def test_import_taxonomy(self, mock_api_importer):
        """
        Test case for the 'import-taxonomy' command of the CLI.

        Args:
            mock_api_importer: A mock for the ApiImporter class.
        """
        mock_api_importer.return_value.import_taxononomy.return_value = (
            "Import successful"
        )

        runner = CliRunner()

        result = runner.invoke(
            commands.cli, ["import-taxonomy", "test.csv", "--ranks", "species"]
        )

        mock_api_importer.return_value.import_taxononomy.assert_called_once_with(
            "test.csv", ("species",)
        )

        self.assertEqual(result.output.strip(), "Import successful")

    @mock.patch("niamoto.cli.commands.ApiImporter")
    def test_import_plots(self, mock_api_importer):
        """
        Test case for the 'import-plots' command of the CLI.

        Args:
            mock_api_importer: A mock for the ApiImporter class.
        """
        mock_api_importer.return_value.import_plots.return_value = "Import successful"

        runner = CliRunner()

        result = runner.invoke(commands.cli, ["import-plots", "test.gpkg"])

        mock_api_importer.return_value.import_plots.assert_called_once_with("test.gpkg")

        self.assertEqual(result.output.strip(), "Import successful")

    @mock.patch("niamoto.cli.commands.ApiMapper")
    def test_generate_mapping_add_new_field(self, mock_api_mapper):
        """
        Test case for the 'generate-mapping' command of the CLI.

        Args:
            mock_api_mapper: A mock for the ApiMapper class.
        """
        mock_api_mapper.return_value.add_new_mapping.return_value = None

        runner = CliRunner()

        result = runner.invoke(
            commands.cli,
            ["generate-mapping", "--add", "new_field", "--key", "mapping_key"],
        )

        self.assertEqual(result.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
