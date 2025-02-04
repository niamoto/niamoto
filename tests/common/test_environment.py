"""Test module for the Environment class."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from niamoto.common.config import Config
from niamoto.common.environment import Environment


class TestEnvironment(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.mock_config = MagicMock(spec=Config)
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
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("niamoto.common.environment.Database")
    @patch("niamoto.common.environment.Base")
    def test_initialize(self, mock_base, mock_database):
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
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)

    @patch("os.path.exists")
    @patch("os.remove")
    @patch("shutil.rmtree")
    @patch("os.listdir")
    @patch("os.path.isfile")
    @patch("os.path.isdir")
    def test_reset(
        self,
        mock_isdir,
        mock_isfile,
        mock_listdir,
        mock_rmtree,
        mock_remove,
        mock_exists,
    ):
        """Test environment reset."""

        # Set up mocks to simulate existing directories and files
        def exists_side_effect(path):
            if path == self.mock_config.database_path:
                return True
            elif path == self.mock_config.get_export_config["web"]:
                return True
            elif path == self.mock_config.get_export_config["api"]:
                return True
            elif path == self.mock_config.logs_path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        # Mock the web directory contents
        web_dir = self.mock_config.get_export_config["web"]
        mock_listdir.return_value = ["file1.txt", "dir1", "files"]

        def isfile_side_effect(path):
            return os.path.basename(path) == "file1.txt"

        def isdir_side_effect(path):
            return os.path.basename(path) in ["dir1", "files"]

        mock_isfile.side_effect = isfile_side_effect
        mock_isdir.side_effect = isdir_side_effect

        # Call reset and verify behavior
        with patch.object(self.environment, "initialize") as mock_initialize:
            self.environment.reset()

            # Verify that the existing database file has been removed
            mock_remove.assert_any_call(self.mock_config.database_path)

            # Verify that files and directories in web directory are handled correctly
            mock_remove.assert_any_call(os.path.join(web_dir, "file1.txt"))
            mock_rmtree.assert_any_call(os.path.join(web_dir, "dir1"))

            # Verify that the API directory has been removed
            mock_rmtree.assert_any_call(self.mock_config.get_export_config["api"])

            # Verify that the logs directory has been removed
            mock_rmtree.assert_any_call(self.mock_config.logs_path)

            # Verify that the environment has been re-initialized
            mock_initialize.assert_called_once()

    @patch("niamoto.common.environment.Database")
    def test_initialization_with_empty_paths(self, mock_database):
        """Test environment initialization with empty paths."""
        self.mock_config.logs_path = ""
        self.mock_config.data_sources = {"empty_source": {"path": ""}}
        self.mock_config.get_export_config = {"empty_output": ""}

        self.environment.initialize()


if __name__ == "__main__":
    unittest.main()
