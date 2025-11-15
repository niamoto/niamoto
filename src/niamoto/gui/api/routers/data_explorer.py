"""Data Explorer API endpoints for querying database tables."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, inspect
import yaml

from niamoto.common.database import Database
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

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()

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
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            if request.table not in inspector.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Table '{request.table}' not found"
                )

            columns = request.columns if request.columns else ["*"]
            columns_str = ", ".join(columns)

            query = f"SELECT {columns_str} FROM {request.table}"

            if request.where:
                where_clause = request.where.strip()
                if where_clause.upper().startswith("WHERE "):
                    where_clause = where_clause[6:].strip()
                query += f" WHERE {where_clause}"

            if request.order_by:
                query += f" ORDER BY {request.order_by}"

            count_query = f"SELECT COUNT(*) FROM {request.table}"
            if request.where:
                where_clause = request.where.strip()
                if where_clause.upper().startswith("WHERE "):
                    where_clause = where_clause[6:].strip()
                count_query += f" WHERE {where_clause}"

            with db.session() as session:
                total_result = session.execute(text(count_query))
                total_count = total_result.scalar() or 0

                query += f" LIMIT {request.limit} OFFSET {request.offset}"
                result = session.execute(text(query))

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
        with open_database(db_path, read_only=True) as db:
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
