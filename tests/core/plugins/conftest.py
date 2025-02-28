"""
Pytest configuration for plugin tests.

This module contains fixtures and configuration for plugin testing.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock
from pathlib import Path
import sys
import importlib

from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.plugin_loader import PluginLoader


@pytest.fixture(scope="session")
def mock_db():
    """Create a mock database connection for testing."""
    db = MagicMock()

    # Configure common database methods
    db.execute_query.return_value = pd.DataFrame()
    db.execute.return_value = None
    db.get_connection.return_value = MagicMock()

    return db


@pytest.fixture(scope="session")
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["A", "B", "C", "D", "E"],
            "value": [10, 20, 30, 40, 50],
            "category": ["X", "Y", "X", "Y", "Z"],
        }
    )


@pytest.fixture(scope="session")
def sample_geo_dataframe():
    """Create a sample GeoDataFrame for testing."""
    try:
        import geopandas as gpd
        from shapely.geometry import Point

        df = pd.DataFrame(
            {"id": [1, 2, 3], "name": ["A", "B", "C"], "value": [10, 20, 30]}
        )

        geometry = [Point(0, 0), Point(1, 1), Point(2, 2)]
        return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    except ImportError:
        # Return a regular DataFrame with a geometry column if geopandas is not available
        return pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["A", "B", "C"],
                "value": [10, 20, 30],
                "geometry": ["POINT(0 0)", "POINT(1 1)", "POINT(2 2)"],
            }
        )


@pytest.fixture(scope="session")
def plugin_loader():
    """Create a plugin loader instance."""
    return PluginLoader()


@pytest.fixture(scope="function")
def clear_registry():
    """Clear the plugin registry before and after the test."""
    PluginRegistry.clear()
    yield
    PluginRegistry.clear()


@pytest.fixture(scope="session")
def core_plugins_path():
    """Get the path to core plugins."""
    return (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "niamoto"
        / "core"
        / "plugins"
    )


@pytest.fixture(scope="function")
def load_test_plugin(request, core_plugins_path):
    """
    Load a specific plugin for testing.

    Usage:
        @pytest.mark.parametrize('plugin_info', [
            ('transformers.extraction.direct_attribute', 'DirectAttributeTransformer'),
            ('transformers.aggregation.field_aggregator', 'FieldAggregatorTransformer'),
        ])
        def test_something(load_test_plugin, plugin_info):
            module_path, class_name = plugin_info
            plugin_class = load_test_plugin(module_path, class_name)
            # Use plugin_class...
    """

    def _load_plugin(module_path, class_name):
        """Load a plugin by module path and class name."""
        # Add src to path if not already there
        src_dir = str(core_plugins_path.parent.parent.parent)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        try:
            # Import the module
            full_module_path = f"niamoto.core.plugins.{module_path}"
            module = importlib.import_module(full_module_path)

            # Get the plugin class
            plugin_class = getattr(module, class_name)
            return plugin_class
        except (ImportError, AttributeError) as e:
            pytest.skip(f"Could not load plugin {module_path}.{class_name}: {str(e)}")
            return None

    return _load_plugin


# Add more fixtures as needed for plugin testing
