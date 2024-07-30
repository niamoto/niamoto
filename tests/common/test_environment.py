import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from niamoto.common.config import Config
from niamoto.common.environment import Environment


class TestEnvironment(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.database_path = os.path.join(self.test_dir, "db", "niamoto.db")
        self.mock_config.logs_path = os.path.join(self.test_dir, "logs")
        self.mock_config.data_sources = {
            "source1": {"path": os.path.join(self.test_dir, "data", "source1.csv")},
            "source2": {"path": os.path.join(self.test_dir, "data", "source2.csv")},
        }
        self.mock_config.output_paths = {
            "static_site": os.path.join(self.test_dir, "output", "static_site"),
            "static_api": os.path.join(self.test_dir, "output", "static_api"),
        }
        self.environment = Environment(self.mock_config)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.test_dir)

    @patch("niamoto.common.environment.Database")
    @patch("niamoto.common.environment.Base")
    def test_initialize(self, mock_base, mock_database):
        mock_engine = MagicMock()
        mock_database.return_value.engine = mock_engine

        self.environment.initialize()

        # Verify that all necessary directories have been created
        self.assertTrue(os.path.exists(os.path.dirname(self.mock_config.database_path)))
        self.assertTrue(os.path.exists(self.mock_config.logs_path))
        for source in self.mock_config.data_sources.values():
            self.assertTrue(os.path.exists(os.path.dirname(source["path"])))
        for path in self.mock_config.output_paths.values():
            self.assertTrue(os.path.exists(path))

        # Verify that the database has been initialized
        mock_database.assert_called_once_with(self.mock_config.database_path)
        mock_base.metadata.create_all.assert_called_once_with(mock_engine)

    @patch("os.path.exists")
    @patch("os.remove")
    @patch("shutil.rmtree")
    def test_reset(self, mock_rmtree, mock_remove, mock_exists):
        mock_exists.return_value = True

        with patch.object(self.environment, "initialize") as mock_initialize:
            self.environment.reset()

            # Verify that the existing database, configuration, web and api static_files have been deleted
            mock_remove.assert_called_once_with(self.mock_config.database_path)
            mock_rmtree.assert_any_call(self.mock_config.output_paths["static_site"])
            mock_rmtree.assert_any_call(self.mock_config.output_paths["static_api"])

            # Verify that the environment has been re-initialized
            mock_initialize.assert_called_once()

    @patch("niamoto.common.environment.Database")
    def test_initialization_with_empty_paths(self, mock_database):
        self.mock_config.logs_path = ""
        self.mock_config.data_sources = {"empty_source": {"path": ""}}
        self.mock_config.output_paths = {"empty_output": ""}

        self.environment.initialize()


if __name__ == "__main__":
    unittest.main()
