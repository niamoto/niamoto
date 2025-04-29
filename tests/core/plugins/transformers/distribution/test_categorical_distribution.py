import pytest
import pandas as pd
from unittest.mock import MagicMock

from niamoto.core.plugins.transformers.distribution.categorical_distribution import (
    CategoricalDistribution,
    CategoricalDistributionConfig,
)


class TestCategoricalDistribution:
    """Tests for the CategoricalDistribution plugin."""

    @pytest.fixture(autouse=True)
    def setup_plugin(self):
        """Initialize the plugin for each test."""
        # Pass the mock db object during instantiation
        self.plugin = CategoricalDistribution(db=MagicMock())
        # No longer need to assign db separately
        # self.plugin.db = MagicMock()

    # --- Configuration Validation Tests --- #

    def test_valid_config_minimal(self):
        """Test minimal valid configuration."""
        config = {"params": {"source": "occurrences", "field": "category_col"}}
        validated = self.plugin.validate_config(config)
        assert validated["params"]["source"] == "occurrences"
        assert validated["params"]["field"] == "category_col"
        # Use .get() to safely check for default values
        assert validated["params"].get("categories", []) == []
        assert validated["params"].get("labels", []) == []
        assert not validated["params"].get("include_percentages", False)

    def test_valid_config_full(self):
        """Test full valid configuration."""
        config = {
            "params": {
                "source": "my_table",
                "field": "status",
                "categories": ["A", "B", "C"],
                "labels": ["Alpha", "Beta", "Charlie"],
                "include_percentages": True,
            }
        }
        validated = self.plugin.validate_config(config)
        assert validated["params"]["source"] == "my_table"
        assert validated["params"]["field"] == "status"
        assert validated["params"]["categories"] == ["A", "B", "C"]
        assert validated["params"]["labels"] == ["Alpha", "Beta", "Charlie"]
        assert validated["params"]["include_percentages"]

    def test_invalid_config_missing_field(self):
        """Test config validation fails with missing required field."""
        config = {"params": {"source": "occurrences"}}  # Missing 'field'
        with pytest.raises(ValueError, match="Missing required field: field"):
            CategoricalDistributionConfig(**config)  # Test Pydantic validation directly

    def test_invalid_config_missing_source(self):
        """Test config validation fails with missing required source."""
        config = {"params": {"field": "category_col"}}  # Missing 'source'
        with pytest.raises(ValueError, match="Missing required field: source"):
            CategoricalDistributionConfig(**config)

    def test_invalid_config_categories_not_list(self):
        """Test config validation fails if categories is not a list."""
        config = {
            "params": {"source": "occurrences", "field": "col", "categories": "A"}
        }
        with pytest.raises(ValueError, match="categories must be a list"):
            CategoricalDistributionConfig(**config)

    def test_invalid_config_labels_not_list(self):
        """Test config validation fails if labels is not a list."""
        config = {"params": {"source": "occurrences", "field": "col", "labels": "L1"}}
        with pytest.raises(ValueError, match="labels must be a list"):
            CategoricalDistributionConfig(**config)

    def test_invalid_config_mismatched_labels_categories(self):
        """Test config validation fails if labels/categories count mismatch."""
        config = {
            "params": {
                "source": "occurrences",
                "field": "col",
                "categories": ["A", "B"],
                "labels": ["L1"],
            }
        }
        with pytest.raises(ValueError, match="number of labels must be equal"):
            CategoricalDistributionConfig(**config)

    # --- Transformation Logic Tests --- #

    def test_transform_basic(self):
        """Test basic transformation deriving categories."""
        data = pd.DataFrame({"category": ["A", "B", "A", "C", "B", "A"]})
        config = {"params": {"source": "occurrences", "field": "category"}}
        result = self.plugin.transform(data, config)
        expected = {
            "categories": ["A", "B", "C"],  # Auto-sorted
            "counts": [3, 2, 1],
            "labels": ["A", "B", "C"],
        }
        assert result == expected

    def test_transform_with_percentages(self):
        """Test transformation including percentages."""
        data = pd.DataFrame({"category": ["X", "Y", "X", "X"]})
        config = {
            "params": {
                "source": "occurrences",
                "field": "category",
                "include_percentages": True,
            }
        }
        result = self.plugin.transform(data, config)
        expected = {
            "categories": ["X", "Y"],  # Auto-sorted
            "counts": [3, 1],
            "labels": ["X", "Y"],
            "percentages": [75.0, 25.0],
        }
        assert result == expected

    def test_transform_with_explicit_categories_and_labels(self):
        """Test transformation with explicit categories and labels."""
        data = pd.DataFrame({"status": [1, 2, 1, 3, 1, 4]})  # 4 is not in categories
        config = {
            "params": {
                "source": "occurrences",
                "field": "status",
                "categories": [1, 2, 3],
                "labels": ["Low", "Medium", "High"],
                "include_percentages": False,
            }
        }
        result = self.plugin.transform(data, config)
        expected = {
            "categories": [1, 2, 3],
            "counts": [3, 1, 1],  # Count for 4 is ignored
            "labels": ["Low", "Medium", "High"],
        }
        assert result == expected

    def test_transform_with_nan(self):
        """Test transformation ignores NaN values."""
        data = pd.DataFrame({"category": ["A", None, "B", "A", None]})
        config = {"params": {"source": "occurrences", "field": "category"}}
        result = self.plugin.transform(data, config)
        expected = {
            "categories": ["A", "B"],
            "counts": [2, 1],
            "labels": ["A", "B"],
        }
        assert result == expected

    def test_transform_empty_data(self):
        """Test transformation with empty input DataFrame."""
        data = pd.DataFrame({"category": []}, dtype=str)
        config = {
            "params": {
                "source": "occurrences",
                "field": "category",
                "categories": ["X", "Y"],  # Explicit categories needed for empty
                "labels": ["LabelX", "LabelY"],
                "include_percentages": True,
            }
        }
        result = self.plugin.transform(data, config)
        expected = {
            "categories": ["X", "Y"],
            "counts": [0, 0],
            "labels": ["LabelX", "LabelY"],
            "percentages": [0, 0],
        }
        assert result == expected

    def test_transform_empty_after_nan(self):
        """Test transformation when data becomes empty after removing NaN."""
        data = pd.DataFrame({"category": [None, None]}, dtype=str)
        config = {
            "params": {
                "source": "occurrences",
                "field": "category",
                "categories": ["Z"],  # Explicit category
                "labels": ["LabelZ"],
            }
        }
        result = self.plugin.transform(data, config)
        expected = {
            "categories": ["Z"],
            "counts": [0],
            "labels": ["LabelZ"],
        }
        assert result == expected

    # TODO: Add test for source != 'occurrences' if needed, requires more DB mocking
    # TODO: Add test for general transformation error
