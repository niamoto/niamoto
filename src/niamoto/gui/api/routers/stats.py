"""Import statistics API endpoints for post-import dashboard."""

import csv
import html
import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
import yaml

from niamoto.common.database import Database
from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_dataset_table_name,
    resolve_entity_table_name,
    resolve_reference_table_name,
)
from niamoto.common.hierarchy_context import (
    HierarchyMetadata,
    detect_hierarchy_metadata,
)
from ..utils.database import open_database
from ..context import get_working_directory
from .database import get_database_path
from ..services.map_renderer import MapConfig, MapRenderer, MapStyle
from ..services.preview_utils import error_html, wrap_html_response

router = APIRouter()
logger = logging.getLogger(__name__)
NIAMOTO_MAP_GREEN = "#2E7D32"
_WKT_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


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


class ImportSummary(BaseModel):
    """Global import summary."""

    total_entities: int
    total_rows: int
    entities: List[EntitySummary]
    alerts: List[Dict[str, Any]]


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


class SpatialMapLayer(BaseModel):
    """One selectable spatial layer for a mappable reference."""

    value: str
    label: str
    feature_count: int
    with_geometry: int


class SpatialMapInspection(BaseModel):
    """Bounded GeoJSON inspection for a mappable reference."""

    reference_name: str
    table_name: Optional[str]
    is_mappable: bool
    reason: Optional[str] = None
    geometry_column: Optional[str] = None
    geometry_storage: Optional[str] = None
    geometry_kind: str = "unknown"
    geometry_types: List[str] = Field(default_factory=list)
    id_column: Optional[str] = None
    name_column: Optional[str] = None
    type_column: Optional[str] = None
    layer_column: Optional[str] = None
    selected_layer: Optional[str] = None
    layers: List[SpatialMapLayer] = Field(default_factory=list)
    total_features: int = 0
    with_geometry: int = 0
    without_geometry: int = 0
    bounding_box: Optional[Dict[str, float]] = None
    feature_collection: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "FeatureCollection", "features": []}
    )
    limit: int
    offset: int = 0
    result_count: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None


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


class HierarchyNode(BaseModel):
    """One node in a bounded hierarchy inspection response."""

    id: Any
    parent_id: Optional[Any] = None
    label: str
    rank: Optional[str] = None
    level: Optional[int] = None
    child_count: int = 0
    has_children: bool = False
    path: Optional[str] = None


class HierarchyInspection(BaseModel):
    """Bounded hierarchy inspection for a reference."""

    reference_name: str
    table_name: Optional[str]
    is_hierarchical: bool
    metadata_available: bool
    mode: str
    search: Optional[str] = None
    parent_id: Optional[Any] = None
    total_nodes: int = 0
    root_count: int = 0
    orphan_count: int = 0
    levels: List[TaxonomyLevel] = Field(default_factory=list)
    nodes: List[HierarchyNode] = Field(default_factory=list)
    limit: int
    offset: int = 0
    result_count: int = 0
    has_more: bool = False
    next_offset: Optional[int] = None


class HistogramBin(BaseModel):
    """A bin in a histogram."""

    bin_start: float
    bin_end: float
    count: int
    is_outlier_zone: bool = False


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
    # New fields for enhanced outlier analysis
    lower_bound: Optional[float] = None  # Threshold below which values are outliers
    upper_bound: Optional[float] = None  # Threshold above which values are outliers
    outliers_low_count: int = 0  # Count of outliers below lower_bound
    outliers_high_count: int = 0  # Count of outliers above upper_bound
    histogram: Optional[List[HistogramBin]] = None  # Distribution histogram


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

    shape_id: str
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


def classify_table_type(table_name: str) -> str:
    """Classify a table as dataset, reference, or layer (fallback heuristics)."""
    table_lower = table_name.lower()

    # Layers (metadata)
    if any(layer in table_lower for layer in ["layer", "raster", "vector", "dem"]):
        return "layer"

    # Conservative fallback: treat unknown business tables as dataset.
    return "dataset"


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
    resolved = resolve_entity_table_name(table_names, pattern)
    if resolved:
        return resolved

    pattern_lower = pattern.lower()

    # Partial match
    for t in table_names:
        if pattern_lower in t.lower():
            return t

    return None


def _load_import_entities_config() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load datasets/references definitions from import.yml when available."""
    try:
        work_dir = get_working_directory()
        if not work_dir:
            return {}, {}

        import_path = Path(work_dir) / "config" / "import.yml"
        if not import_path.exists():
            return {}, {}

        with open(import_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        entities = config.get("entities", {}) or {}
        datasets = entities.get("datasets", {}) or {}
        references = entities.get("references", {}) or {}

        if not isinstance(datasets, dict):
            datasets = {}
        if not isinstance(references, dict):
            references = {}

        return datasets, references
    except Exception as exc:
        logger.debug("Failed to load entities from import.yml: %s", exc)
        return {}, {}


def _resolve_physical_table_name(
    table_names: List[str], logical_name: Optional[str]
) -> Optional[str]:
    """Resolve logical entity name to an existing physical table."""
    return resolve_entity_table_name(table_names, logical_name)


def _resolve_occurrence_table(
    table_names: List[str], occurrence_entity: str, datasets: Dict[str, Any]
) -> Optional[str]:
    """Resolve occurrence dataset table from explicit query param, then config."""
    # 1) Explicit entity/table requested by caller.
    resolved = resolve_dataset_table_name(table_names, occurrence_entity)
    if resolved:
        return resolved

    # 2) Preferred dataset from import config.
    preferred_dataset = None
    if occurrence_entity in datasets:
        preferred_dataset = occurrence_entity
    elif "occurrences" in datasets:
        preferred_dataset = "occurrences"
    elif datasets:
        preferred_dataset = next(iter(datasets))

    resolved = resolve_dataset_table_name(table_names, preferred_dataset)
    if resolved:
        return resolved

    # 3) Last-resort fuzzy match for backward compatibility.
    for table in table_names:
        if occurrence_entity.lower() in table.lower():
            return table
    return None


def _resolve_entity_table(
    table_names: List[str],
    entity_name: str,
    datasets: Dict[str, Any],
    references: Dict[str, Any],
) -> Optional[str]:
    """Resolve any dataset/reference logical name to a physical table."""
    if entity_name in references:
        resolved = resolve_reference_table_name(table_names, entity_name)
        if resolved:
            return resolved
    if entity_name in datasets:
        resolved = resolve_dataset_table_name(table_names, entity_name)
        if resolved:
            return resolved

    resolved = resolve_entity_table_name(table_names, entity_name)
    if resolved:
        return resolved

    # Special case: default occurrence entity with project-specific dataset naming.
    if entity_name == "occurrences":
        resolved = _resolve_occurrence_table(table_names, entity_name, datasets)
        if resolved:
            return resolved

    # Backward-compatible fuzzy fallback.
    return find_table_by_pattern(table_names, entity_name)


def _build_entity_type_map(
    table_names: List[str], datasets: Dict[str, Any], references: Dict[str, Any]
) -> Dict[str, str]:
    """Build table->entity_type mapping from config metadata."""
    type_map: Dict[str, str] = {}

    for dataset_name in datasets:
        table = resolve_dataset_table_name(table_names, dataset_name)
        if table:
            type_map[table] = "dataset"

    for ref_name in references:
        table = resolve_reference_table_name(table_names, ref_name)
        if table:
            type_map[table] = "reference"

    return type_map


def _resolve_taxonomy_table_name(
    table_names: List[str], references: Dict[str, Any], requested: str
) -> Optional[str]:
    """Resolve taxonomy reference table from explicit request/config metadata."""
    # 1) Explicit reference name from query.
    resolved = resolve_reference_table_name(table_names, requested)
    if resolved:
        return resolved

    # 2) If requested matches a configured reference, use it.
    if requested in references:
        resolved = resolve_reference_table_name(table_names, requested)
        if resolved:
            return resolved

    # 3) Prefer first hierarchical reference from config.
    for ref_name, ref_cfg in references.items():
        if isinstance(ref_cfg, dict) and ref_cfg.get("kind") == "hierarchical":
            resolved = resolve_reference_table_name(table_names, ref_name)
            if resolved:
                return resolved

    # 4) Fallback to legacy fuzzy match for compatibility with older DBs.
    return find_table_by_pattern(table_names, requested)


def _resolve_hierarchy_reference_table(
    table_names: List[str], references: Dict[str, Any], reference_name: str
) -> Optional[str]:
    """Resolve a reference name for hierarchy inspection."""
    if reference_name in references:
        return resolve_reference_table_name(table_names, reference_name)

    return resolve_reference_table_name(table_names, reference_name)


def _is_reference_hierarchical(
    reference_name: str,
    references: Dict[str, Any],
    metadata: Optional[HierarchyMetadata],
) -> bool:
    """Return whether the reference should expose hierarchy inspection."""
    ref_cfg = references.get(reference_name)
    if isinstance(ref_cfg, dict):
        return ref_cfg.get("kind") in {"hierarchical", "nested"}

    # Fallback for projects without import.yml metadata.
    return metadata is not None


def _dict_config(value: Any) -> Dict[str, Any]:
    """Return a mapping-like config section or an empty dict."""
    return value if isinstance(value, dict) else {}


def _detect_configured_hierarchy_metadata(
    columns: List[str], ref_cfg: Dict[str, Any]
) -> Optional[HierarchyMetadata]:
    """Detect hierarchy columns, preferring explicit import.yml metadata."""
    schema = _dict_config(ref_cfg.get("schema"))
    hierarchy = _dict_config(ref_cfg.get("hierarchy"))
    connector = _dict_config(ref_cfg.get("connector"))
    extraction = _dict_config(connector.get("extraction"))

    columns_by_lower = {column.lower(): column for column in columns}

    def pick(candidates: List[Optional[str]]) -> Optional[str]:
        return _pick_first_existing(columns_by_lower, candidates)

    id_field = pick(
        [
            hierarchy.get("id_field"),
            schema.get("id_field"),
            extraction.get("id_column"),
            "id",
        ]
    )
    parent_field = pick(
        [
            hierarchy.get("parent_field"),
            hierarchy.get("parent_id_field"),
            schema.get("parent_field"),
            "parent_id",
            "parent",
            "id_parent",
        ]
    )
    left_field = pick(
        [
            hierarchy.get("left_field"),
            schema.get("left_field"),
            "lft",
            "left",
            "left_bound",
        ]
    )
    right_field = pick(
        [
            hierarchy.get("right_field"),
            schema.get("right_field"),
            "rght",
            "rgt",
            "right",
            "right_bound",
        ]
    )
    rank_field = pick(
        [
            hierarchy.get("rank_field"),
            hierarchy.get("level_field"),
            schema.get("rank_field"),
            "rank_name",
            "rank",
            "rank_value",
            "level_name",
            "level",
            "category",
        ]
    )
    name_field = pick(
        [
            hierarchy.get("name_field"),
            schema.get("name_field"),
            extraction.get("name_column"),
            "full_name",
            "name",
            "label",
            "title",
            "rank_value",
        ]
    )

    if not id_field or not rank_field or not name_field:
        return None
    if not parent_field and not (left_field and right_field):
        return None

    join_field = pick(
        [
            hierarchy.get("join_field"),
            schema.get("join_field"),
            schema.get("id_field"),
            id_field,
        ]
    )

    return HierarchyMetadata(
        id_field=id_field,
        join_field=join_field or id_field,
        parent_field=parent_field,
        left_field=left_field,
        right_field=right_field,
        rank_field=rank_field,
        name_field=name_field,
    )


def _first_existing_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    """Return the first existing column from a case-insensitive candidate list."""
    by_lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        resolved = by_lower.get(candidate.lower())
        if resolved:
            return resolved
    return None


def _is_numeric_column(
    columns_info: List[Dict[str, Any]], column_name: Optional[str]
) -> bool:
    """Return whether a column is declared as a numeric SQL type."""
    if not column_name:
        return False

    numeric_types = {
        "BIGINT",
        "DECIMAL",
        "DOUBLE",
        "FLOAT",
        "HUGEINT",
        "INT",
        "INTEGER",
        "NUMBER",
        "NUMERIC",
        "REAL",
        "SMALLINT",
        "TINYINT",
        "UBIGINT",
        "UHUGEINT",
        "UINTEGER",
        "USMALLINT",
        "UTINYINT",
    }
    requested = column_name.lower()
    for column in columns_info:
        if str(column.get("name", "")).lower() != requested:
            continue
        declared_type = str(column.get("type", "")).upper()
        base_type = declared_type.replace("(", " ").split()[0]
        return base_type in numeric_types
    return False


def _hierarchy_order_clause(
    db: Database, metadata: HierarchyMetadata, alias: str
) -> str:
    """Build stable ordering for bounded hierarchy queries."""
    prefix = f"{quote_identifier(db, alias)}." if alias else ""
    fields: List[str] = []

    if metadata.left_field:
        fields.append(f"{prefix}{quote_identifier(db, metadata.left_field)} ASC")
    elif metadata.parent_field:
        if metadata.rank_field:
            fields.append(f"{prefix}{quote_identifier(db, metadata.rank_field)} ASC")
        fields.append(f"{prefix}{quote_identifier(db, metadata.name_field)} ASC")

    fields.append(f"{prefix}{quote_identifier(db, metadata.id_field)} ASC")
    return " ORDER BY " + ", ".join(fields)


def _hierarchy_node_select_sql(
    db: Database,
    table_name: str,
    metadata: HierarchyMetadata,
    path_field: Optional[str],
    level_field: Optional[str],
    alias: str = "node",
) -> str:
    """Build a safe SELECT clause for hierarchy nodes."""
    quoted_alias = quote_identifier(db, alias)
    quoted_table = quote_identifier(db, table_name)

    def col(name: str) -> str:
        return f"{quoted_alias}.{quote_identifier(db, name)}"

    selected = [
        f"{col(metadata.id_field)} AS id_value",
        (
            f"{col(metadata.parent_field)} AS parent_value"
            if metadata.parent_field
            else "NULL AS parent_value"
        ),
        f"{col(metadata.name_field)} AS label_value",
        f"{col(metadata.rank_field)} AS rank_value",
        (
            f"{col(level_field)} AS level_value"
            if level_field
            else "NULL AS level_value"
        ),
        (
            f"{col(path_field)} AS path_value"
            if path_field
            else f"{col(metadata.name_field)} AS path_value"
        ),
    ]
    return f"SELECT {', '.join(selected)} FROM {quoted_table} {quoted_alias}"


def _serialize_hierarchy_node(
    row: Any, child_count: int, level_fallback: Optional[int] = None
) -> HierarchyNode:
    """Convert a SQL row into the API node shape."""
    mapping = row._mapping if hasattr(row, "_mapping") else row
    raw_level = mapping.get("level_value", level_fallback)
    try:
        level_value = int(raw_level) if raw_level is not None else level_fallback
    except (TypeError, ValueError):
        level_value = level_fallback
    label = mapping.get("label_value")

    return HierarchyNode(
        id=mapping.get("id_value"),
        parent_id=mapping.get("parent_value"),
        label=str(label) if label not in (None, "") else str(mapping.get("id_value")),
        rank=(
            str(mapping.get("rank_value"))
            if mapping.get("rank_value") not in (None, "")
            else None
        ),
        level=level_value,
        child_count=child_count,
        has_children=child_count > 0,
        path=(
            str(mapping.get("path_value"))
            if mapping.get("path_value") not in (None, "")
            else None
        ),
    )


def _count_hierarchy_children_bulk(
    conn: Any,
    db: Database,
    table_name: str,
    metadata: HierarchyMetadata,
    node_ids: List[Any],
) -> Dict[Any, int]:
    """Count direct children for visible hierarchy nodes in one query."""
    if not node_ids:
        return {}

    quoted_table = quote_identifier(db, table_name)
    id_params = {f"node_id_{idx}": node_id for idx, node_id in enumerate(node_ids)}
    id_placeholders = ", ".join(f":{key}" for key in id_params)

    if metadata.parent_field:
        query = text(
            f"""
            SELECT {quote_identifier(db, metadata.parent_field)}, COUNT(*)
            FROM {quoted_table}
            WHERE {quote_identifier(db, metadata.parent_field)} IN ({id_placeholders})
            GROUP BY {quote_identifier(db, metadata.parent_field)}
            """
        )
        return {row[0]: int(row[1]) for row in conn.execute(query, id_params)}

    if not metadata.left_field or not metadata.right_field:
        return {}

    parent_alias = quote_identifier(db, "parent_node")
    child_alias = quote_identifier(db, "child")
    mid_alias = quote_identifier(db, "mid")
    left_col = quote_identifier(db, metadata.left_field)
    right_col = quote_identifier(db, metadata.right_field)
    id_col = quote_identifier(db, metadata.id_field)

    query = text(
        f"""
        SELECT {parent_alias}.{id_col}, COUNT({child_alias}.{id_col})
        FROM {quoted_table} {parent_alias}
        JOIN {quoted_table} {child_alias}
          ON {child_alias}.{left_col} > {parent_alias}.{left_col}
         AND {child_alias}.{right_col} < {parent_alias}.{right_col}
        WHERE {parent_alias}.{id_col} IN ({id_placeholders})
          AND NOT EXISTS (
            SELECT 1
            FROM {quoted_table} {mid_alias}
            WHERE {mid_alias}.{left_col} > {parent_alias}.{left_col}
              AND {mid_alias}.{right_col} < {parent_alias}.{right_col}
              AND {child_alias}.{left_col} > {mid_alias}.{left_col}
              AND {child_alias}.{right_col} < {mid_alias}.{right_col}
          )
        GROUP BY {parent_alias}.{id_col}
        """
    )
    return {row[0]: int(row[1]) for row in conn.execute(query, id_params)}


def _find_geometry_column(
    columns_info: List[Dict[str, Any]],
) -> Tuple[Optional[str], bool]:
    """Detect geometry column and whether it's native GEOMETRY/BYTEA."""
    native_patterns = ["_geom", "geometry", "the_geom", "wkb_geometry"]
    wkt_patterns = ["geo_pt", "geo", "geom", "location", "wkt"]

    wkt_candidate = None
    for col in columns_info:
        col_name = col["name"].lower()
        col_type = str(col.get("type", "")).upper()

        if "GEOMETRY" in col_type or "BYTEA" in col_type:
            if any(col_name.endswith(p) or col_name == p for p in native_patterns):
                return col["name"], True
        elif wkt_candidate is None and any(p in col_name for p in wkt_patterns):
            wkt_candidate = col["name"]

    return wkt_candidate, False


def _is_native_geometry_column(
    columns_info: List[Dict[str, Any]], column_name: Optional[str]
) -> bool:
    """Return whether a resolved geometry column is stored as native geometry."""
    if not column_name:
        return False

    for col in columns_info:
        if col.get("name") == column_name:
            col_type = str(col.get("type", "")).upper()
            return "GEOMETRY" in col_type or "BYTEA" in col_type

    return False


def _geometry_sql_expression(
    db: Database,
    column_name: str,
    is_native: bool,
    alias: Optional[str] = None,
) -> str:
    """Build a SQL expression that safely normalizes a geometry column."""
    quoted_col = quote_identifier(db, column_name)
    col_ref = f"{quote_identifier(db, alias)}.{quoted_col}" if alias else quoted_col

    if is_native:
        return f"TRY_CAST({col_ref} AS GEOMETRY)"

    return f"TRY(ST_GeomFromText(CAST({col_ref} AS VARCHAR)))"


def _extract_wkt_bbox(value: Any) -> Optional[Dict[str, float]]:
    """Extract a bbox from common 2D WKT strings without DuckDB spatial."""
    if value in (None, ""):
        return None

    text_value = str(value).strip()
    if not text_value:
        return None
    if ";" in text_value and text_value.upper().startswith("SRID="):
        text_value = text_value.split(";", 1)[1].strip()

    header = text_value.split("(", 1)[0].strip().upper()
    geometry_type = header.split()[0] if header else ""
    if geometry_type not in {
        "GEOMETRYCOLLECTION",
        "LINESTRING",
        "MULTILINESTRING",
        "MULTIPOINT",
        "MULTIPOLYGON",
        "POINT",
        "POLYGON",
    }:
        return None
    if "EMPTY" in header:
        return None

    dimensions = 2
    header_tokens = header.split()
    if "ZM" in header_tokens:
        dimensions = 4
    elif "Z" in header_tokens or "M" in header_tokens:
        dimensions = 3

    values = [float(match.group()) for match in _WKT_NUMBER_RE.finditer(text_value)]
    if len(values) < 2:
        return None

    points = [
        (values[index], values[index + 1])
        for index in range(0, len(values) - 1, dimensions)
    ]
    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
    }


def _merge_bbox(
    current: Optional[Dict[str, float]], next_bbox: Dict[str, float]
) -> Dict[str, float]:
    """Merge one bbox into an aggregate bbox."""
    if not current:
        return dict(next_bbox)

    return {
        "min_x": min(current["min_x"], next_bbox["min_x"]),
        "min_y": min(current["min_y"], next_bbox["min_y"]),
        "max_x": max(current["max_x"], next_bbox["max_x"]),
        "max_y": max(current["max_y"], next_bbox["max_y"]),
    }


def _compute_wkt_geometry_stats_fallback(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    layer_column: Optional[str] = None,
    selected_layer: Optional[str] = None,
) -> Tuple[int, Optional[Dict[str, float]]]:
    """Count WKT geometries and bbox without DuckDB spatial functions."""
    quoted_table = quote_identifier(db, table_name)
    geometry_col = quote_identifier(db, geometry_column)
    layer_filter = _spatial_layer_filter_sql(db, layer_column, selected_layer)
    params = {"selected_layer": selected_layer} if selected_layer is not None else {}
    rows = conn.execute(
        text(
            f"""
            SELECT {geometry_col}
            FROM {quoted_table}
            WHERE {geometry_col} IS NOT NULL
            {layer_filter}
            """
        ),
        params,
    ).fetchall()

    count = 0
    bbox: Optional[Dict[str, float]] = None
    for row in rows:
        row_bbox = _extract_wkt_bbox(row[0])
        if not row_bbox:
            continue
        count += 1
        bbox = _merge_bbox(bbox, row_bbox)

    return count, bbox


def _load_spatial_extension_best_effort(conn: Any) -> None:
    """Load DuckDB spatial functions for short-lived API connections."""
    try:
        conn.execute(text("LOAD spatial"))
    except Exception as exc:
        logger.debug("Could not load spatial extension: %s", exc)


def _compute_geometry_bbox(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    is_native: bool,
) -> Optional[Dict[str, float]]:
    """Compute a bounding box for point, line, or polygon geometries."""
    quoted_table = quote_identifier(db, table_name)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)

    try:
        _load_spatial_extension_best_effort(conn)
        row = conn.execute(
            text(
                f"""
                WITH mapped AS (
                    SELECT {geom_expr} AS geom
                    FROM {quoted_table}
                    WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                ),
                extent AS (
                    SELECT ST_Extent_Agg(geom) AS bbox
                    FROM mapped
                    WHERE geom IS NOT NULL
                )
                SELECT
                    ST_XMin(bbox),
                    ST_YMin(bbox),
                    ST_XMax(bbox),
                    ST_YMax(bbox)
                FROM extent
                WHERE bbox IS NOT NULL
                """
            )
        ).fetchone()
    except Exception as exc:
        logger.debug(
            "Failed to compute geometry bounding box for table '%s': %s",
            table_name,
            exc,
        )
        if not is_native:
            _, bbox = _compute_wkt_geometry_stats_fallback(
                conn, db, table_name, geometry_column
            )
            return bbox
        return None

    if not row or row[0] is None:
        return None

    return {
        "min_x": float(row[0]),
        "min_y": float(row[1]),
        "max_x": float(row[2]),
        "max_y": float(row[3]),
    }


def _count_valid_geometries(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    is_native: bool,
) -> int:
    """Count rows with a parseable geometry value."""
    quoted_table = quote_identifier(db, table_name)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)

    try:
        _load_spatial_extension_best_effort(conn)
        return int(
            conn.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM (
                        SELECT {geom_expr} AS geom
                        FROM {quoted_table}
                        WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                    ) mapped
                    WHERE geom IS NOT NULL
                    """
                )
            ).scalar()
            or 0
        )
    except Exception as exc:
        logger.debug(
            "Failed to count valid geometries for table '%s': %s",
            table_name,
            exc,
        )
        if not is_native:
            count, _ = _compute_wkt_geometry_stats_fallback(
                conn, db, table_name, geometry_column
            )
            return count
        return 0


def _spatial_layer_candidates(
    column_names: List[str], preferred_column: Optional[str]
) -> List[str]:
    """Return candidate columns that can split a spatial reference into layers."""
    columns_by_lower = {column.lower(): column for column in column_names}
    ordered_candidates = [
        preferred_column,
        "type",
        "category",
        "group",
        "entity_type",
        "shape_type",
    ]
    candidates: List[str] = []
    for candidate in ordered_candidates:
        if not candidate:
            continue
        resolved = columns_by_lower.get(str(candidate).lower())
        if resolved and resolved not in candidates:
            candidates.append(resolved)
    return candidates


def _spatial_layer_filter_sql(
    db: Database,
    layer_column: Optional[str],
    selected_layer: Optional[str],
    *,
    prefix: str = " AND ",
) -> str:
    """Build a parameterized SQL fragment for a selected map layer."""
    if not layer_column or selected_layer is None:
        return ""

    return (
        f"{prefix}TRY_CAST({quote_identifier(db, layer_column)} AS VARCHAR) "
        "= :selected_layer"
    )


def _resolve_spatial_layer_column(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    is_native: bool,
    column_names: List[str],
    preferred_column: Optional[str] = None,
) -> Optional[str]:
    """Resolve the best column for splitting a spatial reference into layers."""
    quoted_table = quote_identifier(db, table_name)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)

    for candidate in _spatial_layer_candidates(column_names, preferred_column):
        layer_col = quote_identifier(db, candidate)
        try:
            row = conn.execute(
                text(
                    f"""
                    WITH mapped AS (
                        SELECT
                            TRY_CAST({layer_col} AS VARCHAR) AS layer_value,
                            {geom_expr} AS geom
                        FROM {quoted_table}
                        WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                    )
                    SELECT COUNT(DISTINCT layer_value)
                    FROM mapped
                    WHERE geom IS NOT NULL
                      AND layer_value IS NOT NULL
                      AND layer_value <> ''
                    """
                )
            ).fetchone()
        except Exception as exc:
            logger.debug(
                "Failed to inspect layer column '%s' for table '%s': %s",
                candidate,
                table_name,
                exc,
            )
            continue

        distinct_count = int(row[0] or 0) if row else 0
        if 1 < distinct_count <= 80:
            return candidate

    return None


def _fetch_spatial_layers(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    is_native: bool,
    layer_column: Optional[str],
) -> List[SpatialMapLayer]:
    """Return layer counts for a mappable spatial reference."""
    if not layer_column:
        return []

    quoted_table = quote_identifier(db, table_name)
    layer_col = quote_identifier(db, layer_column)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)

    try:
        rows = conn.execute(
            text(
                f"""
                WITH mapped AS (
                    SELECT
                        TRY_CAST({layer_col} AS VARCHAR) AS layer_value,
                        {geom_expr} AS geom
                    FROM {quoted_table}
                )
                SELECT
                    layer_value,
                    COUNT(*) AS feature_count,
                    SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END) AS with_geometry
                FROM mapped
                WHERE layer_value IS NOT NULL
                  AND layer_value <> ''
                GROUP BY layer_value
                ORDER BY with_geometry DESC, feature_count DESC, layer_value
                """
            )
        ).fetchall()
    except Exception as exc:
        logger.debug(
            "Failed to fetch spatial layers for table '%s': %s",
            table_name,
            exc,
        )
        return []

    return [
        SpatialMapLayer(
            value=str(row[0]),
            label=str(row[0]),
            feature_count=int(row[1] or 0),
            with_geometry=int(row[2] or 0),
        )
        for row in rows
        if row[0] is not None
    ]


def _count_spatial_features(
    conn: Any,
    db: Database,
    table_name: str,
    layer_column: Optional[str] = None,
    selected_layer: Optional[str] = None,
) -> int:
    """Count rows in the selected spatial scope."""
    quoted_table = quote_identifier(db, table_name)
    layer_filter = _spatial_layer_filter_sql(
        db, layer_column, selected_layer, prefix=" WHERE "
    )
    params = {"selected_layer": selected_layer} if selected_layer is not None else {}

    return int(
        conn.execute(
            text(f"SELECT COUNT(*) FROM {quoted_table}{layer_filter}"),
            params,
        ).scalar()
        or 0
    )


def _count_valid_geometries_for_scope(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    is_native: bool,
    layer_column: Optional[str] = None,
    selected_layer: Optional[str] = None,
) -> int:
    """Count parseable geometries in the selected spatial scope."""
    quoted_table = quote_identifier(db, table_name)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)
    layer_filter = _spatial_layer_filter_sql(db, layer_column, selected_layer)
    params = {"selected_layer": selected_layer} if selected_layer is not None else {}

    return int(
        conn.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM (
                    SELECT {geom_expr} AS geom
                    FROM {quoted_table}
                    WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                    {layer_filter}
                ) mapped
                WHERE geom IS NOT NULL
                """
            ),
            params,
        ).scalar()
        or 0
    )


def _compute_geometry_bbox_for_scope(
    conn: Any,
    db: Database,
    table_name: str,
    geometry_column: str,
    is_native: bool,
    layer_column: Optional[str] = None,
    selected_layer: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    """Compute a bounding box for the selected spatial scope."""
    quoted_table = quote_identifier(db, table_name)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)
    layer_filter = _spatial_layer_filter_sql(db, layer_column, selected_layer)
    params = {"selected_layer": selected_layer} if selected_layer is not None else {}

    try:
        row = conn.execute(
            text(
                f"""
                WITH mapped AS (
                    SELECT {geom_expr} AS geom
                    FROM {quoted_table}
                    WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                    {layer_filter}
                ),
                extent AS (
                    SELECT ST_Extent_Agg(geom) AS bbox
                    FROM mapped
                    WHERE geom IS NOT NULL
                )
                SELECT
                    ST_XMin(bbox),
                    ST_YMin(bbox),
                    ST_XMax(bbox),
                    ST_YMax(bbox)
                FROM extent
                WHERE bbox IS NOT NULL
                """
            ),
            params,
        ).fetchone()
    except Exception as exc:
        logger.debug(
            "Failed to compute scoped geometry bounding box for table '%s': %s",
            table_name,
            exc,
        )
        return None

    if not row or row[0] is None:
        return None

    return {
        "min_x": float(row[0]),
        "min_y": float(row[1]),
        "max_x": float(row[2]),
        "max_y": float(row[3]),
    }


def _find_configured_geometry_column(
    ref_cfg: Dict[str, Any], columns_by_lower: Dict[str, str]
) -> Optional[str]:
    """Resolve a geometry column declared in import.yml schema metadata."""
    schema = _dict_config(ref_cfg.get("schema"))
    fields = schema.get("fields")
    candidates: List[Optional[str]] = [
        schema.get("geometry_field"),
        schema.get("geo_field"),
        schema.get("location_field"),
    ]

    def is_geometry_type(value: Any) -> bool:
        normalized = str(value or "").lower()
        return (
            normalized in {"geometry", "geography", "wkt"} or "geometry" in normalized
        )

    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict):
                continue
            field_name = field.get("name") or field.get("field") or field.get("column")
            if is_geometry_type(field.get("type")) or is_geometry_type(
                field.get("semantic_type")
            ):
                candidates.append(field_name)
    elif isinstance(fields, dict):
        for field_name, field_config in fields.items():
            if isinstance(field_config, dict):
                if is_geometry_type(field_config.get("type")) or is_geometry_type(
                    field_config.get("semantic_type")
                ):
                    candidates.append(str(field_name))
            elif is_geometry_type(field_config):
                candidates.append(str(field_name))

    return _pick_first_existing(columns_by_lower, candidates)


def _resolve_mappable_reference_metadata(
    db: Database,
    table_names: List[str],
    references: Dict[str, Any],
    reference_name: str,
) -> Optional[Dict[str, Any]]:
    """Resolve mapping metadata for a reference with point or polygon geometry."""
    target_table = resolve_reference_table_name(table_names, reference_name)
    if not target_table:
        target_table = resolve_entity_table_name(table_names, reference_name)
    if not target_table:
        return None

    ref_cfg = _dict_config(references.get(reference_name))
    columns_info = db.get_columns(target_table)
    column_names = [col["name"] for col in columns_info]
    columns_by_lower = {column.lower(): column for column in column_names}

    detected_geo_column, detected_is_native = _find_geometry_column(columns_info)
    configured_geo_column = _find_configured_geometry_column(ref_cfg, columns_by_lower)

    geometry_column = configured_geo_column or detected_geo_column
    is_native = detected_is_native
    if geometry_column and geometry_column != detected_geo_column:
        is_native = _is_native_geometry_column(columns_info, geometry_column)

    schema = _dict_config(ref_cfg.get("schema"))
    id_column = _pick_first_existing(
        columns_by_lower,
        [
            schema.get("id_field"),
            "id",
            f"{reference_name}_id",
            f"id_{reference_name.rstrip('s')}",
        ],
    ) or (column_names[0] if column_names else None)
    name_column = (
        _pick_first_existing(
            columns_by_lower,
            [
                schema.get("name_field"),
                "name",
                "full_name",
                "label",
                "title",
                reference_name.rstrip("s"),
                id_column,
            ],
        )
        or id_column
    )
    type_column = _pick_first_existing(
        columns_by_lower,
        ["type", "category", "group", "entity_type", "shape_type"],
    )

    return {
        "reference_name": reference_name,
        "table_name": target_table,
        "geometry_column": geometry_column,
        "is_native": is_native,
        "id_column": id_column,
        "name_column": name_column,
        "type_column": type_column,
        "configured_as_spatial": ref_cfg.get("kind") == "spatial",
        "configured_geometry_column": configured_geo_column,
    }


def _classify_geometry_kind(geometry_types: List[str]) -> str:
    """Return a coarse map rendering kind from geometry type names."""
    normalized = {geometry_type.upper() for geometry_type in geometry_types}
    if not normalized:
        return "unknown"
    if normalized <= {"POINT", "MULTIPOINT"}:
        return "point"
    if normalized <= {"POLYGON", "MULTIPOLYGON"}:
        return "polygon"
    if normalized <= {"LINESTRING", "MULTILINESTRING"}:
        return "line"
    return "mixed"


def _pick_first_existing(
    columns_by_lower: Dict[str, str], candidates: List[Optional[str]]
) -> Optional[str]:
    """Return first candidate column that exists in table columns."""
    for candidate in candidates:
        if not candidate:
            continue
        resolved = columns_by_lower.get(str(candidate).lower())
        if resolved:
            return resolved
    return None


def _resolve_spatial_reference_tables(
    db: Database,
    table_names: List[str],
    inspector: Any,
    references: Dict[str, Any],
    occurrence_table: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Resolve spatial reference tables from config first, then fallback by geometry."""
    spatial_tables: List[Dict[str, Any]] = []
    seen_tables: set[str] = set()

    # Config-first resolution: explicit spatial references from import.yml.
    for ref_name, ref_cfg in references.items():
        if not isinstance(ref_cfg, dict):
            continue

        connector = ref_cfg.get("connector", {}) or {}
        is_spatial = (
            ref_cfg.get("kind") == "spatial"
            or connector.get("type") == "file_multi_feature"
        )
        if not is_spatial:
            continue

        table_name = resolve_reference_table_name(table_names, ref_name)
        if not table_name or table_name in seen_tables:
            continue
        seen_tables.add(table_name)

        columns_info = db.get_columns(table_name)
        geo_column, is_native = _find_geometry_column(columns_info)
        column_names = [col["name"] for col in columns_info]
        columns_by_lower = {c.lower(): c for c in column_names}
        schema = (
            ref_cfg.get("schema", {}) if isinstance(ref_cfg.get("schema"), dict) else {}
        )

        id_column = _pick_first_existing(
            columns_by_lower,
            [
                schema.get("id_field"),
                "id",
                f"{ref_name}_id",
                f"id_{ref_name.rstrip('s')}",
            ],
        ) or (column_names[0] if column_names else None)

        name_column = (
            _pick_first_existing(
                columns_by_lower,
                [
                    "name",
                    "full_name",
                    "label",
                    "title",
                    ref_name.rstrip("s"),
                    id_column,
                ],
            )
            or id_column
        )

        type_column = _pick_first_existing(
            columns_by_lower,
            ["type", "category", "group", "entity_type", "shape_type"],
        )

        spatial_tables.append(
            {
                "reference_name": ref_name,
                "table_name": table_name,
                "display_name": (
                    ref_cfg.get("description") or ref_name.replace("_", " ").title()
                ),
                "has_geometry": bool(geo_column),
                "geo_column": geo_column,
                "is_native": is_native,
                "id_column": id_column,
                "name_column": name_column,
                "type_column": type_column,
            }
        )

    # Fallback resolution for projects without/partial import.yml metadata.
    if not spatial_tables:
        for table_name in table_names:
            if table_name in seen_tables:
                continue
            if occurrence_table and table_name == occurrence_table:
                continue
            if table_name.startswith("_") or table_name.startswith("sqlite"):
                continue

            columns_info = db.get_columns(table_name)
            geo_column, is_native = _find_geometry_column(columns_info)
            if not geo_column:
                continue

            column_names = [col["name"] for col in columns_info]
            columns_by_lower = {c.lower(): c for c in column_names}
            id_column = (
                _pick_first_existing(columns_by_lower, ["id"]) or column_names[0]
            )
            name_column = _pick_first_existing(
                columns_by_lower, ["name", "full_name", "label", "title", id_column]
            )
            type_column = _pick_first_existing(
                columns_by_lower,
                ["type", "category", "group", "entity_type", "shape_type"],
            )

            spatial_tables.append(
                {
                    "reference_name": table_name,
                    "table_name": table_name,
                    "display_name": table_name.replace("_", " ").title(),
                    "has_geometry": True,
                    "geo_column": geo_column,
                    "is_native": is_native,
                    "id_column": id_column,
                    "name_column": name_column,
                    "type_column": type_column,
                }
            )

    return spatial_tables


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
        )

    try:
        with open_database(db_path, read_only=True) as db:
            preparer = db.engine.dialect.identifier_preparer

            table_names = db.get_table_names()
            datasets, references = _load_import_entities_config()
            entity_type_map = _build_entity_type_map(table_names, datasets, references)
            entities = []
            total_rows = 0
            alerts = []

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
                    columns_info = db.get_columns(table_name)
                    column_names = [c["name"] for c in columns_info]

                    entity_type = entity_type_map.get(
                        table_name, classify_table_type(table_name)
                    )

                    entities.append(
                        EntitySummary(
                            name=table_name,
                            entity_type=entity_type,
                            row_count=row_count,
                            column_count=len(column_names),
                            columns=column_names,
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

            return ImportSummary(
                total_entities=len(entities),
                total_rows=total_rows,
                entities=entities,
                alerts=alerts,
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
            preparer = db.engine.dialect.identifier_preparer

            if entity not in db.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity}' not found"
                )

            quoted_table = preparer.quote(entity)

            # Get total count
            with db.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}"))
                total_count = result.scalar() or 0

            columns_info = db.get_columns(entity)
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


@router.get("/hierarchy/{reference_name}", response_model=HierarchyInspection)
async def get_hierarchy_inspection(
    reference_name: str,
    mode: str = Query(
        default="roots",
        pattern="^(roots|children|search)$",
        description="Hierarchy loading mode",
    ),
    parent_id: Optional[str] = Query(
        default=None, description="Parent node id for child loading"
    ),
    search: Optional[str] = Query(default=None, description="Node label search"),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
):
    """Inspect a hierarchical reference with bounded root, child, or search results."""
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            table_names = db.get_table_names()
            _, references = _load_import_entities_config()
            target_table = _resolve_hierarchy_reference_table(
                table_names, references, reference_name
            )

            if not target_table:
                raise HTTPException(
                    status_code=404, detail=f"Reference '{reference_name}' not found"
                )

            columns_info = db.get_columns(target_table)
            column_names = [col["name"] for col in columns_info]
            ref_cfg = _dict_config(references.get(reference_name))
            metadata = _detect_configured_hierarchy_metadata(
                column_names, ref_cfg
            ) or detect_hierarchy_metadata(column_names)
            is_hierarchical = _is_reference_hierarchical(
                reference_name, references, metadata
            )

            if not is_hierarchical or not metadata:
                return HierarchyInspection(
                    reference_name=reference_name,
                    table_name=target_table,
                    is_hierarchical=is_hierarchical,
                    metadata_available=bool(metadata),
                    mode=mode,
                    search=search,
                    parent_id=parent_id,
                    limit=limit,
                    offset=offset,
                )

            path_field = _first_existing_column(column_names, ["full_path", "path"])
            level_field = _first_existing_column(column_names, ["level", "depth"])
            quoted_table = quote_identifier(db, target_table)
            node_alias = quote_identifier(db, "node")
            parent_alias = quote_identifier(db, "parent_node")
            id_col = quote_identifier(db, metadata.id_field)
            name_col = quote_identifier(db, metadata.name_field)
            rank_col = quote_identifier(db, metadata.rank_field)
            parent_col = (
                quote_identifier(db, metadata.parent_field)
                if metadata.parent_field
                else None
            )
            left_col = (
                quote_identifier(db, metadata.left_field)
                if metadata.left_field
                else None
            )
            right_col = (
                quote_identifier(db, metadata.right_field)
                if metadata.right_field
                else None
            )
            level_col = quote_identifier(db, level_field) if level_field else None
            level_is_numeric = _is_numeric_column(columns_info, level_field)

            select_sql = _hierarchy_node_select_sql(
                db, target_table, metadata, path_field, level_field, alias="node"
            )
            order_clause = _hierarchy_order_clause(db, metadata, "node")
            params: Dict[str, Any] = {"limit": limit + 1, "offset": offset}

            if mode == "search":
                search_value = (search or "").strip().lower()
                if not search_value:
                    where_clause = " WHERE 1 = 0"
                else:
                    search_conditions = [
                        f"LOWER(CAST({node_alias}.{name_col} AS VARCHAR)) LIKE :search",
                        f"LOWER(CAST({node_alias}.{rank_col} AS VARCHAR)) LIKE :search",
                    ]
                    if path_field:
                        search_conditions.append(
                            f"LOWER(CAST({node_alias}.{quote_identifier(db, path_field)} AS VARCHAR)) LIKE :search"
                        )
                    where_clause = " WHERE " + " OR ".join(search_conditions)
                    params["search"] = f"%{search_value}%"
            elif mode == "children":
                if parent_id is None:
                    raise HTTPException(
                        status_code=400,
                        detail="parent_id is required when mode is 'children'",
                    )
                params["parent_id"] = parent_id
                if metadata.parent_field and parent_col:
                    where_clause = f" WHERE {node_alias}.{parent_col} = :parent_id"
                elif left_col and right_col:
                    where_clause = f"""
                    JOIN {quoted_table} {parent_alias}
                      ON {parent_alias}.{id_col} = :parent_id
                    WHERE {node_alias}.{left_col} > {parent_alias}.{left_col}
                      AND {node_alias}.{right_col} < {parent_alias}.{right_col}
                      AND NOT EXISTS (
                        SELECT 1
                        FROM {quoted_table} mid_node
                        WHERE mid_node.{left_col} > {parent_alias}.{left_col}
                          AND mid_node.{right_col} < {parent_alias}.{right_col}
                          AND {node_alias}.{left_col} > mid_node.{left_col}
                          AND {node_alias}.{right_col} < mid_node.{right_col}
                      )
                    """
                else:
                    where_clause = " WHERE 1 = 0"
            else:
                if metadata.parent_field and parent_col:
                    where_clause = f" WHERE {node_alias}.{parent_col} IS NULL"
                elif left_col and right_col:
                    where_clause = f"""
                    WHERE NOT EXISTS (
                      SELECT 1
                      FROM {quoted_table} {parent_alias}
                      WHERE {node_alias}.{left_col} > {parent_alias}.{left_col}
                        AND {node_alias}.{right_col} < {parent_alias}.{right_col}
                    )
                    """
                else:
                    where_clause = " WHERE 1 = 0"

            with db.engine.connect() as conn:
                total_nodes = int(
                    conn.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar()
                    or 0
                )

                if metadata.parent_field and parent_col:
                    root_count = int(
                        conn.execute(
                            text(
                                f"""
                                SELECT COUNT(*) FROM {quoted_table}
                                WHERE {parent_col} IS NULL
                                """
                            )
                        ).scalar()
                        or 0
                    )
                    orphan_condition = (
                        f"({node_alias}.{parent_col} IS NOT NULL AND NOT EXISTS ("
                        f"SELECT 1 FROM {quoted_table} parent_lookup "
                        f"WHERE parent_lookup.{id_col} = {node_alias}.{parent_col}"
                        "))"
                    )
                    if level_col and level_is_numeric:
                        orphan_condition = (
                            f"({orphan_condition} OR "
                            f"({node_alias}.{level_col} > 0 AND {node_alias}.{parent_col} IS NULL))"
                        )
                    orphan_count = int(
                        conn.execute(
                            text(
                                f"""
                                SELECT COUNT(*) FROM {quoted_table} {node_alias}
                                WHERE {orphan_condition}
                                """
                            )
                        ).scalar()
                        or 0
                    )
                else:
                    root_count = int(
                        conn.execute(
                            text(
                                f"""
                                SELECT COUNT(*) FROM {quoted_table} {node_alias}
                                WHERE NOT EXISTS (
                                  SELECT 1
                                  FROM {quoted_table} {parent_alias}
                                  WHERE {node_alias}.{left_col} > {parent_alias}.{left_col}
                                    AND {node_alias}.{right_col} < {parent_alias}.{right_col}
                                )
                                """
                            )
                        ).scalar()
                        or 0
                    )
                    orphan_condition = "FALSE"
                    orphan_count = 0

                level_order = (
                    f" ORDER BY MIN({node_alias}.{level_col})"
                    if level_col
                    else f" ORDER BY MIN({node_alias}.{rank_col})"
                )
                level_rows = conn.execute(
                    text(
                        f"""
                        SELECT {node_alias}.{rank_col}, COUNT(*),
                               SUM(CASE WHEN {orphan_condition} THEN 1 ELSE 0 END)
                        FROM {quoted_table} {node_alias}
                        WHERE {node_alias}.{rank_col} IS NOT NULL
                        GROUP BY {node_alias}.{rank_col}
                        {level_order}
                        """
                    )
                ).fetchall()
                levels = [
                    TaxonomyLevel(
                        level=str(row[0]),
                        count=int(row[1]),
                        orphan_count=int(row[2] or 0),
                    )
                    for row in level_rows
                ]

                rows = conn.execute(
                    text(
                        f"{select_sql}{where_clause}{order_clause} "
                        "LIMIT :limit OFFSET :offset"
                    ),
                    params,
                ).fetchall()

                result_count = int(
                    conn.execute(
                        text(
                            f"""
                            SELECT COUNT(*)
                            FROM {quoted_table} {node_alias}
                            {where_clause}
                            """
                        ),
                        params,
                    ).scalar()
                    or 0
                )

                has_more = len(rows) > limit
                visible_rows = rows[:limit]
                child_counts = _count_hierarchy_children_bulk(
                    conn,
                    db,
                    target_table,
                    metadata,
                    [row._mapping["id_value"] for row in visible_rows],
                )
                nodes = [
                    _serialize_hierarchy_node(
                        row,
                        child_count=child_counts.get(row._mapping["id_value"], 0),
                    )
                    for row in visible_rows
                ]

            return HierarchyInspection(
                reference_name=reference_name,
                table_name=target_table,
                is_hierarchical=True,
                metadata_available=True,
                mode=mode,
                search=search,
                parent_id=parent_id,
                total_nodes=total_nodes,
                root_count=root_count,
                orphan_count=orphan_count,
                levels=levels,
                nodes=nodes,
                limit=limit,
                offset=offset,
                result_count=result_count,
                has_more=has_more,
                next_offset=offset + limit if has_more else None,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting hierarchy inspection: {str(e)}"
        )


def _build_spatial_map_inspection(
    db: Database,
    reference_name: str,
    limit: int,
    offset: int = 0,
    layer: Optional[str] = None,
    simplify_tolerance: Optional[float] = None,
) -> SpatialMapInspection:
    """Build the spatial map inspection payload for JSON and rendered maps."""
    table_names = db.get_table_names()
    _, references = _load_import_entities_config()
    metadata = _resolve_mappable_reference_metadata(
        db, table_names, references, reference_name
    )

    if not metadata:
        raise HTTPException(
            status_code=404, detail=f"Reference '{reference_name}' not found"
        )

    table_name = metadata["table_name"]
    geometry_column = metadata.get("geometry_column")

    if not geometry_column:
        return SpatialMapInspection(
            reference_name=reference_name,
            table_name=table_name,
            is_mappable=False,
            reason="no_geometry_column",
            id_column=metadata.get("id_column"),
            name_column=metadata.get("name_column"),
            type_column=metadata.get("type_column"),
            limit=limit,
            offset=offset,
        )

    selected_layer = layer.strip() if isinstance(layer, str) and layer.strip() else None
    is_native = bool(metadata.get("is_native"))
    geometry_storage = "native" if is_native else "wkt"
    quoted_table = quote_identifier(db, table_name)
    geom_expr = _geometry_sql_expression(db, geometry_column, is_native)
    columns_info = db.get_columns(table_name)
    column_names = [col["name"] for col in columns_info]
    id_column = metadata.get("id_column")
    name_column = metadata.get("name_column")
    type_column = metadata.get("type_column")

    id_expr = (
        f"TRY_CAST({quote_identifier(db, id_column)} AS VARCHAR)"
        if id_column
        else "NULL"
    )
    name_expr = (
        f"TRY_CAST({quote_identifier(db, name_column)} AS VARCHAR)"
        if name_column
        else id_expr
    )
    type_expr = (
        f"TRY_CAST({quote_identifier(db, type_column)} AS VARCHAR)"
        if type_column
        else "NULL"
    )

    with db.engine.connect() as conn:
        _load_spatial_extension_best_effort(conn)
        layer_column = _resolve_spatial_layer_column(
            conn,
            db,
            table_name,
            geometry_column,
            is_native,
            column_names,
            preferred_column=type_column,
        )
        if selected_layer is not None and not layer_column:
            raise HTTPException(
                status_code=400,
                detail="Layer filtering is not available for this reference",
            )

        layers = _fetch_spatial_layers(
            conn, db, table_name, geometry_column, is_native, layer_column
        )
        layer_filter = _spatial_layer_filter_sql(db, layer_column, selected_layer)
        layer_expr = (
            f"TRY_CAST({quote_identifier(db, layer_column)} AS VARCHAR)"
            if layer_column
            else "NULL"
        )
        params = (
            {"selected_layer": selected_layer} if selected_layer is not None else {}
        )

        total_features = _count_spatial_features(
            conn, db, table_name, layer_column, selected_layer
        )
        with_geometry = _count_valid_geometries_for_scope(
            conn,
            db,
            table_name,
            geometry_column,
            is_native,
            layer_column,
            selected_layer,
        )
        bbox = _compute_geometry_bbox_for_scope(
            conn,
            db,
            table_name,
            geometry_column,
            is_native,
            layer_column,
            selected_layer,
        )
        geometry_rows = conn.execute(
            text(
                f"""
                WITH mapped AS (
                    SELECT {geom_expr} AS geom
                    FROM {quoted_table}
                    WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                    {layer_filter}
                )
                SELECT DISTINCT CAST(ST_GeometryType(geom) AS VARCHAR)
                FROM mapped
                WHERE geom IS NOT NULL
                ORDER BY 1
                """
            ),
            params,
        ).fetchall()
        geometry_types = [str(row[0]) for row in geometry_rows if row[0]]

        rows = []
        if limit > 0:
            feature_params = {**params, "limit": limit + 1, "offset": offset}
            if simplify_tolerance and simplify_tolerance > 0:
                geometry_json_expr = "ST_Simplify(geom, :simplify_tolerance)"
                feature_params["simplify_tolerance"] = simplify_tolerance
            else:
                geometry_json_expr = "geom"
            rows = conn.execute(
                text(
                    f"""
                    WITH mapped AS (
                        SELECT
                            {id_expr} AS id_value,
                            {name_expr} AS name_value,
                            {type_expr} AS type_value,
                            {layer_expr} AS layer_value,
                            {geom_expr} AS geom
                        FROM {quoted_table}
                        WHERE {quote_identifier(db, geometry_column)} IS NOT NULL
                        {layer_filter}
                    )
                    SELECT
                        id_value,
                        name_value,
                        type_value,
                        layer_value,
                        CAST(ST_GeometryType(geom) AS VARCHAR) AS geometry_type,
                        CAST(ST_AsGeoJSON({geometry_json_expr}) AS VARCHAR) AS geometry_json
                    FROM mapped
                    WHERE geom IS NOT NULL
                    ORDER BY id_value NULLS LAST
                    LIMIT :limit OFFSET :offset
                    """
                ),
                feature_params,
            ).fetchall()

    visible_rows = rows[:limit]
    features: List[Dict[str, Any]] = []
    for row in visible_rows:
        mapping = row._mapping if hasattr(row, "_mapping") else row
        geometry_json = mapping["geometry_json"]
        if not geometry_json:
            continue

        try:
            geometry = json.loads(geometry_json)
        except (TypeError, json.JSONDecodeError) as exc:
            logger.debug(
                "Failed to decode GeoJSON for reference '%s': %s",
                reference_name,
                exc,
            )
            continue

        feature_id = mapping["id_value"]
        feature_name = mapping["name_value"] or feature_id
        feature_type = mapping["type_value"]
        feature_layer = mapping["layer_value"]
        features.append(
            {
                "type": "Feature",
                "id": feature_id,
                "geometry": geometry,
                "properties": {
                    "id": feature_id,
                    "label": str(feature_name) if feature_name else None,
                    "name": str(feature_name) if feature_name else None,
                    "type": str(feature_type) if feature_type else None,
                    "layer": str(feature_layer) if feature_layer else None,
                    "geometry_type": mapping["geometry_type"],
                },
            }
        )

    has_more = limit > 0 and len(rows) > limit
    return SpatialMapInspection(
        reference_name=reference_name,
        table_name=table_name,
        is_mappable=True,
        geometry_column=geometry_column,
        geometry_storage=geometry_storage,
        geometry_kind=_classify_geometry_kind(geometry_types),
        geometry_types=geometry_types,
        id_column=id_column,
        name_column=name_column,
        type_column=type_column,
        layer_column=layer_column,
        selected_layer=selected_layer,
        layers=layers,
        total_features=total_features,
        with_geometry=with_geometry,
        without_geometry=max(total_features - with_geometry, 0),
        bounding_box=bbox,
        feature_collection={
            "type": "FeatureCollection",
            "features": features,
        },
        limit=limit,
        offset=offset,
        result_count=with_geometry,
        has_more=has_more,
        next_offset=offset + limit if has_more else None,
    )


@router.get("/spatial-map/{reference_name}", response_model=SpatialMapInspection)
async def get_spatial_map_inspection(
    reference_name: str,
    limit: int = Query(default=250, ge=0, le=500),
    offset: int = Query(default=0, ge=0),
    layer: Optional[str] = Query(default=None, description="Optional layer value"),
):
    """Return bounded GeoJSON features for a mappable reference."""
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            return _build_spatial_map_inspection(
                db,
                reference_name,
                limit=limit,
                offset=offset,
                layer=layer,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting spatial map data: {str(e)}"
        )


@router.get("/spatial-map/{reference_name}/render", response_class=HTMLResponse)
async def render_spatial_map(
    reference_name: str,
    layer: Optional[str] = Query(default=None, description="Optional layer value"),
    limit: int = Query(default=500, ge=1, le=1000),
):
    """Render a Plotly map with a base map for a mappable reference."""
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            selected_layer = (
                layer.strip() if isinstance(layer, str) and layer.strip() else None
            )
            inspection = _build_spatial_map_inspection(
                db,
                reference_name,
                limit=0 if selected_layer is None else limit,
                offset=0,
                layer=selected_layer,
                simplify_tolerance=0.001,
            )

            if (
                inspection.is_mappable
                and selected_layer is None
                and len(inspection.layers) > 1
            ):
                layer_items = "".join(
                    "<li>"
                    f"<strong>{html.escape(item.label)}</strong> "
                    f"({item.with_geometry}/{item.feature_count})"
                    "</li>"
                    for item in inspection.layers
                )
                content = f"""
                <div class="info" style="text-align:left;max-width:560px;margin:0 auto;">
                    <p>Select a layer to load the interactive map.</p>
                    <ul>{layer_items}</ul>
                </div>
                """
                return HTMLResponse(
                    wrap_html_response(
                        content,
                        title=f"{reference_name} map",
                        plotly_bundle="none",
                    )
                )

            if inspection.is_mappable and selected_layer is None:
                inspection = _build_spatial_map_inspection(
                    db,
                    reference_name,
                    limit=limit,
                    offset=0,
                    layer=None,
                    simplify_tolerance=0.001,
                )

        if not inspection.is_mappable:
            content = error_html("No geometry column is available for this reference.")
        elif not inspection.feature_collection.get("features"):
            content = "<p class='info'>No geometry is available for this layer.</p>"
        else:
            content = MapRenderer.render(
                inspection.feature_collection,
                config=MapConfig(
                    title=reference_name,
                    auto_zoom=True,
                    zoom_offset=0.85,
                    map_style="open-street-map",
                    height=520,
                    style=MapStyle(
                        color=NIAMOTO_MAP_GREEN,
                        fill_color=NIAMOTO_MAP_GREEN,
                        fill_opacity=0.24,
                        stroke_width=2,
                        point_radius=8,
                    ),
                ),
                engine="plotly",
            )

        title = f"{reference_name} map"
        if inspection.selected_layer:
            title = f"{title} - {inspection.selected_layer}"
        return HTMLResponse(
            wrap_html_response(content, title=title, plotly_bundle="maps")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error rendering spatial map: {str(e)}"
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
            preparer = db.engine.dialect.identifier_preparer

            datasets, references = _load_import_entities_config()
            # Resolve table from config metadata first.
            table_names = db.get_table_names()
            target_table = _resolve_entity_table(
                table_names, entity, datasets, references
            )

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
            columns_info = db.get_columns(target_table)
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
                    geometry_column = coord_cols["wkt_col"]
                    is_native = _is_native_geometry_column(
                        columns_info, geometry_column
                    )
                    with_coords = _count_valid_geometries(
                        conn, db, target_table, geometry_column, is_native
                    )
                    bbox = _compute_geometry_bbox(
                        conn, db, target_table, geometry_column, is_native
                    )

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
    entity: str = Query(default="taxons", description="Taxonomy reference name"),
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
            preparer = db.engine.dialect.identifier_preparer
            _, references = _load_import_entities_config()

            # Find taxonomy table
            table_names = db.get_table_names()
            target_table = _resolve_taxonomy_table_name(table_names, references, entity)

            if not target_table:
                return TaxonomyConsistency(
                    total_taxa=0,
                    levels=[],
                    orphan_records=[],
                    duplicate_names=[],
                    hierarchy_depth=0,
                )

            quoted_table = preparer.quote(target_table)
            columns_info = db.get_columns(target_table)
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
            preparer = db.engine.dialect.identifier_preparer

            if entity not in db.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity}' not found"
                )

            quoted_table = preparer.quote(entity)
            columns_info = db.get_columns(entity)

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
                        except Exception as exc:
                            logger.debug(
                                "Median computation failed for %s.%s: %s",
                                entity,
                                col_name,
                                exc,
                            )
                            median_val = None

                        # Outlier detection - initialize variables
                        outliers = []
                        outlier_count = 0
                        lower_bound = None
                        upper_bound = None
                        outliers_low_count = 0
                        outliers_high_count = 0
                        histogram_bins: List[HistogramBin] = []

                        # Prepare safe columns list (exclude BYTEA for JSON serialization)
                        safe_columns = [
                            c["name"]
                            for c in columns_info
                            if "BYTEA" not in str(c.get("type", "")).upper()
                        ]

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
                                    lower_bound = q1 - threshold * iqr
                                    upper_bound = q3 + threshold * iqr

                                    # Count outliers (total, low, high)
                                    result = conn.execute(
                                        text(
                                            f"""
                                        SELECT
                                            COUNT(*) FILTER (WHERE {quoted_col} < {lower_bound}),
                                            COUNT(*) FILTER (WHERE {quoted_col} > {upper_bound})
                                        FROM {quoted_table}
                                        WHERE {quoted_col} IS NOT NULL
                                    """
                                        )
                                    )
                                    count_row = result.fetchone()
                                    outliers_low_count = count_row[0] or 0
                                    outliers_high_count = count_row[1] or 0
                                    outlier_count = (
                                        outliers_low_count + outliers_high_count
                                    )

                                    # Get sample outliers with the analyzed column first
                                    # Reorder columns to put analyzed column first
                                    cols_ordered = [col_name] + [
                                        c for c in safe_columns if c != col_name
                                    ]
                                    cols_ordered_sql = ", ".join(
                                        preparer.quote(c) for c in cols_ordered[:10]
                                    )
                                    result = conn.execute(
                                        text(
                                            f"""
                                        SELECT {cols_ordered_sql} FROM {quoted_table}
                                        WHERE {quoted_col} IS NOT NULL
                                        AND ({quoted_col} < {lower_bound} OR {quoted_col} > {upper_bound})
                                        ORDER BY ABS({quoted_col} - {(lower_bound + upper_bound) / 2}) DESC
                                        LIMIT 5
                                    """
                                        )
                                    )
                                    for out_row in result:
                                        outliers.append(dict(out_row._mapping))

                                    # Generate histogram (20 bins)
                                    if (
                                        min_val is not None
                                        and max_val is not None
                                        and max_val > min_val
                                    ):
                                        num_bins = 20
                                        bin_width = (max_val - min_val) / num_bins
                                        result = conn.execute(
                                            text(
                                                f"""
                                            SELECT
                                                FLOOR(({quoted_col} - {min_val}) / {bin_width}) as bin_idx,
                                                COUNT(*) as cnt
                                            FROM {quoted_table}
                                            WHERE {quoted_col} IS NOT NULL
                                            GROUP BY bin_idx
                                            ORDER BY bin_idx
                                        """
                                            )
                                        )
                                        bin_counts = {
                                            int(r[0]): int(r[1])
                                            for r in result
                                            if r[0] is not None
                                        }
                                        for i in range(num_bins):
                                            bin_start = min_val + i * bin_width
                                            bin_end = min_val + (i + 1) * bin_width
                                            is_outlier = (
                                                bin_start < lower_bound
                                                or bin_end > upper_bound
                                            )
                                            histogram_bins.append(
                                                HistogramBin(
                                                    bin_start=round(bin_start, 2),
                                                    bin_end=round(bin_end, 2),
                                                    count=bin_counts.get(i, 0),
                                                    is_outlier_zone=is_outlier,
                                                )
                                            )
                            except Exception as exc:
                                logger.warning(
                                    "IQR outlier analysis failed for %s.%s: %s",
                                    entity,
                                    col_name,
                                    exc,
                                )

                        elif method == "zscore":
                            # Z-score: outlier if |z| > threshold (z = (x - mean) / std)
                            # Default threshold: 3 (99.7% of data)
                            try:
                                result = conn.execute(
                                    text(
                                        f"""
                                    SELECT AVG({quoted_col}), STDDEV({quoted_col})
                                    FROM {quoted_table}
                                    WHERE {quoted_col} IS NOT NULL
                                """
                                    )
                                )
                                stats_row = result.fetchone()
                                if (
                                    stats_row
                                    and stats_row[0] is not None
                                    and stats_row[1] is not None
                                ):
                                    mean = float(stats_row[0])
                                    std = float(stats_row[1])

                                    if std > 0:
                                        lower_bound = mean - threshold * std
                                        upper_bound = mean + threshold * std

                                        # Count outliers (total, low, high)
                                        result = conn.execute(
                                            text(
                                                f"""
                                            SELECT
                                                COUNT(*) FILTER (WHERE {quoted_col} < {lower_bound}),
                                                COUNT(*) FILTER (WHERE {quoted_col} > {upper_bound})
                                            FROM {quoted_table}
                                            WHERE {quoted_col} IS NOT NULL
                                        """
                                            )
                                        )
                                        count_row = result.fetchone()
                                        outliers_low_count = count_row[0] or 0
                                        outliers_high_count = count_row[1] or 0
                                        outlier_count = (
                                            outliers_low_count + outliers_high_count
                                        )

                                        # Get sample outliers with analyzed column first
                                        cols_ordered = [col_name] + [
                                            c for c in safe_columns if c != col_name
                                        ]
                                        cols_ordered_sql = ", ".join(
                                            preparer.quote(c) for c in cols_ordered[:10]
                                        )
                                        result = conn.execute(
                                            text(
                                                f"""
                                            SELECT {cols_ordered_sql} FROM {quoted_table}
                                            WHERE {quoted_col} IS NOT NULL
                                            AND ({quoted_col} < {lower_bound} OR {quoted_col} > {upper_bound})
                                            ORDER BY ABS({quoted_col} - {mean}) DESC
                                            LIMIT 5
                                        """
                                            )
                                        )
                                        for out_row in result:
                                            outliers.append(dict(out_row._mapping))

                                        # Generate histogram (20 bins)
                                        if (
                                            min_val is not None
                                            and max_val is not None
                                            and max_val > min_val
                                        ):
                                            num_bins = 20
                                            bin_width = (max_val - min_val) / num_bins
                                            result = conn.execute(
                                                text(
                                                    f"""
                                                SELECT
                                                    FLOOR(({quoted_col} - {min_val}) / {bin_width}) as bin_idx,
                                                    COUNT(*) as cnt
                                                FROM {quoted_table}
                                                WHERE {quoted_col} IS NOT NULL
                                                GROUP BY bin_idx
                                                ORDER BY bin_idx
                                            """
                                                )
                                            )
                                            bin_counts = {
                                                int(r[0]): int(r[1])
                                                for r in result
                                                if r[0] is not None
                                            }
                                            for i in range(num_bins):
                                                bin_start = min_val + i * bin_width
                                                bin_end = min_val + (i + 1) * bin_width
                                                is_outlier = (
                                                    bin_start < lower_bound
                                                    or bin_end > upper_bound
                                                )
                                                histogram_bins.append(
                                                    HistogramBin(
                                                        bin_start=round(bin_start, 2),
                                                        bin_end=round(bin_end, 2),
                                                        count=bin_counts.get(i, 0),
                                                        is_outlier_zone=is_outlier,
                                                    )
                                                )
                            except Exception as exc:
                                logger.warning(
                                    "Z-score outlier analysis failed for %s.%s: %s",
                                    entity,
                                    col_name,
                                    exc,
                                )

                        elif method == "percentile":
                            # Percentile: outlier if value < P(threshold) or > P(100-threshold)
                            # Default threshold: 5 (excludes bottom 5% and top 5%)
                            try:
                                lower_pct = threshold / 100.0
                                upper_pct = 1.0 - lower_pct

                                result = conn.execute(
                                    text(
                                        f"""
                                    SELECT
                                        PERCENTILE_CONT({lower_pct}) WITHIN GROUP (ORDER BY {quoted_col}),
                                        PERCENTILE_CONT({upper_pct}) WITHIN GROUP (ORDER BY {quoted_col})
                                    FROM {quoted_table}
                                    WHERE {quoted_col} IS NOT NULL
                                """
                                    )
                                )
                                pct_row = result.fetchone()
                                if pct_row and pct_row[0] is not None:
                                    lower_bound = float(pct_row[0])
                                    upper_bound = float(pct_row[1])

                                    # Count outliers (total, low, high)
                                    result = conn.execute(
                                        text(
                                            f"""
                                        SELECT
                                            COUNT(*) FILTER (WHERE {quoted_col} < {lower_bound}),
                                            COUNT(*) FILTER (WHERE {quoted_col} > {upper_bound})
                                        FROM {quoted_table}
                                        WHERE {quoted_col} IS NOT NULL
                                    """
                                        )
                                    )
                                    count_row = result.fetchone()
                                    outliers_low_count = count_row[0] or 0
                                    outliers_high_count = count_row[1] or 0
                                    outlier_count = (
                                        outliers_low_count + outliers_high_count
                                    )

                                    # Get sample outliers with analyzed column first
                                    cols_ordered = [col_name] + [
                                        c for c in safe_columns if c != col_name
                                    ]
                                    cols_ordered_sql = ", ".join(
                                        preparer.quote(c) for c in cols_ordered[:10]
                                    )
                                    result = conn.execute(
                                        text(
                                            f"""
                                        SELECT {cols_ordered_sql} FROM {quoted_table}
                                        WHERE {quoted_col} IS NOT NULL
                                        AND ({quoted_col} < {lower_bound} OR {quoted_col} > {upper_bound})
                                        ORDER BY ABS({quoted_col} - {(lower_bound + upper_bound) / 2}) DESC
                                        LIMIT 5
                                    """
                                        )
                                    )
                                    for out_row in result:
                                        outliers.append(dict(out_row._mapping))

                                    # Generate histogram (20 bins)
                                    if (
                                        min_val is not None
                                        and max_val is not None
                                        and max_val > min_val
                                    ):
                                        num_bins = 20
                                        bin_width = (max_val - min_val) / num_bins
                                        result = conn.execute(
                                            text(
                                                f"""
                                            SELECT
                                                FLOOR(({quoted_col} - {min_val}) / {bin_width}) as bin_idx,
                                                COUNT(*) as cnt
                                            FROM {quoted_table}
                                            WHERE {quoted_col} IS NOT NULL
                                            GROUP BY bin_idx
                                            ORDER BY bin_idx
                                        """
                                            )
                                        )
                                        bin_counts = {
                                            int(r[0]): int(r[1])
                                            for r in result
                                            if r[0] is not None
                                        }
                                        for i in range(num_bins):
                                            bin_start = min_val + i * bin_width
                                            bin_end = min_val + (i + 1) * bin_width
                                            is_outlier = (
                                                bin_start < lower_bound
                                                or bin_end > upper_bound
                                            )
                                            histogram_bins.append(
                                                HistogramBin(
                                                    bin_start=round(bin_start, 2),
                                                    bin_end=round(bin_end, 2),
                                                    count=bin_counts.get(i, 0),
                                                    is_outlier_zone=is_outlier,
                                                )
                                            )
                            except Exception as exc:
                                logger.warning(
                                    "Percentile outlier analysis failed for %s.%s: %s",
                                    entity,
                                    col_name,
                                    exc,
                                )

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
                                lower_bound=round(lower_bound, 4)
                                if lower_bound is not None
                                else None,
                                upper_bound=round(upper_bound, 4)
                                if upper_bound is not None
                                else None,
                                outliers_low_count=outliers_low_count,
                                outliers_high_count=outliers_high_count,
                                histogram=histogram_bins if histogram_bins else None,
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


@router.get("/value-validation/{entity}/export-outliers")
async def export_outliers_csv(
    entity: str,
    column: str = Query(..., description="Column to analyze for outliers"),
    method: str = Query(
        default="iqr", description="Detection method: iqr, zscore, percentile"
    ),
    threshold: float = Query(default=1.5, description="Detection threshold"),
):
    """
    Export all outliers for a specific column as CSV.

    Returns a CSV file with all records that are detected as outliers
    according to the specified method and threshold.
    """
    db_path = get_database_path()
    if not db_path:
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        with open_database(db_path, read_only=True) as db:
            preparer = db.engine.dialect.identifier_preparer

            if entity not in db.get_table_names():
                raise HTTPException(
                    status_code=404, detail=f"Entity '{entity}' not found"
                )

            columns_info = db.get_columns(entity)
            col_names = [c["name"] for c in columns_info]

            if column not in col_names:
                raise HTTPException(
                    status_code=404, detail=f"Column '{column}' not found in {entity}"
                )

            quoted_table = preparer.quote(entity)
            quoted_col = preparer.quote(column)

            # Prepare safe columns (exclude BYTEA)
            safe_columns = [
                c["name"]
                for c in columns_info
                if "BYTEA" not in str(c.get("type", "")).upper()
            ]

            with db.engine.connect() as conn:
                # Calculate bounds based on method
                lower_bound = None
                upper_bound = None

                if method == "iqr":
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
                        lower_bound = q1 - threshold * iqr
                        upper_bound = q3 + threshold * iqr

                elif method == "zscore":
                    result = conn.execute(
                        text(
                            f"""
                        SELECT AVG({quoted_col}), STDDEV({quoted_col})
                        FROM {quoted_table}
                        WHERE {quoted_col} IS NOT NULL
                    """
                        )
                    )
                    stats_row = result.fetchone()
                    if stats_row and stats_row[0] is not None and stats_row[1]:
                        mean = float(stats_row[0])
                        std = float(stats_row[1])
                        if std > 0:
                            lower_bound = mean - threshold * std
                            upper_bound = mean + threshold * std

                elif method == "percentile":
                    lower_pct = threshold / 100.0
                    upper_pct = 1.0 - lower_pct
                    result = conn.execute(
                        text(
                            f"""
                        SELECT
                            PERCENTILE_CONT({lower_pct}) WITHIN GROUP (ORDER BY {quoted_col}),
                            PERCENTILE_CONT({upper_pct}) WITHIN GROUP (ORDER BY {quoted_col})
                        FROM {quoted_table}
                        WHERE {quoted_col} IS NOT NULL
                    """
                        )
                    )
                    pct_row = result.fetchone()
                    if pct_row and pct_row[0] is not None:
                        lower_bound = float(pct_row[0])
                        upper_bound = float(pct_row[1])

                if lower_bound is None or upper_bound is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Could not calculate outlier bounds for this column",
                    )

                # Fetch all outliers
                cols_ordered = [column] + [c for c in safe_columns if c != column]
                cols_ordered_sql = ", ".join(preparer.quote(c) for c in cols_ordered)

                result = conn.execute(
                    text(
                        f"""
                    SELECT {cols_ordered_sql} FROM {quoted_table}
                    WHERE {quoted_col} IS NOT NULL
                    AND ({quoted_col} < {lower_bound} OR {quoted_col} > {upper_bound})
                    ORDER BY {quoted_col}
                """
                    )
                )

                # Generate CSV
                output = io.StringIO()
                writer = csv.writer(output)

                # Write header
                writer.writerow(cols_ordered)

                # Write data
                for row in result:
                    writer.writerow(row)

                output.seek(0)

                filename = f"{entity}_{column}_outliers_{method}.csv"
                return StreamingResponse(
                    iter([output.getvalue()]),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error exporting outliers: {str(e)}"
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
            table_names = db.get_table_names()
            datasets, references = _load_import_entities_config()

            # Resolve occurrence table from explicit param/config.
            occ_table = _resolve_occurrence_table(
                table_names, occurrence_entity, datasets
            )

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
            columns_info = db.get_columns(occ_table)
            geo_column, _ = _find_geometry_column(columns_info)

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

            # Resolve spatial references from config (kind=spatial), fallback to geometry scan.
            spatial_tables = _resolve_spatial_reference_tables(
                db, table_names, inspector, references, occurrence_table=occ_table
            )
            available_shapes = []

            for ref in spatial_tables:
                table_name = ref["table_name"]
                quoted_t = preparer.quote(table_name)
                has_geo = ref.get("has_geometry", False)
                type_column = ref.get("type_column")

                # Get row count and distinct shape types (if available)
                shape_count = 0
                shape_types: List[str] = []
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {quoted_t}"))
                    shape_count = result.scalar() or 0

                    if type_column:
                        quoted_type = preparer.quote(type_column)
                        try:
                            result = conn.execute(
                                text(
                                    f"""
                                    SELECT DISTINCT CAST({quoted_type} AS VARCHAR)
                                    FROM {quoted_t}
                                    WHERE {quoted_type} IS NOT NULL
                                      AND CAST({quoted_type} AS VARCHAR) != ''
                                    LIMIT 10
                                """
                                )
                            )
                            shape_types = [
                                row[0] for row in result.fetchall() if row[0]
                            ]
                        except Exception as exc:
                            logger.debug(
                                "Failed to fetch shape types for table '%s': %s",
                                table_name,
                                exc,
                            )
                            shape_types = []

                available_shapes.append(
                    ShapeInfo(
                        table_name=table_name,
                        display_name=ref.get("display_name", table_name),
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
            table_names = db.get_table_names()
            datasets, references = _load_import_entities_config()

            # Resolve occurrence table from explicit param/config.
            occ_table = _resolve_occurrence_table(
                table_names, occurrence_entity, datasets
            )

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

            # Find geo column in occurrences.
            columns_info = db.get_columns(occ_table)
            geo_column, occ_geo_is_native = _find_geometry_column(columns_info)

            if not geo_column:
                return SpatialAnalysisResult(
                    total_occurrences=0,
                    occurrences_with_geo=0,
                    occurrences_without_geo=0,
                    shape_coverage=[],
                    analysis_time_seconds=time.time() - start_time,
                    geo_column=None,
                    status="no_geo_column",
                    message=f"No geometry column found in '{occ_table}'",
                )

            quoted_occ = preparer.quote(occ_table)
            quoted_geo = preparer.quote(geo_column)

            spatial_tables = _resolve_spatial_reference_tables(
                db, table_names, inspector, references, occurrence_table=occ_table
            )
            shape_tables = [s for s in spatial_tables if s.get("has_geometry")]
            shape_tables_without_geo = [
                s.get("table_name", "")
                for s in spatial_tables
                if not s.get("has_geometry")
            ]

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
                for shape_meta in shape_tables:
                    shape_table = shape_meta["table_name"]
                    shape_geo_col = shape_meta["geo_column"]
                    shape_is_native = shape_meta["is_native"]
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
                    except Exception as exc:
                        logger.debug(
                            "ST_Intersects failed for shape table '%s': %s",
                            shape_table,
                            exc,
                        )
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
                        except Exception as exc:
                            logger.debug(
                                "ST_Contains fallback failed for shape table '%s': %s",
                                shape_table,
                                exc,
                            )
                            # Spatial functions not available or query failed
                            covered = 0

                    coverage_pct = (covered / with_geo * 100) if with_geo > 0 else 0

                    shape_coverage.append(
                        ShapeCoverageDetail(
                            shape_type=shape_meta.get("display_name", shape_table),
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
            table_names = db.get_table_names()
            datasets, references = _load_import_entities_config()

            # Resolve occurrence table from explicit param/config.
            occ_table = _resolve_occurrence_table(
                table_names, occurrence_entity, datasets
            )

            if not occ_table:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="error",
                    message=f"Occurrence table '{occurrence_entity}' not found",
                )

            # Find geo column in occurrences.
            columns_info = db.get_columns(occ_table)
            geo_column, occ_geo_is_native = _find_geometry_column(columns_info)

            if not geo_column:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="no_geo_column",
                    message=f"No geometry column found in '{occ_table}'",
                )

            spatial_tables = _resolve_spatial_reference_tables(
                db, table_names, inspector, references, occurrence_table=occ_table
            )
            shape_candidates = [s for s in spatial_tables if s.get("has_geometry")]

            if not shape_candidates:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="no_shapes",
                    message="No shape table with geometry found",
                )

            # Deterministic choice: first configured spatial reference.
            shape_meta = shape_candidates[0]
            shape_table = shape_meta["table_name"]
            shape_geo_col = shape_meta["geo_column"]
            shape_is_native = shape_meta["is_native"]

            # Resolve id/name/type columns dynamically (no hardcoded `id`/`name`).
            shape_columns = [c["name"] for c in db.get_columns(shape_table)]
            shape_cols_by_lower = {c.lower(): c for c in shape_columns}
            shape_id_col = shape_meta.get("id_column") or _pick_first_existing(
                shape_cols_by_lower, ["id", "name"]
            )
            shape_name_col = shape_meta.get("name_column") or _pick_first_existing(
                shape_cols_by_lower, ["name", "label", "title", shape_id_col]
            )
            shape_type_col = shape_meta.get("type_column")

            if not shape_id_col:
                return ShapeDistributionResult(
                    total_occurrences_with_geo=0,
                    shapes=[],
                    analysis_time_seconds=time.time() - start_time,
                    status="error",
                    message=f"Unable to resolve an identifier column for '{shape_table}'",
                )

            if not shape_name_col:
                shape_name_col = shape_id_col

            quoted_occ = preparer.quote(occ_table)
            quoted_geo = preparer.quote(geo_column)
            quoted_shape = preparer.quote(shape_table)
            quoted_shape_geo = preparer.quote(shape_geo_col)
            quoted_shape_id = preparer.quote(shape_id_col)
            quoted_shape_name = preparer.quote(shape_name_col)
            quoted_shape_type = (
                preparer.quote(shape_type_col) if shape_type_col else None
            )

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
                shape_type_expr = (
                    f"COALESCE(CAST(s.{quoted_shape_type} AS VARCHAR), 'unknown')"
                    if quoted_shape_type
                    else "'unknown'"
                )
                result = conn.execute(
                    text(
                        f"""
                        SELECT
                            CAST(s.{quoted_shape_id} AS VARCHAR) as shape_id,
                            CAST(s.{quoted_shape_name} AS VARCHAR) as shape_name,
                            {shape_type_expr} as shape_type,
                            SUM(CASE WHEN o.{quoted_geo} IS NOT NULL THEN 1 ELSE 0 END) as occurrence_count
                        FROM {quoted_shape} s
                        LEFT JOIN {quoted_occ} o
                            ON o.{quoted_geo} IS NOT NULL
                            AND s.{quoted_shape_geo} IS NOT NULL
                            AND ST_Intersects({occ_geom_expr}, {shape_geom_expr})
                        WHERE s.{quoted_shape_geo} IS NOT NULL
                        GROUP BY 1, 2, 3
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
                            shape_id=str(row[0]),
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
        with open(rules_path, "r", encoding="utf-8") as f:
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

        with open(rules_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(rules_data, f, default_flow_style=False)

        return rules

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving validation rules: {str(e)}"
        )
