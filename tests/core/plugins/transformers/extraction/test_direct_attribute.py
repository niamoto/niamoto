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
        assert config.params["source"] == "plots"
        assert config.params["field"] == "area"

    def test_config_with_units(self):
        """Test configuration with units parameter."""
        config = DirectAttributeConfig(
            plugin="direct_attribute",
            params={"source": "plots", "field": "area", "units": "m²"},
        )
        assert config.params["units"] == "m²"

    def test_config_with_max_value(self):
        """Test configuration with max_value parameter."""
        config = DirectAttributeConfig(
            plugin="direct_attribute",
            params={"source": "plots", "field": "area", "max_value": 1000},
        )
        assert config.params["max_value"] == 1000

    def test_missing_source(self):
        """Test configuration with missing source."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(plugin="direct_attribute", params={"field": "area"})
        assert "Missing required field: source" in str(exc_info.value)

    def test_missing_field(self):
        """Test configuration with missing field."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(plugin="direct_attribute", params={"source": "plots"})
        assert "Missing required field: field" in str(exc_info.value)

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
        assert "source must be a string" in str(exc_info.value)

    def test_invalid_field_type(self):
        """Test configuration with invalid field type."""
        with pytest.raises(ValueError) as exc_info:
            DirectAttributeConfig(
                plugin="direct_attribute", params={"source": "plots", "field": 123}
            )
        assert "field must be a string" in str(exc_info.value)


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
        assert validated["plugin"] == "direct_attribute"
        assert validated["params"]["source"] == "plots"
        assert validated["params"]["field"] == "area"

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
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (42.5,)
        mock_db.execute_select.return_value = mock_result

        result = direct_attribute._get_field_from_table("plots", "area", 1)

        assert result == 42.5
        mock_db.execute_select.assert_called_once()
        call_args = mock_db.execute_select.call_args[0][0]
        assert "SELECT area FROM plots WHERE id = 1" in call_args

    def test_get_field_from_table_not_found(self, direct_attribute, mock_db):
        """Test field retrieval when record not found."""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute_select.return_value = mock_result

        result = direct_attribute._get_field_from_table("plots", "area", 999)

        assert result is None

    def test_get_field_from_table_null_value(self, direct_attribute, mock_db):
        """Test field retrieval with NULL value."""
        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (None,)
        mock_db.execute_select.return_value = mock_result

        result = direct_attribute._get_field_from_table("plots", "area", 1)

        assert result is None

    def test_get_field_from_table_error(self, direct_attribute, mock_db):
        """Test field retrieval with database error."""
        mock_db.execute_select.side_effect = Exception("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            direct_attribute._get_field_from_table("plots", "area", 1)

        assert "Error getting field area from plots" in str(exc_info.value)

    @patch("os.path.dirname")
    @patch("pandas.read_csv")
    def test_get_field_value_from_csv_import(
        self, mock_read_csv, mock_dirname, direct_attribute
    ):
        """Test field retrieval from CSV import source."""
        # Ensure imports_config has the correct structure
        direct_attribute.imports_config = {
            "occurrences": {
                "type": "csv",
                "path": "data/occurrences.csv",
                "identifier": "id",
            }
        }

        # Mock path construction
        mock_dirname.return_value = "/mock/base"

        # Mock CSV data
        mock_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "species": ["Species A", "Species B", "Species C"],
                "count": [10, 20, 30],
            }
        )
        mock_read_csv.return_value = mock_df

        result = direct_attribute._get_field_value("occurrences", "species", 2)

        assert result == "Species B"
        mock_read_csv.assert_called_once()

    @patch("os.path.dirname")
    @patch("geopandas.read_file")
    def test_get_field_value_from_vector_import(
        self, mock_read_file, mock_dirname, direct_attribute
    ):
        """Test field retrieval from vector import source."""
        # Ensure imports_config has the correct structure
        direct_attribute.imports_config = {
            "plots": {
                "type": "vector",
                "path": "data/plots.shp",
                "identifier": "plot_id",
            }
        }

        # Mock path construction
        mock_dirname.return_value = "/mock/base"

        # Mock GeoDataFrame
        mock_gdf = gpd.GeoDataFrame(
            {
                "plot_id": [1, 2, 3],
                "name": ["Plot A", "Plot B", "Plot C"],
                "area": [100.5, 200.0, 150.3],
                "geometry": [Point(0, 0), Point(1, 1), Point(2, 2)],
            }
        )
        mock_read_file.return_value = mock_gdf

        result = direct_attribute._get_field_value("plots", "area", 2)

        assert result == 200.0
        mock_read_file.assert_called_once()

    def test_get_field_value_from_table(self, direct_attribute, mock_db):
        """Test field retrieval from database table (not in imports)."""
        # Remove the source from imports config
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = ("Value from DB",)
        mock_db.execute_select.return_value = mock_result

        result = direct_attribute._get_field_value("custom_table", "field", 1)

        assert result == "Value from DB"

    @patch("os.path.dirname")
    @patch("pandas.read_csv")
    def test_get_field_value_not_found_in_import(
        self, mock_read_csv, mock_dirname, direct_attribute
    ):
        """Test field retrieval when record not found in import."""
        # Ensure imports_config has the correct structure
        direct_attribute.imports_config = {
            "occurrences": {
                "type": "csv",
                "path": "data/occurrences.csv",
                "identifier": "id",
            }
        }

        # Mock path construction
        mock_dirname.return_value = "/mock/base"

        # Mock CSV data
        mock_df = pd.DataFrame(
            {"id": [1, 2, 3], "species": ["Species A", "Species B", "Species C"]}
        )
        mock_read_csv.return_value = mock_df

        result = direct_attribute._get_field_value("occurrences", "species", 999)

        assert result is None

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
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (42.5,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

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
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (100.0,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "units": "m²"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # Value is converted to string
        assert result["value"] == "100"
        assert result["units"] == "m²"

    def test_transform_with_max_value_applied(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with max_value restriction applied."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response with value exceeding max
        mock_result = Mock()
        mock_result.fetchone.return_value = (150.0,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "max_value": 100.0},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # When max_value is applied, it's still converted to string
        assert result["value"] == "100"

    def test_transform_with_max_value_not_applied(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with max_value when value is below limit."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (50.0,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "max_value": 100.0},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # When max_value not applied, preserves original format as string
        assert result["value"] == "50"

    def test_transform_preserves_string_format(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test that transform preserves original string format of numbers."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response with string number
        mock_result = Mock()
        mock_result.fetchone.return_value = ("42.50",)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # Should preserve the decimal places from original string
        assert result["value"] == "42.50"

    def test_transform_integer_format(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with integer values."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (42,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "count"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # Integer is converted to string
        assert result["value"] == "42"

    def test_transform_non_numeric_value(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform with non-numeric value."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = ("Text value",)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "name"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        assert result["value"] == "Text value"

    def test_transform_null_value(self, direct_attribute, sample_dataframe, mock_db):
        """Test transform with NULL value from database."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response
        mock_result = Mock()
        mock_result.fetchone.return_value = (None,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "optional_field"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        assert result["value"] is None

    def test_transform_error_handling(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test transform error handling."""
        # Mock database error
        mock_db.execute_select.side_effect = Exception("Database connection lost")

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        with pytest.raises(ValueError) as exc_info:
            direct_attribute.transform(sample_dataframe, config)

        assert "Error transforming data" in str(exc_info.value)

    def test_transform_float_to_string_conversion(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test float to string conversion maintains precision."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response with float
        mock_result = Mock()
        mock_result.fetchone.return_value = (42.0,)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # Should remove trailing .0 for integer-like floats
        assert result["value"] == "42"

    @patch("pandas.read_csv")
    def test_file_path_construction(self, mock_read_csv, direct_attribute):
        """Test correct file path construction for imports."""
        # Ensure imports_config has the correct structure
        direct_attribute.imports_config = {
            "occurrences": {
                "type": "csv",
                "path": "data/occurrences.csv",
                "identifier": "id",
            }
        }

        # Set up a mock config with config_dir
        direct_attribute.config = Mock()
        direct_attribute.config.config_dir = "/base/dir/config/niamoto.yml"

        mock_df = pd.DataFrame({"id": [1], "species": ["Test Species"]})
        mock_read_csv.return_value = mock_df

        # Patch os.path at the module level
        with patch(
            "niamoto.core.plugins.transformers.extraction.direct_attribute.os.path.dirname"
        ) as mock_dirname:
            with patch(
                "niamoto.core.plugins.transformers.extraction.direct_attribute.os.path.join"
            ) as mock_join:
                mock_dirname.return_value = "/base/dir/config"
                mock_join.return_value = "/base/dir/config/data/occurrences.csv"

                result = direct_attribute._get_field_value("occurrences", "species", 1)

        # Verify result
        assert result == "Test Species"
        mock_read_csv.assert_called_once_with("/base/dir/config/data/occurrences.csv")

    def test_max_value_with_string_numeric(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test max_value application with string numeric value."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response with string number
        mock_result = Mock()
        mock_result.fetchone.return_value = ("150.75",)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "area", "max_value": "100"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

        # Should apply max_value and return as string, preserving decimal places from original
        assert result["value"] == "100.00"

    def test_decimal_precision_preservation(
        self, direct_attribute, sample_dataframe, mock_db
    ):
        """Test that decimal precision is preserved from original format."""
        # Mock imports_config to ensure source is treated as a table
        direct_attribute.imports_config = {}

        # Mock database response with specific decimal places
        mock_result = Mock()
        mock_result.fetchone.return_value = ("123.456",)
        mock_db.execute_select.return_value = mock_result

        config = {
            "plugin": "direct_attribute",
            "group_id": 1,
            "params": {"source": "plots", "field": "precise_value"},
        }

        result = direct_attribute.transform(sample_dataframe, config)

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
        # Create the actual file path that will be used
        csv_file_path = str(temp_data_dir / "occurrences.csv")

        # Create config with temp directory
        mock_config = Mock()
        mock_config.config_dir = str(temp_data_dir.parent / "config")
        mock_config.get_imports_config.return_value = {
            "occurrences": {
                "type": "csv",
                "path": csv_file_path,  # Use the actual file path
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

            result = direct_attribute.transform(pd.DataFrame(), config)

            assert result["value"] == "Hibbertia pancheri"

    def test_full_workflow_vector(self, mock_db, temp_data_dir):
        """Test complete workflow with vector import."""
        # Create the actual file path that will be used
        shp_file_path = str(temp_data_dir / "plots.shp")

        # Create config with temp directory
        mock_config = Mock()
        mock_config.config_dir = str(temp_data_dir.parent / "config")
        mock_config.get_imports_config.return_value = {
            "plots": {
                "type": "vector",
                "path": shp_file_path,  # Use the actual file path
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

            result = direct_attribute.transform(pd.DataFrame(), config)

            assert result["value"] == "200"
            assert result["units"] == "m²"
