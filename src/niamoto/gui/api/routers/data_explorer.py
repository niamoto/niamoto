"""Data Explorer API endpoints for querying database tables."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, inspect

from niamoto.common.database import Database
from niamoto.gui.api.context import get_database_path

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


# Table descriptions
TABLE_DESCRIPTIONS = {
    "occurrences": "Species occurrence data with measurements and location",
    "taxon_ref": "Taxonomic hierarchy and reference data",
    "plot_ref": "Plot locations and metadata",
    "shape_ref": "Geographic boundaries and shapes",
    "taxon": "Transformed taxon data with widgets",
    "plot": "Transformed plot data with widgets",
    "shape": "Transformed shape data with widgets",
}


def get_table_count(db: Database, table_name: str) -> int:
    """Get the number of rows in a table."""
    try:
        with db.session() as session:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar() or 0
    except Exception:
        return 0


def get_table_columns(db: Database, table_name: str) -> List[str]:
    """Get column names for a table."""
    try:
        inspector = inspect(db.engine)
        columns = inspector.get_columns(table_name)
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

    db = Database(str(db_path))

    try:
        # Get all table names
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        tables = []
        for table_name in table_names:
            # Skip internal SQLite tables
            if table_name.startswith("sqlite_"):
                continue

            count = get_table_count(db, table_name)
            columns = get_table_columns(db, table_name)
            description = TABLE_DESCRIPTIONS.get(table_name, f"Table: {table_name}")

            tables.append(
                TableInfo(
                    name=table_name,
                    count=count,
                    description=description,
                    columns=columns,
                )
            )

        # Sort by count (descending) then name
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

    db = Database(str(db_path))

    # Validate table exists
    inspector = inspect(db.engine)
    if request.table not in inspector.get_table_names():
        raise HTTPException(
            status_code=404, detail=f"Table '{request.table}' not found"
        )

    try:
        # Build query
        columns = request.columns if request.columns else ["*"]
        columns_str = ", ".join(columns)

        query = f"SELECT {columns_str} FROM {request.table}"

        if request.where:
            # Basic sanitization - in production, use parameterized queries
            # Remove "WHERE" prefix if user included it
            where_clause = request.where.strip()
            if where_clause.upper().startswith("WHERE "):
                where_clause = where_clause[6:].strip()
            query += f" WHERE {where_clause}"

        if request.order_by:
            query += f" ORDER BY {request.order_by}"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM {request.table}"
        if request.where:
            where_clause = request.where.strip()
            if where_clause.upper().startswith("WHERE "):
                where_clause = where_clause[6:].strip()
            count_query += f" WHERE {where_clause}"

        with db.session() as session:
            # Get total count
            total_result = session.execute(text(count_query))
            total_count = total_result.scalar() or 0

            # Get paginated data
            query += f" LIMIT {request.limit} OFFSET {request.offset}"
            result = session.execute(text(query))

            # Get column names
            column_names = list(result.keys())

            # Fetch rows
            rows = []
            for row in result:
                row_dict = {}
                for idx, col_name in enumerate(column_names):
                    value = row[idx]
                    # Convert to JSON-serializable types
                    if isinstance(value, (bytes, bytearray)):
                        row_dict[col_name] = None  # Skip binary data
                    else:
                        row_dict[col_name] = value
                rows.append(row_dict)

            return QueryResponse(
                columns=column_names,
                rows=rows,
                total_count=total_count,
                page_count=len(rows),
            )

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

    db = Database(str(db_path))

    try:
        inspector = inspect(db.engine)

        if table_name not in inspector.get_table_names():
            raise HTTPException(
                status_code=404, detail=f"Table '{table_name}' not found"
            )

        columns = inspector.get_columns(table_name)

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
