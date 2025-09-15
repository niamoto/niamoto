"""Database introspection API endpoints."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, inspect, text

router = APIRouter()


class ColumnInfo(BaseModel):
    """Database column information."""

    name: str
    type: str
    nullable: bool
    primary_key: bool = False
    foreign_key: Optional[str] = None


class TableInfo(BaseModel):
    """Database table information."""

    name: str
    row_count: int
    columns: List[ColumnInfo]
    indexes: List[str] = []
    is_view: bool = False


class DatabaseSchema(BaseModel):
    """Complete database schema information."""

    tables: List[TableInfo]
    views: List[TableInfo] = []
    total_size: Optional[int] = None


class TablePreview(BaseModel):
    """Preview of table data."""

    table_name: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    preview_limit: int


class TableStats(BaseModel):
    """Statistics for a table."""

    table_name: str
    row_count: int
    column_count: int
    null_counts: Dict[str, int]
    unique_counts: Dict[str, int]
    data_types: Dict[str, str]


def get_database_path() -> Optional[Path]:
    """Get the path to the SQLite database."""
    # First check config for database path
    import yaml

    config_path = Path.cwd() / "config" / "config.yml"

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
                db_path_str = config.get("database", {}).get("path", "db/niamoto.db")
                db_path = Path.cwd() / db_path_str
                if db_path.exists():
                    return db_path
        except Exception:
            pass

    # Fallback to common locations
    db_path = Path.cwd() / "db" / "niamoto.db"
    if db_path.exists():
        return db_path

    db_path = Path.cwd() / "niamoto.db"
    if db_path.exists():
        return db_path

    # Check in data directory
    data_path = Path.cwd() / "data" / "niamoto.db"
    if data_path.exists():
        return data_path

    return None


@router.get("/schema", response_model=DatabaseSchema)
async def get_database_schema():
    """
    Get the complete database schema including tables, views, and columns.

    Returns detailed information about all tables and views in the database.
    """
    db_path = get_database_path()
    if not db_path:
        return DatabaseSchema(tables=[], views=[], total_size=None)

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)

        tables = []
        views = []

        # Get all table names
        table_names = inspector.get_table_names()

        for table_name in table_names:
            # Get columns
            columns = []
            for col in inspector.get_columns(table_name):
                column_info = ColumnInfo(
                    name=col["name"],
                    type=str(col["type"]),
                    nullable=col.get("nullable", True),
                    primary_key=col.get("primary_key", False),
                )
                columns.append(column_info)

            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            if pk_constraint and pk_constraint.get("constrained_columns"):
                for col in columns:
                    if col.name in pk_constraint["constrained_columns"]:
                        col.primary_key = True

            # Get foreign keys
            fk_constraints = inspector.get_foreign_keys(table_name)
            for fk in fk_constraints:
                for col_name in fk.get("constrained_columns", []):
                    for col in columns:
                        if col.name == col_name:
                            ref_table = fk.get("referred_table")
                            ref_cols = fk.get("referred_columns", [])
                            if ref_table and ref_cols:
                                col.foreign_key = f"{ref_table}.{ref_cols[0]}"

            # Get row count
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar() or 0

            # Get indexes
            indexes = [
                idx["name"]
                for idx in inspector.get_indexes(table_name)
                if idx.get("name")
            ]

            table_info = TableInfo(
                name=table_name,
                row_count=row_count,
                columns=columns,
                indexes=indexes,
                is_view=False,
            )
            tables.append(table_info)

        # Get views
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='view'")
            )
            view_names = [row[0] for row in result]

            for view_name in view_names:
                # Try to get view columns
                try:
                    result = conn.execute(text(f"PRAGMA table_info({view_name})"))
                    columns = []
                    for row in result:
                        column_info = ColumnInfo(
                            name=row[1],
                            type=row[2] or "UNKNOWN",
                            nullable=row[3] == 0,
                            primary_key=row[5] == 1,
                        )
                        columns.append(column_info)

                    # Get row count
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}"))
                    row_count = result.scalar() or 0

                    view_info = TableInfo(
                        name=view_name,
                        row_count=row_count,
                        columns=columns,
                        indexes=[],
                        is_view=True,
                    )
                    views.append(view_info)
                except Exception:
                    # Skip views that can't be introspected
                    pass

        # Get database size
        total_size = db_path.stat().st_size if db_path.exists() else None

        engine.dispose()

        return DatabaseSchema(tables=tables, views=views, total_size=total_size)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading database schema: {str(e)}"
        )


@router.get("/tables/{table_name}/preview", response_model=TablePreview)
async def get_table_preview(
    table_name: str,
    limit: int = Query(
        default=100, ge=1, le=1000, description="Number of rows to preview"
    ),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """
    Get a preview of data from a specific table.

    Args:
        table_name: Name of the table to preview
        limit: Maximum number of rows to return (1-1000)
        offset: Number of rows to skip for pagination

    Returns:
        Preview of the table data with column names and sample rows
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        engine = create_engine(f"sqlite:///{db_path}")

        with engine.connect() as conn:
            # Check if table exists
            inspector = inspect(engine)
            if table_name not in inspector.get_table_names():
                # Check if it's a view
                result = conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='view' AND name=:name"
                    ),
                    {"name": table_name},
                )
                if not result.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Table or view '{table_name}' not found",
                    )

            # Get total row count
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total_rows = result.scalar() or 0

            # Get preview data
            result = conn.execute(
                text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )

            columns = list(result.keys())
            rows = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert bytes to string for display
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8")
                        except UnicodeDecodeError:
                            value = f"<binary:{len(value)}bytes>"
                    row_dict[col] = value
                rows.append(row_dict)

        engine.dispose()

        return TablePreview(
            table_name=table_name,
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            preview_limit=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing table: {str(e)}")


@router.get("/tables/{table_name}/stats", response_model=TableStats)
async def get_table_stats(table_name: str):
    """
    Get statistics for a specific table.

    Args:
        table_name: Name of the table to analyze

    Returns:
        Statistical information about the table including null counts,
        unique value counts, and data types for each column
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)

        # Check if table exists
        if table_name not in inspector.get_table_names():
            raise HTTPException(
                status_code=404, detail=f"Table '{table_name}' not found"
            )

        with engine.connect() as conn:
            # Get row count
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = result.scalar() or 0

            # Get column information
            columns = inspector.get_columns(table_name)
            column_count = len(columns)

            null_counts = {}
            unique_counts = {}
            data_types = {}

            for col in columns:
                col_name = col["name"]
                data_types[col_name] = str(col["type"])

                # Count nulls
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL")
                )
                null_counts[col_name] = result.scalar() or 0

                # Count unique values
                result = conn.execute(
                    text(f"SELECT COUNT(DISTINCT {col_name}) FROM {table_name}")
                )
                unique_counts[col_name] = result.scalar() or 0

        engine.dispose()

        return TableStats(
            table_name=table_name,
            row_count=row_count,
            column_count=column_count,
            null_counts=null_counts,
            unique_counts=unique_counts,
            data_types=data_types,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting table statistics: {str(e)}"
        )


@router.get("/query")
async def execute_query(
    query: str = Query(..., description="SQL query to execute"),
    limit: int = Query(
        default=100, ge=1, le=1000, description="Maximum rows to return"
    ),
):
    """
    Execute a custom SQL query (read-only).

    Args:
        query: SQL query to execute (SELECT only)
        limit: Maximum number of rows to return

    Returns:
        Query results with column names and data

    Note: Only SELECT queries are allowed for safety
    """
    # Basic safety check - only allow SELECT queries
    query_lower = query.strip().lower()
    if not query_lower.startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    # Block potentially dangerous keywords
    dangerous_keywords = [
        "drop",
        "delete",
        "insert",
        "update",
        "alter",
        "create",
        "pragma",
    ]
    for keyword in dangerous_keywords:
        if keyword in query_lower:
            raise HTTPException(
                status_code=400, detail=f"Query contains forbidden keyword: {keyword}"
            )

    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        engine = create_engine(f"sqlite:///{db_path}")

        with engine.connect() as conn:
            # Add LIMIT if not present
            if "limit" not in query_lower:
                query = f"{query} LIMIT {limit}"

            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = []

            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert bytes to string for display
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8")
                        except UnicodeDecodeError:
                            value = f"<binary:{len(value)}bytes>"
                    row_dict[col] = value
                rows.append(row_dict)

        engine.dispose()

        return {"columns": columns, "rows": rows, "row_count": len(rows)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
