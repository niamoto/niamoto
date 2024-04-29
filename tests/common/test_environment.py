import unittest
from unittest import mock
from niamoto.common.environment import Environment


class TestEnvironment(unittest.TestCase):
    def setUp(self):
        self.config = {
            "sources": {"raster": "/tmp/raster"},
            "web": {"static_pages": "/tmp/static_pages"},
            "logs": {},
            "database": {"path": "/tmp/test.db"},
        }
        self.env = Environment(self.config)

    @mock.patch("os.makedirs")
    @mock.patch("os.getcwd")
    def test_initialize(self, mock_getcwd, mock_makedirs):
        mock_getcwd.return_value = "/tmp"
        self.env.initialize()
        mock_makedirs.assert_any_call("/tmp/raster", exist_ok=True)

    @mock.patch("os.remove")
    @mock.patch("os.path.exists")
    @mock.patch("shutil.rmtree")
    def test_reset(self, mock_rmtree, mock_exists, mock_remove):
        mock_exists.return_value = True
        self.env.reset()
        mock_remove.assert_called_once_with("/tmp/test.db")
        mock_rmtree.assert_called_once_with("/tmp/static_pages")


if __name__ == "__main__":
    unittest.main()
