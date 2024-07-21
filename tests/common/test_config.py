import os
import tempfile
import unittest
from unittest.mock import patch, mock_open, Mock
import yaml
from niamoto.common.config import Config


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_niamoto_home = os.environ.get('NIAMOTO_HOME')
        os.environ['NIAMOTO_HOME'] = self.test_dir

    def tearDown(self):
        if self.old_niamoto_home:
            os.environ['NIAMOTO_HOME'] = self.old_niamoto_home
        else:
            os.environ.pop('NIAMOTO_HOME', None)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_init_with_default_config(self):
        config = Config()
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "config.yml")))
        self.assertEqual(config.database_path, "data/db/niamoto.db")

    def test_init_with_custom_config_path(self):
        custom_path = os.path.join(self.test_dir, "custom_config.yml")
        config = Config(config_path=custom_path, create_default=True)
        self.assertTrue(os.path.exists(custom_path))

    def test_get_section(self):
        config = Config()
        sources = config.get_section("sources")
        self.assertIsInstance(sources, dict)
        self.assertIn("taxonomy", sources)

    def test_get(self):
        config = Config()
        taxonomy_path = config.get("sources", "taxonomy")
        self.assertEqual(taxonomy_path["path"], "data/sources/taxonomy.csv")

    def test_set_and_save(self):
        config = Config()
        new_path = "/new/path/to/db"
        config.set("database", "path", new_path)
        config.save()

        # Recharger la configuration pour vérifier que les changements ont été sauvegardés
        new_config = Config()
        self.assertEqual(new_config.database_path, new_path)

    def test_validate_config(self):
        config = Config()
        validated_config = config.validate_config()
        self.assertIsNotNone(validated_config)

    def test_validate_config_with_missing_section(self):
        # Create an invalid configuration
        invalid_config = {
            "logs": {"path": "logs"},
            "sources": {
                "taxonomy": {"path": "data/sources/taxonomy.csv"},
                "plots": {"path": "data/sources/plots.gpkg"},
                "occurrences": {"path": "data/sources/occurrences.csv"},
                "occurrence-plots": {"path": "data/sources/occurrence-plots.csv"},
                "shapes": {"path": "data/sources/shapes.csv"},
                "rasters": {"path": "data/sources/rasters"}
            },
            "outputs": {"static_site": "outputs", "static_api": "outputs/api"},
            "aggregations": []
        }

        # Create a mock Config instance with the invalid configuration
        mock_config = Mock(spec=Config)
        mock_config.config = invalid_config
        mock_config.config_path = os.path.join(self.test_dir, "config.yml")

        # Call the validate_config method
        with self.assertRaises(ValueError) as context:
            Config.validate_config(mock_config)

        # Verify that the expected exception was raised
        self.assertIn("Missing section: database", str(context.exception))

    def test_get_niamoto_home(self):
        # Test with NIAMOTO_HOME environment variable
        self.assertEqual(Config.get_niamoto_home(), self.test_dir)

        # Test without NIAMOTO_HOME environment variable
        old_home = os.environ.pop('NIAMOTO_HOME', None)
        try:
            self.assertEqual(Config.get_niamoto_home(), os.getcwd())
        finally:
            if old_home:
                os.environ['NIAMOTO_HOME'] = old_home

    def test_config_initialization(self):
        # Test with default configuration file creation
        config = Config(create_default=True)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "config.yml")))

        # Test without default configuration file creation
        os.remove(os.path.join(self.test_dir, "config.yml"))
        with self.assertRaises(FileNotFoundError):
            Config(create_default=False)

    def test_data_sources_property(self):
        config = Config()
        sources = config.data_sources
        self.assertIn("taxonomy", sources)
        self.assertIn("plots", sources)

    def test_output_paths_property(self):
        config = Config()
        outputs = config.output_paths
        self.assertIn("static_site", outputs)
        self.assertIn("static_api", outputs)

    def test_create_config_file(self):
        custom_config = {
            "test": {
                "key": "value"
            }
        }
        config = Config()
        config.create_config_file(custom_config)

        with open(config.config_path, 'r') as f:
            loaded_config = yaml.safe_load(f)

        self.assertEqual(loaded_config, custom_config)


if __name__ == '__main__':
    unittest.main()