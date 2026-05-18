"""
Sample tests for specific plugins.

This module contains tests for a representative sample of plugins from each category.
These tests verify that the plugins can be instantiated and their core methods work.
"""

import unittest
import pandas as pd
import tempfile
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
        from niamoto.core.plugins.transformers.extraction.direct_attribute import (
            DirectAttribute,
        )

        config = {
            "plugin": "direct_attribute",
            "params": {"field": "name"},
            "group_id": 1,
        }

        transformer = DirectAttribute(self.db)
        transformer.validate_config(config)

        result = transformer.transform(SAMPLE_DF, config)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["value"], "A")

    def test_field_aggregator_transformer(self):
        """Test the field_aggregator transformer plugin."""
        from niamoto.core.plugins.transformers.aggregation.field_aggregator import (
            FieldAggregator,
        )

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "field": "value",
                        "target": "total_value",
                        "transformation": "sum",
                    }
                ]
            },
        }

        transformer = FieldAggregator(self.db)
        transformer.validate_config(config)

        result = transformer.transform(SAMPLE_DF, config)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["total_value"]["value"], 60)


class TestSampleExporters(unittest.TestCase):
    """Tests for a sample of exporter plugins."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MagicMock()

    def test_json_api_exporter(self):
        """Test the JSON API exporter plugin."""
        from niamoto.core.plugins.exporters.json_api_exporter import JsonApiExporter
        from niamoto.core.plugins.models import TargetConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TargetConfig(
                name="test_api",
                exporter="json_api_exporter",
                params={
                    "output_dir": tmpdir,
                    "detail_output_pattern": "{group_by}/{id}.json",
                },
                groups=[],
            )

            exporter = JsonApiExporter(self.db)
            exporter.export(config, self.db)

        self.assertGreaterEqual(exporter.stats["total_files_generated"], 1)


class TestSampleLoaders(unittest.TestCase):
    """Tests for a sample of loader plugins."""

    def setUp(self):
        """Set up test fixtures."""
        self.db = MagicMock()

    def test_join_table_loader(self):
        """Test the join_table loader plugin."""
        from niamoto.common.exceptions import DatabaseQueryError
        from niamoto.core.plugins.loaders.join_table import JoinTableLoader

        config = {
            "plugin": "join_table",
            "data": "test_table",
            "key": "id",
            "join_table": "test_join_table",
            "keys": {"source": "id_source", "reference": "id_reference"},
        }

        mock_result = pd.DataFrame({"id": [1, 2, 3], "extra_data": ["X", "Y", "Z"]})

        self.db.has_table = MagicMock(return_value=True)
        self.db.get_table_columns = MagicMock(side_effect=lambda name: ["id", "value"])
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

    def test_spatial_loader(self):
        """Test the spatial loader plugin."""
        from niamoto.core.plugins.loaders.spatial import SpatialLoader

        config = {
            "plugin": "spatial",
            "key": "id",
            "geometry_field": "geom",
            "reference": {"name": "test_shapes"},
            "main": "test_points",
        }
        mock_result = pd.DataFrame(
            {"id": [1, 2, 3], "geom": ["POINT(0 0)", "POINT(1 1)", "POINT(2 2)"]}
        )

        self.db.execute = MagicMock()
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"
        self.db.execute.return_value = mock_scalar

        loader = SpatialLoader(self.db)
        loader.validate_config(config)

        with patch("pandas.read_sql", return_value=mock_result) as mock_read_sql:
            result = loader.load_data(1, config)
            mock_read_sql.assert_called_once()

        self.assertIsInstance(result, pd.DataFrame)


# Add more test classes for other plugin samples as needed


if __name__ == "__main__":
    unittest.main()
