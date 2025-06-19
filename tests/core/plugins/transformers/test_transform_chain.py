"""
Tests for the TransformChain plugin.

This module contains comprehensive tests for the transform_chain plugin,
which allows chaining multiple transformations together.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from niamoto.core.plugins.transformers.chains.transform_chain import (
    TransformChain,
    TransformChainConfig,
)
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.common.exceptions import DataTransformError


class TestTransformChain:
    """Test suite for TransformChain plugin."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        return Mock()

    @pytest.fixture
    def transform_chain(self, mock_db):
        """Create a TransformChain instance."""
        return TransformChain(mock_db)

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame(
            {"id": [1, 2, 3], "value": [10, 20, 30], "category": ["A", "B", "A"]}
        )

    @pytest.fixture
    def sample_geodataframe(self):
        """Create a sample GeoDataFrame for testing."""
        return gpd.GeoDataFrame(
            {
                "id": [1, 2, 3],
                "value": [10, 20, 30],
                "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
            }
        )

    def test_initialization(self, transform_chain, mock_db):
        """Test TransformChain initialization."""
        assert transform_chain.db == mock_db
        assert transform_chain.config_model == TransformChainConfig

    def test_validate_config_with_legacy_format(self, transform_chain):
        """Test configuration validation with legacy format (steps at top level)."""
        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "count_transformer",
                    "params": {"field": "id", "distinct": True},
                    "output_key": "count_result",
                }
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            validated = transform_chain.validate_config(config)
            assert validated is not None
            assert len(validated.steps) == 1
            assert validated.steps[0].plugin == "count_transformer"
            assert validated.steps[0].output_key == "count_result"

    def test_validate_config_with_new_format(self, transform_chain):
        """Test configuration validation with new format (steps in params)."""
        config = {
            "plugin": "transform_chain",
            "params": {
                "steps": [
                    {
                        "plugin": "count_transformer",
                        "params": {"field": "id", "distinct": True},
                        "output_key": "count_result",
                    },
                    {
                        "plugin": "statistics_transformer",
                        "params": {"field": "value"},
                        "output_key": "stats_result",
                    },
                ]
            },
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            validated = transform_chain.validate_config(config)
            assert validated is not None
            assert len(validated.steps) == 2
            assert validated.steps[0].plugin == "count_transformer"
            assert validated.steps[1].plugin == "statistics_transformer"

    def test_validate_config_no_steps(self, transform_chain):
        """Test configuration validation with no steps."""
        config = {"plugin": "transform_chain"}

        with pytest.raises(DataTransformError) as exc_info:
            transform_chain.validate_config(config)

        assert "No steps found" in str(exc_info.value)

    def test_validate_config_invalid_plugin(self, transform_chain):
        """Test configuration validation with invalid plugin reference."""
        config = {
            "plugin": "transform_chain",
            "steps": [
                {"plugin": "non_existent_plugin", "params": {}, "output_key": "result"}
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=False):
            with patch.object(
                PluginRegistry,
                "list_plugins",
                return_value={
                    PluginType.TRANSFORMER: [
                        "count_transformer",
                        "statistics_transformer",
                    ]
                },
            ):
                with pytest.raises(DataTransformError) as exc_info:
                    transform_chain.validate_config(config)

                assert "Plugin non_existent_plugin not found" in str(exc_info.value)

    def test_resolve_references_simple(self, transform_chain):
        """Test reference resolution with simple references."""
        params = {"field": "@step1.count", "threshold": 10}
        context = {"step1": {"count": 5, "total": 100}}

        resolved = transform_chain._resolve_references(params, context)
        assert resolved["field"] == 5
        assert resolved["threshold"] == 10

    def test_resolve_references_nested(self, transform_chain):
        """Test reference resolution with nested references."""
        params = {"config": {"field": "@step1.stats.mean", "max": "@step1.stats.max"}}
        context = {"step1": {"stats": {"mean": 25.5, "max": 100, "min": 0}}}

        resolved = transform_chain._resolve_references(params, context)
        assert resolved["config"]["field"] == 25.5
        assert resolved["config"]["max"] == 100

    def test_resolve_references_in_list(self, transform_chain):
        """Test reference resolution within lists."""
        params = {"values": ["@step1.value1", 42, "@step2.value2"]}
        context = {"step1": {"value1": 10}, "step2": {"value2": 20}}

        resolved = transform_chain._resolve_references(params, context)
        assert resolved["values"] == [10, 42, 20]

    def test_resolve_references_missing_reference(self, transform_chain):
        """Test reference resolution with missing reference."""
        params = {"field": "@missing_step.value"}
        context = {"step1": {"value": 10}}

        resolved = transform_chain._resolve_references(params, context)
        # Should keep the reference as-is when not found
        assert resolved["field"] == "@missing_step.value"

    def test_resolve_references_invalid_path(self, transform_chain):
        """Test reference resolution with invalid nested path."""
        params = {"field": "@step1.missing.nested.path"}
        context = {"step1": {"value": 10}}

        resolved = transform_chain._resolve_references(params, context)
        # Should return the top-level value when path is invalid
        assert resolved["field"] == {"value": 10}

    def test_transform_simple_chain(self, transform_chain, sample_dataframe):
        """Test simple transformation chain."""
        # Mock plugin registry and transformers
        mock_count_transformer = Mock()
        mock_count_transformer.transform.return_value = {"count": 3}

        mock_stats_transformer = Mock()
        mock_stats_transformer.transform.return_value = {"mean": 20.0, "sum": 60}

        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "count_transformer",
                    "params": {"field": "id", "distinct": True},
                    "output_key": "count_result",
                },
                {
                    "plugin": "statistics_transformer",
                    "params": {"field": "value"},
                    "output_key": "stats_result",
                },
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(PluginRegistry, "get_plugin") as mock_get_plugin:
                # Configure mock to return different plugins for different calls
                def get_plugin_side_effect(name, plugin_type):
                    if name == "count_transformer":
                        return lambda db: mock_count_transformer
                    elif name == "statistics_transformer":
                        return lambda db: mock_stats_transformer

                mock_get_plugin.side_effect = get_plugin_side_effect

                result = transform_chain.transform(sample_dataframe, config)

                assert "count_result" in result
                assert result["count_result"] == {"count": 3}
                assert "stats_result" in result
                assert result["stats_result"] == {"mean": 20.0, "sum": 60}

                # Verify transformers were called correctly
                mock_count_transformer.transform.assert_called_once()
                mock_stats_transformer.transform.assert_called_once()

    def test_transform_with_references(self, transform_chain, sample_dataframe):
        """Test transformation chain with parameter references."""
        # Mock transformers
        mock_filter_transformer = Mock()
        mock_filter_transformer.transform.return_value = pd.DataFrame(
            {"id": [1, 3], "value": [10, 30], "category": ["A", "A"]}
        )

        mock_count_transformer = Mock()
        mock_count_transformer.transform.return_value = {"count": 2}

        config = {
            "plugin": "transform_chain",
            "params": {
                "steps": [
                    {
                        "plugin": "filter_transformer",
                        "params": {"category": "A"},
                        "output_key": "filtered_data",
                    },
                    {
                        "plugin": "count_transformer",
                        "params": {"data": "@filtered_data"},
                        "output_key": "count_result",
                    },
                ]
            },
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(PluginRegistry, "get_plugin") as mock_get_plugin:

                def get_plugin_side_effect(name, plugin_type):
                    if name == "filter_transformer":
                        return lambda db: mock_filter_transformer
                    elif name == "count_transformer":
                        return lambda db: mock_count_transformer

                mock_get_plugin.side_effect = get_plugin_side_effect

                transform_chain.transform(sample_dataframe, config)

                # Verify count transformer received the filtered data
                count_call_args = mock_count_transformer.transform.call_args[0]
                # The first argument should be the filtered DataFrame
                assert isinstance(count_call_args[0], pd.DataFrame)
                assert len(count_call_args[0]) == 2  # Filtered to 2 rows

    def test_transform_with_geodataframe(self, transform_chain, sample_geodataframe):
        """Test transformation chain with GeoDataFrame handling."""
        # Mock transformers
        mock_vector_overlay = Mock()
        mock_vector_overlay.transform.return_value = {
            "overlays": [{"id": 1, "overlay_count": 2}],
            "_gdf": sample_geodataframe,
        }

        mock_raster_stats = Mock()
        mock_raster_stats.transform.return_value = {"stats": {"mean": 15.5, "max": 30}}

        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "vector_overlay",
                    "params": {"layer": "regions"},
                    "output_key": "overlay_result",
                },
                {
                    "plugin": "raster_stats",
                    "params": {"raster": "elevation.tif"},
                    "output_key": "raster_result",
                },
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(PluginRegistry, "get_plugin") as mock_get_plugin:

                def get_plugin_side_effect(name, plugin_type):
                    if name == "vector_overlay":
                        return lambda db: mock_vector_overlay
                    elif name == "raster_stats":
                        return lambda db: mock_raster_stats

                mock_get_plugin.side_effect = get_plugin_side_effect

                # Remove print statements from the actual implementation during test
                with patch("builtins.print"):
                    transform_chain.transform(sample_geodataframe, config)

                # Verify raster_stats received the GeoDataFrame
                raster_call_args = mock_raster_stats.transform.call_args[0]
                assert isinstance(raster_call_args[0], gpd.GeoDataFrame)

    def test_transform_step_error(self, transform_chain, sample_dataframe):
        """Test error handling in transformation step."""
        # Mock transformer that raises an error
        mock_error_transformer = Mock()
        mock_error_transformer.transform.side_effect = ValueError("Invalid parameter")

        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "error_transformer",
                    "params": {"invalid": "param"},
                    "output_key": "error_result",
                }
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(
                PluginRegistry,
                "get_plugin",
                return_value=lambda db: mock_error_transformer,
            ):
                # Remove print statements from the actual implementation during test
                with patch("builtins.print"):
                    with pytest.raises(DataTransformError) as exc_info:
                        transform_chain.transform(sample_dataframe, config)

                    # The outer exception wraps the inner error
                    assert "Failed to execute transform chain" in str(exc_info.value)
                    # Check the details contain the actual error
                    if hasattr(exc_info.value, "details"):
                        assert "Invalid parameter" in str(
                            exc_info.value.details.get("error", "")
                        )

    def test_transform_with_group_id(self, transform_chain, sample_dataframe):
        """Test that group_id is passed through to each step."""
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"result": "success"}

        config = {
            "plugin": "transform_chain",
            "group_id": 123,
            "steps": [
                {
                    "plugin": "test_transformer",
                    "params": {"param": "value"},
                    "output_key": "test_result",
                }
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(
                PluginRegistry, "get_plugin", return_value=lambda db: mock_transformer
            ):
                transform_chain.transform(sample_dataframe, config)

                # Verify transformer was called with group_id
                call_config = mock_transformer.transform.call_args[0][1]
                assert call_config["group_id"] == 123

    def test_transform_empty_params(self, transform_chain, sample_dataframe):
        """Test transformation with empty parameters."""
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"result": "success"}

        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "test_transformer",
                    "params": {},
                    "output_key": "test_result",
                }
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(
                PluginRegistry, "get_plugin", return_value=lambda db: mock_transformer
            ):
                result = transform_chain.transform(sample_dataframe, config)

                assert "test_result" in result
                assert result["test_result"] == {"result": "success"}

    def test_complex_reference_resolution(self, transform_chain):
        """Test complex reference resolution scenarios."""
        params = {
            "nested": {
                "list": ["@step1.values", "@step2.result"],
                "dict": {"ref": "@step1.metadata.count", "static": 42},
            },
            "simple": "@step3",
        }

        context = {
            "step1": {
                "values": [1, 2, 3],
                "metadata": {"count": 10, "type": "numeric"},
            },
            "step2": {"result": "success"},
            "step3": {"complete": True},
        }

        resolved = transform_chain._resolve_references(params, context)

        assert resolved["nested"]["list"] == [[1, 2, 3], "success"]
        assert resolved["nested"]["dict"]["ref"] == 10
        assert resolved["nested"]["dict"]["static"] == 42
        assert resolved["simple"] == {"complete": True}

    @pytest.mark.integration
    def test_real_plugin_integration(self, transform_chain, sample_dataframe):
        """Integration test with real plugin classes (if available)."""
        # This test would use actual plugin classes if they're available
        # For now, it's marked as integration and can be skipped in unit tests
        pytest.skip("Integration test - requires actual plugin implementations")

    def test_transform_with_result_gdf_key(self, transform_chain, sample_geodataframe):
        """Test handling of result_gdf key in step results."""
        # Mock transformer that returns result_gdf
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {
            "data": {"processed": True},
            "result_gdf": sample_geodataframe,
        }

        config = {
            "plugin": "transform_chain",
            "steps": [
                {"plugin": "geo_transformer", "params": {}, "output_key": "geo_result"}
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(
                PluginRegistry, "get_plugin", return_value=lambda db: mock_transformer
            ):
                with patch("builtins.print"):
                    result = transform_chain.transform(sample_geodataframe, config)

                assert "geo_result" in result
                assert result["geo_result"]["data"]["processed"] is True

    def test_transform_preserves_geodataframe_between_steps(
        self, transform_chain, sample_geodataframe
    ):
        """Test that GeoDataFrame is preserved between geospatial steps."""
        # First transformer returns regular dict with _gdf
        mock_overlay = Mock()
        mock_overlay.transform.return_value = {
            "overlay_count": 5,
            "_gdf": sample_geodataframe,
        }

        # Second transformer should receive the GeoDataFrame
        mock_raster = Mock()
        mock_raster.transform.return_value = {"mean_value": 42.5}

        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "vector_overlay",
                    "params": {"layer": "test"},
                    "output_key": "overlay",
                },
                {
                    "plugin": "raster_stats",
                    "params": {"raster": "test.tif"},
                    "output_key": "stats",
                },
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(PluginRegistry, "get_plugin") as mock_get_plugin:

                def get_plugin_side_effect(name, plugin_type):
                    if name == "vector_overlay":
                        return lambda db: mock_overlay
                    elif name == "raster_stats":
                        return lambda db: mock_raster

                mock_get_plugin.side_effect = get_plugin_side_effect

                with patch("builtins.print"):
                    transform_chain.transform(sample_geodataframe, config)

                # Verify that raster_stats received the GeoDataFrame from vector_overlay
                raster_call = mock_raster.transform.call_args[0]
                assert isinstance(raster_call[0], gpd.GeoDataFrame)

    def test_transform_with_none_params(self, transform_chain, sample_dataframe):
        """Test transformation with None parameters becomes empty dict."""
        mock_transformer = Mock()
        mock_transformer.transform.return_value = {"result": "ok"}

        # The TransformStepConfig model has a default_factory for params
        # So even if we don't provide params, it should default to an empty dict
        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "test_transformer",
                    # Omitting params entirely - should default to {}
                    "output_key": "test",
                }
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(
                PluginRegistry, "get_plugin", return_value=lambda db: mock_transformer
            ):
                transform_chain.transform(sample_dataframe, config)

                # Verify empty dict was passed as params
                call_config = mock_transformer.transform.call_args[0][1]
                assert call_config["params"] == {}

    def test_resolve_references_with_attribute_access(self, transform_chain):
        """Test reference resolution with object attribute access."""

        # Create a mock object with attributes
        class MockResult:
            def __init__(self):
                self.count = 42
                self.data = {"nested": "value"}

        params = {"count_ref": "@step1.count", "nested_ref": "@step1.data"}

        context = {"step1": MockResult()}

        resolved = transform_chain._resolve_references(params, context)
        assert resolved["count_ref"] == 42
        assert resolved["nested_ref"] == {"nested": "value"}

    def test_validate_config_with_invalid_step_format(self, transform_chain):
        """Test configuration validation with invalid step format."""
        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "test_transformer",
                    # Missing required 'output_key'
                    "params": {},
                }
            ],
        }

        with pytest.raises(DataTransformError) as exc_info:
            transform_chain.validate_config(config)

        assert "Invalid transform chain configuration" in str(exc_info.value)

    def test_transform_maintains_data_flow(self, transform_chain, sample_dataframe):
        """Test that data flows correctly through multiple transformation steps."""
        # First transformer modifies the data
        transformed_df = pd.DataFrame(
            {"id": [1, 2], "value": [100, 200], "new_col": ["X", "Y"]}
        )
        mock_transformer1 = Mock()
        mock_transformer1.transform.return_value = transformed_df

        # Second transformer works on the modified data
        mock_transformer2 = Mock()
        mock_transformer2.transform.return_value = {"row_count": 2}

        config = {
            "plugin": "transform_chain",
            "steps": [
                {
                    "plugin": "transform1",
                    "params": {"multiply": 10},
                    "output_key": "step1",
                },
                {"plugin": "transform2", "params": {}, "output_key": "step2"},
            ],
        }

        with patch.object(PluginRegistry, "has_plugin", return_value=True):
            with patch.object(PluginRegistry, "get_plugin") as mock_get_plugin:

                def get_plugin_side_effect(name, plugin_type):
                    if name == "transform1":
                        return lambda db: mock_transformer1
                    elif name == "transform2":
                        return lambda db: mock_transformer2

                mock_get_plugin.side_effect = get_plugin_side_effect

                transform_chain.transform(sample_dataframe, config)

                # Verify second transformer received the output of the first
                second_call_data = mock_transformer2.transform.call_args[0][0]
                assert isinstance(second_call_data, pd.DataFrame)
                assert list(second_call_data.columns) == ["id", "value", "new_col"]
