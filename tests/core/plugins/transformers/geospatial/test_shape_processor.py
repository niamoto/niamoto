"""
Unit tests for the shape processor plugin.
"""

import copy
import os
import shutil
import unittest
import yaml
import tempfile
from unittest import mock

import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.wkb import dumps

from niamoto.core.plugins.transformers.geospatial.shape_processor import (
    ShapeProcessor,
)
from niamoto.common.database import Database
from tests.common.base_test import NiamotoTestCase


class TestShapeProcessor(NiamotoTestCase):
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Create config directory in temporary location
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")
        self.test_data_dir = os.path.join(self.temp_dir, "data")
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.test_data_dir, exist_ok=True)

        # Create test layers with more complex geometries
        test_gdf = gpd.GeoDataFrame(
            geometry=[
                Polygon(
                    [
                        (0, 0),
                        (0.25, 0.1),
                        (0.5, 0.15),
                        (0.75, 0.1),
                        (1, 0),
                        (1, 0.25),
                        (0.9, 0.5),
                        (1, 0.75),
                        (1, 1),
                        (0.75, 0.9),
                        (0.5, 0.85),
                        (0.25, 0.9),
                        (0, 1),
                        (0.1, 0.75),
                        (0.15, 0.5),
                        (0.1, 0.25),
                        (0, 0),
                    ]
                ),
                Polygon(
                    [
                        (0.25, 0.25),
                        (0.75, 0.25),
                        (0.75, 0.75),
                        (0.25, 0.75),
                        (0.25, 0.25),
                    ]
                ),
            ],
            crs="EPSG:4326",
        )

        # Create test layer files
        test_layer_path = os.path.join(self.test_data_dir, "test_layer.gpkg")
        test_layer_2_path = os.path.join(self.test_data_dir, "test_layer_2.gpkg")
        test_gdf.to_file(test_layer_path, driver="GPKG")
        test_gdf.to_file(test_layer_2_path, driver="GPKG")

        # Verify that the files were created
        assert os.path.exists(test_layer_path), (
            f"Test layer file not created: {test_layer_path}"
        )
        assert os.path.exists(test_layer_2_path), (
            f"Test layer 2 file not created: {test_layer_2_path}"
        )

        # Create test import.yml with new schema format
        self.import_config = {
            "entities": {"references": {}, "datasets": {}},
            "metadata": {
                "layers": [
                    {
                        "name": "test_layer",
                        "type": "vector",
                        "format": "geopackage",
                        "path": test_layer_path,
                        "description": "Test layer",
                    },
                    {
                        "name": "test_layer_2",
                        "type": "vector",
                        "format": "geopackage",
                        "path": test_layer_2_path,
                        "description": "Test layer 2",
                    },
                ]
            },
        }

        # Write test import.yml
        import_yml_path = os.path.join(self.config_dir, "import.yml")
        with open(import_yml_path, "w") as f:
            yaml.dump(self.import_config, f)

        # Verify that import.yml was created
        assert os.path.exists(import_yml_path), (
            f"Import.yml file not created: {import_yml_path}"
        )

        # Initialize database
        self.db = Database(":memory:")  # Use in-memory SQLite for testing

        # Create test shape with more points for simplification testing
        self.test_polygon = Polygon(
            [
                (0, 0),
                (0.2, 0.1),
                (0.4, 0.15),
                (0.6, 0.2),
                (0.8, 0.1),
                (1, 0),
                (1, 0.2),
                (0.9, 0.4),
                (0.8, 0.6),
                (0.9, 0.8),
                (1, 1),
                (0.8, 1),
                (0.6, 0.9),
                (0.4, 0.85),
                (0.2, 0.9),
                (0, 1),
                (0.1, 0.8),
                (0.15, 0.6),
                (0.1, 0.4),
                (0.05, 0.2),
                (0, 0),
            ]
        )
        self.test_wkb = dumps(self.test_polygon).hex()

        # Create test table and data
        self.db.execute_sql("""
            CREATE TABLE shape_ref (
                id INTEGER PRIMARY KEY,
                location TEXT
            )
        """)
        self.db.execute_sql(
            "INSERT INTO shape_ref (id, location) VALUES (:id, :location)",
            {"id": 1, "location": self.test_wkb},
        )

        # Create test config
        self.test_config = {
            "plugin": "shape_processor",
            "params": {
                "source": "shape_ref",
                "field": "location",
                "format": "topojson",
                "simplify": True,
                "layers": [
                    {"name": "test_layer", "clip": True, "simplify": True},
                    {"name": "test_layer_2", "clip": True, "simplify": True},
                ],
            },
        }

        # Mock the registry to return shape_ref entity
        from types import SimpleNamespace
        from unittest.mock import patch, Mock

        # Create a mock registry BEFORE initializing processor
        mock_registry = Mock()
        mock_registry.get.return_value = SimpleNamespace(
            table_name="shape_ref",
            config={
                "connector": {
                    "type": "duckdb_csv",
                    "path": "test.csv",
                    "identifier": "id",
                }
            },
        )

        # Mock Config to prevent validation errors during processor initialization
        with patch("niamoto.common.config.Config") as mock_config_class:
            mock_cfg = Mock()
            mock_cfg.get_imports_config = Mock()
            mock_cfg.get_imports_config.model_dump.return_value = {}
            mock_config_class.return_value = mock_cfg

            # Initialize processor with registry and config (db, registry, config)
            self.processor = ShapeProcessor(self.db, mock_registry, self.test_config)

        # Override the config_dir to use our test config directory
        self.processor.config_dir = self.temp_dir
        self.processor.project_dir = self.temp_dir
        # Reload the imports config from our test config directory
        import_yml_path = os.path.join(self.config_dir, "import.yml")
        if os.path.exists(import_yml_path):
            with open(import_yml_path, "r") as f:
                self.processor.imports_config = yaml.safe_load(f)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if getattr(self, "db", None):
            try:
                self.db.close_db_session()
            except Exception:
                pass
            if getattr(self.db, "engine", None):
                self.db.engine.dispose()

        # Clean up test files if they exist
        try:
            # Clean up temporary directory (includes config dir)
            if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

        except Exception as e:
            print(f"Error during cleanup: {e}")

        super().tearDown()

    def create_test_files(self):
        """Create test files needed for layer processing."""
        # Create test data directory
        os.makedirs(self.test_data_dir, exist_ok=True)

        # Create test layers with more complex geometries
        test_gdf = gpd.GeoDataFrame(
            geometry=[
                Polygon(
                    [
                        (0, 0),
                        (0.25, 0.1),
                        (0.5, 0.15),
                        (0.75, 0.1),
                        (1, 0),
                        (1, 0.25),
                        (0.9, 0.5),
                        (1, 0.75),
                        (1, 1),
                        (0.75, 0.9),
                        (0.5, 0.85),
                        (0.25, 0.9),
                        (0, 1),
                        (0.1, 0.75),
                        (0.15, 0.5),
                        (0.1, 0.25),
                        (0, 0),
                    ]
                ),
                Polygon(
                    [
                        (0.25, 0.25),
                        (0.75, 0.25),
                        (0.75, 0.75),
                        (0.25, 0.75),
                        (0.25, 0.25),
                    ]
                ),
            ],
            crs="EPSG:4326",
        )
        test_gdf.to_file(
            os.path.join(self.test_data_dir, "test_layer.gpkg"), driver="GPKG"
        )
        test_gdf.to_file(
            os.path.join(self.test_data_dir, "test_layer_2.gpkg"), driver="GPKG"
        )

        # Write test import.yml
        with open(os.path.join(self.config_dir, "import.yml"), "w") as f:
            yaml.dump(self.import_config, f)

    def test_uses_temporary_data_directory(self):
        """Generated layer files should stay out of repository fixtures."""
        repo_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

        self.assertNotEqual(self.test_data_dir, repo_data_dir)
        self.assertTrue(self.test_data_dir.startswith(self.temp_dir))

    def test_validate_config(self):
        """Test configuration validation."""
        # Test valid config
        validated = self.processor.validate_config(self.test_config)
        self.assertEqual(validated.plugin, self.test_config["plugin"])
        self.assertEqual(validated.params.source, self.test_config["params"]["source"])
        self.assertEqual(validated.params.field, self.test_config["params"]["field"])
        self.assertEqual(validated.params.format, self.test_config["params"]["format"])

        # Test invalid config
        with self.assertRaises(ValueError):
            self.processor.validate_config({"invalid": "config"})

    def test_load_shape_geometry(self):
        """Test loading geometry from WKB."""
        gdf = self.processor.load_shape_geometry(self.test_wkb)
        self.assertIsInstance(gdf, gpd.GeoDataFrame)
        self.assertEqual(gdf.crs, "EPSG:4326")
        self.assertEqual(len(gdf), 1)

    def test_relative_layer_paths_resolve_from_project_dir(self):
        """Relative metadata layer paths should not depend on the process cwd."""
        layer_dir = os.path.join(self.temp_dir, "imports")
        os.makedirs(layer_dir, exist_ok=True)
        relative_layer_path = os.path.join(layer_dir, "relative_layer.gpkg")
        gpd.GeoDataFrame(
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])],
            crs="EPSG:4326",
        ).to_file(relative_layer_path, driver="GPKG")

        self.processor.imports_config = {
            "metadata": {
                "layers": [
                    {
                        "name": "relative_layer",
                        "type": "vector",
                        "format": "geopackage",
                        "path": "imports/relative_layer.gpkg",
                    }
                ]
            }
        }
        self.processor.project_dir = self.temp_dir

        previous_cwd = os.getcwd()
        wrong_cwd = tempfile.mkdtemp()
        try:
            os.chdir(wrong_cwd)
            shape_gdf = gpd.GeoDataFrame(
                geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])],
                crs="EPSG:4326",
            )
            result = self.processor._process_layer(
                "relative_layer",
                {"clip": False, "simplify": False},
                shape_gdf,
            )
        finally:
            os.chdir(previous_cwd)
            shutil.rmtree(wrong_cwd, ignore_errors=True)

        self.assertEqual(len(result), 1)

    def test_transform(self):
        """Test complete transformation process."""
        data = pd.DataFrame({"id": [1]})
        result = self.processor.transform(data, self.test_config)

        # Check result structure
        self.assertIn("shape_coords", result)
        self.assertIn("test_layer_coords", result)
        self.assertIn("test_layer_2_coords", result)

        # Check TopoJSON format
        for coords in result.values():
            self.assertIn("type", coords)
            self.assertEqual(coords["type"], "Topology")
            self.assertIn("objects", coords)
            self.assertIn("arcs", coords)

    def test_transform_respects_geojson_format(self):
        """Test GeoJSON output format for shape and layer coordinates."""
        data = pd.DataFrame({"id": [1]})
        config = copy.deepcopy(self.test_config)
        config["params"]["format"] = "geojson"

        result = self.processor.transform(data, config)

        self.assertEqual(
            set(result),
            {"shape_coords", "test_layer_coords", "test_layer_2_coords"},
        )
        for coords in result.values():
            self.assertEqual(coords["type"], "FeatureCollection")
            self.assertIn("features", coords)
            self.assertGreater(len(coords["features"]), 0)

    def test_transform_raises_for_requested_missing_layer(self):
        """Requested layers should fail loudly when they cannot be loaded."""
        data = pd.DataFrame({"id": [1]})
        config = copy.deepcopy(self.test_config)
        config["params"]["layers"] = [
            {"name": "missing_layer", "clip": True, "simplify": True}
        ]

        with self.assertRaisesRegex(ValueError, "missing_layer"):
            self.processor.transform(data, config)

    def test_process_layer(self):
        """Test layer processing."""
        base_gdf = gpd.GeoDataFrame(geometry=[self.test_polygon], crs="EPSG:4326")

        # Test with simple layer config
        layer_gdf = self.processor._process_layer(
            "test_layer", {"clip": True, "simplify": True}, base_gdf
        )
        self.assertIsInstance(layer_gdf, gpd.GeoDataFrame)
        self.assertEqual(layer_gdf.crs, "EPSG:4326")

    def test_simplify_with_utm(self):
        """Test UTM-based geometry simplification."""
        # Test with complex polygon
        simplified = self.processor._simplify_with_utm(self.test_polygon)
        self.assertTrue(simplified.is_valid)
        self.assertLess(
            len(simplified.exterior.coords), len(self.test_polygon.exterior.coords)
        )

        # Test with invalid geometry
        invalid_polygon = Polygon([(0, 0), (1, 1), (1, 0), (0, 0)])
        simplified = self.processor._simplify_with_utm(invalid_polygon)
        self.assertTrue(simplified.is_valid)


def test_shape_processor_teardown_preserves_external_patches():
    """tearDown should not stop patches started outside this test case."""
    patcher = mock.patch(
        "tests.core.plugins.transformers.geospatial.test_shape_processor.yaml.safe_load",
        return_value={},
    )
    patched_safe_load = patcher.start()
    try:
        case = TestShapeProcessor(methodName="runTest")
        case._active_patches = []
        case._had_niamoto_test_mode = False
        case._previous_niamoto_test_mode = None
        case.db = None

        case.tearDown()

        assert yaml.safe_load is patched_safe_load
    finally:
        patcher.stop()


if __name__ == "__main__":
    unittest.main()
