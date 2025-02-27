"""
Unit tests for the shape processor plugin.
"""

import os
import unittest
import yaml

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
        # Create test data directory and files
        self.test_data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "data")
        )
        os.makedirs(self.test_data_dir, exist_ok=True)

        # Create config directory
        self.config_dir = os.path.join(os.getcwd(), "config")
        os.makedirs(self.config_dir, exist_ok=True)

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

        # Create test import.yml
        self.import_config = {
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

        # Initialize processor with config
        self.processor = ShapeProcessor(self.db, self.test_config)

    def tearDown(self):
        """Clean up test fixtures."""
        from unittest import mock

        self.db.close_db_session()

        # Clean up test files if they exist
        try:
            # Remove files in config directory
            if os.path.exists(os.path.join(self.config_dir, "import.yml")):
                os.remove(os.path.join(self.config_dir, "import.yml"))

            # Remove files in test_data_dir
            for file in os.listdir(self.test_data_dir):
                file_path = os.path.join(self.test_data_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

            # Remove directories
            if os.path.exists(self.config_dir):
                os.rmdir(self.config_dir)
            if os.path.exists(self.test_data_dir):
                os.rmdir(self.test_data_dir)
        except Exception as e:
            print(f"Error during cleanup: {e}")

        # Stop all active patches to prevent MagicMock leaks
        mock.patch.stopall()

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

    def test_validate_config(self):
        """Test configuration validation."""
        # Test valid config
        validated = self.processor.validate_config(self.test_config)
        self.assertEqual(validated, self.test_config)

        # Test invalid config
        with self.assertRaises(ValueError):
            self.processor.validate_config({"invalid": "config"})

    def test_load_shape_geometry(self):
        """Test loading geometry from WKB."""
        gdf = self.processor.load_shape_geometry(self.test_wkb)
        self.assertIsInstance(gdf, gpd.GeoDataFrame)
        self.assertEqual(gdf.crs, "EPSG:4326")
        self.assertEqual(len(gdf), 1)

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


if __name__ == "__main__":
    unittest.main()
