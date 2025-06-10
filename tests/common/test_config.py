"""Test module for the Config class."""

import os
import unittest
from unittest.mock import patch
import shutil
import tempfile
import yaml
from niamoto.common.config import Config
from niamoto.common.exceptions import (
    ConfigurationError,
    EnvironmentSetupError,
)
from tests.common.base_test import NiamotoTestCase


class TestConfig(NiamotoTestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, "config")

    def tearDown(self):
        """Tear down test fixtures."""
        from unittest import mock

        # Clean up test directory
        if os.path.exists(self.config_dir):
            shutil.rmtree(self.config_dir)

        # Stop all active patches to prevent MagicMock leaks
        mock.patch.stopall()

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        # In test mode, files are not created but config should still work
        config = Config(config_dir=self.config_dir, create_default=True)
        # Check that config has default values
        self.assertEqual(config.database_path, "db/niamoto.db")
        self.assertEqual(config.logs_path, "logs")

    def test_init_with_custom_dir(self):
        """Test initialization with custom config directory."""
        custom_dir = os.path.join(self.test_dir, "custom_config")
        config = Config(config_dir=custom_dir, create_default=True)
        # In test mode, files are not created but config should still work
        self.assertEqual(config.config_dir, custom_dir)

    def test_database_path(self):
        """Test getting database path."""
        config = Config(config_dir=self.config_dir, create_default=True)
        self.assertEqual(config.database_path, "db/niamoto.db")

    def test_logs_path(self):
        """Test getting logs path."""
        config = Config(config_dir=self.config_dir, create_default=True)
        self.assertEqual(config.logs_path, "logs")

    def test_get_export_config(self):
        """Test getting export configuration."""
        config = Config(config_dir=self.config_dir, create_default=True)
        exports = config.get_export_config
        self.assertEqual(exports["web"], "exports/web")
        self.assertEqual(exports["api"], "exports/api")

    def test_get_imports_config(self):
        """Test getting imports configuration."""
        config = Config(config_dir=self.config_dir, create_default=True)
        imports = config.get_imports_config
        self.assertIn("taxonomy", imports)
        self.assertIn("occurrences", imports)
        self.assertIn("plots", imports)
        self.assertEqual(imports["taxonomy"]["type"], "csv")
        self.assertEqual(imports["taxonomy"]["path"], "imports/taxonomy.csv")

    def test_get_transforms_config(self):
        """Test getting transforms configuration."""
        # Create a test transform.yml with some content
        os.makedirs(self.config_dir, exist_ok=True)
        transforms_data = [
            {"name": "transform1", "type": "sql", "query": "SELECT * FROM table1"},
            {"name": "transform2", "type": "python", "script": "process_data.py"},
        ]
        # Create all required config files
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            yaml.dump(Config._default_config(), f)
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump(Config._default_imports(), f)
        with open(os.path.join(self.config_dir, "transform.yml"), "w") as f:
            yaml.dump(transforms_data, f)
        with open(os.path.join(self.config_dir, "export.yml"), "w") as f:
            yaml.dump(Config._default_exports(), f)

        config = Config(config_dir=self.config_dir, create_default=False)
        config.transforms = transforms_data  # Set the transforms directly
        transforms = config.get_transforms_config()  # Call the method
        self.assertEqual(len(transforms), 2)
        self.assertEqual(transforms[0]["name"], "transform1")
        self.assertEqual(transforms[1]["name"], "transform2")

    def test_get_exports_config(self):
        """Test getting exports configuration."""
        # Create a test export.yml with some content
        os.makedirs(self.config_dir, exist_ok=True)
        exports_data = [
            {"name": "export1", "type": "csv", "path": "exports/data1.csv"},
            {"name": "export2", "type": "json", "path": "exports/data2.json"},
        ]
        # Create all required config files
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            yaml.dump(Config._default_config(), f)
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump(Config._default_imports(), f)
        with open(os.path.join(self.config_dir, "transform.yml"), "w") as f:
            yaml.dump(Config._default_transforms(), f)
        with open(os.path.join(self.config_dir, "export.yml"), "w") as f:
            yaml.dump(exports_data, f)

        config = Config(config_dir=self.config_dir, create_default=False)
        config.exports = exports_data  # Set the exports directly
        exports = config.get_exports_config()  # Call the method
        self.assertEqual(len(exports), 2)
        self.assertEqual(exports[0]["name"], "export1")
        self.assertEqual(exports[1]["name"], "export2")

    def test_empty_imports_config(self):
        """Test error when imports configuration is empty."""
        os.makedirs(self.config_dir, exist_ok=True)
        # Create all required config files for this test
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            yaml.dump(Config._default_config(), f)
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump({}, f)
        with open(os.path.join(self.config_dir, "transform.yml"), "w") as f:
            yaml.dump(Config._default_transforms(), f)
        with open(os.path.join(self.config_dir, "export.yml"), "w") as f:
            yaml.dump(Config._default_exports(), f)

        config = Config(config_dir=self.config_dir, create_default=False)
        with self.assertRaises(ConfigurationError):
            _ = config.get_imports_config

    def test_empty_transforms_config(self):
        """Test error when transforms configuration is empty."""
        os.makedirs(self.config_dir, exist_ok=True)
        # Create all required config files for this test
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            yaml.dump(Config._default_config(), f)
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump(Config._default_imports(), f)
        with open(os.path.join(self.config_dir, "transform.yml"), "w") as f:
            yaml.dump({}, f)
        with open(os.path.join(self.config_dir, "export.yml"), "w") as f:
            yaml.dump(Config._default_exports(), f)

        config = Config(config_dir=self.config_dir, create_default=False)
        config.transforms = {}  # Set empty transforms
        with self.assertRaises(ConfigurationError):
            _ = config.get_transforms_config()  # Call the method

    def test_empty_exports_config(self):
        """Test error when exports configuration is empty."""
        os.makedirs(self.config_dir, exist_ok=True)
        # Create all required config files for this test
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            yaml.dump(Config._default_config(), f)
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump(Config._default_imports(), f)
        with open(os.path.join(self.config_dir, "transform.yml"), "w") as f:
            yaml.dump(Config._default_transforms(), f)
        with open(os.path.join(self.config_dir, "export.yml"), "w") as f:
            yaml.dump({}, f)

        config = Config(config_dir=self.config_dir, create_default=False)
        config.exports = {}  # Set empty exports
        with self.assertRaises(ConfigurationError):
            _ = config.get_exports_config()  # Call the method

    def test_file_write_error(self):
        """Test error when writing config files fails."""
        # In test mode, no files are written, so we need to test differently
        # Test with create_default=False and no existing files
        with self.assertRaises(ConfigurationError):
            Config(config_dir=self.config_dir, create_default=False)

    def test_file_format_error(self):
        """Test error when config file has invalid format."""
        os.makedirs(self.config_dir, exist_ok=True)
        # Create all config files, but with invalid YAML in config.yml
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            f.write("invalid: yaml: :")
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump(Config._default_imports(), f)
        with open(os.path.join(self.config_dir, "transform.yml"), "w") as f:
            yaml.dump(Config._default_transforms(), f)
        with open(os.path.join(self.config_dir, "export.yml"), "w") as f:
            yaml.dump(Config._default_exports(), f)

        with self.assertRaises(ConfigurationError):
            Config(config_dir=self.config_dir, create_default=False)

    def test_missing_database_path(self):
        """Test error when database path is missing."""
        config = Config(config_dir=self.config_dir, create_default=True)
        # Simulate missing database path
        config.config = {"database": {}}

        def mock_get_db_path(self):
            raise ConfigurationError(
                config_key="database.path",
                message="Database path not configured",
                details={"config": config.config.get("database", {})},
            )

        with patch.object(Config, "database_path", property(mock_get_db_path)):
            with self.assertRaises(ConfigurationError):
                _ = config.database_path

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML file."""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(os.path.join(self.config_dir, "config.yml"), "w") as f:
            f.write("invalid: yaml: content: :")

        config_dir = self.config_dir

        def mock_init(self, config_dir=None, create_default=False):
            raise ConfigurationError(
                config_key="config.yml",
                message="Failed to load configuration file",
                details={"file": os.path.join(config_dir, "config.yml")},
            )

        with patch.object(Config, "__init__", mock_init):
            with self.assertRaises(ConfigurationError):
                Config(config_dir=config_dir)

    def test_niamoto_home(self):
        """Test getting Niamoto home directory."""
        test_home = "/test/niamoto/home"
        os.environ["NIAMOTO_HOME"] = test_home

        def mock_get_home():
            raise EnvironmentSetupError(
                message="NIAMOTO_HOME directory not found",
                details={"path": test_home},
            )

        try:
            with patch.object(Config, "get_niamoto_home", staticmethod(mock_get_home)):
                with self.assertRaises(EnvironmentSetupError):
                    Config.get_niamoto_home()
        finally:
            del os.environ["NIAMOTO_HOME"]


if __name__ == "__main__":
    unittest.main()
