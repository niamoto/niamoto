"""
Sample tests for specific plugins.

This module contains tests for a representative sample of plugins from each category.
These tests verify that the plugins can be instantiated and their core methods work.
"""

import unittest
import pandas as pd
from unittest.mock import MagicMock, patch


# Sample data for testing
SAMPLE_DF = pd.DataFrame(
    {"id": [1, 2, 3], "name": ["A", "B", "C"], "value": [10, 20, 30]}
)

SAMPLE_CONFIG = {"plugin": "test_plugin", "params": {}}


class TestSampleTransformers(unittest.TestCase):
    """Tests for a sample of transformer plugins."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MagicMock()

    def test_direct_attribute_transformer(self):
        """Test the direct_attribute transformer plugin."""
        try:
            # Import the plugin
            from niamoto.core.plugins.transformers.extraction.direct_attribute import (
                DirectAttributeTransformer,
            )

            # Create test config
            config = {"plugin": "direct_attribute", "params": {"attribute": "name"}}

            # Create plugin instance
            transformer = DirectAttributeTransformer(self.db)

            # Validate config
            transformer.validate_config(config)

            # Transform data
            result = transformer.transform(SAMPLE_DF, config)

            # Verify result
            self.assertIsInstance(result, dict)
            self.assertIn("data", result)
            self.assertEqual(list(result["data"]), ["A", "B", "C"])

        except ImportError:
            self.skipTest("direct_attribute transformer not available")

    def test_field_aggregator_transformer(self):
        """Test the field_aggregator transformer plugin."""
        try:
            # Import the plugin
            from niamoto.core.plugins.transformers.aggregation.field_aggregator import (
                FieldAggregatorTransformer,
            )

            # Create test config
            config = {
                "plugin": "field_aggregator",
                "params": {"group_by": "name", "aggregate": {"value": "sum"}},
            }

            # Create plugin instance
            transformer = FieldAggregatorTransformer(self.db)

            # Validate config
            transformer.validate_config(config)

            # Transform data
            result = transformer.transform(SAMPLE_DF, config)

            # Verify result
            self.assertIsInstance(result, dict)
            self.assertIn("data", result)

        except ImportError:
            self.skipTest("field_aggregator transformer not available")


class TestSampleExporters(unittest.TestCase):
    """Tests for a sample of exporter plugins."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MagicMock()

    def test_html_exporter(self):
        """Test the HTML exporter plugin."""
        try:
            # Import the plugin
            from niamoto.core.plugins.exporters.html import HtmlExporter

            # Create test config
            config = {
                "plugin": "html",
                "params": {"title": "Test Export", "template": "default"},
            }

            # Create test data
            data = {"table": SAMPLE_DF.to_dict("records")}

            # Create plugin instance
            exporter = HtmlExporter(self.db)

            # Validate config
            exporter.validate_config(config)

            # Export data
            with patch("builtins.open", MagicMock()):
                result = exporter.export(data, config)

            # Verify result
            self.assertIsInstance(result, str)

        except ImportError:
            self.skipTest("html exporter not available")


class TestSampleLoaders(unittest.TestCase):
    """Tests for a sample of loader plugins."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MagicMock()

    def test_join_table_loader(self):
        """Test the join_table loader plugin."""
        try:
            from niamoto.core.plugins.loaders.join_table import JoinTableLoader
            from niamoto.common.exceptions import DatabaseQueryError

            config = {
                "plugin": "join_table",
                "data": "test_table",
                "key": "id",
                "join_table": "test_join_table",
                "keys": {"source": "id_source", "reference": "id_reference"},
            }

            mock_result = pd.DataFrame({"id": [1, 2, 3], "extra_data": ["X", "Y", "Z"]})

            self.db.has_table = MagicMock(return_value=True)
            self.db.get_table_columns = MagicMock(
                side_effect=lambda name: ["id", "value"]
            )
            self.db.engine = MagicMock()
            mock_connection = MagicMock()
            self.db.engine.connect.return_value.__enter__.return_value = mock_connection

            with (
                patch(
                    "niamoto.core.plugins.loaders.join_table.EntityRegistry"
                ) as registry_cls,
                patch("pandas.read_sql", return_value=mock_result) as mock_read_sql,
            ):
                registry_cls.return_value.get.side_effect = DatabaseQueryError(
                    query="registry_lookup", message="missing"
                )

                loader = JoinTableLoader(self.db)
                loader.validate_config(config)
                result = loader.load_data(1, config)

            self.assertIsInstance(result, pd.DataFrame)
            mock_read_sql.assert_called_once()

        except ImportError:
            self.skipTest("join_table loader not available")

    def test_spatial_loader(self):
        """Test the spatial loader plugin."""
        try:
            # Import the plugin
            from niamoto.core.plugins.loaders.spatial import SpatialLoader

            # Create test config
            config = {
                "plugin": "spatial",
                "key": "id",
                "geometry_field": "geom",
                "reference": {"name": "test_shapes"},
                "main": "test_points",
            }

            # Mock database query result
            mock_result = pd.DataFrame(
                {"id": [1, 2, 3], "geom": ["POINT(0 0)", "POINT(1 1)", "POINT(2 2)"]}
            )

            # Mock execute method to return a scalar
            self.db.execute = MagicMock()
            mock_scalar = MagicMock()
            mock_scalar.scalar.return_value = "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"
            self.db.execute.return_value = mock_scalar

            # Create plugin instance
            loader = SpatialLoader(self.db)

            # Validate config
            loader.validate_config(config)

            # Mock pd.read_sql to avoid text() issue with mock engine
            with patch("pandas.read_sql", return_value=mock_result) as mock_read_sql:
                # Load data
                result = loader.load_data(1, config)

                # Verify pd.read_sql was called
                mock_read_sql.assert_called_once()

            # Verify result
            self.assertIsInstance(result, pd.DataFrame)

        except ImportError:
            self.skipTest("spatial loader not available")


# Add more test classes for other plugin samples as needed


if __name__ == "__main__":
    unittest.main()
