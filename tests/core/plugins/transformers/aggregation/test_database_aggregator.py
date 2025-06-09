"""
Tests for the database aggregator plugin.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError

from niamoto.core.plugins.transformers.aggregation.database_aggregator import (
    DatabaseAggregatorPlugin,
    QueryConfig,
    ComputedFieldConfig,
    DatabaseAggregatorConfig,
)
from niamoto.common.exceptions import DataValidationError


class TestDatabaseAggregatorPlugin:
    """Test cases for DatabaseAggregatorPlugin."""

    def setup_method(self):
        """Setup test fixtures."""
        self.plugin = DatabaseAggregatorPlugin()
        self.plugin.db = Mock()
        # Set up context manager for database session
        self.mock_session = Mock()
        self.plugin.db.get_session.return_value.__enter__ = Mock(
            return_value=self.mock_session
        )
        self.plugin.db.get_session.return_value.__exit__ = Mock(return_value=None)

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = {
            "plugin": "database_aggregator",
            "params": {
                "queries": {
                    "simple_query": "SELECT COUNT(*) FROM taxon_ref",
                    "complex_query": {
                        "sql": "SELECT * FROM occurrences LIMIT 10",
                        "format": "table",
                        "description": "Test query",
                    },
                }
            },
        }

        validated_config = DatabaseAggregatorConfig(**config)
        assert validated_config.plugin == "database_aggregator"
        assert "simple_query" in validated_config.params["queries"]

    def test_config_validation_invalid_format(self):
        """Test config validation with invalid format."""
        config = {
            "plugin": "database_aggregator",
            "params": {
                "queries": {
                    "bad_query": {"sql": "SELECT 1", "format": "invalid_format"}
                }
            },
        }

        with pytest.raises(ValueError):
            DatabaseAggregatorConfig(**config)

    def test_sql_security_validation(self):
        """Test SQL security validation."""
        plugin = DatabaseAggregatorPlugin()

        # Valid SELECT query
        valid_sql = "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'"
        assert plugin._validate_sql_security(valid_sql) == valid_sql

        # Invalid queries (should raise ValueError)
        invalid_queries = [
            "DROP TABLE taxon_ref",
            "DELETE FROM occurrences",
            "INSERT INTO taxon_ref VALUES (1, 'test')",
            "UPDATE taxon_ref SET name = 'test'",
            "SELECT * FROM taxon_ref; DROP TABLE occurrences;",
            "SELECT * FROM taxon_ref -- comment",
            "EXEC sp_some_procedure",
        ]

        for invalid_sql in invalid_queries:
            with pytest.raises(ValueError):
                plugin._validate_sql_security(invalid_sql)

    def test_execute_query_scalar(self):
        """Test executing query with scalar result."""
        plugin = self.plugin

        # Mock database session
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        self.mock_session.execute.return_value = mock_result

        result = plugin._execute_query("SELECT COUNT(*) FROM taxon_ref")

        assert result == 42
        self.mock_session.execute.assert_called()

    def test_execute_query_table(self):
        """Test executing query with table result."""
        plugin = self.plugin

        # Mock database session
        mock_result = Mock()

        # Create mock rows
        mock_row1 = Mock()
        mock_row1._mapping = {"name": "Species A", "count": 10}
        mock_row1.__iter__ = lambda self: iter(["Species A", 10])
        mock_row2 = Mock()
        mock_row2._mapping = {"name": "Species B", "count": 5}
        mock_row2.__iter__ = lambda self: iter(["Species B", 5])

        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        self.mock_session.execute.return_value = mock_result

        result = plugin._execute_query(
            "SELECT name, count FROM species_summary", format_type="table"
        )

        expected = [
            {"name": "Species A", "count": 10},
            {"name": "Species B", "count": 5},
        ]
        assert result == expected

    def test_execute_query_sql_error(self):
        """Test SQL execution error handling."""
        plugin = self.plugin

        # Mock database session that raises an error
        self.mock_session.execute.side_effect = SQLAlchemyError("Table not found")

        with pytest.raises(DataValidationError):
            plugin._execute_query("SELECT * FROM nonexistent_table")

    def test_execute_template(self):
        """Test template-based query execution."""
        plugin = DatabaseAggregatorPlugin()

        # Mock successful query execution
        plugin._execute_query = Mock(return_value=[{"field": "species", "count": 100}])

        query_config = QueryConfig(
            template="count_by_field",
            template_params={"field": "rank_name", "table": "taxon_ref", "limit": "10"},
            format="table",
        )

        templates = {
            "count_by_field": {
                "sql": "SELECT {field}, COUNT(*) as count FROM {table} GROUP BY {field} LIMIT {limit}",
                "params": ["field", "table", "limit"],
            }
        }

        result = plugin._execute_template(query_config, templates)

        assert result == [{"field": "species", "count": 100}]
        plugin._execute_query.assert_called_once()

    def test_execute_template_missing_params(self):
        """Test template execution with missing parameters."""
        plugin = DatabaseAggregatorPlugin()

        query_config = QueryConfig(
            template="count_by_field",
            template_params={"field": "rank_name"},  # Missing table and limit
            format="table",
        )

        templates = {
            "count_by_field": {
                "sql": "SELECT {field}, COUNT(*) as count FROM {table} GROUP BY {field} LIMIT {limit}",
                "params": ["field", "table", "limit"],
            }
        }

        with pytest.raises(ValueError, match="Missing template parameters"):
            plugin._execute_template(query_config, templates)

    def test_calculate_computed_field(self):
        """Test computed field calculation."""
        plugin = DatabaseAggregatorPlugin()

        field_config = ComputedFieldConfig(
            expression="(endemic_count * 100.0) / total_count",
            dependencies=["endemic_count", "total_count"],
        )

        results = {"endemic_count": 78, "total_count": 100}

        result = plugin._calculate_computed_field(field_config, results)
        assert result == 78.0

    def test_calculate_computed_field_with_functions(self):
        """Test computed field with mathematical functions."""
        plugin = DatabaseAggregatorPlugin()

        field_config = ComputedFieldConfig(
            expression="round(sqrt(area), 2)", dependencies=["area"]
        )

        results = {"area": 100}

        result = plugin._calculate_computed_field(field_config, results)
        assert result == 10.0

    def test_calculate_computed_field_missing_dependency(self):
        """Test computed field with missing dependency."""
        plugin = DatabaseAggregatorPlugin()

        field_config = ComputedFieldConfig(expression="a + b", dependencies=["a", "b"])

        results = {"a": 10}  # Missing 'b'

        with pytest.raises(ValueError, match="Missing dependencies"):
            plugin._calculate_computed_field(field_config, results)

    def test_calculate_computed_field_invalid_expression(self):
        """Test computed field with invalid expression."""
        plugin = DatabaseAggregatorPlugin()

        field_config = ComputedFieldConfig(
            expression="invalid_function(x)", dependencies=["x"]
        )

        results = {"x": 10}

        with pytest.raises(DataValidationError):
            plugin._calculate_computed_field(field_config, results)

    def test_transform_complete_workflow(self):
        """Test complete transformation workflow."""
        plugin = self.plugin

        # Mock query results
        def mock_execute(query):
            mock_result = Mock()
            if "COUNT(*) FROM taxon_ref" in str(query):
                mock_result.scalar.return_value = 100
            elif "COUNT(*) FROM occurrences" in str(query):
                mock_result.scalar.return_value = 5000
            return mock_result

        self.mock_session.execute.side_effect = mock_execute

        config = {
            "plugin": "database_aggregator",
            "params": {
                "queries": {
                    "species_count": "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'",
                    "occurrence_count": "SELECT COUNT(*) FROM occurrences",
                },
                "computed_fields": {
                    "avg_occurrences_per_species": {
                        "expression": "occurrence_count / species_count if species_count > 0 else 0",
                        "dependencies": ["occurrence_count", "species_count"],
                    }
                },
            },
        }

        result = plugin.transform(None, config)

        assert result["species_count"] == 100
        assert result["occurrence_count"] == 5000
        assert result["avg_occurrences_per_species"] == 50.0
        assert "_metadata" in result
        assert result["_metadata"]["plugin"] == "database_aggregator"

    def test_get_example_config(self):
        """Test example configuration generation."""
        config = DatabaseAggregatorPlugin.get_example_config()

        assert config["plugin"] == "database_aggregator"
        assert "queries" in config["params"]
        assert "templates" in config["params"]
        assert "computed_fields" in config["params"]
        assert "validation" in config["params"]

    @patch("niamoto.core.plugins.transformers.aggregation.database_aggregator.logging")
    def test_logging(self, mock_logging):
        """Test logging functionality."""
        plugin = self.plugin

        # Mock database session
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        self.mock_session.execute.return_value = mock_result

        config = {
            "plugin": "database_aggregator",
            "params": {"queries": {"test_query": "SELECT COUNT(*) FROM taxon_ref"}},
        }

        # Mock the logger
        plugin.logger = Mock()

        plugin.transform(None, config)

        # Verify logging was called
        plugin.logger.info.assert_called()
