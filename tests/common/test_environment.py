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
    @patch("niamoto.common.environment.Base", autospec=True)
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

    @patch("os.path.exists", autospec=True)
    @patch("os.remove", autospec=True)
    @patch("shutil.rmtree", autospec=True)
    @patch("os.listdir", autospec=True)
    @patch("os.path.isfile", autospec=True)
    @patch("os.path.isdir", autospec=True)
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

        # Mock the web directory contents - not used anymore since entire directory is removed
        mock_listdir.return_value = ["file1.txt", "dir1"]

        def isfile_side_effect(path):
            return os.path.basename(path) == "file1.txt"

        def isdir_side_effect(path):
            return os.path.basename(path) == "dir1"

        mock_isfile.side_effect = isfile_side_effect
        mock_isdir.side_effect = isdir_side_effect

        # Call reset and verify behavior
        with patch.object(
            self.environment, "initialize", autospec=True
        ) as mock_initialize:
            self.environment.reset()

            # Verify that the existing database file has been removed
            mock_remove.assert_any_call(self.mock_config.database_path)

            # Verify that the web directory has been removed completely
            mock_rmtree.assert_any_call(self.mock_config.get_export_config["web"])

            # Verify that the API directory has been removed
            mock_rmtree.assert_any_call(self.mock_config.get_export_config["api"])

            # Verify that the logs directory has been removed
            mock_rmtree.assert_any_call(self.mock_config.logs_path)

            # Verify that the environment has been re-initialized
            mock_initialize.assert_called_once()

    @patch("niamoto.common.environment.Database", autospec=True)
    @patch("niamoto.common.environment.Base", autospec=True)
    def test_initialization_with_empty_paths(self, mock_base, mock_database):
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


if __name__ == "__main__":
    unittest.main()
