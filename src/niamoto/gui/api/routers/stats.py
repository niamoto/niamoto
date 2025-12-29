"""Import statistics API endpoints for post-import dashboard."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import inspect, text

from ..utils.database import open_database
from ..context import get_working_directory
from .database import get_database_path

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class EntitySummary(BaseModel):
    """Summary for a single entity."""

    name: str
    entity_type: str  # 'dataset', 'reference', 'layer'
    row_count: int
    column_count: int
    columns: List[str]
    quality_score: float  # 0-1, based on completeness


class ImportSummary(BaseModel):
    """Global import summary."""

    total_entities: int
    total_rows: int
    entities: List[EntitySummary]
    alerts: List[Dict[str, Any]]
    quality_score: float  # Average across entities


class ColumnCompleteness(BaseModel):
    """Completeness info for a column."""

    column: str
    type: str
    total_count: int
    null_count: int
    non_null_count: int
    completeness: float  # 0-1
    unique_count: int


class EntityCompleteness(BaseModel):
    """Completeness data for an entity."""

    entity: str
    columns: List[ColumnCompleteness]
    overall_completeness: float


class SpatialStats(BaseModel):
    """Spatial distribution statistics."""

    total_points: int
    with_coordinates: int
    without_coordinates: int
    bounding_box: Optional[Dict[str, float]]  # min_x, min_y, max_x, max_y
    points_outside_bounds: int
    coordinate_columns: Dict[str, str]  # x_col, y_col


class TaxonomyLevel(BaseModel):
    """Statistics for a taxonomy level."""

    level: str
    count: int
    orphan_count: int


class TaxonomyConsistency(BaseModel):
    """Taxonomy consistency analysis."""

    total_taxa: int
    levels: List[TaxonomyLevel]
    orphan_records: List[Dict[str, Any]]
    duplicate_names: List[Dict[str, Any]]
    hierarchy_depth: int


class ColumnValidation(BaseModel):
    """Validation statistics for a numeric column."""

    column: str
    min_value: Optional[float]
    max_value: Optional[float]
    mean_value: Optional[float]
    median_value: Optional[float]
    std_dev: Optional[float]
    outlier_count: int
    outliers: List[Dict[str, Any]]  # Sample of outlier records


class EntityValidation(BaseModel):
    """Validation data for an entity."""

    entity: str
    columns: List[ColumnValidation]


class ShapeInfo(BaseModel):
    """Information about an available shape table."""

    table_name: str
    display_name: str
    shape_count: int
    has_geometry: bool
    shape_types: List[str]


class GeoCoverage(BaseModel):
    """Geographic coverage analysis (quick overview)."""

    total_occurrences: int
    occurrences_with_geo: int
    geo_column: Optional[str]
    available_shapes: List[ShapeInfo]
    ready_for_analysis: bool


class ShapeCoverageDetail(BaseModel):
    """Coverage detail for a single shape type."""

    shape_type: str
    shape_table: str
    total_shapes: int
    occurrences_covered: int
    coverage_percent: float


class SpatialAnalysisResult(BaseModel):
    """Full spatial analysis result (computed on demand)."""

    total_occurrences: int
    occurrences_with_geo: int
    occurrences_without_geo: int
    shape_coverage: List[ShapeCoverageDetail]
    analysis_time_seconds: float
    geo_column: Optional[str]
    status: str  # 'success', 'no_geo_column', 'no_shapes', 'error'
    message: Optional[str] = None


class ShapeOccurrenceCount(BaseModel):
    """Occurrence count for a single shape."""

    shape_id: int
    shape_name: str
    shape_type: str
    occurrence_count: int
    percent_of_total: float


class ShapeDistributionResult(BaseModel):
    """Distribution of occurrences by individual shape."""

    total_occurrences_with_geo: int
    shapes: List[ShapeOccurrenceCount]
    analysis_time_seconds: float
    status: str
    message: Optional[str] = None


class ValidationRule(BaseModel):
    """A single validation rule."""

    rule_type: str  # 'outlier', 'bounds', 'required'
    target: str  # Entity or column
    method: str  # 'iqr', 'zscore', 'percentile', 'manual'
    params: Dict[str, Any]


class ValidationRules(BaseModel):
    """Collection of validation rules."""

    rules: List[ValidationRule]


# =============================================================================
# Helper Functions
# =============================================================================


def get_entity_tables() -> Dict[str, str]:
    """Map entity types to their expected table names."""
    # Standard Niamoto table patterns
    return {
        "occurrences": "dataset",
        "taxon": "reference",
        "taxons": "reference",
        "plots": "dataset",
        "plot_occurrences": "dataset",
        "shapes": "reference",
    }


def classify_table_type(table_name: str) -> str:
    """Classify a table as dataset, reference, or layer."""
    table_lower = table_name.lower()

    # References
    if any(
        ref in table_lower
        for ref in ["taxon", "taxonomy", "reference", "shapes", "communes", "provinces"]
    ):
        return "reference"

    # Layers (metadata)
    if any(layer in table_lower for layer in ["layer", "raster", "vector", "dem"]):
        return "layer"

    # Default to dataset
    return "dataset"


def calculate_quality_score(completeness_values: List[float]) -> float:
    """Calculate quality score from completeness values."""
    if not completeness_values:
        return 1.0
    return sum(completeness_values) / len(completeness_values)


def detect_coordinate_columns(columns: List[str]) -> Dict[str, str]:
    """Detect coordinate columns from column names."""
    result = {}
    x_patterns = ["x", "lon", "longitude", "lng", "coord_x", "geo_x"]
    y_patterns = ["y", "lat", "latitude", "coord_y", "geo_y"]
    # WKT geometry columns
    wkt_patterns = ["geo_pt", "geo", "geom", "geometry", "wkt", "location"]

    columns_lower = [c.lower() for c in columns]

    # First check for WKT columns
    for i, col_lower in enumerate(columns_lower):
        for pattern in wkt_patterns:
            if pattern == col_lower or col_lower.startswith(pattern):
                result["wkt_col"] = columns[i]
                break
        if "wkt_col" in result:
            break

    # Then check for x/y columns
    for i, col_lower in enumerate(columns_lower):
        for pattern in x_patterns:
            if pattern == col_lower or col_lower.startswith(pattern):
                result["x_col"] = columns[i]
                break
        for pattern in y_patterns:
            if pattern == col_lower or col_lower.startswith(pattern):
                result["y_col"] = columns[i]
                break

    return result


def find_table_by_pattern(table_names: List[str], pattern: str) -> Optional[str]:
    """Find a table matching a pattern (handles dataset_*, entity_* prefixes)."""
    pattern_lower = pattern.lower()

    # Exact match first
    for t in table_names:
        if t.lower() == pattern_lower:
            return t

    # Then with prefixes
    prefixes = ["dataset_", "entity_", "ref_", ""]
    for prefix in prefixes:
        for t in table_names:
            if t.lower() == f"{prefix}{pattern_lower}":
                return t

    # Partial match
    for t in table_names:
        if pattern_lower in t.lower():
            return t

    return None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/summary", response_model=ImportSummary)
async def get_import_summary():
    """
    Get global import summary with stats per entity.

    Returns count per entity, quality scores, and priority alerts.
    """
    db_path = get_database_path()
    if not db_path:
        return ImportSummary(
            total_entities=0,
            total_rows=0,
            entities=[],
            alerts=[],
            quality_score=1.0,
        )

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer

            table_names = inspector.get_table_names() or []
            entities = []
            total_rows = 0
            alerts = []
            quality_scores = []

            with db.engine.connect() as conn:
                for table_name in table_names:
                    # Skip internal tables
                    if table_name.startswith("_") or table_name.startswith("sqlite"):
                        continue

                    quoted_table = preparer.quote(table_name)

                    # Get row count
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                    row_count = result.scalar() or 0
                    total_rows += row_count

                    # Get columns
                    columns_info = inspector.get_columns(table_name)
                    column_names = [c["name"] for c in columns_info]

                    # Calculate completeness for quality score
                    completeness_values = []
                    for col in column_names:
                        quoted_col = preparer.quote(col)
                        try:
                            result = conn.execute(
                                text(
                                    f"SELECT COUNT(*) FROM {quoted_table} WHERE {quoted_col} IS NOT NULL"
                                )
                            )
                            non_null = result.scalar() or 0
                            if row_count > 0:
                                completeness_values.append(non_null / row_count)
                        except Exception:
                            pass

                    quality_score = calculate_quality_score(completeness_values)
                    quality_scores.append(quality_score)

                    entity_type = classify_table_type(table_name)

                    entities.append(
                        EntitySummary(
                            name=table_name,
                            entity_type=entity_type,
                            row_count=row_count,
                            column_count=len(column_names),
                            columns=column_names,
                            quality_score=quality_score,
                        )
                    )

                    # Generate alerts
                    if row_count == 0:
                        alerts.append(
                            {
                                "level": "warning",
                                "entity": table_name,
                                "message": f"Table '{table_name}' is empty",
                            }
                        )
                    if quality_score < 0.5:
                        alerts.append(
                            {
                                "level": "warning",
                                "entity": table_name,
                                "message": f"Low data quality ({quality_score:.0%}) in '{table_name}'",
                            }
                        )

            overall_quality = (
                calculate_quality_score(quality_scores) if quality_scores else 1.0
            )

            return ImportSummary(
                total_entities=len(entities),
                total_rows=total_rows,
                entities=entities,
                alerts=alerts,
                quality_score=overall_quality,
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting import summary: {str(e)}"
        )


@router.get("/completeness/{entity}", response_model=EntityCompleteness)
async def get_completeness(entity: str):
    """
    Get completeness statistics per column for an entity.

    Returns % non-null, unique counts, and detected types.
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer

            if entity not in inspector.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity}' not found"
                )

            quoted_table = preparer.quote(entity)

            # Get total count
            with db.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                total_count = result.scalar() or 0

            columns_info = inspector.get_columns(entity)
            column_stats = []

            with db.engine.connect() as conn:
                for col in columns_info:
                    col_name = col["name"]
                    col_type = str(col.get("type", "UNKNOWN"))
                    quoted_col = preparer.quote(col_name)

                    # Null count
                    result = conn.execute(
                        text(
                            f"SELECT COUNT(*) FROM {quoted_table} WHERE {quoted_col} IS NULL"
                        )
                    )
                    null_count = result.scalar() or 0
                    non_null_count = total_count - null_count

                    # Unique count
                    result = conn.execute(
                        text(f"SELECT COUNT(DISTINCT {quoted_col}) FROM {quoted_table}")
                    )
                    unique_count = result.scalar() or 0

                    completeness = (
                        non_null_count / total_count if total_count > 0 else 1.0
                    )

                    column_stats.append(
                        ColumnCompleteness(
                            column=col_name,
                            type=col_type,
                            total_count=total_count,
                            null_count=null_count,
                            non_null_count=non_null_count,
                            completeness=completeness,
                            unique_count=unique_count,
                        )
                    )

            overall = (
                sum(c.completeness for c in column_stats) / len(column_stats)
                if column_stats
                else 1.0
            )

            return EntityCompleteness(
                entity=entity, columns=column_stats, overall_completeness=overall
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting completeness: {str(e)}"
        )


@router.get("/spatial", response_model=SpatialStats)
async def get_spatial_stats(
    entity: str = Query(default="occurrences", description="Entity with spatial data"),
    x_column: Optional[str] = Query(default=None, description="X/Longitude column"),
    y_column: Optional[str] = Query(default=None, description="Y/Latitude column"),
):
    """
    Get spatial distribution statistics.

    Returns bounding box, points without coordinates, and out-of-bounds count.
    Handles both x/y columns and WKT geometry columns (geo_pt, geo, etc.)
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer

            # Find the entity using improved matching
            table_names = inspector.get_table_names() or []
            target_table = find_table_by_pattern(table_names, entity)

            if not target_table:
                return SpatialStats(
                    total_points=0,
                    with_coordinates=0,
                    without_coordinates=0,
                    bounding_box=None,
                    points_outside_bounds=0,
                    coordinate_columns={},
                )

            quoted_table = preparer.quote(target_table)
            columns_info = inspector.get_columns(target_table)
            column_names = [c["name"] for c in columns_info]

            # Detect or use provided coordinate columns
            coord_cols = detect_coordinate_columns(column_names)
            if x_column:
                coord_cols["x_col"] = x_column
            if y_column:
                coord_cols["y_col"] = y_column

            with db.engine.connect() as conn:
                # Total count
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                total = result.scalar() or 0

                # Check if we have WKT column
                if "wkt_col" in coord_cols:
                    wkt_col = preparer.quote(coord_cols["wkt_col"])

                    # With coordinates (WKT not null and not empty)
                    result = conn.execute(
                        text(
                            f"""
                            SELECT COUNT(*) FROM {quoted_table}
                            WHERE {wkt_col} IS NOT NULL AND {wkt_col} != ''
                        """
                        )
                    )
                    with_coords = result.scalar() or 0

                    # Extract bounding box from WKT using regex
                    # WKT format: POINT (x y) or POINT(x y)
                    try:
                        result = conn.execute(
                            text(
                                f"""
                                SELECT
                                    MIN(CAST(regexp_extract({wkt_col}, 'POINT\\s*\\(([\\d.-]+)', 1) AS DOUBLE)),
                                    MIN(CAST(regexp_extract({wkt_col}, 'POINT\\s*\\([\\d.-]+\\s+([\\d.-]+)', 1) AS DOUBLE)),
                                    MAX(CAST(regexp_extract({wkt_col}, 'POINT\\s*\\(([\\d.-]+)', 1) AS DOUBLE)),
                                    MAX(CAST(regexp_extract({wkt_col}, 'POINT\\s*\\([\\d.-]+\\s+([\\d.-]+)', 1) AS DOUBLE))
                                FROM {quoted_table}
                                WHERE {wkt_col} IS NOT NULL AND {wkt_col} LIKE 'POINT%'
                            """
                            )
                        )
                        row = result.fetchone()
                        bbox = None
                        if row and row[0] is not None:
                            bbox = {
                                "min_x": float(row[0]),
                                "min_y": float(row[1]),
                                "max_x": float(row[2]),
                                "max_y": float(row[3]),
                            }
                    except Exception:
                        bbox = None

                    return SpatialStats(
                        total_points=total,
                        with_coordinates=with_coords,
                        without_coordinates=total - with_coords,
                        bounding_box=bbox,
                        points_outside_bounds=0,
                        coordinate_columns=coord_cols,
                    )

                # Fall back to x/y columns
                if "x_col" not in coord_cols or "y_col" not in coord_cols:
                    return SpatialStats(
                        total_points=total,
                        with_coordinates=0,
                        without_coordinates=total,
                        bounding_box=None,
                        points_outside_bounds=0,
                        coordinate_columns=coord_cols,
                    )

                x_col = preparer.quote(coord_cols["x_col"])
                y_col = preparer.quote(coord_cols["y_col"])

                # With coordinates
                result = conn.execute(
                    text(
                        f"""
                    SELECT COUNT(*) FROM {quoted_table}
                    WHERE {x_col} IS NOT NULL AND {y_col} IS NOT NULL
                """
                    )
                )
                with_coords = result.scalar() or 0

                # Bounding box
                result = conn.execute(
                    text(
                        f"""
                    SELECT
                        MIN({x_col}), MIN({y_col}),
                        MAX({x_col}), MAX({y_col})
                    FROM {quoted_table}
                    WHERE {x_col} IS NOT NULL AND {y_col} IS NOT NULL
                """
                    )
                )
                row = result.fetchone()
                bbox = None
                if row and row[0] is not None:
                    bbox = {
                        "min_x": float(row[0]),
                        "min_y": float(row[1]),
                        "max_x": float(row[2]),
                        "max_y": float(row[3]),
                    }

            return SpatialStats(
                total_points=total,
                with_coordinates=with_coords,
                without_coordinates=total - with_coords,
                bounding_box=bbox,
                points_outside_bounds=0,
                coordinate_columns=coord_cols,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting spatial stats: {str(e)}"
        )


@router.get("/taxonomy-consistency", response_model=TaxonomyConsistency)
async def get_taxonomy_consistency(
    entity: str = Query(default="taxon", description="Taxonomy entity name"),
):
    """
    Get taxonomy consistency analysis.

    Returns hierarchy levels, orphan records, and duplicate detection.
    Supports both:
    - Niamoto hierarchical structure (rank_name column)
    - Flat structure with separate columns (family, genus, species)
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer

            # Find taxonomy table
            table_names = inspector.get_table_names() or []
            target_table = None
            for t in table_names:
                if entity.lower() in t.lower() or "taxon" in t.lower():
                    target_table = t
                    break

            if not target_table:
                return TaxonomyConsistency(
                    total_taxa=0,
                    levels=[],
                    orphan_records=[],
                    duplicate_names=[],
                    hierarchy_depth=0,
                )

            quoted_table = preparer.quote(target_table)
            columns_info = inspector.get_columns(target_table)
            column_names = [c["name"].lower() for c in columns_info]

            with db.engine.connect() as conn:
                # Total count
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                total = result.scalar() or 0

                levels = []

                # Strategy 1: Check for Niamoto hierarchical structure (rank_name column)
                if "rank_name" in column_names:
                    # Get hierarchy levels from rank_name column
                    result = conn.execute(
                        text(
                            f"""
                            SELECT rank_name, COUNT(*) as cnt
                            FROM {quoted_table}
                            WHERE rank_name IS NOT NULL
                            GROUP BY rank_name
                            ORDER BY MIN(level)
                        """
                        )
                    )
                    # Fetch all rows before executing any other query (DuckDB closes cursor on new query)
                    all_rows = result.fetchall()

                    for row in all_rows:
                        rank_name = row[0]
                        count = row[1]
                        # Count orphans (records without parent when they should have one)
                        orphan_count = 0
                        if "parent_id" in column_names and "level" in column_names:
                            orphan_result = conn.execute(
                                text(
                                    f"""
                                    SELECT COUNT(*) FROM {quoted_table}
                                    WHERE rank_name = :rank_name
                                    AND level > 0
                                    AND parent_id IS NULL
                                """
                                ),
                                {"rank_name": rank_name},
                            )
                            orphan_count = orphan_result.scalar() or 0

                        levels.append(
                            TaxonomyLevel(
                                level=rank_name, count=count, orphan_count=orphan_count
                            )
                        )
                else:
                    # Strategy 2: Detect hierarchy from separate columns
                    rank_patterns = [
                        "kingdom",
                        "phylum",
                        "class",
                        "order",
                        "family",
                        "genus",
                        "species",
                    ]
                    for pattern in rank_patterns:
                        for col in columns_info:
                            if pattern in col["name"].lower():
                                quoted_col = preparer.quote(col["name"])
                                result = conn.execute(
                                    text(
                                        f"SELECT COUNT(DISTINCT {quoted_col}) FROM {quoted_table} WHERE {quoted_col} IS NOT NULL"
                                    )
                                )
                                count = result.scalar() or 0
                                if count > 0:
                                    levels.append(
                                        TaxonomyLevel(
                                            level=pattern, count=count, orphan_count=0
                                        )
                                    )
                                break

                # Check for duplicates in name/full_name column
                name_col = None
                for col in columns_info:
                    col_name_lower = col["name"].lower()
                    if col_name_lower in ["full_name", "rank_value", "name"]:
                        name_col = col["name"]
                        break

                duplicates = []
                if name_col:
                    quoted_name = preparer.quote(name_col)
                    result = conn.execute(
                        text(
                            f"""
                            SELECT {quoted_name}, COUNT(*) as cnt
                            FROM {quoted_table}
                            WHERE {quoted_name} IS NOT NULL
                            GROUP BY {quoted_name}
                            HAVING COUNT(*) > 1
                            LIMIT 10
                        """
                        )
                    )
                    for row in result:
                        duplicates.append({"name": row[0], "count": row[1]})

            return TaxonomyConsistency(
                total_taxa=total,
                levels=levels,
                orphan_records=[],
                duplicate_names=duplicates,
                hierarchy_depth=len(levels),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting taxonomy consistency: {str(e)}"
        )


@router.get("/value-validation/{entity}", response_model=EntityValidation)
async def get_value_validation(
    entity: str,
    columns: Optional[str] = Query(
        default=None, description="Comma-separated list of columns to validate"
    ),
    method: str = Query(
        default="iqr", description="Outlier detection method: iqr, zscore, percentile"
    ),
    threshold: float = Query(
        default=1.5, description="Threshold for outlier detection"
    ),
):
    """
    Get validation statistics for numeric columns.

    Returns min/max/median/outliers per column with configurable detection.
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer

            if entity not in inspector.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity}' not found"
                )

            quoted_table = preparer.quote(entity)
            columns_info = inspector.get_columns(entity)

            # Filter to numeric columns
            numeric_types = ["INTEGER", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"]
            target_columns = []

            if columns:
                requested = [c.strip() for c in columns.split(",")]
                for col in columns_info:
                    if col["name"] in requested:
                        target_columns.append(col)
            else:
                for col in columns_info:
                    col_type = str(col.get("type", "")).upper()
                    if any(nt in col_type for nt in numeric_types):
                        target_columns.append(col)

            validations = []

            with db.engine.connect() as conn:
                for col in target_columns:
                    col_name = col["name"]
                    quoted_col = preparer.quote(col_name)

                    # Basic stats
                    result = conn.execute(
                        text(
                            f"""
                        SELECT
                            MIN({quoted_col}),
                            MAX({quoted_col}),
                            AVG({quoted_col})
                        FROM {quoted_table}
                        WHERE {quoted_col} IS NOT NULL
                    """
                        )
                    )
                    row = result.fetchone()

                    if row and row[0] is not None:
                        min_val = float(row[0]) if row[0] is not None else None
                        max_val = float(row[1]) if row[1] is not None else None
                        mean_val = float(row[2]) if row[2] is not None else None

                        # Median (approximate for DuckDB)
                        try:
                            result = conn.execute(
                                text(
                                    f"SELECT MEDIAN({quoted_col}) FROM {quoted_table} WHERE {quoted_col} IS NOT NULL"
                                )
                            )
                            median_val = result.scalar()
                            median_val = float(median_val) if median_val else None
                        except Exception:
                            median_val = None

                        # IQR-based outlier detection
                        outliers = []
                        outlier_count = 0

                        if method == "iqr":
                            try:
                                result = conn.execute(
                                    text(
                                        f"""
                                    SELECT
                                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {quoted_col}),
                                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {quoted_col})
                                    FROM {quoted_table}
                                    WHERE {quoted_col} IS NOT NULL
                                """
                                    )
                                )
                                q_row = result.fetchone()
                                if q_row and q_row[0] is not None:
                                    q1, q3 = float(q_row[0]), float(q_row[1])
                                    iqr = q3 - q1
                                    lower = q1 - threshold * iqr
                                    upper = q3 + threshold * iqr

                                    # Count outliers
                                    result = conn.execute(
                                        text(
                                            f"""
                                        SELECT COUNT(*) FROM {quoted_table}
                                        WHERE {quoted_col} IS NOT NULL
                                        AND ({quoted_col} < {lower} OR {quoted_col} > {upper})
                                    """
                                        )
                                    )
                                    outlier_count = result.scalar() or 0

                                    # Get sample outliers
                                    result = conn.execute(
                                        text(
                                            f"""
                                        SELECT * FROM {quoted_table}
                                        WHERE {quoted_col} IS NOT NULL
                                        AND ({quoted_col} < {lower} OR {quoted_col} > {upper})
                                        LIMIT 5
                                    """
                                        )
                                    )
                                    for out_row in result:
                                        outliers.append(dict(out_row._mapping))
                            except Exception:
                                pass

                        validations.append(
                            ColumnValidation(
                                column=col_name,
                                min_value=min_val,
                                max_value=max_val,
                                mean_value=mean_val,
                                median_value=median_val,
                                std_dev=None,
                                outlier_count=outlier_count,
                                outliers=outliers[:5],
                            )
                        )
                    else:
                        validations.append(
                            ColumnValidation(
                                column=col_name,
                                min_value=None,
                                max_value=None,
                                mean_value=None,
                                median_value=None,
                                std_dev=None,
                                outlier_count=0,
                                outliers=[],
                            )
                        )

            return EntityValidation(entity=entity, columns=validations)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validating values: {str(e)}"
        )


@router.get("/geo-coverage", response_model=GeoCoverage)
async def get_geo_coverage(
    occurrence_entity: str = Query(
        default="occurrences", description="Occurrences entity"
    ),
):
    """
    Get geographic coverage overview.

    Returns info about occurrences and available shapes for spatial analysis.
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer
            table_names = inspector.get_table_names() or []

            # Find occurrence table
            occ_table = None
            for t in table_names:
                if occurrence_entity.lower() in t.lower():
                    occ_table = t
                    break

            if not occ_table:
                return GeoCoverage(
                    total_occurrences=0,
                    occurrences_with_geo=0,
                    geo_column=None,
                    available_shapes=[],
                    ready_for_analysis=False,
                )

            quoted_occ = preparer.quote(occ_table)

            # Get total occurrences
            with db.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_occ}"))
                total = result.scalar() or 0

            # Find geo column in occurrences
            columns_info = inspector.get_columns(occ_table)
            geo_column = None
            native_geo_patterns = ["_geom", "geometry", "the_geom", "wkb_geometry"]
            wkt_patterns = ["geo_pt", "geo", "geom", "location", "wkt"]

            for col in columns_info:
                col_name = col["name"].lower()
                col_type = str(col.get("type", "")).upper()

                if "GEOMETRY" in col_type or "BYTEA" in col_type:
                    if any(
                        col_name.endswith(p) or col_name == p
                        for p in native_geo_patterns
                    ):
                        geo_column = col["name"]
                        break
                elif any(p in col_name for p in wkt_patterns):
                    if geo_column is None:
                        geo_column = col["name"]

            # Count occurrences with geometry
            occ_with_geo = 0
            if geo_column:
                quoted_geo = preparer.quote(geo_column)
                with db.engine.connect() as conn:
                    result = conn.execute(
                        text(
                            f"SELECT COUNT(*) FROM {quoted_occ} WHERE {quoted_geo} IS NOT NULL"
                        )
                    )
                    occ_with_geo = result.scalar() or 0

            # Find shape tables and their info
            shape_keywords = [
                "shape",
                "commune",
                "province",
                "foret",
                "forest",
                "zone",
                "region",
                "limite",
            ]
            native_shape_geo_patterns = [
                "_geom",
                "geometry",
                "the_geom",
                "wkb_geometry",
            ]
            wkt_shape_geo_patterns = ["geo", "geom", "wkt", "location"]

            available_shapes = []

            for t in table_names:
                t_lower = t.lower()
                if any(kw in t_lower for kw in shape_keywords):
                    t_columns = inspector.get_columns(t)
                    has_geo = False

                    for col in t_columns:
                        col_type = str(col.get("type", "")).upper()
                        col_name = col["name"].lower()

                        if "GEOMETRY" in col_type or "BYTEA" in col_type:
                            if any(
                                col_name.endswith(p) or col_name == p
                                for p in native_shape_geo_patterns
                            ):
                                has_geo = True
                                break
                        elif col_name in wkt_shape_geo_patterns:
                            has_geo = True
                            break

                    # Get shape count and types
                    quoted_t = preparer.quote(t)
                    with db.engine.connect() as conn:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_t}"))
                        shape_count = result.scalar() or 0

                        # Try to get distinct shape types
                        shape_types = []
                        try:
                            result = conn.execute(
                                text(
                                    f"""
                                    SELECT DISTINCT COALESCE(shape_type, type, 'unknown')
                                    FROM {quoted_t}
                                    WHERE COALESCE(shape_type, type, 'unknown') != 'unknown'
                                    LIMIT 10
                                """
                                )
                            )
                            shape_types = [row[0] for row in result.fetchall()]
                        except Exception:
                            pass

                    available_shapes.append(
                        ShapeInfo(
                            table_name=t,
                            display_name=t.replace("_", " ")
                            .replace("entity ", "")
                            .title(),
                            shape_count=shape_count,
                            has_geometry=has_geo,
                            shape_types=shape_types,
                        )
                    )

            ready = bool(
                geo_column
                and occ_with_geo > 0
                and any(s.has_geometry for s in available_shapes)
            )

            return GeoCoverage(
                total_occurrences=total,
                occurrences_with_geo=occ_with_geo,
                geo_column=geo_column,
                available_shapes=available_shapes,
                ready_for_analysis=ready,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting geo coverage: {str(e)}"
        )


@router.post("/geo-coverage/analyze", response_model=SpatialAnalysisResult)
async def analyze_spatial_coverage(
    occurrence_entity: str = Query(
        default="occurrences", description="Occurrences entity"
    ),
):
    """
    Run full spatial analysis (on demand).

    Detects geo column in occurrences and checks coverage against all shape tables
    using spatial intersection queries. This can be slow with many occurrences.
    """
    import time

    start_time = time.time()

    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer
            table_names = inspector.get_table_names() or []

            # Find occurrence table
            occ_table = None
            for t in table_names:
                if occurrence_entity.lower() in t.lower():
                    occ_table = t
                    break

            if not occ_table:
                return SpatialAnalysisResult(
                    total_occurrences=0,
                    occurrences_with_geo=0,
                    occurrences_without_geo=0,
                    shape_coverage=[],
                    analysis_time_seconds=time.time() - start_time,
                    geo_column=None,
                    status="error",
                    message=f"Occurrence table '{occurrence_entity}' not found",
                )

            # Find geo column in occurrences
            # Priority: native GEOMETRY columns (BYTEA in SQLAlchemy) > WKT text columns
            columns_info = inspector.get_columns(occ_table)
            geo_column = None
            wkt_column = None
            occ_geo_is_native = False

            # Patterns for native geometry columns (ending in _geom or named geometry)
            native_geo_patterns = ["_geom", "geometry", "the_geom", "wkb_geometry"]
            # Patterns for WKT text columns
            wkt_patterns = ["geo_pt", "geo", "geom", "location", "wkt"]

            for col in columns_info:
                col_name = col["name"].lower()
                col_type = str(col.get("type", "")).upper()

                # Check for native GEOMETRY (reported as BYTEA or GEOMETRY by SQLAlchemy)
                if "GEOMETRY" in col_type or "BYTEA" in col_type:
                    # Only treat as native geometry if name matches expected patterns
                    if any(
                        col_name.endswith(p) or col_name == p
                        for p in native_geo_patterns
                    ):
                        geo_column = col["name"]
                        occ_geo_is_native = True
                        break
                # Track potential WKT columns as fallback
                elif any(p in col_name for p in wkt_patterns):
                    if wkt_column is None:
                        wkt_column = col["name"]

            # Use WKT column if no native GEOMETRY found
            if not geo_column and wkt_column:
                geo_column = wkt_column
                occ_geo_is_native = False

            if not geo_column:
                return SpatialAnalysisResult(
                    total_occurrences=0,
                    occurrences_with_geo=0,
                    occurrences_without_geo=0,
                    shape_coverage=[],
                    analysis_time_seconds=time.time() - start_time,
                    geo_column=None,
                    status="no_geo_column",
                    message="No geometry column found in occurrences. Expected: geo, geom, geometry, location",
                )

            quoted_occ = preparer.quote(occ_table)
            quoted_geo = preparer.quote(geo_column)

            # Find shape tables with geometry columns
            # Each entry: (table_name, geo_column, is_native_geometry)
            shape_tables = []
            shape_tables_without_geo = []
            shape_keywords = [
                "shape",
                "commune",
                "province",
                "foret",
                "forest",
                "zone",
                "region",
                "limite",
            ]

            # Patterns for detecting geometry columns
            native_shape_geo_patterns = [
                "_geom",
                "geometry",
                "the_geom",
                "wkb_geometry",
            ]
            wkt_shape_geo_patterns = ["geo", "geom", "wkt", "location"]

            for t in table_names:
                t_lower = t.lower()
                if any(kw in t_lower for kw in shape_keywords):
                    # Check if it has a geometry column
                    # Priority: native GEOMETRY type (BYTEA) > WKT column names
                    t_columns = inspector.get_columns(t)
                    native_geo_col = None
                    wkt_geo_col = None

                    for col in t_columns:
                        col_type = str(col.get("type", "")).upper()
                        col_name = col["name"].lower()

                        # Native GEOMETRY type (BYTEA in SQLAlchemy, highest priority)
                        if "GEOMETRY" in col_type or "BYTEA" in col_type:
                            if any(
                                col_name.endswith(p) or col_name == p
                                for p in native_shape_geo_patterns
                            ):
                                native_geo_col = col["name"]
                                break
                        # WKT column names (fallback)
                        elif col_name in wkt_shape_geo_patterns:
                            if wkt_geo_col is None:
                                wkt_geo_col = col["name"]

                    if native_geo_col:
                        shape_tables.append((t, native_geo_col, True))  # is_native=True
                    elif wkt_geo_col:
                        shape_tables.append((t, wkt_geo_col, False))  # is_native=False
                    else:
                        shape_tables_without_geo.append(t)

            if not shape_tables:
                # No shape tables with geometry found
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_occ}"))
                    total = result.scalar() or 0

                    result = conn.execute(
                        text(
                            f"SELECT COUNT(*) FROM {quoted_occ} WHERE {quoted_geo} IS NOT NULL"
                        )
                    )
                    with_geo = result.scalar() or 0

                if shape_tables_without_geo:
                    msg = f"Shape tables found ({', '.join(shape_tables_without_geo)}) but they have no geometry column. Import shapes with geometry to analyze coverage."
                else:
                    msg = "No shape tables found. Import shapes to analyze coverage."

                return SpatialAnalysisResult(
                    total_occurrences=total,
                    occurrences_with_geo=with_geo,
                    occurrences_without_geo=total - with_geo,
                    shape_coverage=[],
                    analysis_time_seconds=time.time() - start_time,
                    geo_column=geo_column,
                    status="no_shapes",
                    message=msg,
                )

            # Run spatial analysis
            shape_coverage = []

            with db.engine.connect() as conn:
                # Get occurrence counts
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_occ}"))
                total_occ = result.scalar() or 0

                result = conn.execute(
                    text(
                        f"SELECT COUNT(*) FROM {quoted_occ} WHERE {quoted_geo} IS NOT NULL"
                    )
                )
                with_geo = result.scalar() or 0

                # For each shape table, count occurrences that intersect
                for shape_table, shape_geo_col, shape_is_native in shape_tables:
                    quoted_shape = preparer.quote(shape_table)
                    quoted_shape_geo = preparer.quote(shape_geo_col)

                    # Count total shapes
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_shape}"))
                    total_shapes = result.scalar() or 0

                    if total_shapes == 0:
                        continue

                    # Build geometry expressions based on column types
                    # Native GEOMETRY columns can be used directly
                    # WKT text columns need ST_GeomFromText conversion
                    if occ_geo_is_native:
                        occ_geom_expr = f"o.{quoted_geo}"
                    else:
                        occ_geom_expr = f"ST_GeomFromText(o.{quoted_geo})"

                    if shape_is_native:
                        shape_geom_expr = f"s.{quoted_shape_geo}"
                    else:
                        shape_geom_expr = f"ST_GeomFromText(s.{quoted_shape_geo})"

                    # Count occurrences covered by any shape
                    # Using ST_Intersects for DuckDB spatial
                    try:
                        # Load spatial extension for this connection
                        conn.execute(text("LOAD spatial"))

                        # Use COUNT(*) instead of COUNT(DISTINCT rowid) for DuckDB
                        result = conn.execute(
                            text(
                                f"""
                                SELECT COUNT(*)
                                FROM {quoted_occ} o
                                WHERE o.{quoted_geo} IS NOT NULL
                                AND EXISTS (
                                    SELECT 1 FROM {quoted_shape} s
                                    WHERE s.{quoted_shape_geo} IS NOT NULL
                                    AND ST_Intersects({occ_geom_expr}, {shape_geom_expr})
                                )
                            """
                            )
                        )
                        covered = result.scalar() or 0
                    except Exception:
                        # Fallback: try with ST_Contains
                        try:
                            result = conn.execute(
                                text(
                                    f"""
                                    SELECT COUNT(*)
                                    FROM {quoted_occ} o
                                    WHERE o.{quoted_geo} IS NOT NULL
                                    AND EXISTS (
                                        SELECT 1 FROM {quoted_shape} s
                                        WHERE s.{quoted_shape_geo} IS NOT NULL
                                        AND ST_Contains({shape_geom_expr}, {occ_geom_expr})
                                    )
                                """
                                )
                            )
                            covered = result.scalar() or 0
                        except Exception:
                            # Spatial functions not available or query failed
                            covered = 0

                    coverage_pct = (covered / with_geo * 100) if with_geo > 0 else 0

                    shape_coverage.append(
                        ShapeCoverageDetail(
                            shape_type=shape_table.replace("_", " ").title(),
                            shape_table=shape_table,
                            total_shapes=total_shapes,
                            occurrences_covered=covered,
                            coverage_percent=round(coverage_pct, 1),
                        )
                    )

            return SpatialAnalysisResult(
                total_occurrences=total_occ,
                occurrences_with_geo=with_geo,
                occurrences_without_geo=total_occ - with_geo,
                shape_coverage=shape_coverage,
                analysis_time_seconds=round(time.time() - start_time, 2),
                geo_column=geo_column,
                status="success",
                message=None,
            )

    except HTTPException:
        raise
    except Exception as e:
        return SpatialAnalysisResult(
            total_occurrences=0,
            occurrences_with_geo=0,
            occurrences_without_geo=0,
            shape_coverage=[],
            analysis_time_seconds=0,
            geo_column=None,
            status="error",
            message=str(e),
        )


@router.post("/geo-coverage/distribution", response_model=ShapeDistributionResult)
async def get_shape_distribution(
    occurrence_entity: str = Query(
        default="occurrences", description="Occurrences entity"
    ),
):
    """
    Get distribution of occurrences by individual shape.

    Returns the count of occurrences that fall within each shape polygon.
    This is computed on demand and may take some time for large datasets.
    """
    import time

    start_time = time.time()

    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            inspector = inspect(db.engine)
            preparer = db.engine.dialect.identifier_preparer
            table_names = inspector.get_table_names() or []

            # Find occurrence table
            occ_table = None
            for t in table_names:
                if occurrence_entity.lower() in t.lower():
                    occ_table = t
                    break

            if not occ_table:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="error",
                    message=f"Occurrence table '{occurrence_entity}' not found",
                )

            # Find geo column in occurrences (prioritize native GEOMETRY)
            columns_info = inspector.get_columns(occ_table)
            geo_column = None
            occ_geo_is_native = False
            native_geo_patterns = ["_geom", "geometry", "the_geom", "wkb_geometry"]
            wkt_patterns = ["geo_pt", "geo", "geom", "location", "wkt"]

            for col in columns_info:
                col_name = col["name"].lower()
                col_type = str(col.get("type", "")).upper()

                if "GEOMETRY" in col_type or "BYTEA" in col_type:
                    if any(
                        col_name.endswith(p) or col_name == p
                        for p in native_geo_patterns
                    ):
                        geo_column = col["name"]
                        occ_geo_is_native = True
                        break
                elif any(p in col_name for p in wkt_patterns):
                    if geo_column is None:
                        geo_column = col["name"]

            if not geo_column:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="no_geo_column",
                    message="No geometry column found in occurrences",
                )

            # Find shape table with geometry
            shape_table = None
            shape_geo_col = None
            shape_is_native = False
            shape_keywords = [
                "shape",
                "commune",
                "province",
                "foret",
                "forest",
                "zone",
                "region",
                "limite",
            ]
            native_shape_geo_patterns = [
                "_geom",
                "geometry",
                "the_geom",
                "wkb_geometry",
            ]
            wkt_shape_geo_patterns = ["geo", "geom", "wkt", "location"]

            for t in table_names:
                t_lower = t.lower()
                if any(kw in t_lower for kw in shape_keywords):
                    t_columns = inspector.get_columns(t)
                    for col in t_columns:
                        col_type = str(col.get("type", "")).upper()
                        col_name = col["name"].lower()

                        if "GEOMETRY" in col_type or "BYTEA" in col_type:
                            if any(
                                col_name.endswith(p) or col_name == p
                                for p in native_shape_geo_patterns
                            ):
                                shape_table = t
                                shape_geo_col = col["name"]
                                shape_is_native = True
                                break
                        elif col_name in wkt_shape_geo_patterns:
                            if shape_geo_col is None:
                                shape_table = t
                                shape_geo_col = col["name"]

                    if shape_table:
                        break

            if not shape_table:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="no_shapes",
                    message="No shape table with geometry found",
                )

            quoted_occ = preparer.quote(occ_table)
            quoted_geo = preparer.quote(geo_column)
            quoted_shape = preparer.quote(shape_table)
            quoted_shape_geo = preparer.quote(shape_geo_col)

            # Build geometry expressions
            if occ_geo_is_native:
                occ_geom_expr = f"o.{quoted_geo}"
            else:
                occ_geom_expr = f"ST_GeomFromText(o.{quoted_geo})"

            if shape_is_native:
                shape_geom_expr = f"s.{quoted_shape_geo}"
            else:
                shape_geom_expr = f"ST_GeomFromText(s.{quoted_shape_geo})"

            with db.engine.connect() as conn:
                # Load spatial extension
                conn.execute(text("LOAD spatial"))

                # Get total occurrences with geometry
                result = conn.execute(
                    text(
                        f"SELECT COUNT(*) FROM {quoted_occ} WHERE {quoted_geo} IS NOT NULL"
                    )
                )
                total_with_geo = result.scalar() or 0

                # Get occurrence count per shape
                # Using a lateral join approach for performance
                result = conn.execute(
                    text(
                        f"""
                        SELECT
                            s.id as shape_id,
                            s.name as shape_name,
                            COALESCE(s.shape_type, s.type, 'unknown') as shape_type,
                            COUNT(o.id) as occurrence_count
                        FROM {quoted_shape} s
                        LEFT JOIN {quoted_occ} o
                            ON o.{quoted_geo} IS NOT NULL
                            AND s.{quoted_shape_geo} IS NOT NULL
                            AND ST_Intersects({occ_geom_expr}, {shape_geom_expr})
                        WHERE s.{quoted_shape_geo} IS NOT NULL
                        GROUP BY s.id, s.name, COALESCE(s.shape_type, s.type, 'unknown')
                        ORDER BY occurrence_count DESC
                    """
                    )
                )
                rows = result.fetchall()

                shapes = []
                for row in rows:
                    count = row[3] or 0
                    pct = (count / total_with_geo * 100) if total_with_geo > 0 else 0
                    shapes.append(
                        ShapeOccurrenceCount(
                            shape_id=row[0],
                            shape_name=row[1] or f"Shape {row[0]}",
                            shape_type=row[2] or "unknown",
                            occurrence_count=count,
                            percent_of_total=round(pct, 2),
                        )
                    )

            return ShapeDistributionResult(
                total_occurrences_with_geo=total_with_geo,
                shapes=shapes,
                analysis_time_seconds=round(time.time() - start_time, 2),
                status="success",
                message=None,
            )

    except HTTPException:
        raise
    except Exception as e:
        return ShapeDistributionResult(
            total_occurrences_with_geo=0,
            shapes=[],
            analysis_time_seconds=0,
            status="error",
            message=str(e),
        )


@router.get("/validation/rules", response_model=ValidationRules)
async def get_validation_rules():
    """
    Get configured validation rules.

    Returns rules from config/validation.yml if it exists.
    """
    import yaml

    work_dir = get_working_directory()
    rules_path = work_dir / "config" / "validation.yml"

    if not rules_path.exists():
        # Return defaults
        return ValidationRules(
            rules=[
                ValidationRule(
                    rule_type="outlier",
                    target="*",
                    method="iqr",
                    params={"threshold": 1.5},
                ),
                ValidationRule(
                    rule_type="bounds",
                    target="coordinates",
                    method="auto",
                    params={"margin": 0.1},
                ),
            ]
        )

    try:
        with open(rules_path, "r") as f:
            config = yaml.safe_load(f) or {}

        rules = []
        for rule_data in config.get("rules", []):
            rules.append(
                ValidationRule(
                    rule_type=rule_data.get("type", "outlier"),
                    target=rule_data.get("target", "*"),
                    method=rule_data.get("method", "iqr"),
                    params=rule_data.get("params", {}),
                )
            )

        return ValidationRules(rules=rules)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading validation rules: {str(e)}"
        )


@router.put("/validation/rules", response_model=ValidationRules)
async def update_validation_rules(rules: ValidationRules):
    """
    Save validation rules to config/validation.yml.
    """
    import yaml

    work_dir = get_working_directory()
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    rules_path = config_dir / "validation.yml"

    try:
        rules_data = {
            "rules": [
                {
                    "type": r.rule_type,
                    "target": r.target,
                    "method": r.method,
                    "params": r.params,
                }
                for r in rules.rules
            ]
        }

        with open(rules_path, "w") as f:
            yaml.safe_dump(rules_data, f, default_flow_style=False)

        return rules

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving validation rules: {str(e)}"
        )
