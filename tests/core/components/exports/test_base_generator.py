"""
Tests for the BaseGenerator class.
"""

from unittest.mock import MagicMock, PropertyMock

from shapely.geometry import Point, mapping

from niamoto.core.components.exports.base_generator import BaseGenerator
from niamoto.core.models import TaxonRef, PlotRef, ShapeRef
from niamoto.common.exceptions import DataValidationError, GenerationError
from tests.common.base_test import NiamotoTestCase


class TestBaseGenerator(NiamotoTestCase):
    """Test case for the BaseGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.generator = BaseGenerator()

    def test_parse_json_field_valid_json(self):
        """Test parse_json_field with valid JSON."""
        # Test with valid JSON string
        json_str = '{"key": "value", "nested": {"key2": 123}}'
        result = self.generator.parse_json_field(json_str)

        self.assertEqual(result, {"key": "value", "nested": {"key2": 123}})

        # Test with non-string input (should return as is)
        dict_input = {"already": "a dict"}
        result = self.generator.parse_json_field(dict_input)

        self.assertEqual(result, dict_input)
        self.assertIs(result, dict_input)  # Should be the same object

    def test_parse_json_field_invalid_json(self):
        """Test parse_json_field with invalid JSON."""
        invalid_json = '{"key": "value", "missing": }'

        with self.assertRaises(DataValidationError):
            self.generator.parse_json_field(invalid_json)

    def test_taxon_to_dict_basic(self):
        """Test taxon_to_dict with basic taxon."""
        # Create a mock taxon
        mock_taxon = MagicMock(spec=TaxonRef)
        mock_taxon.id = 1
        mock_taxon.full_name = "Taxon name"
        mock_taxon.authors = "Author name"
        mock_taxon.rank_name = "species"
        mock_taxon.extra_data = None
        mock_taxon.lft = 1
        mock_taxon.rght = 2
        mock_taxon.level = 1
        mock_taxon.parent_id = None

        # Convert to dict
        result = self.generator.taxon_to_dict(mock_taxon, None)

        # Check result
        expected = {
            "id": 1,
            "full_name": "Taxon name",
            "authors": "Author name",
            "rank_name": "species",
            "metadata": {},
            "lft": 1,
            "rght": 2,
            "level": 1,
            "parent_id": None,
        }
        self.assertEqual(result, expected)

    def test_taxon_to_dict_with_extra_data(self):
        """Test taxon_to_dict with extra data."""
        # Create a mock taxon with extra data
        mock_taxon = MagicMock(spec=TaxonRef)
        mock_taxon.id = 1
        mock_taxon.full_name = "Taxon name"
        mock_taxon.authors = "Author name"
        mock_taxon.rank_name = "species"
        mock_taxon.extra_data = {"key": "value"}
        mock_taxon.lft = 1
        mock_taxon.rght = 2
        mock_taxon.level = 1
        mock_taxon.parent_id = None

        # Convert to dict
        result = self.generator.taxon_to_dict(mock_taxon, None)

        # Check result
        expected = {
            "id": 1,
            "full_name": "Taxon name",
            "authors": "Author name",
            "rank_name": "species",
            "metadata": {"key": "value"},
            "lft": 1,
            "rght": 2,
            "level": 1,
            "parent_id": None,
        }
        self.assertEqual(result, expected)

    def test_taxon_to_dict_with_stats(self):
        """Test taxon_to_dict with stats."""
        # Create a mock taxon
        mock_taxon = MagicMock(spec=TaxonRef)
        mock_taxon.id = 1
        mock_taxon.full_name = "Taxon name"
        mock_taxon.authors = "Author name"
        mock_taxon.rank_name = "species"
        mock_taxon.extra_data = None
        mock_taxon.lft = 1
        mock_taxon.rght = 2
        mock_taxon.level = 1
        mock_taxon.parent_id = None

        # Create stats with JSON string
        stats = {
            "count": 10,
            "metadata": '{"key": "value"}',
            "invalid_json": "{invalid",
        }

        # Convert to dict
        result = self.generator.taxon_to_dict(mock_taxon, stats)

        # Check result
        expected = {
            "id": 1,
            "full_name": "Taxon name",
            "authors": "Author name",
            "rank_name": "species",
            "lft": 1,
            "rght": 2,
            "level": 1,
            "parent_id": None,
            "count": 10,
            "metadata": {"key": "value"},
            "invalid_json": "{invalid",  # Should keep as is when JSON parsing fails
        }
        self.assertEqual(result, expected)

    def test_taxon_to_dict_exception(self):
        """Test taxon_to_dict with exception."""
        # Create a mock taxon that raises an exception when accessing full_name
        mock_taxon = MagicMock(spec=TaxonRef)
        mock_taxon.id = 1

        # Configure the full_name attribute to raise an exception when accessed
        type(mock_taxon).full_name = PropertyMock(
            side_effect=Exception("Test exception")
        )

        # Should raise GenerationError
        with self.assertRaises(GenerationError):
            self.generator.taxon_to_dict(mock_taxon, None)

    def test_plot_to_dict_basic(self):
        """Test plot_to_dict with basic plot."""
        # Create a mock plot without geometry
        mock_plot = MagicMock(spec=PlotRef)
        mock_plot.id = 1
        mock_plot.locality = "Test locality"
        mock_plot.geometry = None

        # Convert to dict
        result = self.generator.plot_to_dict(mock_plot, None)

        # Check result
        expected = {"id": 1, "locality": "Test locality", "geometry": None}
        self.assertEqual(result, expected)

    def test_plot_to_dict_with_geometry(self):
        """Test plot_to_dict with geometry."""
        # Create a mock plot with geometry
        mock_plot = MagicMock(spec=PlotRef)
        mock_plot.id = 1
        mock_plot.locality = "Test locality"

        # Create a point geometry
        point = Point(1, 2)
        mock_plot.geometry = point.wkt

        # Convert to dict
        result = self.generator.plot_to_dict(mock_plot, None)

        # Check result
        expected = {"id": 1, "locality": "Test locality", "geometry": mapping(point)}
        self.assertEqual(result, expected)

    def test_plot_to_dict_with_invalid_geometry(self):
        """Test plot_to_dict with invalid geometry."""
        # Create a mock plot with invalid geometry
        mock_plot = MagicMock(spec=PlotRef)
        mock_plot.id = 1
        mock_plot.locality = "Test locality"
        mock_plot.geometry = "INVALID WKT"

        # Should raise DataValidationError
        with self.assertRaises(DataValidationError):
            self.generator.plot_to_dict(mock_plot, None)

    def test_plot_to_dict_with_stats(self):
        """Test plot_to_dict with stats."""
        # Create a mock plot
        mock_plot = MagicMock(spec=PlotRef)
        mock_plot.id = 1
        mock_plot.locality = "Test locality"
        mock_plot.geometry = None

        # Create stats with JSON string
        stats = {
            "count": 10,
            "metadata": '{"key": "value"}',
            "invalid_json": "{invalid",
        }

        # Convert to dict
        result = self.generator.plot_to_dict(mock_plot, stats)

        # Check result
        expected = {
            "id": 1,
            "locality": "Test locality",
            "geometry": None,
            "count": 10,
            "metadata": {"key": "value"},
            "invalid_json": "{invalid",  # Should keep as is when JSON parsing fails
        }
        self.assertEqual(result, expected)

    def test_plot_to_dict_exception(self):
        """Test plot_to_dict with exception."""
        # Create a mock plot that raises an exception when accessing locality
        mock_plot = MagicMock(spec=PlotRef)
        mock_plot.id = 1
        mock_plot.geometry = None

        # Configure the locality attribute to raise an exception when accessed
        type(mock_plot).locality = PropertyMock(side_effect=Exception("Test exception"))

        # Should raise GenerationError
        with self.assertRaises(GenerationError):
            self.generator.plot_to_dict(mock_plot, None)

    def test_shape_to_dict_basic(self):
        """Test shape_to_dict with basic shape."""
        # Create a mock shape
        mock_shape = MagicMock(spec=ShapeRef)
        mock_shape.id = 1
        mock_shape.label = "Test shape"
        mock_shape.type = "Test type"

        # Convert to dict
        result = self.generator.shape_to_dict(mock_shape, None)

        # Check result
        expected = {"id": 1, "name": "Test shape", "type": "Test type"}
        self.assertEqual(result, expected)

    def test_shape_to_dict_with_stats(self):
        """Test shape_to_dict with stats."""
        # Create a mock shape
        mock_shape = MagicMock(spec=ShapeRef)
        mock_shape.id = 1
        mock_shape.label = "Test shape"
        mock_shape.type = "Test type"

        # Create stats with JSON string
        stats = {
            "count": 10,
            "metadata": '{"key": "value"}',
            "invalid_json": "{invalid",
        }

        # Convert to dict
        result = self.generator.shape_to_dict(mock_shape, stats)

        # Check result
        expected = {
            "id": 1,
            "name": "Test shape",
            "type": "Test type",
            "count": 10,
            "metadata": {"key": "value"},
            "invalid_json": "{invalid",  # Should keep as is when JSON parsing fails
        }
        self.assertEqual(result, expected)

    def test_shape_to_dict_exception(self):
        """Test shape_to_dict with exception."""
        # Create a mock shape that raises an exception when accessing label
        mock_shape = MagicMock(spec=ShapeRef)
        mock_shape.id = 1

        # Configure the label attribute to raise an exception when accessed
        type(mock_shape).label = PropertyMock(side_effect=Exception("Test exception"))

        # Should raise GenerationError
        with self.assertRaises(GenerationError):
            self.generator.shape_to_dict(mock_shape, None)
