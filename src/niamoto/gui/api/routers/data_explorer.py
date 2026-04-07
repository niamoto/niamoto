"""Data Explorer API endpoints for querying database tables."""

import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
import yaml

from niamoto.common.database import Database
from niamoto.common.table_resolver import quote_identifier
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.core.plugins.loaders.api_taxonomy_enricher import ApiTaxonomyEnricher
from ..utils.database import open_database

router = APIRouter()


class TableInfo(BaseModel):
    """Information about a database table."""

    name: str
    count: int
    description: str
    columns: List[str]


class QueryRequest(BaseModel):
    """Request model for querying table data."""

    table: str
    columns: Optional[List[str]] = None
    where: Optional[str] = None
    order_by: Optional[str] = None
    limit: int = 100
    offset: int = 0


class QueryResponse(BaseModel):
    """Response model for query results."""

    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int
    page_count: int


def _build_where_clause(
    where: Optional[str], allowed_columns: set[str], db: Database
) -> tuple[str, Dict[str, Any]]:
    """Build a safe WHERE clause with a restricted boolean expression grammar."""
    if not where:
        return "", {}

    normalized = where.strip()
    if normalized.upper().startswith("WHERE "):
        normalized = normalized[6:].strip()

    if any(token in normalized for token in (";", "--", "/*", "*/")):
        raise HTTPException(status_code=400, detail="Invalid WHERE clause")

    token_pattern = re.compile(
        r"""
        \s*(
            \(|\)|,|
            <=|>=|<>|!=|=|<|>|
            \bAND\b|\bOR\b|\bNOT\b|\bIN\b|\bIS\b|\bNULL\b|\bLIKE\b|\bILIKE\b|\bBETWEEN\b|
            '(?:''|[^'])*'|
            -?\d+\.\d+|-?\d+|
            \btrue\b|\bfalse\b|
            [A-Za-z_][A-Za-z0-9_]*
        )\s*
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def tokenize(expression: str) -> List[str]:
        tokens: List[str] = []
        pos = 0
        while pos < len(expression):
            match = token_pattern.match(expression, pos)
            if not match:
                snippet = expression[pos : pos + 20]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid WHERE syntax near: {snippet!r}",
                )
            token = match.group(1)
            if token:
                tokens.append(token)
            pos = match.end()
        return tokens

    def is_identifier(token: str) -> bool:
        return re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", token) is not None

    def parse_literal(token: str) -> Any:
        if token.startswith("'") and token.endswith("'") and len(token) >= 2:
            return token[1:-1].replace("''", "'")
        if re.match(r"^-?\d+$", token):
            return int(token)
        if re.match(r"^-?\d+\.\d+$", token):
            return float(token)
        if token.lower() in ("true", "false"):
            return token.lower() == "true"
        raise HTTPException(status_code=400, detail=f"Unsupported WHERE value: {token}")

    tokens = tokenize(normalized)
    if not tokens:
        return "", {}

    params: Dict[str, Any] = {}
    param_index = 0
    pos = 0

    def current() -> Optional[str]:
        return tokens[pos] if pos < len(tokens) else None

    def consume(expected: Optional[str] = None) -> str:
        nonlocal pos
        token = current()
        if token is None:
            raise HTTPException(
                status_code=400, detail="Unexpected end of WHERE clause"
            )
        if expected is not None and token.upper() != expected:
            raise HTTPException(
                status_code=400, detail=f"Expected '{expected}' in WHERE clause"
            )
        pos += 1
        return token

    def parse_predicate() -> str:
        nonlocal param_index
        column_token = consume()
        if not is_identifier(column_token):
            raise HTTPException(
                status_code=400, detail="Expected column name in WHERE clause"
            )
        if column_token not in allowed_columns:
            raise HTTPException(
                status_code=400, detail=f"Unknown column in WHERE: {column_token}"
            )
        quoted_col = quote_identifier(db, column_token)

        token = current()
        if token is None:
            raise HTTPException(status_code=400, detail="Incomplete WHERE predicate")
        token_upper = token.upper()

        if token_upper == "IS":
            consume("IS")
            negated = False
            if (current() or "").upper() == "NOT":
                consume("NOT")
                negated = True
            consume("NULL")
            return f"{quoted_col} IS {'NOT ' if negated else ''}NULL"

        if token_upper == "NOT":
            consume("NOT")
            next_token = (current() or "").upper()
            if next_token == "IN":
                consume("IN")
                consume("(")
                values_sql: List[str] = []
                while True:
                    value_token = consume()
                    param_name = f"w_{param_index}"
                    param_index += 1
                    params[param_name] = parse_literal(value_token)
                    values_sql.append(f":{param_name}")
                    if current() == ",":
                        consume(",")
                        continue
                    break
                consume(")")
                if not values_sql:
                    raise HTTPException(
                        status_code=400, detail="NOT IN list cannot be empty"
                    )
                return f"{quoted_col} NOT IN ({', '.join(values_sql)})"
            if next_token == "BETWEEN":
                consume("BETWEEN")
                lower_token = consume()
                consume("AND")
                upper_token = consume()
                lower_param = f"w_{param_index}"
                param_index += 1
                upper_param = f"w_{param_index}"
                param_index += 1
                params[lower_param] = parse_literal(lower_token)
                params[upper_param] = parse_literal(upper_token)
                return f"{quoted_col} NOT BETWEEN :{lower_param} AND :{upper_param}"
            raise HTTPException(
                status_code=400,
                detail="Unsupported WHERE predicate after NOT",
            )

        if token_upper == "IN":
            consume("IN")
            consume("(")
            values_sql = []
            while True:
                value_token = consume()
                param_name = f"w_{param_index}"
                param_index += 1
                params[param_name] = parse_literal(value_token)
                values_sql.append(f":{param_name}")
                if current() == ",":
                    consume(",")
                    continue
                break
            consume(")")
            if not values_sql:
                raise HTTPException(status_code=400, detail="IN list cannot be empty")
            return f"{quoted_col} IN ({', '.join(values_sql)})"

        if token_upper == "BETWEEN":
            consume("BETWEEN")
            lower_token = consume()
            consume("AND")
            upper_token = consume()
            lower_param = f"w_{param_index}"
            param_index += 1
            upper_param = f"w_{param_index}"
            param_index += 1
            params[lower_param] = parse_literal(lower_token)
            params[upper_param] = parse_literal(upper_token)
            return f"{quoted_col} BETWEEN :{lower_param} AND :{upper_param}"

        if token_upper in {"=", "!=", "<>", ">=", "<=", ">", "<", "LIKE", "ILIKE"}:
            operator = consume().upper()
            value_token = consume()
            param_name = f"w_{param_index}"
            param_index += 1
            params[param_name] = parse_literal(value_token)
            return f"{quoted_col} {operator} :{param_name}"

        raise HTTPException(status_code=400, detail="Unsupported WHERE predicate")

    def parse_factor() -> str:
        if (current() or "").upper() == "NOT":
            consume("NOT")
            inner_sql = parse_factor()
            return f"(NOT {inner_sql})"
        if current() == "(":
            consume("(")
            expression_sql = parse_expression()
            consume(")")
            return f"({expression_sql})"
        return parse_predicate()

    def parse_term() -> str:
        sql = parse_factor()
        while (current() or "").upper() == "AND":
            consume("AND")
            rhs = parse_factor()
            sql = f"({sql} AND {rhs})"
        return sql

    def parse_expression() -> str:
        sql = parse_term()
        while (current() or "").upper() == "OR":
            consume("OR")
            rhs = parse_term()
            sql = f"({sql} OR {rhs})"
        return sql

    final_sql = parse_expression()
    if current() is not None:
        raise HTTPException(status_code=400, detail="Unexpected token in WHERE clause")
    return f" WHERE {final_sql}", params


def _build_order_by_clause(
    order_by: Optional[str], allowed_columns: set[str], db: Database
) -> str:
    """Build a safe ORDER BY clause."""
    if not order_by:
        return ""

    segments = [segment.strip() for segment in order_by.split(",") if segment.strip()]
    if not segments:
        return ""

    clauses: List[str] = []
    for segment in segments:
        match = re.match(
            r"^([A-Za-z_][A-Za-z0-9_]*)(?:\s+(ASC|DESC))?$",
            segment,
            flags=re.IGNORECASE,
        )
        if not match:
            raise HTTPException(status_code=400, detail="Invalid ORDER BY clause")
        col_name = match.group(1)
        direction = (match.group(2) or "ASC").upper()
        if col_name not in allowed_columns:
            raise HTTPException(
                status_code=400, detail=f"Unknown column in ORDER BY: {col_name}"
            )
        quoted_col = quote_identifier(db, col_name)
        clauses.append(f"{quoted_col} {direction}")

    return " ORDER BY " + ", ".join(clauses)


def get_table_description(table_name: str) -> str:
    """
    Generate a dynamic description for a table.

    Detects table type (reference, dataset, generated) and provides
    an appropriate description.
    """
    # Reference tables (end with _ref)
    if table_name.endswith("_ref"):
        base_name = table_name[:-4].replace("_", " ").title()
        return f"{base_name} reference data"

    # System/metadata tables
    if table_name.startswith("niamoto_"):
        return "Niamoto system metadata"

    # Common dataset patterns
    dataset_patterns = {
        "occurrence": "occurrence data with measurements and location",
        "observation": "observation data",
        "plot": "plot data",
        "site": "site data",
        "sample": "sample data",
    }

    table_lower = table_name.lower()
    for pattern, desc in dataset_patterns.items():
        if pattern in table_lower:
            return f"Dataset: {desc}"

    # Likely a generated/transformed table
    # Try to determine from name structure
    if "_" not in table_name:
        # Simple name like "taxon", "plot", "shape" - likely transformed
        return f"Transformed {table_name} data with widgets"

    # Default generic description
    return f"Table: {table_name}"


def get_table_count(db: Database, table_name: str) -> int:
    """Get the number of rows in a table."""
    try:
        quoted_table = quote_identifier(db, table_name)
        with db.session() as session:
            result = session.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
            return result.scalar() or 0
    except Exception:
        return 0


def get_table_columns(db: Database, table_name: str) -> List[str]:
    """Get column names for a table."""
    try:
        columns = db.get_columns(table_name)
        return [col["name"] for col in columns]
    except Exception:
        return []


@router.get("/tables", response_model=List[TableInfo])
async def list_tables():
    """
    List all available database tables with metadata.

    Returns information about each table including row count and columns.
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(
            status_code=404,
            detail="Database not found. Please ensure the database is initialized.",
        )

    try:
        with open_database(db_path) as db:
            table_names = db.get_table_names()

            tables = []
            for table_name in table_names:
                # Skip internal SQLite tables
                if table_name.startswith("sqlite_"):
                    continue

                count = get_table_count(db, table_name)
                columns = get_table_columns(db, table_name)
                description = get_table_description(table_name)

                tables.append(
                    TableInfo(
                        name=table_name,
                        count=count,
                        description=description,
                        columns=columns,
                    )
                )

        tables.sort(key=lambda t: (-t.count, t.name))
        return tables

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def query_table(request: QueryRequest):
    """
    Query a database table with optional filtering and pagination.

    Supports:
    - Column selection
    - WHERE clauses
    - ORDER BY
    - LIMIT/OFFSET for pagination
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(
            status_code=404,
            detail="Database not found. Please ensure the database is initialized.",
        )

    try:
        with open_database(db_path) as db:
            if request.table not in db.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Table '{request.table}' not found"
                )

            table_columns = [col["name"] for col in db.get_columns(request.table)]
            allowed_columns = set(table_columns)
            quoted_table = quote_identifier(db, request.table)

            if request.columns:
                invalid_cols = [c for c in request.columns if c not in allowed_columns]
                if invalid_cols:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown columns requested: {', '.join(invalid_cols)}",
                    )
                selected_columns = request.columns
            else:
                selected_columns = table_columns

            quoted_columns = ", ".join(
                quote_identifier(db, col) for col in selected_columns
            )
            where_clause, where_params = _build_where_clause(
                request.where, allowed_columns, db
            )
            order_clause = _build_order_by_clause(request.order_by, allowed_columns, db)

            count_query = text(f"SELECT COUNT(*) FROM {quoted_table}{where_clause}")
            data_query = text(
                f"SELECT {quoted_columns} "
                f"FROM {quoted_table}{where_clause}{order_clause} "
                "LIMIT :limit OFFSET :offset"
            )
            data_params: Dict[str, Any] = {
                **where_params,
                "limit": max(1, int(request.limit)),
                "offset": max(0, int(request.offset)),
            }

            with db.session() as session:
                total_result = session.execute(count_query, where_params)
                total_count = total_result.scalar() or 0

                result = session.execute(data_query, data_params)

                column_names = list(result.keys())

                rows = []
                for row in result:
                    row_dict = {}
                    for idx, col_name in enumerate(column_names):
                        value = row[idx]
                        if isinstance(value, (bytes, bytearray)):
                            row_dict[col_name] = None
                        else:
                            row_dict[col_name] = value
                    rows.append(row_dict)

        return QueryResponse(
            columns=column_names,
            rows=rows,
            total_count=total_count,
            page_count=len(rows),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/tables/{table_name}/columns")
async def get_table_columns_endpoint(table_name: str):
    """
    Get column information for a specific table.

    Returns column names and types.
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(
            status_code=404,
            detail="Database not found. Please ensure the database is initialized.",
        )

    try:
        with open_database(db_path) as db:
            if table_name not in db.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Table '{table_name}' not found"
                )

            columns = db.get_columns(table_name)

        return {
            "table": table_name,
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": col.get("default"),
                }
                for col in columns
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get columns: {str(e)}")


class EnrichmentPreviewRequest(BaseModel):
    """Request model for enrichment preview."""

    taxon_name: str
    table: Optional[str] = "taxon_ref"


@router.post("/enrichment/preview")
async def preview_enrichment(request: EnrichmentPreviewRequest):
    """
    Preview API enrichment for a taxon without saving to database.

    Reads api_enrichment config from import.yml and calls the API.
    """
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=404, detail="Working directory not found")

    # Read import.yml to get API enrichment config
    import_config_path = work_dir / "config" / "import.yml"
    if not import_config_path.exists():
        raise HTTPException(
            status_code=404,
            detail="import.yml not found. API enrichment not configured.",
        )

    try:
        with open(import_config_path, "r") as f:
            import_config = yaml.safe_load(f)

        # Extract API enrichment config from taxonomy section
        taxonomy_config = import_config.get("taxonomy", {})
        api_enrichment = taxonomy_config.get("api_enrichment", {})

        if not api_enrichment:
            raise HTTPException(
                status_code=404,
                detail="API enrichment not configured in import.yml",
            )

        # For preview, we don't require enabled=true, just that config exists

        # Prepare config for the plugin
        plugin_config = {
            "plugin": api_enrichment.get("plugin", "api_taxonomy_enricher"),
            "params": {
                "api_url": api_enrichment.get("api_url"),
                "query_field": api_enrichment.get("query_field", "full_name"),
                "query_param_name": api_enrichment.get("query_param_name", "q"),
                "response_mapping": api_enrichment.get("response_mapping", {}),
                "rate_limit": api_enrichment.get("rate_limit", 1.0),
                "cache_results": False,  # Disable cache for preview
                "auth_method": api_enrichment.get("auth_method", "none"),
                "auth_params": api_enrichment.get("auth_params", {}),
                "query_params": api_enrichment.get("query_params", {}),
                "chained_endpoints": api_enrichment.get("chained_endpoints", []),
            },
        }

        # Create plugin instance and call it
        enricher = ApiTaxonomyEnricher()

        # Prepare taxon data
        taxon_data = {
            api_enrichment.get("query_field", "full_name"): request.taxon_name
        }

        # Call plugin
        result = enricher.load_data(taxon_data, plugin_config)

        # Return enriched data
        return {
            "success": True,
            "taxon_name": request.taxon_name,
            "api_enrichment": result.get("api_enrichment", {}),
            "config_used": {
                "api_url": plugin_config["params"]["api_url"],
                "query_field": plugin_config["params"]["query_field"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to preview enrichment: {str(e)}"
        )
