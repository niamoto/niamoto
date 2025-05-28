import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

from niamoto.core.plugins.transformers.extraction.multi_column_extractor import (
    MultiColumnExtractor,
)


@pytest.fixture
def multi_column_extractor_plugin():
    """Fixture for MultiColumnExtractor plugin instance."""
    # Mock database interaction
    mock_db = MagicMock()

    # Mock Config to prevent creating config directory at project root
    with patch(
        "niamoto.core.plugins.transformers.extraction.multi_column_extractor.Config"
    ) as mock_config:
        mock_config.return_value.get_imports_config = {
            "test_csv": {"path": "data/test.csv", "type": "csv", "identifier": "id"}
        }
        mock_config.return_value.config_dir = "/mock/config"
        plugin = MultiColumnExtractor(db=mock_db)

    return plugin


class TestMultiColumnExtractorValidation:
    """Tests for MultiColumnExtractor configuration validation."""

    def test_validate_config_valid(self, multi_column_extractor_plugin):
        """Test valid configuration."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                "source": "table_name",
                "columns": ["col1", "col2", "col3"],
                "labels": ["Label 1", "Label 2", "Label 3"],
                "include_percentages": True,
            },
        }
        # Should not raise an error
        validated_config = multi_column_extractor_plugin.validate_config(config)
        assert validated_config["params"]["source"] == "table_name"
        assert validated_config["params"]["columns"] == ["col1", "col2", "col3"]

    def test_validate_config_missing_source(self, multi_column_extractor_plugin):
        """Test configuration missing source field."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                # "source": "table_name", # Missing source
                "columns": ["col1", "col2"],
            },
        }
        with pytest.raises(ValueError, match="Missing required field: source"):
            multi_column_extractor_plugin.validate_config(config)

    def test_validate_config_missing_columns(self, multi_column_extractor_plugin):
        """Test configuration missing columns field."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                "source": "table_name",
                # "columns": ["col1", "col2"], # Missing columns
            },
        }
        with pytest.raises(ValueError, match="Missing required field: columns"):
            multi_column_extractor_plugin.validate_config(config)

    def test_validate_config_invalid_source_type(self, multi_column_extractor_plugin):
        """Test configuration with invalid source type."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                "source": 123,  # Invalid source type
                "columns": ["col1", "col2"],
            },
        }
        with pytest.raises(ValueError, match="source must be a string"):
            multi_column_extractor_plugin.validate_config(config)

    def test_validate_config_invalid_columns_type(self, multi_column_extractor_plugin):
        """Test configuration with invalid columns type."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                "source": "table_name",
                "columns": "col1, col2",  # Invalid columns type
            },
        }
        with pytest.raises(ValueError, match="columns must be a list"):
            multi_column_extractor_plugin.validate_config(config)

    def test_validate_config_invalid_labels_type(self, multi_column_extractor_plugin):
        """Test configuration with invalid labels type."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                "source": "table_name",
                "columns": ["col1", "col2"],
                "labels": "Label 1, Label 2",  # Invalid labels type
            },
        }
        with pytest.raises(ValueError, match="labels must be a list"):
            multi_column_extractor_plugin.validate_config(config)

    def test_validate_config_mismatched_labels_columns(
        self, multi_column_extractor_plugin
    ):
        """Test configuration with mismatched number of labels and columns."""
        config = {
            "plugin": "multi_column_extractor",
            "params": {
                "source": "table_name",
                "columns": ["col1", "col2", "col3"],
                "labels": ["Label 1", "Label 2"],  # Fewer labels than columns
            },
        }
        with pytest.raises(
            ValueError, match="number of labels must be equal to number of columns"
        ):
            multi_column_extractor_plugin.validate_config(config)


class TestMultiColumnExtractorTransform:
    """Tests for MultiColumnExtractor transform method."""

    def test_transform_basic(self, multi_column_extractor_plugin):
        """Test basic transformation with column values."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {"id": [1], "col1": [10], "col2": [20], "col3": [30]}
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2", "col3"],
                    "labels": ["Label 1", "Label 2", "Label 3"],
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results
            assert result["labels"] == ["Label 1", "Label 2", "Label 3"]
            assert result["counts"] == [10, 20, 30]

    def test_transform_with_percentages(self, multi_column_extractor_plugin):
        """Test transformation with percentages calculation."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {"id": [1], "col1": [50], "col2": [30], "col3": [20]}
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2", "col3"],
                    "include_percentages": True,
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results
            assert result["counts"] == [50, 30, 20]
            assert result["percentages"] == [50.0, 30.0, 20.0]

    def test_transform_with_derived_columns(self, multi_column_extractor_plugin):
        """Test transformation with derived columns calculation."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {
                "id": [1],
                "col1": [10],
                "col2": [20],
            }
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2", "derived_col"],
                    "derived_columns": [
                        {
                            "name": "derived_col",
                            "formula": "col1 + col2",
                        }
                    ],
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results
            assert result["counts"] == [10, 20, 30]  # 30 is the derived value (10 + 20)

    def test_transform_with_named_fields(self, multi_column_extractor_plugin):
        """Test transformation with named fields."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {
                "id": [1],
                "col1": [10],
                "col2": [20],
            }
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2"],
                    "labels": ["Label 1", "Label 2"],
                    "create_named_fields": True,
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results
            assert "label_1" in result
            assert "label_2" in result
            assert result["label_1"]["value"] == 10
            assert result["label_2"]["value"] == 20

    def test_transform_with_custom_field_names(self, multi_column_extractor_plugin):
        """Test transformation with custom field names."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {
                "id": [1],
                "col1": [10],
                "col2": [20],
            }
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2"],
                    "create_named_fields": True,
                    "field_names": ["custom_field1", "custom_field2"],
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results
            assert "custom_field1" in result
            assert "custom_field2" in result
            assert result["custom_field1"]["value"] == 10
            assert result["custom_field2"]["value"] == 20

    def test_transform_missing_column(self, multi_column_extractor_plugin):
        """Test transformation with a column that doesn't exist in the data."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {
                "id": [1],
                "col1": [10],
                # col2 is missing
            }
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2"],
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results - missing column should have value 0
            assert result["counts"] == [10, 0]

    def test_transform_empty_data(self, multi_column_extractor_plugin):
        """Test transformation with empty source data."""
        # Mock input data
        data = pd.DataFrame()

        # Mock empty source data
        source_data = pd.DataFrame()

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2", "col3"],
                    "labels": ["Label 1", "Label 2", "Label 3"],
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results - should return zeros for all columns
            assert result["labels"] == ["Label 1", "Label 2", "Label 3"]
            assert result["counts"] == [0, 0, 0]

    def test_transform_null_values(self, multi_column_extractor_plugin):
        """Test transformation with null values in the data."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data with NaN values
        source_data = pd.DataFrame(
            {
                "id": [1],
                "col1": [10],
                "col2": [np.nan],
                "col3": [30],
            }
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2", "col3"],
                },
            }

            result = multi_column_extractor_plugin.transform(data, config)

            # Check results - NaN value should be converted to 0
            assert result["counts"] == [10, 0, 30]


class TestMultiColumnExtractorErrors:
    """Tests for error handling in MultiColumnExtractor."""

    def test_invalid_formula_in_derived_column(self, multi_column_extractor_plugin):
        """Test error handling with invalid formula in derived column."""
        # Mock input data
        data = pd.DataFrame()

        # Mock source data
        source_data = pd.DataFrame(
            {
                "id": [1],
                "col1": [10],
                "col2": [20],
            }
        )

        # Mock the get_data_from_source method
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            return_value=source_data,
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "test_table",
                    "columns": ["col1", "col2", "derived_col"],
                    "derived_columns": [
                        {
                            "name": "derived_col",
                            "formula": "col1 / 0",  # Division by zero
                        }
                    ],
                },
            }

            with pytest.raises(ValueError, match="Error evaluating formula"):
                multi_column_extractor_plugin.transform(data, config)

    def test_source_not_found(self, multi_column_extractor_plugin):
        """Test error handling when source data can't be loaded."""
        # Mock input data
        data = pd.DataFrame()

        # Mock the get_data_from_source method to raise an error
        with patch.object(
            multi_column_extractor_plugin,
            "_get_data_from_source",
            side_effect=ValueError("Source not found"),
        ):
            config = {
                "plugin": "multi_column_extractor",
                "params": {
                    "source": "nonexistent_table",
                    "columns": ["col1", "col2"],
                },
            }

            with pytest.raises(ValueError, match="Error transforming data"):
                multi_column_extractor_plugin.transform(data, config)
