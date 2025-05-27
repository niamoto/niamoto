"""Tests for the generic top_ranking plugin."""

import pytest
import pandas as pd
from unittest.mock import MagicMock

from niamoto.core.plugins.transformers.aggregation.top_ranking import TopRanking


class TestTopRankingGeneric:
    """Test the generic top_ranking plugin."""

    def setup_method(self):
        """Set up test environment."""
        self.mock_db = MagicMock()
        self.plugin = TopRanking(self.mock_db)

    def test_direct_mode(self):
        """Test direct mode counting."""
        data = pd.DataFrame(
            {
                "category": ["A", "B", "A", "C", "B", "A", "D", "B"],
                "value": [1, 2, 3, 4, 5, 6, 7, 8],
            }
        )

        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "data",
                "field": "category",
                "count": 3,
                "mode": "direct",
            },
        }

        result = self.plugin.transform(data, config)

        assert result["tops"] == ["A", "B", "C"]
        assert result["counts"] == [3, 3, 1]

    def test_hierarchical_mode_with_custom_columns(self):
        """Test hierarchical mode with custom column names."""
        data = pd.DataFrame({"item_id": [10, 20, 30, 40, 10, 20]})

        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "items",
                "field": "item_id",
                "count": 2,
                "mode": "hierarchical",
                "hierarchy_table": "custom_hierarchy",
                "hierarchy_columns": {
                    "id": "item_id",
                    "name": "item_name",
                    "rank": "item_rank",
                    "parent_id": "parent_item_id",
                },
                "target_ranks": ["category"],
            },
        }

        # Mock database responses
        self.mock_db.execute_select.side_effect = [
            # First query: get initial items
            MagicMock(
                fetchall=lambda: [
                    (10, "Item A", "item", 100),
                    (20, "Item B", "item", 100),
                    (30, "Item C", "item", 200),
                    (40, "Item D", "item", 200),
                ]
            ),
            # Second query: get parents
            MagicMock(
                fetchall=lambda: [
                    (100, "Category 1", "category", None),
                    (200, "Category 2", "category", None),
                ]
            ),
        ]

        result = self.plugin.transform(data, config)

        assert result["tops"] == ["Category 1", "Category 2"]
        assert result["counts"] == [4, 2]

    def test_join_mode(self):
        """Test join mode with custom configuration."""
        data = pd.DataFrame({"location_id": [1, 2, 1, 2]})

        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "locations",
                "field": "location_id",
                "count": 2,
                "mode": "join",
                "join_table": "observations",
                "join_columns": {
                    "source_id": "location_id",
                    "hierarchy_id": "species_id",
                },
                "hierarchy_table": "species",
                "hierarchy_columns": {
                    "id": "species_id",
                    "name": "species_name",
                    "rank": "taxonomic_rank",
                    "left": "lft_bound",
                    "right": "rght_bound",
                },
                "target_ranks": ["family"],
                "aggregate_function": "count",
            },
        }

        # Mock database response
        self.mock_db.execute_select.return_value = MagicMock(
            fetchall=lambda: [("Family A", 25), ("Family B", 15)]
        )

        result = self.plugin.transform(data, config)

        assert result["tops"] == ["Family A", "Family B"]
        assert result["counts"] == [25, 15]

    def test_backward_compatibility_auto_mode_detection(self):
        """Test that old configurations still work via auto mode detection."""
        data = pd.DataFrame({"taxon_ref_id": [1, 2, 3, 1, 2]})

        # Old-style config without mode
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "occurrences",
                "field": "taxon_ref_id",
                "target_ranks": ["family"],
                "count": 2,
            },
        }

        # Mock database responses
        self.mock_db.execute_select.side_effect = [
            # First query
            MagicMock(
                fetchall=lambda: [
                    (1, "Species A", "species", 10),
                    (2, "Species B", "species", 10),
                    (3, "Species C", "species", 20),
                ]
            ),
            # Second query
            MagicMock(
                fetchall=lambda: [
                    (10, "Family 1", "family", None),
                    (20, "Family 2", "family", None),
                ]
            ),
        ]

        result = self.plugin.transform(data, config)

        # Should auto-detect hierarchical mode and use taxon_ref table
        assert "tops" in result
        assert "counts" in result

    def test_empty_data_returns_empty_result(self):
        """Test that empty data returns empty results."""
        data = pd.DataFrame({"field": []})

        config = {
            "plugin": "top_ranking",
            "params": {"source": "data", "field": "field", "mode": "direct"},
        }

        result = self.plugin.transform(data, config)

        assert result == {"tops": [], "counts": []}

    def test_missing_field_returns_empty_result(self):
        """Test that missing field returns empty results."""
        data = pd.DataFrame({"other_field": [1, 2, 3]})

        config = {
            "plugin": "top_ranking",
            "params": {"source": "data", "field": "missing_field", "mode": "direct"},
        }

        result = self.plugin.transform(data, config)

        assert result == {"tops": [], "counts": []}

    def test_default_aggregate_function(self):
        """Test that default aggregate function is count."""
        config = {
            "plugin": "top_ranking",
            "params": {"source": "data", "field": "field"},
        }

        validated = self.plugin.validate_config(config)

        assert validated["params"]["aggregate_function"] == "count"
        assert validated["params"]["mode"] == "direct"

    def test_hierarchical_mode_missing_config(self):
        """Test error when hierarchical mode lacks required config."""
        config = {
            "plugin": "top_ranking",
            "params": {
                "source": "data",
                "field": "field",
                "mode": "hierarchical",
                # Missing hierarchy_table and target_ranks
            },
        }

        with pytest.raises(ValueError, match="hierarchy_table is required"):
            self.plugin.validate_config(config)
