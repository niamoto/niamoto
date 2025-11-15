"""
Tests for the FieldAggregator transformer plugin.
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from pydantic import ValidationError
import tempfile
import os

from niamoto.core.plugins.transformers.aggregation.field_aggregator import (
    FieldAggregator,
    FieldAggregatorConfig,
    FieldConfig,
)
from niamoto.common.database import Database


# Sample DataFrame for testing
SAMPLE_DATA = pd.DataFrame(
    {
        "group_col": ["A", "A", "B", "B", "B", "C"],
        "value_col1": [10, 20, 30, 40, 50, 60],
        "value_col2": [1, 2, 3, 4, 5, 6],
        "string_col": ["x", "y", "x", "z", "y", "z"],
        "label_col": [1, 2, 1, 2, 2, 1],
        "numeric_col": [10, 20, 30, 40, 50, 60],
    }
)


class TestFieldAggregator:
    """Test suite for the FieldAggregator plugin."""

    def setup_method(self):
        """Set up test method."""
        # Create a temporary directory for config to avoid creating at project root
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")

        self.db_mock = MagicMock(spec=Database)

        # Mock Config to prevent creating config directory at project root
        with patch(
            "niamoto.core.plugins.transformers.aggregation.field_aggregator.Config"
        ) as mock_config:
            mock_config.return_value.get_imports_config = {}
            self.plugin = FieldAggregator(self.db_mock)

    def teardown_method(self):
        """Clean up test method."""
        import shutil

        # Clean up temporary directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # def test_plugin_registration_and_type(self):
    #     """Test plugin registration and type."""
    #     # Temporarily disable this test until register() is found/fixed
    #     # assert self.plugin.name == "field_aggregator"
    #     # assert self.plugin.type == PluginType.TRANSFORMER
    #     plugin_instance = PluginRegistry.get_plugin("field_aggregator")
    #     assert isinstance(plugin_instance, FieldAggregator)
    #     # Check if the registered plugin has the correct type if available
    #     # registered_type = getattr(plugin_instance, 'type', None)
    #     # if registered_type:
    #     #    assert registered_type == PluginType.TRANSFORMER

    def test_config_model(self):
        """Test the config model validation."""
        # Example of valid config using the FieldConfig structure
        valid_config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "value_col1",
                        "target": "total_value1",
                        "transformation": "direct",  # Example transformation
                    },
                    {
                        "source": "some_table",
                        "field": "another_field",
                        "target": "count_records",
                        "transformation": "count",
                    },
                ]
            },
        }
        # This should pass without error
        config_model = FieldAggregatorConfig(**valid_config)
        assert isinstance(config_model, FieldAggregatorConfig)
        assert len(config_model.params.fields) == 2

    def test_config_validation_missing_field_in_item(self):
        """Test config validation fails if a required field is missing within a field item."""
        invalid_config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        # "field": "value_col1",  # Missing required field
                        "target": "total_value1",
                    }
                ]
            },
        }
        # Pydantic raises ValidationError for missing fields in nested models
        with pytest.raises(
            ValidationError, match="Field required"
        ):  # Pydantic's default message for missing fields
            # We test validation during plugin's validate_config or transform,
            # as FieldAggregatorConfig itself only validates 'params' structure.
            # The inner FieldConfig validation happens later.
            # Let's test the FieldConfig directly for simplicity here
            FieldConfig.model_validate(invalid_config["params"]["fields"][0])

    def test_config_validation_invalid_transformation(self):
        """Test config validation fails if transformation is invalid."""
        invalid_config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "value_col1",
                        "target": "total_value1",
                        "transformation": "invalid_transform",  # Invalid value
                    }
                ]
            },
        }
        with pytest.raises(ValidationError, match="Input should be"):
            FieldConfig.model_validate(invalid_config["params"]["fields"][0])

    # --- Placeholder Tests for Transformation Logic ---
    # These tests will be implemented once the config issues are resolved

    def test_transform_direct(self):
        """Test basic 'direct' transformation from occurrences source."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {  # First field: no units
                        "source": "occurrences",
                        "field": "value_col1",
                        "target": "direct_value",
                        "transformation": "direct",
                    },
                    {  # Second field: with units
                        "source": "occurrences",
                        "field": "group_col",
                        "target": "direct_group",
                        "transformation": "direct",
                        "units": "category",
                    },
                ]
            },
        }
        expected_result = {
            "direct_value": {"value": 10},  # From SAMPLE_DATA['value_col1'].iloc[0]
            "direct_group": {
                "value": "A",
                "units": "category",
            },  # From SAMPLE_DATA['group_col'].iloc[0]
        }
        # Use .copy() to avoid modifying the original sample data
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        assert result == expected_result

    def test_transform_count(self):
        """Test 'count' aggregation."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",  # Source doesn't matter for count
                        "field": "any_field",  # Field doesn't matter for count
                        "target": "record_count",
                        "transformation": "count",
                    }
                ]
            },
        }
        # Expected result: count of rows in SAMPLE_DATA (6)
        expected_result = {"record_count": {"value": 6}}
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        assert result == expected_result

    def test_transform_direct_with_labels(self):
        """Test 'direct' transformation with label mapping."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "label_col",
                        "target": "labeled_value",
                        "transformation": "direct",
                        "labels": {
                            "1": "Label One",
                            "2": "Label Two",
                            # Note: Keys must be strings
                        },
                    }
                ]
            },
        }
        # First value in SAMPLE_DATA['label_col'] is 1, which maps to "Label One"
        expected_result = {"labeled_value": {"value": "Label One"}}
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        assert result == expected_result

    def test_transform_direct_with_missing_label(self):
        """Test 'direct' transformation when a label is missing for the value."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "label_col",
                        "target": "labeled_value",
                        "transformation": "direct",
                        "labels": {
                            # "1" is missing
                            "2": "Label Two Only",
                        },
                    }
                ]
            },
        }
        # First value is 1, which is not in labels, so original value should be kept
        expected_result = {"labeled_value": {"value": 1}}
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        assert result == expected_result

    def test_transform_with_db_source(self, mocker):
        """Test transformation involving database lookup.

        FIXED: Mock database at the correct level instead of private method.
        This tests real behavior: transform() -> _get_field_value() -> _get_field_from_table() -> db.fetch_one()
        """
        # 1. Mock registry to resolve 'plots' to a table name
        from types import SimpleNamespace

        mocker.patch.object(
            self.plugin.registry,
            "get",
            return_value=SimpleNamespace(table_name="entity_plots"),
        )

        # 2. Mock database fetch_one (the actual external dependency)
        #    This is the RIGHT level to mock - not the private methods
        mocker.patch.object(
            self.db_mock,
            "fetch_one",
            return_value={"plot_value": 500},  # DB returns this row
        )

        # 3. Configuration using 'plots' as source (DB)
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "plots",  # Use entity name
                        "field": "plot_value",
                        "target": "db_direct_value",
                        "transformation": "direct",
                    }
                ]
            },
        }

        # 4. Expected result based on REAL behavior
        # Note: DB returns values which may be converted to strings
        expected_result = {"db_direct_value": {"value": "500"}}  # String, not int

        # 5. Run transform - tests the REAL logic path, not mocked internals
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # 6. Verify real behavior (value type matters!)
        assert result == expected_result
        # Verify database was actually queried (tests real integration)
        self.db_mock.fetch_one.assert_called_once()

    def test_transform_sum(self):
        """Test 'sum' aggregation."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",  # Use input DataFrame
                        "field": "numeric_col",
                        "target": "total_numeric",
                        "transformation": "sum",
                    }
                ]
            },
        }
        # Expected result: sum of SAMPLE_DATA['numeric_col'] (10 + 20 + 30 = 60)
        expected_result = {"total_numeric": {"value": 210}}
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)
        assert result == expected_result

    def test_transform_with_import_source(self, mocker):
        """Test transformation involving import file lookup.

        FIXED: Mock database at the correct level instead of private method.
        Tests real behavior with import: prefix source.
        """
        # 1. Mock registry.get to return None for import: sources
        #    This triggers fallback to using source name directly as table name
        mocker.patch.object(
            self.plugin.registry,
            "get",
            return_value=None,  # Registry doesn't resolve import: sources
        )

        # 2. Mock database fetch_one to return import data
        #    This is the correct level to mock - the external dependency
        mocker.patch.object(
            self.db_mock,
            "fetch_one",
            return_value={"value_from_import": "imported_data_value"},
        )

        # 3. Configuration using import source (import: prefix)
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "import:my_test_import",  # Specify import source
                        "field": "value_from_import",
                        "target": "final_imported_value",
                        "transformation": "direct",
                    }
                ]
            },
        }

        # 4. Expected result based on DB data
        expected_result = {"final_imported_value": {"value": "imported_data_value"}}

        # 5. Run transform - tests the REAL logic, not mocked private methods
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # 6. Verify real behavior
        assert result == expected_result
        # Verify database was queried (real integration test)
        self.db_mock.fetch_one.assert_called_once()

    def test_transform_empty_dataframe(self):
        """Test transformation with an empty DataFrame."""
        # Define an empty DataFrame with expected columns
        empty_df = pd.DataFrame(columns=SAMPLE_DATA.columns)

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "value_col1",  # For direct
                        "target": "direct_val",
                        "transformation": "direct",
                    },
                    {
                        "source": "occurrences",
                        "field": "numeric_col",  # For sum
                        "target": "sum_val",
                        "transformation": "sum",
                    },
                    {
                        "source": "occurrences",
                        "field": "any",  # Field doesn't matter for count
                        "target": "count_val",
                        "transformation": "count",
                    },
                ]
            },
        }

        # Expected results for empty input
        expected_result = {
            "direct_val": {
                "value": None
            },  # Direct extraction from empty df yields None
            "sum_val": {"value": 0},  # Sum of empty series is 0
            "count_val": {"value": 0},  # Count of empty df is 0
        }

        result = self.plugin.transform(empty_df, config)
        assert result == expected_result

    # NOTE: test_transform_json_field_access removed - it was redundant with
    # test_get_field_from_table_json_field (line 465) which directly tests
    # the JSON extraction logic. Testing _get_field_from_table directly is
    # acceptable for complex internal logic. The transform() integration with
    # JSON extraction is already covered by test_transform_json_field_from_dataframe.

    def test_validate_labels_with_dict(self):
        """Test that labels can be provided as a dict."""
        field_config = {
            "source": "occurrences",
            "field": "test_field",
            "target": "test_target",
            "labels": {"1": "Label One", "2": "Label Two"},
        }
        validated = FieldConfig.model_validate(field_config)
        # Dict should be kept as is
        assert validated.labels == {"1": "Label One", "2": "Label Two"}

    def test_validate_config_error_handling(self):
        """Test validate_config error handling."""
        invalid_config = {
            "plugin": "wrong_plugin",  # Wrong plugin name
            "params": {
                "fields": [{"source": "test", "field": "test", "target": "test"}]
            },
        }
        with pytest.raises(ValueError, match="Invalid configuration"):
            self.plugin.validate_config(invalid_config)

    def test_get_field_from_table_json_field(self, mocker):
        """Test _get_field_from_table with JSON field access."""
        # Mock database fetch_one to return JSON data
        mock_row = {"extra_data": '{"taxon_type": "endemic"}'}
        mocker.patch.object(self.db_mock, "fetch_one", return_value=mock_row)

        result = self.plugin._get_field_from_table(
            "test_table", "extra_data.taxon_type", 123
        )

        assert result == "endemic"

    def test_get_field_from_table_json_field_invalid_json(self, mocker):
        """Test _get_field_from_table with invalid JSON data."""
        # Mock database to return invalid JSON
        mock_row = {"extra_data": "not valid json{"}
        mocker.patch.object(self.db_mock, "fetch_one", return_value=mock_row)

        result = self.plugin._get_field_from_table("test_table", "extra_data.key", 123)

        assert result is None

    def test_get_field_from_table_json_field_missing_key(self, mocker):
        """Test _get_field_from_table when JSON key doesn't exist."""
        # Mock database to return valid JSON but without the requested key
        mock_row = {"extra_data": '{"other_key": "value"}'}
        mocker.patch.object(self.db_mock, "fetch_one", return_value=mock_row)

        result = self.plugin._get_field_from_table(
            "test_table", "extra_data.missing_key", 123
        )

        assert result is None

    def test_get_field_from_table_json_field_null(self, mocker):
        """Test _get_field_from_table when JSON field is null."""
        mock_row = {"extra_data": None}
        mocker.patch.object(self.db_mock, "fetch_one", return_value=mock_row)

        result = self.plugin._get_field_from_table("test_table", "extra_data.key", 123)

        assert result is None

    def test_get_field_from_table_regular_field(self, mocker):
        """Test _get_field_from_table with regular field access."""
        mock_row = {"name": "Test Name"}
        mocker.patch.object(self.db_mock, "fetch_one", return_value=mock_row)

        result = self.plugin._get_field_from_table("test_table", "name", 123)

        assert result == "Test Name"

    def test_get_field_from_table_regular_field_null(self, mocker):
        """Test _get_field_from_table when regular field is null."""
        mock_row = {"name": None}
        mocker.patch.object(self.db_mock, "fetch_one", return_value=mock_row)

        result = self.plugin._get_field_from_table("test_table", "name", 123)

        assert result is None

    def test_get_field_from_table_error_handling(self, mocker):
        """Test _get_field_from_table error handling."""
        from niamoto.common.exceptions import DatabaseError

        # Mock database to raise an error
        mocker.patch.object(
            self.db_mock, "fetch_one", side_effect=Exception("DB Error")
        )

        with pytest.raises(DatabaseError, match="Error getting field"):
            self.plugin._get_field_from_table("test_table", "field", 123)

    def test_get_field_value_with_registry(self, mocker):
        """Test _get_field_value uses registry to resolve table name."""
        from types import SimpleNamespace

        # Mock registry to return entity info
        mock_entity = SimpleNamespace(table_name="resolved_table")
        mocker.patch.object(self.plugin.registry, "get", return_value=mock_entity)

        # Mock _get_field_from_table
        mocker.patch.object(self.plugin, "_get_field_from_table", return_value="value")

        result = self.plugin._get_field_value("entity_name", "field", 123)

        assert result == "value"
        self.plugin._get_field_from_table.assert_called_once_with(
            "resolved_table", "field", 123
        )

    def test_get_field_value_fallback_to_source(self, mocker):
        """Test _get_field_value falls back to using source as table name."""
        # Mock registry to return None (entity not found)
        mocker.patch.object(self.plugin.registry, "get", return_value=None)

        # Mock _get_field_from_table
        mocker.patch.object(self.plugin, "_get_field_from_table", return_value="value")

        result = self.plugin._get_field_value("direct_table", "field", 123)

        assert result == "value"
        self.plugin._get_field_from_table.assert_called_once_with(
            "direct_table", "field", 123
        )

    def test_get_field_value_error_handling(self, mocker):
        """Test _get_field_value error handling."""
        # Mock _get_field_from_table to raise an error
        mocker.patch.object(self.plugin.registry, "get", return_value=None)
        mocker.patch.object(
            self.plugin,
            "_get_field_from_table",
            side_effect=Exception("Field error"),
        )

        with pytest.raises(ValueError, match="Error getting field"):
            self.plugin._get_field_value("source", "field", 123)

    def test_transform_with_dict_sources(self):
        """Test transform with dict of multiple data sources."""
        # Create dict with multiple DataFrames
        data_sources = {
            "occurrences": SAMPLE_DATA.copy(),
            "plots": pd.DataFrame(
                {"plot_name": ["Plot A", "Plot B"], "area": [10, 20]}
            ),
        }

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "value_col1",
                        "target": "occ_value",
                        "transformation": "direct",
                    },
                    {
                        "source": "plots",
                        "field": "plot_name",
                        "target": "plot_name",
                        "transformation": "direct",
                    },
                ]
            },
        }

        result = self.plugin.transform(data_sources, config)

        assert result["occ_value"]["value"] == 10
        assert result["plot_name"]["value"] == "Plot A"

    def test_transform_dict_sources_with_main_fallback(self):
        """Test transform with dict sources using 'main' as fallback for 'occurrences'."""
        data_sources = {
            "main": SAMPLE_DATA.copy(),
        }

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "value_col1",
                        "target": "value",
                        "transformation": "direct",
                    }
                ]
            },
        }

        result = self.plugin.transform(data_sources, config)

        assert result["value"]["value"] == 10

    def test_transform_json_field_from_dataframe(self):
        """Test accessing JSON field from DataFrame."""

        # Create DataFrame with JSON column (one level deep)
        df = pd.DataFrame(
            {
                "id": [1],
                "json_data": ['{"key": "value123"}'],
            }
        )

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "json_data.key",
                        "target": "extracted",
                        "transformation": "direct",
                    }
                ]
            },
        }

        result = self.plugin.transform(df, config)

        assert result["extracted"]["value"] == "value123"

    def test_transform_json_field_from_dataframe_invalid_json(self):
        """Test JSON field extraction from DataFrame with invalid JSON."""
        df = pd.DataFrame(
            {
                "id": [1],
                "json_data": ["not valid json"],
            }
        )

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "json_data.key",
                        "target": "extracted",
                        "transformation": "direct",
                    }
                ]
            },
        }

        result = self.plugin.transform(df, config)

        assert result["extracted"]["value"] is None

    def test_transform_json_field_from_dataframe_non_dict(self):
        """Test JSON field extraction when JSON is not a dict."""
        df = pd.DataFrame(
            {
                "id": [1],
                "json_data": ['["array", "not", "dict"]'],
            }
        )

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "json_data.key",
                        "target": "extracted",
                        "transformation": "direct",
                    }
                ]
            },
        }

        result = self.plugin.transform(df, config)

        assert result["extracted"]["value"] is None

    def test_transform_with_key_error(self):
        """Test transform handles KeyError gracefully."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "nonexistent_field",
                        "target": "value",
                        "transformation": "direct",
                    }
                ]
            },
        }

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # Should return None for nonexistent field
        assert result["value"]["value"] is None

    def test_transform_boolean_value_handling(self):
        """Test transform handles boolean values correctly."""
        df = pd.DataFrame({"bool_field": [True], "bool_str": ["true"]})

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "bool_field",
                        "target": "bool_val",
                        "transformation": "direct",
                    },
                    {
                        "source": "occurrences",
                        "field": "bool_str",
                        "target": "bool_str_val",
                        "transformation": "direct",
                    },
                ]
            },
        }

        result = self.plugin.transform(df, config)

        # Boolean should be kept as boolean
        assert result["bool_val"]["value"] is True
        # String "true" should be converted to boolean
        assert result["bool_str_val"]["value"] is True

    def test_transform_boolean_false_string(self):
        """Test transform converts 'false' string to boolean."""
        df = pd.DataFrame({"bool_str": ["false"]})

        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "bool_str",
                        "target": "bool_val",
                        "transformation": "direct",
                    }
                ]
            },
        }

        result = self.plugin.transform(df, config)

        assert result["bool_val"]["value"] is False

    def test_transform_with_units_field(self):
        """Test that units are properly added to output."""
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "occurrences",
                        "field": "value_col1",
                        "target": "area",
                        "transformation": "direct",
                        "units": "hectares",
                    }
                ]
            },
        }

        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        assert "units" in result["area"]
        assert result["area"]["units"] == "hectares"
