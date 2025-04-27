# /Users/julienbarbe/Dev/Niamoto/Niamoto/tests/core/plugins/transformers/aggregation/test_binary_counter.py
import pytest
import pandas as pd
from unittest.mock import MagicMock

from niamoto.core.plugins.transformers.aggregation.binary_counter import BinaryCounter


@pytest.fixture
def binary_counter_plugin():
    """Fixture for BinaryCounter plugin instance."""
    # Mock database interaction if needed for specific tests
    return BinaryCounter(db=MagicMock())  # Assuming BasePlugin takes db object


class TestBinaryCounterValidation:
    """Tests for BinaryCounter configuration validation."""

    def test_validate_config_valid(self, binary_counter_plugin):
        """Test valid configuration."""
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "is_present",
                "true_label": "Present",
                "false_label": "Absent",
                "include_percentages": False,
            },
        }
        # Should not raise an error
        binary_counter_plugin.validate_config(config)

    def test_validate_config_missing_field(self, binary_counter_plugin):
        """Test configuration missing a required field."""
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                # "field": "is_present", # Missing field
                "true_label": "Present",
                "false_label": "Absent",
            },
        }
        with pytest.raises(ValueError, match="Missing required field: field"):
            binary_counter_plugin.validate_config(config)

    def test_validate_config_same_labels(self, binary_counter_plugin):
        """Test configuration with identical true and false labels."""
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "is_present",
                "true_label": "SameLabel",
                "false_label": "SameLabel",  # Identical labels
            },
        }
        with pytest.raises(
            ValueError, match="true_label and false_label must be different"
        ):
            binary_counter_plugin.validate_config(config)

    def test_validate_config_invalid_label_type(self, binary_counter_plugin):
        """Test configuration with non-string label type."""
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "is_present",
                "true_label": 123,  # Invalid type
                "false_label": "Absent",
            },
        }
        with pytest.raises(ValueError, match="true_label must be a string"):
            binary_counter_plugin.validate_config(config)

    # Add more validation tests as needed...


class TestBinaryCounterTransform:
    """Tests for BinaryCounter transform method."""

    def test_transform_basic(self, binary_counter_plugin):
        """Test basic transformation with default labels and no percentages."""
        data = pd.DataFrame({"binary_field": [1, 0, 1, 1, 0, 1]})
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",  # Use input data directly
                "field": "binary_field",
                "true_label": "oui",
                "false_label": "non",
                "include_percentages": False,
            },
        }
        expected_result = {"oui": 4, "non": 2}
        result = binary_counter_plugin.transform(data, config)
        assert result == expected_result

    def test_transform_custom_labels(self, binary_counter_plugin):
        """Test transformation with custom labels."""
        data = pd.DataFrame({"status": [1, 0, 0, 0]})
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "status",
                "true_label": "Active",
                "false_label": "Inactive",
                "include_percentages": False,
            },
        }
        expected_result = {"Active": 1, "Inactive": 3}
        result = binary_counter_plugin.transform(data, config)
        assert result == expected_result

    def test_transform_with_percentages(self, binary_counter_plugin):
        """Test transformation including percentages."""
        data = pd.DataFrame({"flag": [1, 0, 1, 1]})  # 3 True (75%), 1 False (25%)
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "flag",
                "true_label": "Yes",
                "false_label": "No",
                "include_percentages": True,
            },
        }
        expected_result = {
            "Yes": 3,
            "No": 1,
            "Yes_percent": 75.00,
            "No_percent": 25.00,
        }
        result = binary_counter_plugin.transform(data, config)
        assert result == expected_result

    def test_transform_ignore_non_binary(self, binary_counter_plugin):
        """Test transformation ignores values other than 0 and 1."""
        data = pd.DataFrame(
            {"values": [1, 0, 1, 2, -1, 0, None, 1]}
        )  # Expect 3 ones, 2 zeros
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "values",
                "true_label": "T",
                "false_label": "F",
                "include_percentages": False,
            },
        }
        expected_result = {"T": 3, "F": 2}
        result = binary_counter_plugin.transform(data, config)
        assert result == expected_result

    def test_transform_empty_input(self, binary_counter_plugin):
        """Test transformation with an empty input DataFrame."""
        data = pd.DataFrame({"empty_col": []})
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "empty_col",
                "true_label": "oui",
                "false_label": "non",
                "include_percentages": False,
            },
        }
        # Expect zero counts for both labels
        expected_result = {"oui": 0, "non": 0}
        result = binary_counter_plugin.transform(data, config)
        assert result == expected_result

    def test_transform_empty_after_filter(self, binary_counter_plugin):
        """Test transformation where all values are non-binary."""
        data = pd.DataFrame({"values": [2, 3, None, -5]})
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "values",
                "true_label": "oui",
                "false_label": "non",
                "include_percentages": True,  # Also test percentage with zero total
            },
        }
        expected_result = {
            "oui": 0,
            "non": 0,
            "oui_percent": 0,
            "non_percent": 0,
        }
        result = binary_counter_plugin.transform(data, config)
        assert result == expected_result

    def test_transform_with_db_source(self, binary_counter_plugin):
        """Test transformation loading data from a database source."""
        # Setup mock DB result
        mock_cursor = MagicMock()
        mock_cursor.description = [("db_field",)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1,),
            (0,),
            (1,),
            (0,),
            (1,),
        ]  # 3 ones, 2 zeros
        mock_result.cursor = mock_cursor
        # Configure the mock directly
        binary_counter_plugin.db.execute_select.return_value = mock_result

        # Input data is ignored when source is not 'occurrences'
        input_data = pd.DataFrame()
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "my_table",  # Load from this table
                "field": "db_field",
                "true_label": "Valid",
                "false_label": "Invalid",
            },
        }
        expected_result = {"Valid": 3, "Invalid": 2}

        # Use the plugin instance from the fixture
        result = binary_counter_plugin.transform(input_data, config)

        # Assert the mock was called correctly
        expected_sql = "SELECT * FROM my_table"
        binary_counter_plugin.db.execute_select.assert_called_once_with(expected_sql)
        assert result == expected_result

    def test_transform_invalid_config(self, binary_counter_plugin):
        """Test transform call with invalid configuration."""
        data = pd.DataFrame({"binary_field": [1, 0]})
        config = {
            "plugin": "binary_counter",
            "params": {
                "source": "occurrences",
                "field": "binary_field",
                "true_label": "Same",
                "false_label": "Same",  # Invalid: same labels
            },
        }
        # transform calls validate_config internally
        with pytest.raises(
            ValueError, match="true_label and false_label must be different"
        ):
            binary_counter_plugin.transform(data, config)

    # Add more transform tests: e.g., different data types for binary field,
    # field=None, percentage calculation edge cases (division by zero handled)
