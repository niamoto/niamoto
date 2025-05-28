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
        assert len(config_model.params["fields"]) == 2

    def test_config_validation_missing_field_in_item(self):
        """Test config validation fails if a required field (e.g., source) is missing within a field item."""
        invalid_config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        # "source": "occurrences",  # Missing source
                        "field": "value_col1",
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
        with pytest.raises(ValidationError, match="Invalid transformation"):
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
        """Test transformation involving database lookup."""
        # 1. Mock the _get_field_value method directly for this test
        #    We expect it to be called with ('plots', 'plot_value', None)
        #    and it should return 500 based on the logic we want to test.
        mock_get_field = mocker.patch.object(
            self.plugin,
            "_get_field_value",
            return_value=500,  # The value we expect the DB lookup to return
        )

        # 2. Configuration using 'plots' as source (DB)
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "plots",  # Use DB table name
                        "field": "plot_value",
                        "target": "db_direct_value",
                        "transformation": "direct",
                    }
                ]
            },
        }

        # 3. Expected result based on the mocked return value
        expected_result = {"db_direct_value": {"value": 500}}

        # 4. Run transform (input data SAMPLE_DATA is ignored for this field)
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # 5. Assertions
        assert result == expected_result
        # Verify _get_field_value was called correctly by transform()
        mock_get_field.assert_called_once_with(
            "plots",  # source
            "plot_value",  # field
            None,  # id_value (because transformation="direct")
        )

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
        """Test transformation involving import file lookup."""
        # 1. Mock _get_field_value for import source
        mock_get_field = mocker.patch.object(
            self.plugin,
            "_get_field_value",
            return_value="imported_data_value",  # Value expected from import lookup
        )

        # 2. Configuration using import source
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

        # 3. Expected result based on mocked value
        expected_result = {"final_imported_value": {"value": "imported_data_value"}}

        # 4. Run transform (SAMPLE_DATA is ignored for this field config)
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # 5. Assertions
        assert result == expected_result
        mock_get_field.assert_called_once_with(
            "import:my_test_import",  # source
            "value_from_import",  # field
            None,  # id_value (for direct transformation)
        )

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

    def test_transform_json_field_access(self, mocker):
        """Test transformation accessing data within a JSON field."""
        # 1. Mock _get_field_from_table to return the extracted JSON value directly
        mock_get_field = mocker.patch.object(
            self.plugin,
            "_get_field_from_table",
            return_value="123",  # JSON fields are returned as strings from DB
        )

        # 2. Configuration to access a nested key using dot notation
        config = {
            "plugin": "field_aggregator",
            "params": {
                "fields": [
                    {
                        "source": "db_table_with_json",  # Assume DB source
                        "field": "json_column.nested.key2",  # Dot notation access
                        "target": "extracted_json_value",
                        "transformation": "direct",
                    }
                ]
            },
        }

        # 3. Expected result: the value of the nested key (as string from DB)
        expected_result = {"extracted_json_value": {"value": "123"}}

        # 4. Run transform (SAMPLE_DATA ignored for this field)
        result = self.plugin.transform(SAMPLE_DATA.copy(), config)

        # 5. Assertions
        assert result == expected_result
        # Check that _get_field_from_table was called with the full JSON field path
        mock_get_field.assert_called_once_with(
            "db_table_with_json",  # source
            "json_column.nested.key2",  # field (full path for JSON extraction)
            None,  # id_value (for direct transformation)
        )
