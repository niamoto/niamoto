"""
Tests for the ShapeImporter class.
"""

from unittest.mock import patch, MagicMock
import tempfile
import os
from shapely.geometry import Point, LineString, Polygon, MultiPolygon

from niamoto.core.components.imports.shapes import ShapeImporter
from niamoto.common.exceptions import (
    ShapeImportError,
    FileReadError,
    DataValidationError,
    ConfigurationError,
)
from tests.common.base_test import NiamotoTestCase


class TestShapeImporter(NiamotoTestCase):
    """Test case for the ShapeImporter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Use MagicMock directly instead of create_mock to avoid spec_set restrictions
        self.mock_db = MagicMock()
        # Set attributes that are accessed in the code
        self.mock_db.db_path = "mock_db_path"
        self.mock_db.engine = MagicMock()
        self.mock_db.session = MagicMock()
        self.importer = ShapeImporter(self.mock_db)

    def test_init(self):
        """Test initialization of ShapeImporter."""
        self.assertEqual(self.importer.db, self.mock_db)
        self.assertEqual(self.importer.db_path, "mock_db_path")

    @patch("niamoto.core.components.imports.shapes.fiona.open")
    @patch("pathlib.Path.exists")
    def test_import_from_config(self, mock_exists, mock_fiona_open):
        """Test import_from_config method."""
        # Setup mocks
        mock_exists.return_value = True

        # Mock fiona.open context manager
        mock_src = MagicMock()
        mock_src.__enter__.return_value = mock_src
        mock_src.__exit__.return_value = None
        mock_src.crs_wkt = "PROJCS[...]"
        mock_src.__len__.return_value = 3

        # Mock features
        mock_feature1 = {
            "geometry": {"type": "Point", "coordinates": [1, 1]},
            "properties": {"name": "Feature1"},
        }
        mock_feature2 = {
            "geometry": {"type": "Point", "coordinates": [2, 2]},
            "properties": {"name": "Feature2"},
        }
        mock_feature3 = {
            "geometry": {"type": "Point", "coordinates": [3, 3]},
            "properties": {"name": "Feature3"},
        }
        mock_src.__iter__.return_value = [mock_feature1, mock_feature2, mock_feature3]
        mock_fiona_open.return_value = mock_src

        # Use context manager to ensure proper cleanup
        temp_dir = None
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_dir = tmp_dir
                # Mock _process_input_file to avoid file operations
                with patch.object(
                    self.importer, "_process_input_file", return_value="test.shp"
                ):
                    # Mock transformer
                    with patch.object(
                        self.importer, "_setup_transformer"
                    ) as mock_setup_transformer:
                        mock_transformer = MagicMock()
                        mock_setup_transformer.return_value = mock_transformer

                        # Mock _is_valid_feature
                        with patch.object(
                            self.importer, "_is_valid_feature", return_value=True
                        ) as mock_is_valid:
                            # Mock transform_geometry
                            with patch.object(
                                self.importer, "transform_geometry"
                            ) as mock_transform:
                                mock_transform.return_value = Point(1, 1)

                                # Mock _get_feature_label
                                with patch.object(
                                    self.importer,
                                    "_get_feature_label",
                                    return_value="Test Label",
                                ) as mock_get_label:
                                    # Mock _update_or_create_shape
                                    with patch.object(
                                        self.importer,
                                        "_update_or_create_shape",
                                        return_value=True,
                                    ) as mock_update:
                                        config = [
                                            {
                                                "category": "test",
                                                "label": "Test Shape",
                                                "path": "test.shp",
                                                "name_field": "name",
                                            }
                                        ]

                                        result = self.importer.import_from_config(
                                            config
                                        )

                                        # Verify the result
                                        self.assertEqual(
                                            result,
                                            "Shape import to mock_db_path completed: 3 processed, 3 added, 0 updated",
                                        )

                                        # Verify mock calls
                                        mock_fiona_open.assert_called_with(
                                            "test.shp", "r"
                                        )
                                        mock_setup_transformer.assert_called_once()
                                        self.assertEqual(mock_is_valid.call_count, 3)
                                        self.assertEqual(mock_transform.call_count, 3)
                                        self.assertEqual(mock_get_label.call_count, 3)
                                        self.assertEqual(mock_update.call_count, 3)
                                        self.mock_db.session.commit.assert_called_once()
        finally:
            # Ensure cleanup of any remaining temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    def test_validate_config_empty(self):
        """Test _validate_config method with empty config."""
        with self.assertRaises(ConfigurationError):
            ShapeImporter._validate_config([])

    def test_validate_config_missing_fields(self):
        """Test _validate_config method with missing fields."""
        # Missing name_field
        invalid_config = [
            {"category": "test", "label": "Test Shape", "path": "test.shp"}
        ]

        with self.assertRaises(ConfigurationError):
            ShapeImporter._validate_config(invalid_config)

    def test_validate_config_empty_category(self):
        """Test _validate_config method with empty category."""
        invalid_config = [
            {
                "category": "",
                "label": "Test Shape",
                "path": "test.shp",
                "name_field": "name",
            }
        ]

        with self.assertRaises(ConfigurationError):
            ShapeImporter._validate_config(invalid_config)

    def test_validate_config_valid(self):
        """Test _validate_config method with valid config."""
        valid_config = [
            {
                "category": "test",
                "label": "Test Shape",
                "path": "test.shp",
                "name_field": "name",
            }
        ]

        # Should not raise any exception
        ShapeImporter._validate_config(valid_config)

    @patch("fiona.open")
    @patch("pathlib.Path.exists")
    def test_process_shape_file_file_not_found(self, mock_exists, mock_fiona_open):
        """Test _process_shape_file method with file not found."""
        mock_exists.return_value = False

        shape_info = {
            "category": "test",
            "label": "Test Shape",
            "path": "nonexistent.shp",
            "name_field": "name",
        }
        import_stats = {
            "processed": 0,
            "skipped": 0,
            "updated": 0,
            "added": 0,
            "errors": [],
        }

        with self.assertRaises(FileReadError):
            self.importer._process_shape_file(shape_info, import_stats)

        mock_fiona_open.assert_not_called()

    @patch("fiona.open")
    @patch("pathlib.Path.exists")
    def test_process_shape_file_invalid_crs(self, mock_exists, mock_fiona_open):
        """Test _process_shape_file method with invalid CRS."""
        mock_exists.return_value = True

        # Mock fiona.open context manager
        mock_src = MagicMock()
        mock_src.__enter__.return_value = mock_src
        mock_src.__exit__.return_value = None
        mock_src.crs_wkt = None  # Invalid CRS
        mock_fiona_open.return_value = mock_src

        shape_info = {
            "category": "test",
            "label": "Test Shape",
            "path": "test.shp",
            "name_field": "name",
        }
        import_stats = {
            "processed": 0,
            "skipped": 0,
            "updated": 0,
            "added": 0,
            "errors": [],
        }

        with self.assertRaises(DataValidationError):
            self.importer._process_shape_file(shape_info, import_stats)

    @patch("fiona.open")
    @patch("pathlib.Path.exists")
    def test_process_shape_file_fiona_error(self, mock_exists, mock_fiona_open):
        """Test _process_shape_file method with Fiona error."""
        mock_exists.return_value = True

        # Mock fiona.open to raise an error
        mock_fiona_open.side_effect = Exception("Fiona error")

        shape_info = {
            "category": "test",
            "label": "Test Shape",
            "path": "test.shp",
            "name_field": "name",
        }
        import_stats = {
            "processed": 0,
            "skipped": 0,
            "updated": 0,
            "added": 0,
            "errors": [],
        }

        with self.assertRaises(ShapeImportError):
            self.importer._process_shape_file(shape_info, import_stats)

    def test_setup_transformer_valid(self):
        """Test _setup_transformer method with valid CRS."""
        with patch("pyproj.CRS.from_string") as mock_from_string:
            with patch("pyproj.CRS.from_epsg") as mock_from_epsg:
                with patch("pyproj.Transformer.from_crs") as mock_from_crs:
                    mock_transformer = MagicMock()
                    mock_from_crs.return_value = mock_transformer

                    result = ShapeImporter._setup_transformer("PROJCS[...]")

                    self.assertEqual(result, mock_transformer)
                    mock_from_string.assert_called_once_with("PROJCS[...]")
                    mock_from_epsg.assert_called_once_with(4326)
                    mock_from_crs.assert_called_once()

    def test_setup_transformer_invalid(self):
        """Test _setup_transformer method with invalid CRS."""
        with patch("pyproj.CRS.from_string") as mock_from_string:
            mock_from_string.side_effect = Exception("Invalid CRS")

            with self.assertRaises(DataValidationError):
                ShapeImporter._setup_transformer("INVALID")

    def test_is_valid_feature_valid(self):
        """Test _is_valid_feature method with valid feature."""
        valid_feature = {
            "geometry": {"type": "Point", "coordinates": [1, 1]},
            "properties": {"name": "Test"},
        }

        # We need to use the correct import path for the shape function
        with patch("niamoto.core.components.imports.shapes.shape") as mock_shape:
            mock_geom = MagicMock()
            mock_geom.is_empty = False
            mock_shape.return_value = mock_geom

            result = ShapeImporter._is_valid_feature(valid_feature)

            self.assertTrue(result)
            mock_shape.assert_called_once_with(valid_feature["geometry"])

    def test_is_valid_feature_invalid(self):
        """Test _is_valid_feature method with invalid feature."""
        # Missing geometry
        invalid_feature1 = {"properties": {"name": "Test"}}

        # Missing properties
        invalid_feature2 = {"geometry": {"type": "Point", "coordinates": [1, 1]}}

        # Empty geometry
        invalid_feature3 = {
            "geometry": {"type": "Point", "coordinates": [1, 1]},
            "properties": {"name": "Test"},
        }

        # We need to use the correct import path for the shape function
        with patch("niamoto.core.components.imports.shapes.shape") as mock_shape:
            mock_geom = MagicMock()
            mock_geom.is_empty = True
            mock_shape.return_value = mock_geom

            # Test missing geometry
            result1 = ShapeImporter._is_valid_feature(invalid_feature1)
            self.assertFalse(result1)

            # Test missing properties
            result2 = ShapeImporter._is_valid_feature(invalid_feature2)
            self.assertFalse(result2)

            # Test empty geometry
            result3 = ShapeImporter._is_valid_feature(invalid_feature3)
            self.assertFalse(result3)
            mock_shape.assert_called_once_with(invalid_feature3["geometry"])

    def test_get_feature_label(self):
        """Test _get_feature_label method."""
        feature = {"properties": {"name": "Test Feature"}}

        shape_info = {"name_field": "name"}

        result = ShapeImporter._get_feature_label(feature, shape_info)

        self.assertEqual(result, "Test Feature")

    def test_get_feature_label_missing(self):
        """Test _get_feature_label method with missing field."""
        feature = {
            "properties": {"id": 1}  # Missing 'name' field
        }

        shape_info = {"name_field": "name"}

        result = ShapeImporter._get_feature_label(feature, shape_info)

        self.assertEqual(result, "")

    def test_format_result_message(self):
        """Test _format_result_message method."""
        stats = {
            "processed": 10,
            "added": 5,
            "updated": 3,
            "skipped": 2,
            "errors": ["Error 1", "Error 2"],
        }

        result = self.importer._format_result_message(stats)

        self.assertIn("10 processed", result)
        self.assertIn("5 added", result)
        self.assertIn("3 updated", result)

    def test_process_input_file_geojson(self):
        """Test _process_input_file method with GeoJSON file."""
        temp_dir = None
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_dir = tmp_dir
                # Create a temporary GeoJSON file
                geojson_content = '{"type": "FeatureCollection", "features": []}'
                geojson_path = os.path.join(tmp_dir, "test.geojson")

                with open(geojson_path, "w") as f:
                    f.write(geojson_content)

                # Process the file
                result = ShapeImporter._process_input_file(geojson_path, tmp_dir)

                # The function should return the same path for GeoJSON files
                self.assertEqual(result, geojson_path)

                # Check that the content is preserved
                with open(result, "r") as f:
                    content = f.read()
                    self.assertEqual(content, geojson_content)
        finally:
            # Ensure cleanup of any remaining temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    def test_process_input_file_shapefile(self):
        """Test _process_input_file method with Shapefile."""
        temp_dir = None
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_dir = tmp_dir
                # Create a mock shapefile path
                shapefile_path = os.path.join(tmp_dir, "test.shp")

                # For non-GeoJSON files, the original path should be returned
                result = ShapeImporter._process_input_file(shapefile_path, tmp_dir)

                self.assertEqual(result, shapefile_path)
        finally:
            # Ensure cleanup of any remaining temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    def test_process_input_file_error(self):
        """Test _process_input_file method with error."""
        temp_dir = None
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                temp_dir = tmp_dir
                # Create a non-existent file path
                nonexistent_path = os.path.join(tmp_dir, "nonexistent.geojson")

                # Process should raise FileReadError
                with self.assertRaises(FileReadError):
                    ShapeImporter._process_input_file(nonexistent_path, tmp_dir)
        finally:
            # Ensure cleanup of any remaining temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    def test_transform_geometry_point(self):
        """Test transform_geometry method with Point."""
        point = Point(1, 1)
        transformer = MagicMock()

        with patch.object(
            self.importer, "transform_point", return_value=Point(2, 2)
        ) as mock_transform:
            result = self.importer.transform_geometry(point, transformer)

            self.assertEqual(result, Point(2, 2))
            mock_transform.assert_called_once_with(point, transformer)

    def test_transform_geometry_linestring(self):
        """Test transform_geometry method with LineString."""
        linestring = LineString([(1, 1), (2, 2)])
        transformer = MagicMock()

        with patch.object(
            self.importer,
            "transform_linestring",
            return_value=LineString([(2, 2), (3, 3)]),
        ) as mock_transform:
            result = self.importer.transform_geometry(linestring, transformer)

            self.assertEqual(result, LineString([(2, 2), (3, 3)]))
            mock_transform.assert_called_once_with(linestring, transformer)

    def test_transform_geometry_polygon(self):
        """Test transform_geometry method with Polygon."""
        polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        transformer = MagicMock()

        with patch.object(
            self.importer,
            "transform_polygon",
            return_value=Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        ) as mock_transform:
            result = self.importer.transform_geometry(polygon, transformer)

            self.assertIsInstance(result, MultiPolygon)
            mock_transform.assert_called_once_with(polygon, transformer)

    def test_transform_geometry_multipolygon(self):
        """Test transform_geometry method with MultiPolygon."""
        polygon1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        polygon2 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])
        multipolygon = MultiPolygon([polygon1, polygon2])
        transformer = MagicMock()

        with patch.object(self.importer, "transform_polygon") as mock_transform:
            mock_transform.side_effect = [
                Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
                Polygon([(3, 3), (4, 3), (4, 4), (3, 4)]),
            ]

            result = self.importer.transform_geometry(multipolygon, transformer)

            self.assertIsInstance(result, MultiPolygon)
            self.assertEqual(mock_transform.call_count, 2)
