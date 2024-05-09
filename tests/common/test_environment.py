import unittest
from unittest import mock
from niamoto.common.environment import Environment


class TestEnvironment(unittest.TestCase):
    """
    The TestEnvironment class provides test cases for the Environment class.
    """

    def setUp(self):
        """
        Setup method for the test cases. It is automatically called before each test case.
        """
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
        """
        Test case for the initialize method of the Environment class.

        Args:
            mock_getcwd: A mock for the os.getcwd function.
            mock_makedirs: A mock for the os.makedirs function.
        """
        mock_getcwd.return_value = "/tmp"
        self.env.initialize()
        mock_makedirs.assert_any_call("/tmp/raster", exist_ok=True)

    @mock.patch("os.remove")
    @mock.patch("os.path.exists")
    @mock.patch("shutil.rmtree")
    def test_reset(self, mock_rmtree, mock_exists, mock_remove):
        """
        Test case for the reset method of the Environment class.

        Args:
            mock_rmtree: A mock for the shutil.rmtree function.
            mock_exists: A mock for the os.path.exists function.
            mock_remove: A mock for the os.remove function.
        """
        mock_exists.return_value = True
        self.env.reset()
        mock_remove.assert_called_once_with("/tmp/test.db")
        mock_rmtree.assert_called_once_with("/tmp/static_pages")


if __name__ == "__main__":
    unittest.main()
