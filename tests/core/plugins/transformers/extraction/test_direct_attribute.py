"""
Tests for the DirectAttribute transformer plugin.

This module contains comprehensive tests for the direct_attribute plugin,
which extracts field values from database tables or import sources.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from niamoto.core.plugins.transformers.extraction.direct_attribute import (
    DirectAttribute,
    DirectAttributeConfig,
)
from niamoto.common.exceptions import DatabaseError


class TestDirectAttributeConfig:
    """Test suite for DirectAttributeConfig validation."""

    def test_valid_config(self):
        """Test valid configuration."""
        config = DirectAttributeConfig(
            plugin="direct_attribute", params={"source": "plots", "field": "area"}
        )
        assert config.plugin == "direct_attribute"
        assert config.params.source == "plots"
        assert config.params.field == "area"

    def test_config_with_units(self):
        """Test configuration with units parameter."""
        config = DirectAttributeConfig(
            plugin="direct_attribute",
            params={"source": "plots", "field": "area", "units": "m²"},
        )
        assert config.params.units == "m²"

    def test_config_with_max_value(self):
        """Test configuration with max_value parameter."""
        config = DirectAttributeConfig(
            plugin="direct_attribute",
            params={"source": "plots", "field": "area", "max_value": 1000},
        )
        assert config.params.max_value == 1000

    def test_missing_source(self):
        """Test configuration with missing source."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(plugin="direct_attribute", params={"field": "area"})
        assert "Field required" in str(exc_info.value)

    def test_missing_field(self):
        """Test configuration with missing field."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(plugin="direct_attribute", params={"source": "plots"})
        assert "Field required" in str(exc_info.value)

    def test_invalid_params_type(self):
        """Test configuration with invalid params type."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(plugin="direct_attribute", params="invalid")
        assert "Input should be a valid dictionary" in str(exc_info.value)

    def test_invalid_source_type(self):
        """Test configuration with invalid source type."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(
                plugin="direct_attribute", params={"source": 123, "field": "area"}
            )
        assert "Input should be a valid string" in str(exc_info.value)

    def test_invalid_field_type(self):
        """Test configuration with invalid field type."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(
                plugin="direct_attribute", params={"source": "plots", "field": 123}
            )
        assert "Input should be a valid string" in str(exc_info.value)


class TestDirectAttribute:
    """Test suite for DirectAttribute transformer plugin."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        return Mock()

    @pytest.fixture
    def mock_config(self):
        """Create a mock config object."""
        mock = Mock()
        mock.config_dir = "/mock/config"
        mock.get_imports_config.return_value = {
            "occurrences": {
                "type": "csv",
                "path": "data/occurrences.csv",
                "identifier": "id",
            },
            "plots": {
                "type": "vector",
                "path": "data/plots.shp",
                "identifier": "plot_id",
            },
        }
        return mock

    @pytest.fixture
    def direct_attribute(self, mock_db, mock_config):
        """Create a DirectAttribute instance with mocked dependencies."""
        with patch(
            "niamoto.core.plugins.transformers.extraction.direct_attribute.Config"
        ) as mock_config_class:
            mock_config_class.return_value = mock_config
            return DirectAttribute(mock_db)

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})

    def test_initialization(self, direct_attribute, mock_db):
        """Test DirectAttribute initialization."""
        assert direct_attribute.db == mock_db
        assert direct_attribute.config_model == DirectAttributeConfig
        assert hasattr(direct_attribute, "imports_config")

    def test_validate_config_valid(self, direct_attribute):
        """Test configuration validation with valid config."""
        config = {
            "plugin": "direct_attribute",
            "params": {"source": "plots", "field": "area"},
        }

        validated = direct_attribute.validate_config(config)
        assert validated.plugin == "direct_attribute"
        assert validated.params.source == "plots"
        assert validated.params.field == "area"

    def test_validate_config_invalid(self, direct_attribute):
        """Test configuration validation with invalid config."""
        config = {
            "plugin": "direct_attribute",
            "params": {"source": "plots"},  # Missing field
        }

        with pytest.raises(ValueError) as exc_info:
            direct_attribute.validate_config(config)
        assert "Invalid configuration" in str(exc_info.value)

    def test_get_field_from_table_success(self, direct_attribute, mock_db):
        """Test successful field retrieval from database table."""
        # Mock database response - fetch_one returns a dict-like object
        mock_db.fetch_one.return_value = {"area": 42.5}

        result = direct_attribute._get_field_from_table("plots", "area", 1)

        assert result == 42.5
        mock_db.fetch_one.assert_called_once()
        # Check the call arguments - args[0] is query, args[1] is params dict
        call_args = mock_db.fetch_one.call_args
        assert "SELECT area FROM plots WHERE id = :id_value" in call_args.args[0]
        assert call_args.args[1] == {"id_value": 1}

    def test_get_field_from_table_not_found(self, direct_attribute, mock_db):
        """Test field retrieval when record not found."""
        # Mock database response - fetch_one returns None when not found
        mock_db.fetch_one.return_value = None

        result = direct_attribute._get_field_from_table("plots", "area", 999)

        assert result is None

    def test_get_field_from_table_null_value(self, direct_attribute, mock_db):
        """Test field retrieval with NULL value."""
        # Mock database response - fetch_one returns dict with None value
        mock_db.fetch_one.return_value = {"area": None}

        result = direct_attribute._get_field_from_table("plots", "area", 1)

        assert result is None

    def test_get_field_from_table_error(self, direct_attribute, mock_db):
        """Test field retrieval with database error."""
        mock_db.fetch_one.side_effect = Exception("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            direct_attribute._get_field_from_table("plots", "area", 1)

        assert "Error getting field area from plots" in str(exc_info.value)

    def test_get_field_value_from_csv_import(self, direct_attribute, mock_db):
        """Test field retrieval from entity resolved via registry."""
        # Mock registry to return entity info
        from types import SimpleNamespace

        direct_attribute.registry.get = Mock(
            return_value=SimpleNamespace(table_name="dataset_occurrences")
        )

        # Mock database response
        mock_db.fetch_one.return_value = {"species": "Species B"}

        result = direct_attribute._get_field_value("occurrences", "species", 2)

        assert result == "Species B"
        direct_attribute.registry.get.assert_called_once_with("occurrences")
        mock_db.fetch_one.assert_called_once()

    def test_get_field_value_from_vector_import(self, direct_attribute, mock_db):
        """Test field retrieval from entity resolved via registry."""
        # Mock registry to return entity info
        from types import SimpleNamespace

        direct_attribute.registry.get = Mock(
            return_value=SimpleNamespace(table_name="entity_plots")
        )

        # Mock database response
        mock_db.fetch_one.return_value = {"area": 200.0}

        result = direct_attribute._get_field_value("plots", "area", 2)

        assert result == 200.0
        direct_attribute.registry.get.assert_called_once_with("plots")
        mock_db.fetch_one.assert_called_once()

    def test_get_field_value_from_table(self, direct_attribute, mock_db):
        """Test field retrieval from database table (not in registry)."""
        # Mock registry returns None (entity not found)
        direct_attribute.registry.get = Mock(return_value=None)

        # Mock database response - uses source name as table name when not in registry
        mock_db.fetch_one.return_value = {"field": "Value from DB"}

        result = direct_attribute._get_field_value("custom_table", "field", 1)

        assert result == "Value from DB"
        direct_attribute.registry.get.assert_called_once_with("custom_table")
        mock_db.fetch_one.assert_called_once()

    def test_get_field_value_not_found_in_import(self, direct_attribute, mock_db):
        """Test field retrieval when record not found."""
        # Mock registry to return entity info
        from types import SimpleNamespace

        direct_attribute.registry.get = Mock(
            return_value=SimpleNamespace(table_name="dataset_occurrences")
        )

        # Mock database returns None (record not found)
        mock_db.fetch_one.return_value = None

        result = direct_attribute._get_field_value("occurrences", "species", 999)

        assert result is None
        direct_attribute.registry.get.assert_called_once_with("occurrences")
        mock_db.fetch_one.assert_called_once()

    def test_get_field_value_unsupported_import_type(self, direct_attribute):
        """Test field retrieval with unsupported import type."""
        # Mock imports_config with unsupported type
        direct_attribute.imports_config = {
            "custom": {
                "type": "unsupported",
                "path": "data/custom.dat",
                "identifier": "id",
            }
        }

        with pytest.raises(ValueError) as exc_info:
            direct_attribute._get_field_value("custom", "field", 1)

        # The error is wrapped, so check for the general error message
        assert "Error getting field field from custom" in str(exc_info.value)

    def test_transform_with_group_id(self, direct_attribute, sample_dataframe, mock_db):
        """Test transform with valid group_id."""
        # Create a DataFrame with the field we're looking for
        data_df = pd.DataFrame({"area": [42.5, 100.0], "name": ["Plot A", "Plot B"]})

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # The value is converted to string format
        assert result["value"] == "42.5"
        assert result["units"] == ""

    def test_transform_without_group_id(self, direct_attribute, sample_dataframe):
        """Test transform without group_id."""
        config = {
            "plugin": "direct_attribute",
            "params": {"source": "plots", "field": "area"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        assert result == {"value": None}

    def test_transform_with_units(self, direct_attribute, sample_dataframe, mock_db):
        """Test transform with units parameter."""
        # Create a DataFrame with the field we're looking for
        data_df = pd.DataFrame({"area": [100.0, 150.0], "name": ["Plot A", "Plot B"]})

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "units": "m²"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # Value is converted to string
        assert result["value"] == "100"
        assert result["units"] == "m²"

    def test_transform_with_max_value_applied(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with max_value restriction applied."""
        # Create a DataFrame with the field we're looking for
        data_df = pd.DataFrame({"area": [150.0, 200.0], "name": ["Plot A", "Plot B"]})

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "max_value": 100.0},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # When max_value is applied, it's still converted to string
        assert result["value"] == "100"

    def test_transform_with_max_value_not_applied(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with max_value when value is below limit."""
        # Create a DataFrame with the field we're looking for
        data_df = pd.DataFrame({"area": [50.0, 75.0], "name": ["Plot A", "Plot B"]})

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "max_value": 100.0},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # When max_value not applied, preserves original format as string
        assert result["value"] == "50"

    def test_transform_preserves_string_format(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test that transform preserves original string format of numbers."""
        # Create a DataFrame with string number
        data_df = pd.DataFrame(
            {"area": ["42.50", "100.00"], "name": ["Plot A", "Plot B"]}
        )

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # Should preserve the decimal places from original string
        assert result["value"] == "42.50"

    def test_transform_integer_format(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with integer values."""
        # Create a DataFrame with integer values
        data_df = pd.DataFrame({"count": [42, 100], "name": ["Plot A", "Plot B"]})

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "count"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # Integer is converted to string
        assert str(result["value"]) == "42"

    def test_transform_non_numeric_value(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with non-numeric value."""
        # Create a DataFrame with text values
        data_df = pd.DataFrame(
            {"name": ["Text value", "Another text"], "area": [100, 200]}
        )

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "name"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        assert result["value"] == "Text value"

    def test_transform_null_value(self, direct_attribute, sample_dataframe, mock_db):
        """Test transform with NULL value from database."""
        # Create a DataFrame with None values
        data_df = pd.DataFrame(
            {"optional_field": [None, "Value"], "name": ["Plot A", "Plot B"]}
        )

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "optional_field"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        assert result["value"] is None

    def test_transform_error_handling(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform error handling."""
        # Create a DataFrame that will cause an error (missing field)
        data_df = pd.DataFrame(
            {
                "name": ["Plot A", "Plot B"]
                # Missing 'area' field
            }
        )

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        # This should not raise an error, but return None value
        result = direct_attribute.transform(data_df, config)
        assert result["value"] is None

    def test_transform_float_to_string_conversion(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test float to string conversion maintains precision."""
        # Create a DataFrame with float values
        data_df = pd.DataFrame({"area": [42.0, 100.0], "name": ["Plot A", "Plot B"]})

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # Should remove trailing .0 for integer-like floats
        assert result["value"] == "42"

    def test_file_path_construction(self, direct_attribute, mock_db):
        """Test field retrieval uses registry-resolved table names."""
        # Mock registry to return entity info with specific table name
        from types import SimpleNamespace

        direct_attribute.registry.get = Mock(
            return_value=SimpleNamespace(table_name="dataset_occurrences")
        )

        # Mock database response
        mock_db.fetch_one.return_value = {"species": "Test Species"}

        result = direct_attribute._get_field_value("occurrences", "species", 1)

        # Verify result and that registry was consulted
        assert result == "Test Species"
        direct_attribute.registry.get.assert_called_once_with("occurrences")
        # Verify the resolved table name was used in the query
        call_args = mock_db.fetch_one.call_args
        assert "dataset_occurrences" in call_args[0][0]

    def test_max_value_with_string_numeric(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test max_value application with string numeric value."""
        # Create a DataFrame with string numeric values
        data_df = pd.DataFrame(
            {"area": ["150.75", "200.50"], "name": ["Plot A", "Plot B"]}
        )

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "max_value": "100"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # Should apply max_value and return as string, preserving decimal places from original
        assert result["value"] == "100.00"

    def test_decimal_precision_preservation(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test that decimal precision is preserved from original format."""
        # Create a DataFrame with precise decimal values
        data_df = pd.DataFrame(
            {"precise_value": ["123.456", "789.012"], "name": ["Plot A", "Plot B"]}
        )

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "precise_value"},
        }

        # Pass the DataFrame directly (simulating TransformerService smart selection)
        result = direct_attribute.transform(data_df, config)

        # Should preserve the 3 decimal places
        assert result["value"] == "123.456"


@pytest.mark.integration
class TestDirectAttributeIntegration:
    """Integration tests for DirectAttribute plugin."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory with test files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test CSV
        csv_data = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "species": ["Hibbertia lucens", "Hibbertia pancheri", "Syzygium acre"],
                "count": [10, 20, 15],
            }
        )
        csv_data.to_csv(data_dir / "occurrences.csv", index=False)

        # Create test shapefile with CRS to avoid warning
        gdf = gpd.GeoDataFrame(
            {
                "plot_id": [1, 2, 3],
                "name": ["Plot A", "Plot B", "Plot C"],
                "area": [100.5, 200.0, 150.3],
                "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
            },
            crs="EPSG:4326",
        )  # WGS84 coordinate system
        gdf.to_file(data_dir / "plots.shp")

        return data_dir

    def test_full_workflow_csv(self, mock_db, temp_data_dir):
        """Test complete workflow with CSV import."""
        # Create a DataFrame that simulates the CSV data
        data_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "species": ["Hibbertia lucens", "Hibbertia pancheri", "Syzygium acre"],
                "count": [10, 20, 15],
            }
        )

        # For CSV data, we would receive the full DataFrame filtered by group_id
        # Simulate filtering to the second row (group_id=2)
        filtered_df = data_df[data_df["id"] == 2]

        # Create config with temp directory
        mock_config = Mock()
        mock_config.config_dir = str(temp_data_dir.parent / "config")
        mock_config.get_imports_config.return_value = {
            "occurrences": {
                "type": "csv",
                "path": str(temp_data_dir / "occurrences.csv"),
                "identifier": "id",
            }
        }

        # Patch at the module level where it's actually used
        with patch(
            "niamoto.core.plugins.transformers.extraction.direct_attribute.Config"
        ) as mock_config_class:
            mock_config_class.return_value = mock_config

            direct_attribute = DirectAttribute(mock_db)
            # Manually set the imports_config since we're in test environment
            direct_attribute.imports_config = (
                mock_config.get_imports_config.return_value
            )

            config = {
                "plugin": "direct_attribute",
                "group_id": 2,
                "params": {"source": "occurrences", "field": "species"},
            }

            # Pass the filtered DataFrame
            result = direct_attribute.transform(filtered_df, config)

            assert result["value"] == "Hibbertia pancheri"

    def test_full_workflow_vector(self, mock_db, temp_data_dir):
        """Test complete workflow with vector import."""
        # Create a DataFrame that simulates the vector data
        data_df = pd.DataFrame(
            {
                "plot_id": [1, 2, 3],
                "name": ["Plot A", "Plot B", "Plot C"],
                "area": [100.5, 200.0, 150.3],
            }
        )

        # For vector data, we would receive the full DataFrame filtered by group_id
        # Simulate filtering to the second row (group_id=2)
        filtered_df = data_df[data_df["plot_id"] == 2]

        # Create config with temp directory
        mock_config = Mock()
        mock_config.config_dir = str(temp_data_dir.parent / "config")
        mock_config.get_imports_config.return_value = {
            "plots": {
                "type": "vector",
                "path": str(temp_data_dir / "plots.shp"),
                "identifier": "plot_id",
            }
        }

        # Patch at the module level where it's actually used
        with patch(
            "niamoto.core.plugins.transformers.extraction.direct_attribute.Config"
        ) as mock_config_class:
            mock_config_class.return_value = mock_config

            direct_attribute = DirectAttribute(mock_db)
            # Manually set the imports_config since we're in test environment
            direct_attribute.imports_config = (
                mock_config.get_imports_config.return_value
            )

            config = {
                "plugin": "direct_attribute",
                "group_id": 2,
                "params": {"source": "plots", "field": "area", "units": "m²"},
            }

            # Pass the filtered DataFrame
            result = direct_attribute.transform(filtered_df, config)

            assert result["value"] == "200"
            assert result["units"] == "m²"
