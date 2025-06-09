"""
Database Aggregator Plugin

This plugin allows executing SQL queries directly against the Niamoto database
for complex aggregations and site-wide statistics that don't fit the standard
group-by transformation patterns.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, field_validator

from niamoto.core.plugins.base import TransformerPlugin, PluginType, register
from niamoto.core.plugins.models import PluginConfig
from niamoto.common.exceptions import DataValidationError


class QueryConfig(BaseModel):
    """Configuration for a single query."""

    sql: Optional[str] = None
    template: Optional[str] = None
    template_params: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    format: str = Field(default="scalar", pattern="^(scalar|table|series|single_row)$")
    timeout: int = Field(default=30, ge=1, le=300)


class TemplateConfig(BaseModel):
    """Configuration for query templates."""

    sql: str
    params: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class ComputedFieldConfig(BaseModel):
    """Configuration for computed fields."""

    expression: str
    dependencies: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class DatabaseAggregatorConfig(PluginConfig):
    """Configuration schema for database aggregator plugin."""

    plugin: str = "database_aggregator"
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "queries": {},
            "templates": {},
            "computed_fields": {},
            "validation": {
                "check_referential_integrity": True,
                "max_execution_time": 30,
                "required_tables": [],
            },
        }
    )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters structure."""
        queries = v.get("queries", {})
        templates = v.get("templates", {})
        computed_fields = v.get("computed_fields", {})

        # Validate queries
        for query_name, query_config in queries.items():
            if isinstance(query_config, str):
                # Convert simple string to QueryConfig
                queries[query_name] = {"sql": query_config}
            elif isinstance(query_config, dict):
                QueryConfig(**query_config)

        # Validate templates
        for template_name, template_config in templates.items():
            TemplateConfig(**template_config)

        # Validate computed fields
        for field_name, field_config in computed_fields.items():
            ComputedFieldConfig(**field_config)

        return v


@register("database_aggregator", PluginType.TRANSFORMER)
class DatabaseAggregatorPlugin(TransformerPlugin):
    """
    Execute SQL queries for cross-cutting data aggregation.

    This plugin enables direct SQL access for complex queries that span
    multiple tables or require site-wide aggregations.
    """

    config_model = DatabaseAggregatorConfig

    # SQL patterns that are not allowed for security
    FORBIDDEN_PATTERNS = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bTRUNCATE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
        r"\bEXEC\b",
        r"\bEXECUTE\b",
        r"--",  # SQL comments
        r"/\*",  # Block comments
    ]

    def __init__(self, db: Optional[Any] = None) -> None:
        super().__init__(db)
        self.logger = logging.getLogger(__name__)

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration."""
        try:
            return self.config_model(**config).model_dump()
        except Exception as e:
            raise ValueError(f"Invalid configuration: {str(e)}") from e

    def transform(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[override]
        """Execute configured SQL queries and return aggregated results."""
        validated_config = self.validate_config(config)
        params = validated_config["params"]

        results = {}
        queries = params.get("queries", {})
        templates = params.get("templates", {})
        computed_fields = params.get("computed_fields", {})
        validation_config = params.get("validation", {})

        # Validate environment
        if validation_config.get("check_referential_integrity", True):
            self._validate_database_state(validation_config)

        try:
            # Execute direct SQL queries
            for key, query_config in queries.items():
                self.logger.info(f"Executing query: {key}")

                if isinstance(query_config, str):
                    # Simple SQL string
                    results[key] = self._execute_query(query_config)
                elif isinstance(query_config, dict):
                    query_obj = QueryConfig(**query_config)

                    if query_obj.sql:
                        # Direct SQL query
                        results[key] = self._execute_query(
                            query_obj.sql,
                            description=query_obj.description,
                            format_type=query_obj.format,
                            timeout=query_obj.timeout,
                        )
                    elif query_obj.template:
                        # Template-based query
                        results[key] = self._execute_template(query_obj, templates)
                    else:
                        raise ValueError(
                            f"Query '{key}' must have either 'sql' or 'template'"
                        )

            # Calculate computed fields
            for field_name, field_config in computed_fields.items():
                self.logger.info(f"Computing field: {field_name}")
                computed_config = ComputedFieldConfig(**field_config)
                results[field_name] = self._calculate_computed_field(
                    computed_config, results
                )

            # Add metadata
            results["_metadata"] = {
                "computed_at": datetime.utcnow().isoformat(),
                "plugin": "database_aggregator",
                "total_queries": len(queries),
                "total_computed_fields": len(computed_fields),
            }

            return results

        except Exception as e:
            self.logger.error(f"Database aggregation failed: {str(e)}")
            raise DataValidationError(
                "Database aggregation failed", [{"error": str(e)}]
            )

    def _validate_database_state(self, validation_config: Dict[str, Any]) -> None:
        """Validate database state before executing queries."""
        required_tables = validation_config.get("required_tables", [])

        if required_tables:
            with self.db.get_session() as session:
                for table in required_tables:
                    try:
                        result = session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                        result.fetchone()
                    except SQLAlchemyError:
                        raise DataValidationError(
                            f"Required table '{table}' not found or not accessible",
                            [{"table": table}],
                        )

    def _validate_sql_security(self, sql: str) -> str:
        """Validate SQL for security issues."""
        # Remove extra whitespace and normalize
        sql_normalized = re.sub(r"\s+", " ", sql.strip()).upper()

        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql_normalized, re.IGNORECASE):
                raise ValueError(f"SQL contains forbidden pattern: {pattern}")

        # Must be a SELECT statement
        if not sql_normalized.startswith("SELECT"):
            raise ValueError("Only SELECT statements are allowed")

        return sql

    def _execute_query(
        self,
        sql: str,
        description: Optional[str] = None,
        format_type: str = "scalar",
        timeout: int = 30,
    ) -> Any:
        """Execute a SQL query and format the result."""
        # Validate SQL security
        validated_sql = self._validate_sql_security(sql)

        try:
            with self.db.get_session() as session:
                # Set query timeout
                session.execute(text(f"PRAGMA busy_timeout = {timeout * 1000}"))

                self.logger.debug(f"Executing SQL: {validated_sql}")
                result = session.execute(text(validated_sql))

                if format_type == "scalar":
                    # Single value
                    value = result.scalar()
                    return value

                elif format_type == "table":
                    # Multiple rows as list of dicts
                    rows = result.fetchall()
                    if rows:
                        columns = list(rows[0]._mapping.keys())
                        return [dict(zip(columns, row)) for row in rows]
                    return []

                elif format_type == "series":
                    # Single column as list
                    rows = result.fetchall()
                    return [row[0] for row in rows]

                elif format_type == "single_row":
                    # Single row as dict
                    row = result.fetchone()
                    if row:
                        return dict(row._mapping)
                    return {}

                else:
                    # Default to scalar
                    return result.scalar()

        except SQLAlchemyError as e:
            self.logger.error(f"SQL execution failed: {validated_sql}\nError: {str(e)}")
            raise DataValidationError(
                f"SQL query failed: {str(e)}", [{"sql": sql, "error": str(e)}]
            )
        except Exception as e:
            self.logger.error(f"Unexpected error executing SQL: {str(e)}")
            raise

    def _execute_template(
        self, query_config: QueryConfig, templates: Dict[str, Any]
    ) -> Any:
        """Execute a templated query."""
        template_name = query_config.template
        template_params = query_config.template_params

        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found")

        template_config = TemplateConfig(**templates[template_name])

        # Validate template parameters
        required_params = set(template_config.params)
        provided_params = set(template_params.keys())

        missing_params = required_params - provided_params
        if missing_params:
            raise ValueError(f"Missing template parameters: {missing_params}")

        # Extra parameters are allowed (will be ignored)

        # Format SQL with parameters
        try:
            formatted_sql = template_config.sql.format(**template_params)
        except KeyError as e:
            raise ValueError(f"Template parameter not provided: {str(e)}")

        return self._execute_query(
            formatted_sql,
            query_config.description or template_config.description,
            query_config.format,
            query_config.timeout,
        )

    def _calculate_computed_field(
        self, field_config: ComputedFieldConfig, results: Dict[str, Any]
    ) -> Any:
        """Calculate computed fields from other results."""
        expression = field_config.expression
        dependencies = field_config.dependencies

        # Validate dependencies exist
        missing_deps = [dep for dep in dependencies if dep not in results]
        if missing_deps:
            raise ValueError(f"Missing dependencies for computed field: {missing_deps}")

        # Create a safe namespace for evaluation
        namespace = {}
        for dep in dependencies:
            value = results.get(dep)
            # Convert None to 0 for calculations
            if value is None:
                value = 0
            namespace[dep] = value

        # Add safe mathematical functions
        import math

        safe_functions = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "int": int,
            "float": float,
            "pow": pow,
            "sqrt": math.sqrt,
            "ceil": math.ceil,
            "floor": math.floor,
        }
        namespace.update(safe_functions)

        try:
            # Evaluate expression in safe namespace
            result = eval(expression, {"__builtins__": {}}, namespace)
            return result
        except Exception as e:
            self.logger.error(
                f"Computed field calculation failed: {expression}\nError: {str(e)}"
            )
            raise DataValidationError(
                f"Computed field calculation failed: {str(e)}",
                [{"expression": expression, "error": str(e)}],
            )

    def get_dependencies(self) -> List[str]:
        """Return plugin dependencies."""
        return []  # No external dependencies

    @classmethod
    def get_example_config(cls) -> Dict[str, Any]:
        """Return example configuration."""
        return {
            "plugin": "database_aggregator",
            "params": {
                "queries": {
                    "species_count": {
                        "sql": "SELECT COUNT(*) FROM taxon_ref WHERE rank_name = 'species'",
                        "description": "Total number of species",
                    },
                    "occurrence_count": {
                        "sql": "SELECT COUNT(*) FROM occurrences",
                        "description": "Total number of occurrences",
                    },
                    "data_quality": {
                        "sql": """
                            SELECT
                                'Occurrences with coordinates' as metric,
                                COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) as count,
                                ROUND(COUNT(CASE WHEN geo_pt IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as percentage
                            FROM occurrences
                        """,
                        "format": "single_row",
                        "description": "Data quality metrics",
                    },
                },
                "templates": {
                    "count_by_field": {
                        "sql": "SELECT {field}, COUNT(*) as count FROM {table} GROUP BY {field} ORDER BY count DESC LIMIT {limit}",
                        "params": ["field", "table", "limit"],
                        "description": "Count records by field",
                    }
                },
                "computed_fields": {
                    "endemic_percentage": {
                        "expression": "(endemic_count * 100.0) / species_count if species_count > 0 else 0",
                        "dependencies": ["endemic_count", "species_count"],
                        "description": "Percentage of endemic species",
                    }
                },
                "validation": {
                    "check_referential_integrity": True,
                    "max_execution_time": 30,
                    "required_tables": ["taxon_ref", "occurrences"],
                },
            },
        }
