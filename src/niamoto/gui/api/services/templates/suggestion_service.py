"""
Suggestion service for templates.

Provides functions to generate widget suggestions based on data analysis.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml
from sqlalchemy import text

from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_entity_table as shared_resolve_entity_table,
)
from niamoto.core.imports.data_analyzer import (
    DataCategory,
    EnrichedColumnProfile,
    FieldPurpose,
)
from niamoto.core.imports.template_suggester import (
    TemplateSuggester,
    TemplateSuggestion,
)
from niamoto.core.imports.widget_generator import WidgetGenerator, WidgetSuggestion
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.core.imports.class_object_suggester import suggest_widgets_for_source

logger = logging.getLogger(__name__)

_REFERENCE_FIELD_SKIP_EXACT = {
    "id",
    "lft",
    "rght",
    "level",
    "parent_id",
    "location",
    "geo_pt",
    "extra_data",
    "geometry",
}
_REFERENCE_FIELD_SKIP_SUFFIXES = ("_id", "_geom", "_ref", "_key")
_REFERENCE_FIELD_SKIP_SUBSTRINGS = ("created", "updated", "geometry", "geom", "_wkt")
_REFERENCE_FIELD_SUGGESTIONS_CACHE: Dict[
    Tuple[str, str, str, int, int], List[Dict[str, Any]]
] = {}
_FAST_REFERENCE_CATEGORY_WIDGETS: Dict[DataCategory, List[Tuple[str, str, bool]]] = {
    DataCategory.NUMERIC_CONTINUOUS: [
        ("binned_distribution", "bar_plot", True),
        ("statistical_summary", "radial_gauge", False),
    ],
    DataCategory.NUMERIC_DISCRETE: [
        ("binned_distribution", "bar_plot", True),
        ("statistical_summary", "radial_gauge", False),
    ],
    DataCategory.CATEGORICAL: [
        ("categorical_distribution", "donut_chart", True),
        ("top_ranking", "bar_plot", False),
    ],
    DataCategory.CATEGORICAL_HIGH_CARD: [
        ("top_ranking", "bar_plot", True),
    ],
    DataCategory.BOOLEAN: [
        ("binary_counter", "donut_chart", True),
    ],
}


def _get_path_mtime_ns(path: Path) -> int:
    """Return path mtime in nanoseconds, or 0 when the path is missing."""
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _build_reference_field_cache_key(
    reference_name: str,
) -> Optional[Tuple[str, str, str, int, int]]:
    """Build a cache key that invalidates when project DB or import config changes."""
    work_dir = get_working_directory()
    db_path = get_database_path()
    if not work_dir or not db_path:
        return None

    import_path = Path(work_dir) / "config" / "import.yml"
    return (
        str(Path(work_dir).resolve()),
        reference_name,
        str(Path(db_path).resolve()),
        _get_path_mtime_ns(Path(db_path)),
        _get_path_mtime_ns(import_path),
    )


def _should_profile_reference_field(column_name: str, series: pd.Series) -> bool:
    """Return whether a reference-table column is worth profiling for widgets."""
    col_lower = column_name.lower()
    if col_lower in _REFERENCE_FIELD_SKIP_EXACT:
        return False
    if col_lower.endswith(_REFERENCE_FIELD_SKIP_SUFFIXES):
        return False
    if col_lower.startswith("id_"):
        return False
    if any(sub in col_lower for sub in _REFERENCE_FIELD_SKIP_SUBSTRINGS):
        return False

    total_count = len(series)
    if total_count == 0:
        return False

    non_null = series.dropna()
    if non_null.empty:
        return False

    null_ratio = 1 - (len(non_null) / total_count)
    if null_ratio > 0.9:
        return False

    first_value = non_null.iloc[0]
    if isinstance(first_value, (bytes, bytearray, memoryview)):
        return False

    return True


def _safe_registry_get(registry: Any, entity_name: str) -> Optional[Any]:
    """Return registry metadata when available, swallowing lookup errors."""
    if registry is None:
        return None
    try:
        return registry.get(entity_name)
    except Exception:
        return None


def _is_internal_registry_reference(entity_meta: Any, entity_table: str) -> bool:
    """Return whether the resolved table is an internal Niamoto reference table."""
    if entity_meta is None:
        return False

    kind_value = str(getattr(entity_meta, "kind", "")).lower()
    table_name = str(getattr(entity_meta, "table_name", "") or "")
    if kind_value not in {"reference", "entitykind.reference"}:
        return False
    if not entity_table or entity_table != table_name:
        return False
    return entity_table.startswith("entity_")


def _extract_reference_metadata_signals(
    *,
    reference_name: str,
    columns: List[str],
    entity_meta: Any,
    reference_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Collect lightweight hints from import config and registry metadata."""
    config = getattr(entity_meta, "config", {}) if entity_meta is not None else {}
    if not isinstance(config, dict):
        config = {}

    schema = config.get("schema", {})
    if not isinstance(schema, dict):
        schema = {}
    ref_schema = reference_config.get("schema", {})
    if not isinstance(ref_schema, dict):
        ref_schema = {}

    id_field = (
        schema.get("id_field")
        or ref_schema.get("id_field")
        or _pick_identifier_column(columns, entity_name=reference_name)
        or "id"
    )

    derived = config.get("derived", {})
    if not isinstance(derived, dict):
        derived = {}

    label_fields = {
        str(field)
        for field in [
            derived.get("external_name_field"),
            _pick_name_column(columns, id_field, reference_name) if columns else None,
        ]
        if field
    }

    geometry_fields = {
        str(field.get("name"))
        for field in schema.get("fields", [])
        if isinstance(field, dict) and str(field.get("type", "")).lower() == "geometry"
    }
    geometry_fields.update(
        str(field.get("name"))
        for field in ref_schema.get("fields", [])
        if isinstance(field, dict) and str(field.get("type", "")).lower() == "geometry"
    )

    technical_fields = {
        str(field)
        for field in [
            id_field,
            derived.get("external_id_field"),
        ]
        if field
    }

    return {
        "id_field": id_field,
        "label_fields": label_fields,
        "geometry_fields": geometry_fields,
        "technical_fields": technical_fields,
    }


def _coerce_reference_series_numeric(series: pd.Series) -> Tuple[pd.Series, float]:
    """Attempt numeric coercion and return both values and success ratio."""
    non_null = series.dropna()
    if non_null.empty:
        return pd.Series(dtype="float64"), 0.0

    coerced = pd.to_numeric(non_null, errors="coerce")
    success_ratio = float(coerced.notna().mean())
    return coerced.dropna(), success_ratio


def _is_boolean_like(series: pd.Series) -> bool:
    """Return whether the column behaves like a boolean."""
    non_null = series.dropna()
    if non_null.empty:
        return False

    lowered_values = {str(value).strip().lower() for value in non_null}
    boolean_tokens = {
        "0",
        "1",
        "true",
        "false",
        "yes",
        "no",
        "oui",
        "non",
        "y",
        "n",
        "t",
        "f",
    }
    return len(lowered_values) <= 2 and lowered_values.issubset(boolean_tokens)


def _classify_reference_column_fast(
    *,
    column_name: str,
    series: pd.Series,
    metadata_signals: Dict[str, Any],
) -> Optional[DataCategory]:
    """Classify a reference-table column with a lightweight heuristic."""
    non_null = series.dropna()
    if non_null.empty:
        return None

    distinct_count = int(non_null.nunique())
    unique_ratio = distinct_count / len(non_null)

    if _is_boolean_like(non_null):
        return DataCategory.BOOLEAN

    numeric_non_null = non_null
    numeric_ratio = 0.0
    if pd.api.types.is_numeric_dtype(series):
        numeric_ratio = 1.0
    else:
        numeric_non_null, numeric_ratio = _coerce_reference_series_numeric(non_null)

    if numeric_ratio >= 0.95:
        if numeric_non_null.empty:
            return None
        if distinct_count <= 2:
            return DataCategory.BOOLEAN

        integer_like = (numeric_non_null % 1 == 0).all()
        if integer_like and distinct_count <= 12:
            return DataCategory.NUMERIC_DISCRETE
        return DataCategory.NUMERIC_CONTINUOUS

    if 0.2 <= numeric_ratio < 0.95:
        return None

    if distinct_count <= 20 or unique_ratio <= 0.4:
        return DataCategory.CATEGORICAL
    return DataCategory.CATEGORICAL_HIGH_CARD


def _should_skip_reference_fast_path(
    *,
    column_name: str,
    series: pd.Series,
    metadata_signals: Dict[str, Any],
) -> bool:
    """Return whether the column should be ignored instead of sent to fallback ML."""
    if not _should_profile_reference_field(column_name, series):
        return True
    if column_name in metadata_signals["geometry_fields"]:
        return True
    if column_name in metadata_signals["label_fields"]:
        return True
    if column_name in metadata_signals["technical_fields"]:
        return True
    return False


def _build_fast_enriched_profile(
    *,
    column_name: str,
    series: pd.Series,
    category: DataCategory,
) -> EnrichedColumnProfile:
    """Create a lightweight EnrichedColumnProfile without running ML profiling."""
    non_null = series.dropna()
    numeric_non_null = non_null
    if not pd.api.types.is_numeric_dtype(series):
        coerced, numeric_ratio = _coerce_reference_series_numeric(non_null)
        if numeric_ratio >= 0.95:
            numeric_non_null = coerced

    value_range = None
    if (
        category
        in {
            DataCategory.NUMERIC_CONTINUOUS,
            DataCategory.NUMERIC_DISCRETE,
        }
        and not numeric_non_null.empty
    ):
        value_range = (
            float(numeric_non_null.min()),
            float(numeric_non_null.max()),
        )

    suggested_labels = None
    if category in {DataCategory.CATEGORICAL, DataCategory.CATEGORICAL_HIGH_CARD}:
        suggested_labels = [str(value) for value in non_null.astype(str).unique()[:10]]

    sample_values = [value for value in non_null.head(10).tolist()]
    if suggested_labels:
        sample_values = suggested_labels

    field_purpose = (
        FieldPurpose.MEASUREMENT
        if category in {DataCategory.NUMERIC_CONTINUOUS, DataCategory.NUMERIC_DISCRETE}
        else FieldPurpose.CLASSIFICATION
    )

    return EnrichedColumnProfile(
        name=column_name,
        dtype=str(series.dtype),
        semantic_type=None,
        unique_ratio=(non_null.nunique() / len(non_null)) if len(non_null) else 0.0,
        null_ratio=1 - (len(non_null) / len(series)) if len(series) else 1.0,
        sample_values=sample_values,
        confidence=0.8,
        data_category=category,
        field_purpose=field_purpose,
        suggested_bins=None,
        suggested_labels=suggested_labels,
        cardinality=int(non_null.nunique()) if len(non_null) else 0,
        value_range=value_range,
    )


def _generate_fast_reference_widget_suggestions(
    *,
    reference_name: str,
    profiles: List[EnrichedColumnProfile],
) -> List[TemplateSuggestion]:
    """Generate TemplateSuggestion objects from fast classified profiles."""
    generator = WidgetGenerator()
    suggester = TemplateSuggester()
    template_suggestions: List[TemplateSuggestion] = []

    for profile in profiles:
        combos = _FAST_REFERENCE_CATEGORY_WIDGETS.get(profile.data_category, [])
        column_suggestions: List[WidgetSuggestion] = []
        for transformer_name, widget_name, is_primary in combos:
            suggestion = generator._create_suggestion(
                profile=profile,
                transformer_name=transformer_name,
                widget_name=widget_name,
                source_table=reference_name,
                is_primary=is_primary,
                match_score=1.0,
            )
            if suggestion is not None:
                column_suggestions.append(suggestion)

        suggestion_ids = [suggestion.id for suggestion in column_suggestions]
        for suggestion in column_suggestions:
            suggestion.alternatives = [
                suggestion_id
                for suggestion_id in suggestion_ids
                if suggestion_id != suggestion.id
            ]
            template_suggestions.append(
                suggester._convert_widget_suggestion(suggestion)
            )

    template_suggestions = [
        suggestion
        for suggestion in template_suggestions
        if suggestion.confidence >= TemplateSuggester.MIN_CONFIDENCE
    ]
    template_suggestions.sort(
        key=lambda suggestion: (
            -suggestion.confidence,
            not suggestion.is_recommended,
            suggestion.name,
        )
    )
    return template_suggestions


def _merge_reference_template_suggestions(
    *,
    reference_name: str,
    heuristic_suggestions: List[TemplateSuggestion],
    ml_suggestions: List[TemplateSuggestion],
) -> List[Dict[str, Any]]:
    """Merge heuristic and ML suggestions while preferring heuristic duplicates."""
    merged: Dict[str, TemplateSuggestion] = {}
    for suggestion in heuristic_suggestions:
        merged[suggestion.template_id] = suggestion
    for suggestion in ml_suggestions:
        merged.setdefault(suggestion.template_id, suggestion)

    ordered = sorted(
        merged.values(),
        key=lambda suggestion: (
            -suggestion.confidence,
            not suggestion.is_recommended,
            suggestion.name,
        ),
    )
    result: List[Dict[str, Any]] = []
    for suggestion in ordered:
        suggestion_dict = suggestion.to_dict()
        suggestion_dict["source"] = "reference"
        suggestion_dict["source_name"] = reference_name
        result.append(suggestion_dict)
    return result


def _generate_reference_suggestions_via_ml(
    *,
    entity_table: str,
    reference_name: str,
    profile_df: pd.DataFrame,
) -> List[TemplateSuggestion]:
    """Run the existing ML-backed suggestion pipeline for a DataFrame subset."""
    from niamoto.core.imports.data_analyzer import DataAnalyzer
    from niamoto.core.imports.profiler import DataProfiler

    if profile_df.empty:
        return []

    profiler = DataProfiler()
    dataset_profile = profiler.profile_dataframe(profile_df, Path(entity_table))

    analyzer = DataAnalyzer()
    enriched_profiles = []
    for col_profile in dataset_profile.columns:
        if col_profile.name in profile_df.columns:
            enriched = analyzer.enrich_profile(
                col_profile, profile_df[col_profile.name]
            )
            enriched_profiles.append(enriched)

    if not enriched_profiles:
        return []

    generator = WidgetGenerator()
    widget_suggestions = generator.generate_for_columns(
        enriched_profiles, source_table=reference_name
    )

    suggester = TemplateSuggester()
    return [
        suggester._convert_widget_suggestion(widget_suggestion)
        for widget_suggestion in widget_suggestions
    ]


def _load_import_config() -> Dict[str, Any]:
    """Load import.yml from current working directory when available."""
    work_dir = get_working_directory()
    if not work_dir:
        return {}

    import_path = Path(work_dir) / "config" / "import.yml"
    if not import_path.exists():
        return {}

    try:
        with open(import_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_entity_registry(db: Any):
    """Create an EntityRegistry when metadata table is available."""
    try:
        from niamoto.core.imports.registry import EntityRegistry

        return EntityRegistry(db)
    except Exception:
        return None


def _resolve_entity_table(
    db: Any, entity_name: str, registry: Any = None, kind: Optional[str] = None
) -> Optional[str]:
    """Resolve entity table using shared resolver."""
    return shared_resolve_entity_table(db, entity_name, registry=registry, kind=kind)


def _get_reference_config(
    reference_name: str, import_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Return reference config from import.yml when available."""
    references = import_config.get("entities", {}).get("references", {})
    if isinstance(references, dict):
        cfg = references.get(reference_name)
        if isinstance(cfg, dict):
            return cfg
    return {}


def _get_first_dataset_name(
    import_config: Dict[str, Any], registry: Any = None
) -> Optional[str]:
    """Resolve default dataset name from registry metadata, then import.yml."""
    if registry:
        try:
            from niamoto.core.imports.registry import EntityKind

            datasets = registry.list_entities(kind=EntityKind.DATASET)
            if datasets:
                return datasets[0].name
        except Exception:
            pass

    datasets_cfg = import_config.get("entities", {}).get("datasets", {})
    if isinstance(datasets_cfg, dict) and datasets_cfg:
        return next(iter(datasets_cfg))
    return None


def _pick_identifier_column(
    columns: List[str],
    entity_name: Optional[str] = None,
    preferred: Optional[str] = None,
) -> Optional[str]:
    """Pick a likely identifier column."""
    if not columns:
        return None

    lowered = {c.lower(): c for c in columns}
    candidates: List[str] = []
    if preferred:
        candidates.append(preferred)
    if entity_name:
        candidates.extend([f"id_{entity_name}", f"{entity_name}_id", entity_name])
    candidates.extend(["id", "uuid"])

    for candidate in candidates:
        resolved = lowered.get(candidate.lower())
        if resolved:
            return resolved

    return next((c for c in columns if c.lower().endswith("_id")), columns[0])


def _pick_name_column(columns: List[str], id_field: str, entity_name: str) -> str:
    """Pick a likely display name column."""
    lowered = {c.lower(): c for c in columns}
    candidates = [
        "full_name",
        "name",
        "label",
        "title",
        entity_name,
        "plot",
        "plot_code",
        "code",
        "site",
        "station",
    ]
    for candidate in candidates:
        resolved = lowered.get(candidate.lower())
        if resolved:
            return resolved

    return next(
        (
            c
            for c in columns
            if c != id_field
            and any(token in c.lower() for token in ("name", "label", "title"))
        ),
        id_field,
    )


def generate_navigation_suggestion(reference_name: str) -> Optional[Dict[str, Any]]:
    """Generate a navigation widget suggestion for a reference.

    Detects hierarchy fields from the database and generates appropriate config.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots')

    Returns:
        Dict in TemplateSuggestion format, or None if generation fails
    """
    try:
        db_path = get_database_path()
        if not db_path:
            # Return basic navigation suggestion without hierarchy detection
            return WidgetGenerator.generate_navigation_suggestion(
                reference_name=reference_name,
                is_hierarchical=False,
                hierarchy_fields=None,
            )

        from niamoto.common.database import Database

        db = Database(str(db_path), read_only=True)
        try:
            import_config = _load_import_config()
            ref_config = _get_reference_config(reference_name, import_config)
            registry = _get_entity_registry(db)

            table_name = _resolve_entity_table(
                db, reference_name, registry=registry, kind="reference"
            )
            if not table_name:
                return WidgetGenerator.generate_navigation_suggestion(
                    reference_name=reference_name,
                    is_hierarchical=False,
                    hierarchy_fields=None,
                )

            # Get column names from the table
            quoted_table_name = quote_identifier(db, table_name)
            columns_df = pd.read_sql(
                text(f"SELECT * FROM {quoted_table_name} LIMIT 0"),
                db.engine,
            )
            columns = columns_df.columns.tolist()
            columns_set = set(columns)

            # Detect hierarchy structure
            has_nested_set = "lft" in columns_set and "rght" in columns_set
            has_parent = "parent_id" in columns_set
            has_level = "level" in columns_set

            is_hierarchical = has_nested_set or (has_parent and has_level)

            # Detect ID field
            schema = (
                ref_config.get("schema", {}) if isinstance(ref_config, dict) else {}
            )
            preferred_id = schema.get("id_field") if isinstance(schema, dict) else None
            id_field = _pick_identifier_column(
                columns, entity_name=reference_name, preferred=preferred_id
            )
            if not id_field:
                id_field = "id"
            name_field = _pick_name_column(columns, id_field, reference_name)

            hierarchy_fields = {
                "has_nested_set": has_nested_set,
                "has_parent": has_parent,
                "has_level": has_level,
                "lft_field": "lft" if has_nested_set else None,
                "rght_field": "rght" if has_nested_set else None,
                "parent_id_field": "parent_id" if has_parent else None,
                "level_field": "level" if has_level else None,
                "id_field": id_field,
                "name_field": name_field,
            }

            return WidgetGenerator.generate_navigation_suggestion(
                reference_name=reference_name,
                is_hierarchical=is_hierarchical,
                hierarchy_fields=hierarchy_fields,
            )

        finally:
            db.close_db_session()

    except Exception as e:
        logger.warning(f"Error generating navigation suggestion: {e}")
        # Return basic suggestion on error
        return WidgetGenerator.generate_navigation_suggestion(
            reference_name=reference_name,
            is_hierarchical=False,
            hierarchy_fields=None,
        )


def generate_general_info_suggestion(
    reference_name: str, db: Any = None
) -> Optional[Dict[str, Any]]:
    """Generate a general_info widget suggestion for a reference.

    Dynamically analyzes columns to find the most useful fields for a summary card.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots', 'shapes')
        db: Optional Database instance to reuse (avoids DuckDB connection conflicts)

    Returns:
        Dict in TemplateSuggestion format, or None if no useful fields found
    """
    try:
        own_db = db is None
        if own_db:
            db_path = get_database_path()
            if not db_path:
                return None
            from niamoto.common.database import Database

            db = Database(str(db_path), read_only=True)
        try:
            import_config = _load_import_config()
            ref_config = _get_reference_config(reference_name, import_config)
            registry = _get_entity_registry(db)

            ref_table = _resolve_entity_table(
                db, reference_name, registry=registry, kind="reference"
            )
            if not ref_table:
                return None

            # Get column info to exclude geometry columns (binary WKB causes encoding errors)
            quoted_ref_table = quote_identifier(db, ref_table)
            with db.engine.connect() as conn:
                result = conn.execute(text(f"DESCRIBE {quoted_ref_table}"))
                col_info = result.fetchall()
            safe_columns = [
                quote_identifier(db, c[0])
                for c in col_info
                if c[1].upper() not in ("GEOMETRY", "BLOB", "BYTEA")
                and not c[0].endswith("_geom")
            ]
            if not safe_columns:
                return None

            # Get sample data to analyze columns (excluding geometry)
            columns_sql = ", ".join(safe_columns)
            sample_df = pd.read_sql(
                text(f"SELECT {columns_sql} FROM {quoted_ref_table} LIMIT 100"),
                db.engine,
            )
            if sample_df.empty:
                return None

            # Patterns to exclude (technical/internal columns)
            exclude_patterns = {
                "id",
                "lft",
                "rght",
                "level",
                "parent_id",
                "parent",
                "created_at",
                "updated_at",
                "modified",
                "created",
            }
            exclude_suffixes = ("_id", "_ref", "_key", "_idx", "_geom")

            # Analyze each column and score its usefulness
            column_scores = []
            for col in sample_df.columns:
                col_lower = col.lower()

                # Skip excluded columns
                if col_lower in exclude_patterns:
                    continue
                if any(col_lower.endswith(s) for s in exclude_suffixes):
                    continue
                if col_lower.startswith("id_"):
                    continue

                # Skip extra_data (handled separately)
                if col_lower == "extra_data":
                    continue

                # Analyze column characteristics
                non_null = sample_df[col].notna().sum()
                null_ratio = (
                    1 - (non_null / len(sample_df)) if len(sample_df) > 0 else 1
                )

                # Skip columns with too many nulls
                if null_ratio > 0.8:
                    continue

                unique_count = sample_df[col].nunique()
                unique_ratio = unique_count / non_null if non_null > 0 else 1

                # Calculate usefulness score
                score = 0.0

                # Prefer columns with values
                score += (1 - null_ratio) * 0.3

                # Prefer low cardinality (categories) but not unique values (IDs)
                if 0.01 < unique_ratio < 0.5:
                    score += 0.3  # Good for categories
                elif unique_ratio <= 0.01:
                    score += 0.1  # Too few unique values
                elif unique_ratio >= 0.9:
                    score -= 0.2  # Likely an ID

                # Prefer text columns (object dtype)
                if sample_df[col].dtype == "object":
                    # Check average string length
                    non_null_vals = sample_df[col].dropna()
                    if len(non_null_vals) > 0:
                        avg_len = non_null_vals.astype(str).str.len().mean()
                        if avg_len < 100:  # Short text = good for display
                            score += 0.2
                        elif avg_len > 500:  # Long text = not good for summary
                            score -= 0.3

                # Boost columns with meaningful names
                meaningful_keywords = [
                    "name",
                    "type",
                    "status",
                    "category",
                    "rank",
                    "label",
                    "title",
                ]
                if any(kw in col_lower for kw in meaningful_keywords):
                    score += 0.2

                if score > 0:
                    column_scores.append((col, score, unique_ratio))

            # Sort by score and take top fields
            column_scores.sort(key=lambda x: -x[1])
            selected_columns = column_scores[:6]  # Max 6 fields from main table

            # Build field configurations
            field_configs = []
            for col, score, _ in selected_columns:
                field_configs.append(
                    {
                        "source": reference_name,
                        "field": col,
                        "target": col.lower().replace(" ", "_"),
                    }
                )

            # Check for extra_data JSON column
            if "extra_data" in sample_df.columns:
                try:
                    non_null_extra = sample_df["extra_data"].dropna()
                    if len(non_null_extra) > 0:
                        sample_extra = non_null_extra.iloc[0]
                        if isinstance(sample_extra, str):
                            sample_extra = json.loads(sample_extra)
                        if isinstance(sample_extra, dict):
                            # Add up to 3 JSON fields
                            json_count = 0
                            for key, value in sample_extra.items():
                                if json_count >= 3:
                                    break
                                # Skip complex nested values
                                if (
                                    isinstance(value, (str, int, float, bool))
                                    or value is None
                                ):
                                    field_configs.append(
                                        {
                                            "source": reference_name,
                                            "field": f"extra_data.{key}",
                                            "target": key,
                                        }
                                    )
                                    json_count += 1
                except Exception:
                    pass

            # Add source dataset count if available
            try:
                relation = (
                    ref_config.get("relation", {})
                    if isinstance(ref_config, dict)
                    else {}
                )
                connector = (
                    ref_config.get("connector", {})
                    if isinstance(ref_config, dict)
                    else {}
                )
                source_dataset = relation.get("dataset") or connector.get("source")
                if not source_dataset:
                    source_dataset = _get_first_dataset_name(import_config, registry)

                source_table = _resolve_entity_table(
                    db, source_dataset or "", registry=registry, kind="dataset"
                )
                if source_dataset and source_table:
                    quoted_source_table = quote_identifier(db, source_table)
                    dataset_cols = pd.read_sql(
                        text(f"SELECT * FROM {quoted_source_table} LIMIT 0"), db.engine
                    ).columns.tolist()
                    count_field = _pick_identifier_column(
                        dataset_cols, entity_name=source_dataset
                    )
                    if not count_field and dataset_cols:
                        count_field = dataset_cols[0]
                    if count_field:
                        count_target = f"{source_dataset}_count"
                    else:
                        count_target = "records_count"

                    field_configs.append(
                        {
                            "source": source_dataset,
                            "field": count_field or "id",
                            "target": count_target,
                            "transformation": "count",
                        }
                    )
            except Exception:
                pass

            # Need at least 2 fields to be useful
            if len(field_configs) < 2:
                return None

            # Generate labels
            ref_label = reference_name.replace("_", " ").title()

            # Build info_grid items from field configs
            info_items = []
            for fc in field_configs:
                label = fc["target"].replace("_", " ").title()
                item = {"label": label, "source": fc["target"]}
                if fc.get("transformation") == "count":
                    item["format"] = "number"
                info_items.append(item)

            return {
                "template_id": f"general_info_{reference_name}_field_aggregator_info_grid",
                "name": "Informations générales",
                "description": f"Fiche d'information pour {ref_label} (champs détectés automatiquement)",
                "plugin": "field_aggregator",
                "transformer_plugin": "field_aggregator",
                "widget_plugin": "info_grid",
                "category": "info",
                "icon": "Info",
                "confidence": 0.85,
                "source": "auto",
                "source_name": reference_name,
                "matched_column": reference_name,
                "match_reason": f"Agrégation de {len(field_configs)} champs détectés dans '{reference_name}'",
                "is_recommended": True,
                "config": {
                    "fields": field_configs,
                },
                "transformer_config": {
                    "plugin": "field_aggregator",
                    "params": {
                        "fields": field_configs,
                    },
                },
                "widget_params": {"items": info_items},
                "alternatives": [],
            }

        finally:
            if own_db:
                db.close_db_session()

    except Exception as e:
        logger.warning(f"Error generating general_info suggestion: {e}")
        return None


def get_entity_map_suggestions(reference_name: str) -> List[Dict[str, Any]]:
    """Generate map widget suggestions based on geometry columns in entity table.

    Detection strategy (in priority order):
    1. Read import.yml schema for explicitly declared geometry fields
    2. Pattern matching on column names (with WKT validation)
    3. Sample data to detect WKT format

    For spatial references (shapes), also generates type-based suggestions
    using the entity_type column.

    Args:
        reference_name: Name of the reference (e.g., 'taxons', 'plots', 'shapes')

    Returns:
        List of map widget suggestions
    """
    from niamoto.common.database import Database

    suggestions = []

    db_path = get_database_path()
    work_dir = get_working_directory()
    if not db_path:
        return suggestions

    db = Database(str(db_path), read_only=True)

    try:
        import_config = _load_import_config()
        reference_config = _get_reference_config(reference_name, import_config)
        registry = _get_entity_registry(db)

        entity_table = _resolve_entity_table(
            db, reference_name, registry=registry, kind="reference"
        )
        if not entity_table:
            return suggestions

        quoted_entity_table = quote_identifier(db, entity_table)
        # Get columns from entity table
        columns_df = pd.read_sql(
            text(f"SELECT * FROM {quoted_entity_table} LIMIT 0"),
            db.engine,
        )
        columns = columns_df.columns.tolist()

        # =====================================================================
        # STEP 1: Read import.yml for declared geometry fields
        # =====================================================================
        declared_geometry_fields = set()

        schema_cfg = (
            reference_config.get("schema", {})
            if isinstance(reference_config, dict)
            else {}
        )
        schema_fields = (
            schema_cfg.get("fields", []) if isinstance(schema_cfg, dict) else []
        )
        for field in schema_fields:
            if isinstance(field, dict) and field.get("type") == "geometry":
                field_name = field.get("name")
                if field_name:
                    declared_geometry_fields.add(field_name)

        if work_dir and not reference_config:
            import_path = Path(work_dir) / "config" / "import.yml"
            if import_path.exists():
                try:
                    with open(import_path, "r", encoding="utf-8") as f:
                        import_config = yaml.safe_load(f) or {}

                    references = (
                        import_config.get("entities", {}).get("references", {}) or {}
                    )
                    ref_config = references.get(reference_name, {})
                    reference_config = (
                        ref_config if isinstance(ref_config, dict) else {}
                    )
                    schema = ref_config.get("schema", {})
                    fields = schema.get("fields", [])

                    for field in fields:
                        if isinstance(field, dict) and field.get("type") == "geometry":
                            declared_geometry_fields.add(field.get("name"))

                except Exception as e:
                    logger.debug(
                        f"Could not read import.yml for geometry detection: {e}"
                    )

        # =====================================================================
        # STEP 2: Build geometry columns list
        # =====================================================================
        geometry_columns = []

        # Helper to validate WKT content
        def _validate_wkt_column(col_name: str) -> Optional[str]:
            """Check if column contains valid WKT geometry. Returns geometry type or None."""
            try:
                quoted_col_name = quote_identifier(db, col_name)
                sample = pd.read_sql(
                    text(
                        f"SELECT {quoted_col_name} FROM {quoted_entity_table} "
                        f"WHERE {quoted_col_name} IS NOT NULL LIMIT 1"
                    ),
                    db.engine,
                )
                if not sample.empty:
                    val = str(sample.iloc[0][col_name]).strip()
                    if val.startswith("POINT"):
                        return "point"
                    elif val.startswith("POLYGON") or val.startswith("MULTIPOLYGON"):
                        return "polygon"
            except Exception:
                pass
            return None

        # First, add declared geometry fields (from import.yml)
        for field_name in declared_geometry_fields:
            if field_name in columns:
                geom_type = _validate_wkt_column(field_name)
                if geom_type:
                    geometry_columns.append((field_name, geom_type))

        # Then, pattern matching with validation
        # Only use patterns if no declared geometry found
        if not geometry_columns:
            point_patterns = ["geo_pt", "geom_pt", "coordinates", "position"]
            polygon_patterns = ["location", "geometry", "polygon", "boundary"]

            for col in columns:
                if col in declared_geometry_fields:
                    continue  # Already processed
                col_lower = col.lower()

                # Check for point patterns
                if any(p in col_lower for p in point_patterns):
                    geom_type = _validate_wkt_column(col)
                    if geom_type:
                        geometry_columns.append((col, geom_type))
                # Check for polygon patterns
                elif any(p in col_lower for p in polygon_patterns):
                    geom_type = _validate_wkt_column(col)
                    if geom_type:
                        geometry_columns.append((col, geom_type))

        # =====================================================================
        # STEP 3: Detect metadata fields (name, id, entity_type)
        # =====================================================================

        # Detect ID field from schema or by pattern
        schema = (
            reference_config.get("schema", {})
            if isinstance(reference_config, dict)
            else {}
        )
        preferred_id = schema.get("id_field") if isinstance(schema, dict) else None
        id_field = _pick_identifier_column(
            columns, entity_name=reference_name, preferred=preferred_id
        )
        if not id_field:
            id_field = "id"
        name_field = _pick_name_column(columns, id_field, reference_name)

        # =====================================================================
        # STEP 4: Generate suggestions
        # =====================================================================
        ref_label = reference_name.replace("_", " ").title()

        for geom_col, geom_type in geometry_columns:
            single_id = f"{reference_name}_{geom_col}_entity_map"

            if geom_type == "point":
                single_name = f"{ref_label} location"
                single_desc = (
                    f"Map showing the position of the selected {reference_name} entity"
                )
                icon_single = "MapPin"
            else:
                single_name = f"{ref_label} polygon"
                single_desc = (
                    f"Map showing the polygon of the selected {reference_name} entity"
                )
                icon_single = "Hexagon"

            properties = [
                field_name
                for field_name in (name_field, id_field)
                if field_name and field_name in columns
            ]

            suggestions.append(
                {
                    "template_id": single_id,
                    "name": single_name,
                    "description": single_desc,
                    "plugin": "geospatial_extractor",
                    "widget_plugin": "interactive_map",
                    "widget_params": {
                        "geojson_field": "features",
                    },
                    "category": "map",
                    "icon": icon_single,
                    "confidence": 0.90,
                    "source": "entity",
                    "source_name": reference_name,
                    "matched_column": geom_col,
                    "match_reason": f"Colonne géométrique '{geom_col}' détectée ({geom_type})",
                    "is_recommended": True,
                    "config": {
                        "source": reference_name,
                        "field": geom_col,
                        "format": "geojson",
                        "properties": properties,
                        "title": single_name,
                    },
                    "alternatives": [],
                }
            )

        return suggestions

    except Exception as e:
        logger.warning(
            f"Error detecting entity map columns for '{reference_name}': {e}"
        )
        return []
    finally:
        db.close_db_session()


def get_class_object_suggestions(reference_name: str) -> List[Dict[str, Any]]:
    """Get widget suggestions from pre-calculated CSV sources configured for this group.

    Reads transform.yml to find CSV sources, then analyzes each to suggest widgets.
    Returns empty list if no sources configured or working directory not set.
    """
    work_dir = get_working_directory()
    if not work_dir:
        return []

    work_dir = Path(work_dir)
    transform_path = work_dir / "config" / "transform.yml"

    if not transform_path.exists():
        return []

    try:
        with open(transform_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # transform.yml can have different structures:
        # 1. List of groups: [{group_by: taxons, ...}, {group_by: plots, ...}]
        # 2. Dict with groups key as list: {groups: [{group_by: taxons}, ...]}
        # 3. Dict with groups key as dict: {groups: {taxons: {...}, plots: {...}}}
        group_config = None

        if isinstance(config, list):
            # Format 1: List at root
            for group in config:
                if isinstance(group, dict) and group.get("group_by") == reference_name:
                    group_config = group
                    break
        elif isinstance(config, dict):
            groups = config.get("groups", {})
            if isinstance(groups, list):
                # Format 2: groups is a list
                for group in groups:
                    if (
                        isinstance(group, dict)
                        and group.get("group_by") == reference_name
                    ):
                        group_config = group
                        break
            elif isinstance(groups, dict):
                # Format 3: groups is a dict with reference names as keys
                group_config = groups.get(reference_name)

        if not group_config:
            return []

        sources = group_config.get("sources", [])

        all_suggestions = []
        for source in sources:
            data_path = source.get("data", "")
            # Only process CSV files (skip table references like 'occurrences')
            if not data_path.endswith(".csv"):
                continue

            source_name = source.get("name", Path(data_path).stem)
            csv_path = work_dir / data_path

            if not csv_path.exists():
                continue

            # Generate suggestions for this source
            suggestions = suggest_widgets_for_source(
                csv_path, source_name, reference_name
            )
            all_suggestions.extend(suggestions)

        return all_suggestions

    except Exception as e:
        logger.warning("Error loading class_object suggestions: %s", e, exc_info=True)
        return []


def get_reference_field_suggestions(reference_name: str) -> List[Dict[str, Any]]:
    """Generate widget suggestions based on columns in the reference entity table.

    Analyzes columns in entity_{reference_name} (e.g., entity_plots) via the
    standard DataProfiler → DataAnalyzer → WidgetGenerator pipeline, ensuring
    consistent suggestions with the same config format as occurrence-based ones.

    Args:
        reference_name: Name of the reference (e.g., 'plots', 'shapes')

    Returns:
        List of widget suggestions in dict format
    """
    from niamoto.common.database import Database

    db_path = get_database_path()
    if not db_path:
        return []

    cache_key = _build_reference_field_cache_key(reference_name)
    cached = _REFERENCE_FIELD_SUGGESTIONS_CACHE.get(cache_key) if cache_key else None
    if cached is not None:
        return copy.deepcopy(cached)

    db = Database(str(db_path), read_only=True)

    try:
        registry = _get_entity_registry(db)
        entity_table = _resolve_entity_table(
            db, reference_name, registry=registry, kind="reference"
        )
        if not entity_table:
            return []

        quoted_entity_table = quote_identifier(db, entity_table)
        sample_df = pd.read_sql(
            text(f"SELECT * FROM {quoted_entity_table} LIMIT 100"),
            db.engine,
        )

        if sample_df.empty:
            return []

        # Only profile columns that can actually produce widget suggestions.
        profile_columns = [
            column
            for column in sample_df.columns
            if _should_profile_reference_field(column, sample_df[column])
        ]
        if not profile_columns:
            return []

        entity_meta = _safe_registry_get(registry, reference_name)
        import_config = _load_import_config()
        reference_config = _get_reference_config(reference_name, import_config)

        heuristic_suggestions: List[TemplateSuggestion] = []
        ml_suggestions: List[TemplateSuggestion] = []

        if _is_internal_registry_reference(entity_meta, entity_table):
            metadata_signals = _extract_reference_metadata_signals(
                reference_name=reference_name,
                columns=profile_columns,
                entity_meta=entity_meta,
                reference_config=reference_config,
            )
            fast_profiles: List[EnrichedColumnProfile] = []
            ml_candidate_columns: List[str] = []

            for column in profile_columns:
                if _should_skip_reference_fast_path(
                    column_name=column,
                    series=sample_df[column],
                    metadata_signals=metadata_signals,
                ):
                    continue
                category = _classify_reference_column_fast(
                    column_name=column,
                    series=sample_df[column],
                    metadata_signals=metadata_signals,
                )
                if category is None:
                    ml_candidate_columns.append(column)
                    continue

                fast_profiles.append(
                    _build_fast_enriched_profile(
                        column_name=column,
                        series=sample_df[column],
                        category=category,
                    )
                )

            if fast_profiles:
                heuristic_suggestions = _generate_fast_reference_widget_suggestions(
                    reference_name=reference_name,
                    profiles=fast_profiles,
                )

            if ml_candidate_columns:
                ml_suggestions = _generate_reference_suggestions_via_ml(
                    entity_table=entity_table,
                    reference_name=reference_name,
                    profile_df=sample_df[ml_candidate_columns].copy(),
                )
        else:
            ml_suggestions = _generate_reference_suggestions_via_ml(
                entity_table=entity_table,
                reference_name=reference_name,
                profile_df=sample_df[profile_columns].copy(),
            )

        result = _merge_reference_template_suggestions(
            reference_name=reference_name,
            heuristic_suggestions=heuristic_suggestions,
            ml_suggestions=ml_suggestions,
        )

        if cache_key is not None:
            _REFERENCE_FIELD_SUGGESTIONS_CACHE[cache_key] = copy.deepcopy(result)

        return result

    except Exception as e:
        logger.warning(
            f"Error generating reference field suggestions for '{reference_name}': {e}"
        )
        return []
    finally:
        db.close_db_session()
