"""Test module for the Environment class."""

import os
import unittest
from unittest.mock import patch, MagicMock
import shutil
import tempfile

from niamoto.common.environment import Environment
from tests.common.base_test import NiamotoTestCase


class TestEnvironment(NiamotoTestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()

        # Create a mock with necessary attributes
        self.mock_config = MagicMock()
        self.mock_config.database_path = os.path.join(self.test_dir, "db", "niamoto.db")
        self.mock_config.logs_path = os.path.join(self.test_dir, "logs")
        self.mock_config.data_sources = {
            "source1": {"path": os.path.join(self.test_dir, "data", "source1.csv")},
            "source2": {"path": os.path.join(self.test_dir, "data", "source2.csv")},
        }
        self.mock_config.get_export_config = {
            "web": os.path.join(self.test_dir, "output", "static_site"),
            "api": os.path.join(self.test_dir, "output", "static_api"),
        }
        self.mock_config.get_niamoto_home.return_value = self.test_dir

        with patch("niamoto.common.environment.Config", return_value=self.mock_config):
            self.environment = Environment(self.test_dir)

    def tearDown(self):
        """Tear down test fixtures."""
        from unittest import mock

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # Stop all active patches to prevent MagicMock leaks
        mock.patch.stopall()

    @patch("niamoto.common.environment.Database", autospec=True)
    def test_initialize(self, mock_database):
        """Test environment initialization."""
        # Create the mock database
        mock_engine = MagicMock()
        mock_database.return_value.engine = mock_engine

        # Create necessary parent directories
        os.makedirs(os.path.dirname(self.mock_config.database_path), exist_ok=True)
        os.makedirs(self.mock_config.logs_path, exist_ok=True)
        for source in self.mock_config.data_sources.values():
            os.makedirs(os.path.dirname(source["path"]), exist_ok=True)
        for path in self.mock_config.get_export_config.values():
            os.makedirs(path, exist_ok=True)

        # Initialize the environment
        self.environment.initialize()

        # Verify that all necessary directories have been created
        self.assertTrue(os.path.exists(os.path.dirname(self.mock_config.database_path)))
        self.assertTrue(os.path.exists(self.mock_config.logs_path))
        for source in self.mock_config.data_sources.values():
            self.assertTrue(os.path.exists(os.path.dirname(source["path"])))
        for path in self.mock_config.get_export_config.values():
            self.assertTrue(os.path.exists(path))

        # Verify that the database has been initialized
        mock_database.assert_called_once_with(self.mock_config.database_path)

    @patch("niamoto.common.environment.Database")
    def test_reset(self, mock_database):
        """Test environment reset actually removes files and directories."""
        # Create real test files and directories to verify actual cleanup
        db_dir = os.path.dirname(self.mock_config.database_path)
        os.makedirs(db_dir, exist_ok=True)

        # Create a fake database file
        with open(self.mock_config.database_path, "w") as f:
            f.write("fake database content")

        # Create export directories with some content
        web_dir = self.mock_config.get_export_config["web"]
        api_dir = self.mock_config.get_export_config["api"]
        os.makedirs(web_dir, exist_ok=True)
        os.makedirs(api_dir, exist_ok=True)

        # Add some files to verify they get cleaned up
        with open(os.path.join(web_dir, "index.html"), "w") as f:
            f.write("<html>test</html>")
        with open(os.path.join(api_dir, "data.json"), "w") as f:
            f.write('{"test": "data"}')

        # Create logs directory with content
        os.makedirs(self.mock_config.logs_path, exist_ok=True)
        with open(os.path.join(self.mock_config.logs_path, "test.log"), "w") as f:
            f.write("log content")

        # Verify everything exists before reset
        self.assertTrue(os.path.exists(self.mock_config.database_path))
        self.assertTrue(os.path.exists(web_dir))
        self.assertTrue(os.path.exists(api_dir))
        self.assertTrue(os.path.exists(self.mock_config.logs_path))
        self.assertTrue(os.path.exists(os.path.join(web_dir, "index.html")))

        # Call reset
        self.environment.reset()

        # Verify actual cleanup happened (test real behavior, not mocks)
        # Database file should be deleted and not recreated
        self.assertFalse(
            os.path.exists(self.mock_config.database_path),
            "Database file should be removed",
        )

        # Export directories and their contents should be removed
        # Note: initialize() may recreate empty directories, but content should be gone
        if os.path.exists(web_dir):
            # If directory was recreated, it should be empty
            self.assertEqual(
                len(os.listdir(web_dir)), 0, "Web directory should be empty after reset"
            )
        # Original files should definitely be gone
        self.assertFalse(
            os.path.exists(os.path.join(web_dir, "index.html")),
            "Web directory content should be removed",
        )

        if os.path.exists(api_dir):
            self.assertEqual(
                len(os.listdir(api_dir)), 0, "API directory should be empty after reset"
            )
        self.assertFalse(
            os.path.exists(os.path.join(api_dir, "data.json")),
            "API directory content should be removed",
        )

        if os.path.exists(self.mock_config.logs_path):
            self.assertEqual(
                len(os.listdir(self.mock_config.logs_path)),
                0,
                "Logs directory should be empty after reset",
            )
        self.assertFalse(
            os.path.exists(os.path.join(self.mock_config.logs_path, "test.log")),
            "Log files should be removed",
        )

        # Verify environment was reinitialized
        # Database directory should be recreated by initialize()
        self.assertTrue(
            os.path.exists(db_dir),
            "Database directory should be recreated by initialize()",
        )

    @patch("niamoto.common.environment.Database", autospec=True)
    def test_initialization_with_empty_paths(self, mock_database):
        """Test environment initialization with empty paths."""
        self.mock_config.logs_path = ""
        self.mock_config.database_path = "/tmp/test_db.sqlite"  # Concrete value
        self.mock_config.data_sources = {"empty_source": {"path": ""}}
        self.mock_config.get_export_config = {"empty_output": ""}

        # Configure the mock database
        mock_instance = mock_database.return_value
        mock_instance.engine = MagicMock()

        with patch("niamoto.common.environment.Config", return_value=self.mock_config):
            self.environment = Environment(self.test_dir)
            self.environment.initialize()

    def test_init_with_config_error(self):
        """Test Environment initialization handles Config errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Mock Config to raise an error
        with patch(
            "niamoto.common.environment.Config", side_effect=Exception("Config failed")
        ):
            with self.assertRaises(EnvironmentSetupError) as cm:
                Environment("/invalid/path")
            self.assertIn(
                "Failed to initialize environment configuration", str(cm.exception)
            )

    @patch("niamoto.common.environment.Database")
    def test_initialize_creates_plugins_directory(self, mock_database):
        """Test that initialize creates plugins directory when configured."""
        # Add plugins config
        self.mock_config.config = {"plugins": {"path": "custom_plugins"}}

        self.environment.initialize()

        plugins_path = os.path.join(self.test_dir, "custom_plugins")
        self.assertTrue(os.path.exists(plugins_path))

    @patch("niamoto.common.environment.Database")
    def test_initialize_creates_templates_directory(self, mock_database):
        """Test that initialize creates templates directory and assets subdirectory."""
        # Add templates config
        self.mock_config.config = {"templates": {"path": "custom_templates"}}

        self.environment.initialize()

        templates_path = os.path.join(self.test_dir, "custom_templates")
        assets_path = os.path.join(templates_path, "assets")
        self.assertTrue(os.path.exists(templates_path))
        self.assertTrue(os.path.exists(assets_path))

    @patch("niamoto.common.environment.Database")
    def test_initialize_with_absolute_plugins_path(self, mock_database):
        """Test that initialize handles absolute paths for plugins."""
        abs_plugins_path = os.path.join(self.test_dir, "absolute_plugins")

        self.mock_config.config = {"plugins": {"path": abs_plugins_path}}

        self.environment.initialize()
        self.assertTrue(os.path.exists(abs_plugins_path))

    @patch("niamoto.common.environment.Database")
    def test_initialize_updates_project_name_in_config(self, mock_database):
        """Test that initialize updates project name in config.yml."""
        import yaml

        # Create a temporary config.yml
        config_file = os.path.join(self.test_dir, "config.yml")
        os.makedirs(self.test_dir, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump({"project": {}}, f)

        self.mock_config.config_dir = self.test_dir

        # Create Environment with project_name
        with patch("niamoto.common.environment.Config", return_value=self.mock_config):
            env = Environment(self.test_dir, project_name="Test Project")
            env.initialize()

        # Verify project name was written to config
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)

        self.assertEqual(config_data["project"]["name"], "Test Project")
        self.assertIn("created_at", config_data["project"])
        self.assertIn("niamoto_version", config_data["project"])

    @patch(
        "niamoto.common.environment.Database", side_effect=Exception("DB init failed")
    )
    def test_initialize_database_error(self, mock_database):
        """Test that initialize handles database initialization errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        with self.assertRaises(EnvironmentSetupError) as cm:
            self.environment.initialize()

        self.assertIn("Failed to initialize environment", str(cm.exception))

    def test_initialize_output_directory_error(self):
        """Test that initialize handles errors creating output directories."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Mock os.makedirs to fail for output directories
        with patch("os.makedirs") as mock_makedirs:
            # Let first calls succeed (db_dir, logs), then fail on output
            call_count = [0]

            def makedirs_side_effect(path, exist_ok=False):
                call_count[0] += 1
                if call_count[0] > 2:  # Fail after db and logs dirs
                    raise OSError("Permission denied")

            mock_makedirs.side_effect = makedirs_side_effect

            with self.assertRaises(EnvironmentSetupError):
                self.environment.initialize()

    def test_reset_handles_missing_database(self):
        """Test that reset handles missing database file gracefully."""
        # Database doesn't exist - should not raise
        self.mock_config.database_path = os.path.join(self.test_dir, "nonexistent.db")

        with patch.object(self.environment, "initialize"):
            self.environment.reset()  # Should not raise

    @patch("os.remove", side_effect=OSError("Permission denied"))
    def test_reset_database_removal_error(self, mock_remove):
        """Test that reset handles database removal errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Create a fake database file
        os.makedirs(os.path.dirname(self.mock_config.database_path), exist_ok=True)
        with open(self.mock_config.database_path, "w") as f:
            f.write("fake db")

        with self.assertRaises(EnvironmentSetupError):
            self.environment.reset()

    @patch("shutil.rmtree", side_effect=OSError("Permission denied"))
    def test_reset_web_directory_removal_error(self, mock_rmtree):
        """Test that reset handles web directory removal errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Create web directory
        web_dir = self.mock_config.get_export_config["web"]
        os.makedirs(web_dir, exist_ok=True)

        with self.assertRaises(EnvironmentSetupError):
            self.environment.reset()

    @patch("shutil.rmtree")
    def test_reset_api_directory_removal_error(self, mock_rmtree):
        """Test that reset handles API directory removal errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Create API directory
        api_dir = self.mock_config.get_export_config["api"]
        os.makedirs(api_dir, exist_ok=True)

        # Make rmtree fail only for API directory
        def rmtree_side_effect(path):
            if path == api_dir:
                raise OSError("Permission denied")

        mock_rmtree.side_effect = rmtree_side_effect

        with self.assertRaises(EnvironmentSetupError):
            self.environment.reset()

    @patch("shutil.rmtree")
    def test_reset_logs_directory_removal_error(self, mock_rmtree):
        """Test that reset handles logs directory removal errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Create logs directory
        os.makedirs(self.mock_config.logs_path, exist_ok=True)

        # Make rmtree fail only for logs directory
        def rmtree_side_effect(path):
            if path == self.mock_config.logs_path:
                raise OSError("Permission denied")

        mock_rmtree.side_effect = rmtree_side_effect

        with self.assertRaises(EnvironmentSetupError):
            self.environment.reset()

    @patch("niamoto.common.environment.Database")
    def test_reset_reinitialize_error(self, mock_database):
        """Test that reset handles reinitialize errors."""
        from niamoto.common.exceptions import EnvironmentSetupError

        # Make initialize fail after reset
        with patch.object(
            self.environment, "initialize", side_effect=Exception("Reinit failed")
        ):
            with self.assertRaises(EnvironmentSetupError) as cm:
                self.environment.reset()

            self.assertIn("Failed to reset environment", str(cm.exception))

    @patch("niamoto.common.environment.Database")
    def test_initialize_creates_imports_directory(self, mock_database):
        """Test that initialize creates imports directory."""
        self.environment.initialize()

        imports_dir = os.path.join(self.test_dir, "imports")
        self.assertTrue(os.path.exists(imports_dir))

    @patch("niamoto.common.environment.Database")
    def test_initialize_with_no_logs_path(self, mock_database):
        """Test initialize when logs_path is None."""
        self.mock_config.logs_path = None
        self.environment.initialize()  # Should not raise

    @patch("niamoto.common.environment.Database")
    def test_initialize_with_no_export_config(self, mock_database):
        """Test initialize when export config is empty."""
        self.mock_config.get_export_config = {}
        self.environment.initialize()  # Should not raise


if __name__ == "__main__":
    unittest.main()
