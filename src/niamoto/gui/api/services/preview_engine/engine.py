"""Unified preview engine for Niamoto widgets.

Synchronous pipeline: resolve -> load -> transform -> render -> wrap.
Called from endpoints via `await run_in_threadpool(engine.render, req)`.

Uses the same utilities as templates.py for resolution,
data loading, transformation, and rendering.
"""

from __future__ import annotations

import hashlib
import html as html_module
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from niamoto.core.services.transformer import TransformerService

import pandas as pd
from sqlalchemy import inspect, text

from niamoto.common.database import Database
from niamoto.common.exceptions import DataLoadError, DataTransformError
from niamoto.common.table_resolver import (
    quote_identifier,
    resolve_entity_table,
    resolve_reference_table,
)
from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.services.preview_engine.models import (
    PreviewMode,
    PreviewRequest,
    PreviewResult,
)
from niamoto.gui.api.services.preview_engine.plotly_bundle_resolver import (
    resolve_bundle,
)
from niamoto.gui.api.services.preview_utils import (
    error_html,
    execute_transformer,
    parse_wkt_to_geojson,
    render_widget,
    wrap_html_response,
)
from niamoto.gui.api.services.templates.utils.class_object_rendering import (
    _extract_class_objects_from_params,
    _execute_configured_transformer,
    _render_widget_for_class_object,
    _render_widget_for_configured,
)
from niamoto.gui.api.services.templates.utils.config_loader import (
    get_hierarchy_info,
    load_import_config,
)
from niamoto.gui.api.services.templates.utils.data_loader import (
    load_class_object_csv_dataframe,
    load_class_object_data_for_preview,
    load_sample_data,
)
from niamoto.gui.api.services.templates.utils.entity_finder import (
    find_entity_by_id,
    find_representative_entity,
)
from niamoto.gui.api.services.templates.suggestion_service import (
    _pick_identifier_column,
    _pick_name_column,
)
from niamoto.gui.api.services.templates.utils.widget_utils import (
    find_widget_group,
    is_class_object_template,
    load_configured_widget,
    load_widget_params_from_export,
    parse_dynamic_template_id,
)

logger = logging.getLogger(__name__)

# Cached TransformerService — shared across preview calls, invalidated
# when data changes (import, config save, etc.).
_transformer_svc: "TransformerService | None" = None
_transformer_svc_lock = threading.Lock()


# Re-export from preview_utils for backward compatibility within engine
from niamoto.gui.api.services.preview_utils import (  # noqa: E402
    preprocess_data_for_widget as _preprocess_data_for_widget,
)


def _get_column_profile(column: str, data_source: str, db: Database) -> Any:
    """Look up the stored semantic profile for a column.

    Returns an EnrichedColumnProfile or None if not found.
    """
    from niamoto.core.imports.data_analyzer import EnrichedColumnProfile
    from niamoto.core.imports.registry import EntityKind, EntityRegistry

    registry = EntityRegistry(db)

    entity_meta = None
    for kind in (EntityKind.DATASET, EntityKind.REFERENCE):
        for ent in registry.list_entities(kind=kind):
            if ent.name == data_source:
                entity_meta = ent
                break
        if entity_meta:
            break

    if not entity_meta:
        return None

    col_data = next(
        (
            c
            for c in entity_meta.config.get("semantic_profile", {}).get("columns", [])
            if c.get("name") == column
        ),
        None,
    )
    if not col_data:
        return None

    return EnrichedColumnProfile.from_stored_dict(col_data)


def _build_transformer_config(
    column: str,
    transformer: str,
    data_source: str,
    db: Database | None,
) -> dict[str, Any]:
    """Build a complete transformer config from semantic profiles.

    Uses WidgetGenerator to produce the same config as the suggestion flow,
    so every transformer gets its required params automatically.
    """
    fallback: dict[str, Any] = {"source": data_source, "field": column}

    if not db:
        return fallback

    try:
        from niamoto.core.imports.widget_generator import WidgetGenerator

        profile = _get_column_profile(column, data_source, db)
        if not profile:
            return fallback

        config = WidgetGenerator()._generate_transformer_config(
            profile, transformer, data_source
        )
        return config or fallback

    except Exception as exc:
        logger.debug("Could not build transformer config: %s", exc)
        return fallback


def _build_widget_params_for_preview(
    column: str,
    transformer: str,
    widget: str,
    data_source: str,
    db: Database | None,
) -> dict[str, Any]:
    """Build widget params for GET preview (fallback path).

    Returns the full widget config (x_axis, y_axis, transform, field_mapping, etc.)
    generated by WidgetGenerator for the given transformer→widget pair.
    """
    try:
        from niamoto.core.imports.widget_generator import WidgetGenerator

        # Profile is optional — _generate_widget_params only uses it for scatter_plot
        profile = _get_column_profile(column, data_source, db) if db else None

        return WidgetGenerator()._generate_widget_params(profile, transformer, widget)

    except Exception:
        return {}


class PreviewEngine:
    """Unified preview engine -- a single pipeline for all widget types.

    The engine is synchronous (file I/O + DB). Endpoints call it
    via ``await run_in_threadpool(engine.render, req)``.
    """

    def __init__(self, db_path: str, config_dir: str):
        self._db_path = db_path
        self._config_dir = config_dir
        self._work_dir = Path(config_dir).parent
        self._data_fingerprint: str = self._compute_data_fingerprint()
        # Caches -- cleared on invalidate()
        self._db: Database | None = None
        self._rich_entity_cache: dict[str, Any] = {}
        self._group_ids_cache: dict[str, list[Any]] = {}

        # Dispatch table for special widget types.
        # Each entry: (matcher, widget_plugin, handler)
        # Adding a new special widget = one entry here + one handler method.
        self._special_renderers: list[
            tuple[
                Callable[[str], bool],
                str,
                Callable[[str, "PreviewRequest", Database, list[str]], str],
            ]
        ] = [
            (
                lambda tid: tid.endswith("_hierarchical_nav_widget"),
                "hierarchical_nav_widget",
                self._handle_navigation,
            ),
            (
                lambda tid: (
                    tid.startswith("general_info_")
                    and tid.endswith("_field_aggregator_info_grid")
                ),
                "info_grid",
                self._handle_general_info,
            ),
            (
                lambda tid: tid.endswith(("_entity_map", "_all_map")),
                "interactive_map",
                self._handle_entity_map,
            ),
        ]

    # ------------------------------------------------------------------
    # TransformerService (lazy, cached, shared across requests)
    # ------------------------------------------------------------------

    def _get_transformer_service(self, db: Database) -> "TransformerService":
        """Return (or create) a cached TransformerService for preview.

        Uses ``TransformerService.for_preview()`` which properly loads
        plugins via cascade (system + user + project) and initialises
        the entity registry.  The instance is cached module-wide and
        cleared on ``invalidate()``.
        """
        global _transformer_svc
        if _transformer_svc is not None:
            return _transformer_svc

        with _transformer_svc_lock:
            if _transformer_svc is not None:
                return _transformer_svc

            from niamoto.core.services.transformer import TransformerService

            svc = TransformerService.for_preview(db, self._config_dir)
            _transformer_svc = svc
            return svc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, request: PreviewRequest) -> PreviewResult:
        """Single entry point -- resolve, load, transform, render, wrap."""
        warnings: list[str] = []
        template_id = request.template_id

        db = self._open_db()
        try:
            # Ensure plugins are loaded (cascade: system + user + project)
            self._get_transformer_service(db)

            # --- Inline (POST): explicit transformer + widget ---
            if request.inline:
                widget_plugin = request.inline.get("widget_plugin", "")
                widget_html = self._render_inline(request, db, warnings)
                return self._build_result(
                    request, widget_html, warnings, widget_plugin=widget_plugin
                )

            if not template_id:
                return self._error_result(request, "template_id requis", warnings)

            # --- Special widget types (dispatch table) ---
            for matcher, wp, handler in self._special_renderers:
                if matcher(template_id):
                    widget_html = handler(template_id, request, db, warnings)
                    return self._build_result(
                        request, widget_html, warnings, widget_plugin=wp
                    )

            # --- Standard: Configured / Dynamic / Class object / Occurrence ---
            widget_html = self._render_standard(request, db, warnings)
            # Extract widget plugin for Plotly bundle resolution
            parsed = parse_dynamic_template_id(template_id)
            wp = parsed["widget"] if parsed else None
            # Fallback: configured widget (simple template_id like "distribution_map")
            if not wp:
                grp = request.group_by or find_widget_group(template_id)
                if grp:
                    cfg = load_configured_widget(template_id, grp)
                    if cfg:
                        wp = cfg.get("widget_plugin")
            return self._build_result(request, widget_html, warnings, widget_plugin=wp)
        finally:
            pass  # DB instance is shared and reused across requests

    # ------------------------------------------------------------------
    # Special widget handlers (used by dispatch table)
    # ------------------------------------------------------------------

    def _handle_navigation(
        self,
        template_id: str,
        request: PreviewRequest,
        db: Database,
        warnings: list[str],
    ) -> str:
        reference = template_id.removesuffix("_hierarchical_nav_widget")
        return self._render_navigation(reference, db, warnings)

    def _handle_general_info(
        self,
        template_id: str,
        request: PreviewRequest,
        db: Database,
        warnings: list[str],
    ) -> str:
        reference = template_id.removeprefix("general_info_").removesuffix(
            "_field_aggregator_info_grid"
        )
        return self._render_general_info(reference, request.entity_id, db, warnings)

    def _handle_entity_map(
        self,
        template_id: str,
        request: PreviewRequest,
        db: Database,
        warnings: list[str],
    ) -> str:
        return self._render_entity_map(template_id, request.entity_id, db, warnings)

    def invalidate(self) -> None:
        """Recompute fingerprint -- called after import or config save."""
        global _transformer_svc
        _transformer_svc = None
        self._data_fingerprint = self._compute_data_fingerprint()
        self._db = None
        self._rich_entity_cache.clear()
        self._group_ids_cache.clear()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _load_group_config(
        self, group_by: str, svc: "TransformerService | None" = None
    ) -> dict[str, Any] | None:
        """Load a single group config from transform.yml."""
        if svc and hasattr(svc, "transforms_config"):
            configs = svc.transforms_config
        else:
            import yaml as _yaml

            transform_path = self._work_dir / "config" / "transform.yml"
            if not transform_path.exists():
                return None
            with open(transform_path, "r", encoding="utf-8") as _f:
                configs = _yaml.safe_load(_f) or []

        if isinstance(configs, list):
            for gc in configs:
                if isinstance(gc, dict) and gc.get("group_by") == group_by:
                    return gc
        return None

    @staticmethod
    def _resolve_entity_id(entity_id: str | None, group_ids: list[Any]) -> Any:
        """Resolve an explicit entity_id against available group IDs.

        Checks exact match first, then tries numeric conversion.
        Returns ``None`` when the ID is not found.
        """
        if entity_id is None:
            return group_ids[0] if group_ids else None

        if entity_id in group_ids:
            return entity_id

        try:
            numeric = int(entity_id)
            if numeric in group_ids:
                return numeric
        except (ValueError, TypeError):
            pass

        return None

    def _find_rich_entity_id(
        self,
        db: Database,
        group_by: str,
        group_ids: list[Any],
    ) -> Any:
        """Pick a data-rich entity for preview (cached per group_by).

        For hierarchical references (nested set), picks the family with
        the most descendants. Falls back to group_ids[0].
        """
        if group_by in self._rich_entity_cache:
            cached = self._rich_entity_cache[group_by]
            if cached in set(group_ids):
                return cached

        gid = self._query_rich_entity(db, group_by, group_ids)
        self._rich_entity_cache[group_by] = gid
        return gid

    def _query_rich_entity(
        self, db: Database, group_by: str, group_ids: list[Any]
    ) -> Any:
        """Pick the entity with the most data for preview.

        Strategy:
        1. Hierarchical (nested set): largest lft/rght span (family level)
        2. Flat: entity with most occurrences via transform.yml relation
        3. Fallback: group_ids[0]
        """
        try:
            ref_table = resolve_reference_table(db, group_by)
            if not ref_table or not db.has_table(ref_table):
                return group_ids[0]

            quoted_table = quote_identifier(db, ref_table)
            group_ids_set = set(group_ids)

            columns = set(db.get_table_columns(ref_table))

            # Detect ID column (may not be "id")
            id_col = _pick_identifier_column(list(columns))
            q_id = quote_identifier(db, id_col)

            # Strategy 1: hierarchical (nested set)
            if {"lft", "rght"} <= columns:
                query = text(f"""
                    SELECT {q_id}
                    FROM {quoted_table}
                    WHERE (rght - lft) > 3
                    ORDER BY (rght - lft) DESC
                    LIMIT 5
                """)
                with db.engine.connect() as conn:
                    for row in conn.execute(query):
                        eid = row[0]
                        if eid in group_ids_set:
                            return eid
                        # Try numeric coercion for mixed-type sets
                        try:
                            if int(eid) in group_ids_set:
                                return int(eid)
                        except (ValueError, TypeError):
                            pass

            # Strategy 2: flat — pick entity with most occurrences
            group_config = self._load_group_config(group_by)
            if group_config:
                sources = group_config.get("sources", [])
                if sources:
                    relation = sources[0].get("relation", {})
                    rel_key = relation.get("key")
                    src_table = sources[0].get("data")
                    if rel_key and src_table:
                        from niamoto.common.table_resolver import (
                            resolve_dataset_table,
                        )

                        occ_table = resolve_dataset_table(db, src_table)
                        if occ_table and db.has_table(occ_table):
                            q_occ = quote_identifier(db, occ_table)
                            q_key = quote_identifier(db, rel_key)
                            query = text(f"""
                                SELECT {q_key}, COUNT(*) as cnt
                                FROM {q_occ}
                                WHERE {q_key} IS NOT NULL
                                GROUP BY {q_key}
                                ORDER BY cnt DESC
                                LIMIT 5
                            """)
                            with db.engine.connect() as conn:
                                for row in conn.execute(query):
                                    eid = row[0]
                                    if eid in group_ids_set:
                                        return eid
                                    try:
                                        numeric = int(eid)
                                        if numeric in group_ids_set:
                                            return numeric
                                    except (ValueError, TypeError):
                                        pass

            return group_ids[0]

        except Exception:
            return group_ids[0]

    @staticmethod
    def _build_preview_group_config(
        group_config: dict[str, Any],
        widget_id: str,
        transformer_plugin: str,
        transformer_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a temporary transform-style config for suggestion previews."""
        return {
            "group_by": group_config["group_by"],
            "sources": group_config.get("sources", []),
            "widgets_data": {
                widget_id: {
                    "plugin": transformer_plugin,
                    "params": transformer_config,
                }
            },
        }

    def _resolve_preview_group_context(
        self,
        group_by: str | None,
        entity_id: str | None,
        db: Database,
    ) -> tuple["TransformerService", dict[str, Any], Any] | None:
        """Resolve the real transform group and target entity for preview."""
        if not group_by:
            return None

        svc = self._get_transformer_service(db)
        group_config = self._load_group_config(group_by, svc)
        if not group_config:
            return None

        if group_by in self._group_ids_cache:
            group_ids = self._group_ids_cache[group_by]
        else:
            group_ids = svc._get_group_ids(group_config)
            self._group_ids_cache[group_by] = group_ids
        if not group_ids:
            raise DataLoadError("No entities available")

        if entity_id is not None:
            gid = self._resolve_entity_id(entity_id, group_ids)
            if gid is None:
                raise DataLoadError(f"Entity '{entity_id}' not found in {group_by}")
        else:
            # Pick a data-rich entity (family level for hierarchical refs)
            gid = self._find_rich_entity_id(db, group_by, group_ids)

        return svc, group_config, gid

    # ------------------------------------------------------------------
    # Result construction
    # ------------------------------------------------------------------

    def _build_result(
        self,
        request: PreviewRequest,
        widget_html: str,
        warnings: list[str],
        *,
        widget_plugin: str | None = None,
    ) -> PreviewResult:
        bundle = resolve_bundle(
            widget_plugin=widget_plugin,
            template_id=request.template_id,
        )
        html = self._wrap_html(widget_html, mode=request.mode, bundle=bundle)
        etag = self._compute_etag(request)
        preview_key = request.template_id or "inline"
        return PreviewResult(
            html=html,
            etag=etag,
            preview_key=preview_key,
            warnings=tuple(warnings),
        )

    def _error_result(
        self, request: PreviewRequest, message: str, warnings: list[str]
    ) -> PreviewResult:
        return self._build_result(request, error_html(message), warnings)

    def _info_html(self, message: str) -> str:
        return f"<p class='info'>{html_module.escape(message)}</p>"

    def _error_html(self, message: str) -> str:
        return error_html(message)

    # ------------------------------------------------------------------
    # ETag / fingerprint
    # ------------------------------------------------------------------

    def _compute_data_fingerprint(self) -> str:
        """Fingerprint from mtime(DB) + mtime(configs). Zero I/O between invalidate()."""
        parts: list[str] = []
        if os.path.exists(self._db_path):
            parts.append(str(os.path.getmtime(self._db_path)))
        for name in ("import.yml", "transform.yml", "export.yml"):
            cfg = os.path.join(self._config_dir, name)
            if os.path.exists(cfg):
                parts.append(str(os.path.getmtime(cfg)))
        return hashlib.md5(":".join(parts).encode()).hexdigest()[:12]

    def _compute_etag(self, request: PreviewRequest) -> str:
        key = (
            f"{request.template_id}:{request.group_by}:{request.source}"
            f":{request.entity_id}:{self._data_fingerprint}"
        )
        return hashlib.md5(key.encode()).hexdigest()

    # ------------------------------------------------------------------
    # HTML wrapper
    # ------------------------------------------------------------------

    def _wrap_html(
        self,
        content: str,
        mode: PreviewMode = "full",
        bundle: str = "core",
    ) -> str:
        """Complete HTML document for injection into an iframe via srcDoc."""
        return wrap_html_response(
            content,
            title="Preview",
            plotly_bundle=bundle,
            thumbnail=(mode == "thumbnail"),
        )

    # ------------------------------------------------------------------
    # Column discovery via DESCRIBE
    # ------------------------------------------------------------------

    def _get_column_names(self, db: Database, quoted_table: str) -> list[str]:
        """Discover table columns via DESCRIBE (more efficient than SELECT * LIMIT 0)."""
        with db.engine.connect() as conn:
            result = conn.execute(text(f"DESCRIBE {quoted_table}"))
            return [row[0] for row in result.fetchall()]

    # ------------------------------------------------------------------
    # INLINE branch (POST)
    # ------------------------------------------------------------------

    def _render_inline(
        self,
        request: PreviewRequest,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        inline = request.inline
        if not inline:
            return self._info_html("Missing inline configuration")

        if not db:
            return self._info_html("Database not configured")

        transformer_plugin = inline.get("transformer_plugin", "")
        transformer_params = inline.get("transformer_params", {})
        widget_plugin = inline.get("widget_plugin", "")
        widget_params = inline.get("widget_params")
        widget_title = inline.get("widget_title", "Preview")
        group_by = request.group_by or ""

        try:
            # Class object transformers use CSV data
            if transformer_plugin.startswith("class_object_"):
                co_data = load_class_object_data_for_preview(
                    self._work_dir,
                    transformer_params.get("source", ""),
                    group_by,
                )
                if not co_data:
                    return self._info_html("Class object data not found")
                result = execute_transformer(
                    db, transformer_plugin, transformer_params, co_data
                )
            else:
                # Use TransformerService for real pipeline when possible
                preview_group = self._resolve_preview_group_context(
                    group_by, request.entity_id, db
                )
                if preview_group:
                    svc, group_config, gid = preview_group
                    temp_config = self._build_preview_group_config(
                        group_config,
                        widget_title,
                        transformer_plugin,
                        transformer_params,
                    )
                    result = svc.transform_single_widget(temp_config, widget_title, gid)
                else:
                    # Fallback: ad-hoc execution
                    import_config = load_import_config(self._work_dir)
                    hierarchy_info = get_hierarchy_info(import_config, group_by)
                    representative = find_representative_entity(db, hierarchy_info)
                    sample = load_sample_data(db, representative, transformer_params)
                    if sample.empty:
                        return self._info_html("No data available")
                    result = execute_transformer(
                        db, transformer_plugin, transformer_params, sample
                    )

            if not result:
                return self._info_html("Transformer returned no data")

            # Adapt transformer output → widget format
            result = _preprocess_data_for_widget(
                result, transformer_plugin, widget_plugin
            )

            return render_widget(db, widget_plugin, result, widget_params, widget_title)
        except Exception as e:
            logger.exception("Inline preview error: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # NAVIGATION branch
    # ------------------------------------------------------------------

    def _render_navigation(
        self,
        reference_name: str,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        if not db:
            return self._info_html("Database not configured")

        try:
            table_name = resolve_reference_table(db, reference_name)
            if not table_name:
                return self._info_html(f"Table '{reference_name}' not found")

            quoted = quote_identifier(db, table_name)

            # Columns (exclude geometries)
            with db.engine.connect() as conn:
                result = conn.execute(text(f"DESCRIBE {quoted}"))
                col_info = result.fetchall()

            safe_columns = [
                c[0]
                for c in col_info
                if c[1].upper() not in ("GEOMETRY", "BLOB", "BYTEA")
                and not c[0].endswith("_geom")
            ]
            columns = set(safe_columns)
            safe_sql = ", ".join(quote_identifier(db, c) for c in safe_columns)

            has_nested_set = "lft" in columns and "rght" in columns
            has_parent = "parent_id" in columns
            has_level = "level" in columns
            is_hierarchical = has_nested_set or (has_parent and has_level)

            # ID / name field (shared utilities)
            id_field = (
                _pick_identifier_column(safe_columns, entity_name=reference_name)
                or "id"
            )
            name_field = _pick_name_column(safe_columns, id_field, reference_name)

            # Sample query
            if is_hierarchical and has_nested_set:
                query = text(
                    f"SELECT {safe_sql} FROM {quoted} "
                    f"WHERE {quote_identifier(db, 'level')} <= 3 "
                    f"ORDER BY {quote_identifier(db, 'lft')} LIMIT 50"
                )
            elif is_hierarchical and has_parent:
                query = text(
                    f"SELECT {safe_sql} FROM {quoted} "
                    f"WHERE {quote_identifier(db, 'level')} <= 3 LIMIT 50"
                )
            else:
                query = text(f"SELECT {safe_sql} FROM {quoted} LIMIT 30")

            df = pd.read_sql(query, db.engine)
            if df.empty:
                return self._info_html(f"No data in '{reference_name}'")

            # Inline rendering with CSS/JS (the plugin render() assumes an
            # external environment with assets already loaded, which is
            # not the case in a preview iframe).
            return self._render_navigation_inline(
                df,
                reference_name,
                id_field,
                name_field,
                is_hierarchical,
                has_parent,
                has_nested_set,
                has_level,
            )
        except Exception as e:
            logger.exception("Navigation preview error: %s", e)
            return self._error_html(str(e))

    def _render_navigation_inline(
        self,
        df: pd.DataFrame,
        reference_name: str,
        id_field: str,
        name_field: str,
        is_hierarchical: bool,
        has_parent: bool,
        has_nested_set: bool,
        has_level: bool,
    ) -> str:
        """Navigation rendering with inlined CSS/JS (self-contained in preview iframe)."""
        import json

        # Load CSS/JS assets from publish/assets
        # engine.py is in gui/api/services/preview_engine/ -- 5 levels up to niamoto/
        assets_path = (
            Path(__file__).parent.parent.parent.parent.parent / "publish" / "assets"
        )
        css_content = ""
        js_content = ""
        css_file = assets_path / "css" / "niamoto_hierarchical_nav.css"
        js_file = assets_path / "js" / "niamoto_hierarchical_nav.js"
        if css_file.exists():
            css_content = css_file.read_text()
        if js_file.exists():
            js_content = js_file.read_text()

        widget_id = f"hierarchical-nav-{reference_name.replace('_', '-')}"
        container_id = f"{widget_id}-container"
        search_id = f"{widget_id}-search"

        items = df.to_dict("records")

        js_config = {
            "containerId": container_id,
            "searchInputId": search_id,
            "items": items,
            "params": {
                "idField": id_field,
                "nameField": name_field,
                "parentIdField": "parent_id" if has_parent else None,
                "lftField": "lft" if has_nested_set else None,
                "rghtField": "rght" if has_nested_set else None,
                "levelField": "level" if has_level else None,
                "flatMode": not is_hierarchical,
                "baseUrl": "#",
            },
            "currentItemId": None,
        }
        safe_json = json.dumps(js_config, ensure_ascii=False).replace("</", "<\\/")

        # Tailwind CSS utilities used by niamoto_hierarchical_nav.js
        tailwind_shim = """
        .flex { display: flex; }
        .flex-1 { flex: 1 1 0%; }
        .items-center { align-items: center; }
        .inline-block { display: inline-block; }
        .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .rounded { border-radius: 0.25rem; }
        .cursor-pointer { cursor: pointer; }
        .font-semibold { font-weight: 600; }
        .no-underline { text-decoration: none; }
        .w-4 { width: 1rem; }
        .px-2 { padding-left: 0.5rem; padding-right: 0.5rem; }
        .py-1 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
        .ml-2 { margin-left: 0.5rem; }
        .ml-10 { margin-left: 2.5rem; }
        .mb-1 { margin-bottom: 0.25rem; }
        .mb-4 { margin-bottom: 1rem; }
        .text-xs { font-size: 0.75rem; line-height: 1rem; }
        .text-sm { font-size: 0.875rem; line-height: 1.25rem; }
        .text-gray-500 { color: #6b7280; }
        .text-gray-700 { color: #374151; }
        .text-gray-900 { color: #111827; }
        .text-primary { color: #3b82f6; }
        .bg-gray-50 { background-color: #f9fafb; }
        .bg-gray-100 { background-color: #f3f4f6; }
        .transition-colors { transition-property: color, background-color, border-color; transition-timing-function: ease; transition-duration: 150ms; }
        .transition-transform { transition-property: transform; transition-timing-function: ease; transition-duration: 150ms; }
        .duration-150 { transition-duration: 150ms; }
        .duration-200 { transition-duration: 200ms; }
        .rotate-90 { transform: rotate(90deg); }
        [class*="bg-primary/10"] { background-color: rgba(59, 130, 246, 0.1); }
        .hover\\:bg-gray-100:hover { background-color: #f3f4f6; }
        .hover\\:text-primary:hover { color: #3b82f6; }
        .fas.fa-chevron-right::before {
            content: "";
            display: inline-block;
            width: 0.4em;
            height: 0.4em;
            border-right: 2px solid currentColor;
            border-bottom: 2px solid currentColor;
            transform: rotate(-45deg);
        }
        .chevron { font-style: normal; }
        .tree-node-link, .tree-node a {
            pointer-events: none;
            cursor: default;
        }
        """

        return f"""
<style>
    body {{ overflow: auto; height: auto; }}
    .preview-content {{ padding: 16px; font-family: system-ui, -apple-system, sans-serif; }}
    .search-input {{
        width: 100%; padding: 8px 12px; border: 1px solid #d1d5db;
        border-radius: 6px; font-size: 14px; outline: none; box-sizing: border-box;
    }}
    .search-input:focus {{ border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.3); }}
    {tailwind_shim}
    {css_content}
</style>
<div class="preview-content">
    <div style="margin-bottom:16px">
        <input type="text" id="{search_id}" class="search-input" placeholder="Search...">
    </div>
    <div id="{container_id}" class="hierarchical-nav-tree" role="tree"></div>
</div>
<script>
{js_content}
</script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    if (typeof NiamotoHierarchicalNav !== 'undefined') {{
        new NiamotoHierarchicalNav({safe_json});
    }}
}});
</script>"""

    # ------------------------------------------------------------------
    # GENERAL INFO branch
    # ------------------------------------------------------------------

    def _render_general_info(
        self,
        reference_name: str,
        entity_id: str | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        if not db:
            return self._info_html("Database not configured")

        try:
            from niamoto.gui.api.services.templates.suggestion_service import (
                generate_general_info_suggestion,
            )

            suggestion = generate_general_info_suggestion(reference_name, db=db)
            if not suggestion:
                return self._info_html(f"No fields detected for '{reference_name}'")

            field_configs = suggestion["config"]["fields"]

            # Find the reference table
            ref_table = f"reference_{reference_name}"
            if not db.has_table(ref_table):
                fallbacks = (
                    [f"entity_{reference_name}", reference_name]
                    if entity_id
                    else [reference_name, f"entity_{reference_name}"]
                )
                for alt in fallbacks:
                    if db.has_table(alt):
                        ref_table = alt
                        break
                else:
                    return self._info_html(f"Table '{reference_name}' not found")

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(ref_table)
            col_names = [c.lower() for c in self._get_column_names(db, quoted_table)]

            # Detect ID field — prefer "id" (PK) over "{ref}_id" (FK)
            id_field = _pick_identifier_column(col_names, preferred="id") or "id"

            # Load a sample entity
            if entity_id:
                query = text(
                    f"SELECT * FROM {quoted_table} "
                    f"WHERE {preparer.quote(id_field)} = :eid LIMIT 1"
                )
                sample_df = pd.read_sql(
                    query, db.engine, params={"eid": str(entity_id)}
                )
            else:
                sample_df = pd.read_sql(
                    text(f"SELECT * FROM {quoted_table} LIMIT 1"), db.engine
                )

            if sample_df.empty:
                return self._info_html(f"No data in '{reference_name}'")

            row = sample_df.iloc[0]

            # Build data for info_grid
            items: list[dict[str, Any]] = []
            for field_cfg in field_configs:
                field_name = field_cfg.get("field", "")
                target = field_cfg.get("target", field_name)
                label = field_cfg.get("label", target.replace("_", " ").title())
                units = field_cfg.get("units", "")

                # Handle count transformations separately
                if field_cfg.get("transformation") == "count":
                    source = field_cfg.get("source", "")
                    count_table = None
                    for prefix in (
                        f"dataset_{source}",
                        source,
                        f"entity_{source}",
                    ):
                        if db.has_table(prefix):
                            count_table = prefix
                            break
                    if count_table:
                        try:
                            qt = preparer.quote(count_table)
                            qf = preparer.quote(field_name)
                            qid = preparer.quote(id_field)
                            count_q = text(
                                f"SELECT COUNT({qf}) FROM {qt} WHERE {qid} = :eid"
                            )
                            cnt = pd.read_sql(
                                count_q, db.engine, params={"eid": str(entity_id or "")}
                            )
                            value = int(cnt.iloc[0, 0]) if not cnt.empty else 0
                        except Exception:
                            value = None
                    else:
                        value = None
                elif "." in field_name:
                    # JSON path (e.g. extra_data.holdridge)
                    parts = field_name.split(".", 1)
                    container = row.get(parts[0])
                    if container is not None and not (
                        isinstance(container, float) and pd.isna(container)
                    ):
                        if isinstance(container, str):
                            try:
                                import json as _json

                                container = _json.loads(container)
                            except Exception:
                                container = None
                        value = (
                            container.get(parts[1])
                            if isinstance(container, dict)
                            else None
                        )
                    else:
                        value = None
                elif field_name in row.index:
                    value = row.get(field_name)
                else:
                    # Field not in this table — skip silently
                    value = None

                if value is not None and pd.isna(value):
                    value = None
                elif hasattr(value, "item"):
                    value = value.item()

                items.append(
                    {
                        "label": label,
                        "value": value,
                        "units": units,
                    }
                )

            # Render via info_grid
            try:
                plugin_class = PluginRegistry.get_plugin("info_grid", PluginType.WIDGET)
                plugin_instance = plugin_class(db=db)
                widget_data = {
                    field_cfg.get("target", field_cfg.get("field", f"field_{i}")): {
                        "value": item["value"],
                        "units": item.get("units", ""),
                    }
                    for i, (field_cfg, item) in enumerate(zip(field_configs, items))
                }
                widget_params = {
                    "title": f"Informations - {reference_name.title()}",
                    "items": items,
                    "grid_columns": 2,
                }
                # Validate via the plugin's Pydantic schema
                if (
                    hasattr(plugin_instance, "param_schema")
                    and plugin_instance.param_schema
                ):
                    validated = plugin_instance.param_schema.model_validate(
                        widget_params
                    )
                else:
                    validated = widget_params
                return plugin_instance.render(widget_data, validated)
            except Exception as e:
                logger.warning("Info grid render error: %s", e)
                return self._render_general_info_fallback(items, reference_name)

        except Exception as e:
            logger.exception("General info preview error: %s", e)
            return self._error_html(str(e))

    def _render_general_info_fallback(
        self, items: list[dict[str, Any]], reference_name: str
    ) -> str:
        rows = ""
        for item in items[:8]:
            label = html_module.escape(str(item.get("label", "")))
            value = html_module.escape(str(item.get("value", "\u2014")))
            units = html_module.escape(str(item.get("units", "")))
            rows += (
                f"<tr><td style='padding:4px 8px;color:#6b7280'>{label}</td>"
                f"<td style='padding:4px 8px;font-weight:500'>{value} {units}</td></tr>\n"
            )
        title = html_module.escape(reference_name.title())
        return f"""
<div style="padding:8px;font-family:system-ui,sans-serif;font-size:13px;">
  <h4 style="margin:0 0 8px">{title}</h4>
  <table style="border-collapse:collapse;width:100%">{rows}</table>
</div>"""

    # ------------------------------------------------------------------
    # ENTITY MAP branch
    # ------------------------------------------------------------------

    def _render_entity_map(
        self,
        template_id: str,
        entity_id: str | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        """Entity map rendering via MapRenderer.render (classmethod)."""
        from niamoto.gui.api.services.map_renderer import (
            MapConfig,
            MapRenderer,
            MapStyle,
        )

        if not db:
            return self._error_html("Database not found")

        try:
            # Parse the template_id
            if template_id.endswith("_entity_map"):
                mode = "single"
                prefix = template_id[:-11]
            elif template_id.endswith("_all_map"):
                mode = "all"
                prefix = template_id[:-8]
            else:
                return self._error_html(f"Invalid entity map format: {template_id}")

            parts = prefix.split("_")
            if len(parts) < 2:
                return self._error_html(f"Cannot parse template_id: {template_id}")

            reference = parts[0]
            geom_col = "_".join(parts[1:])

            entity_table = resolve_reference_table(db, reference)
            if not entity_table:
                return self._info_html(f"Table '{reference}' not found")

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(entity_table)
            col_names = self._get_column_names(db, quoted_table)

            # Resolve the geometry column
            actual_geom_col = None
            if geom_col in col_names:
                actual_geom_col = geom_col
            elif f"{geom_col}_geom" in col_names:
                actual_geom_col = f"{geom_col}_geom"
            else:
                for c in col_names:
                    if c.endswith("_geom") or c in ("geometry", "geom"):
                        actual_geom_col = c
                        break

            if not actual_geom_col:
                return self._info_html(f"Geometry column '{geom_col}' not found")

            # Detect name and id fields
            id_field = _pick_identifier_column(col_names, entity_name=reference) or (
                col_names[0] if col_names else "id"
            )
            name_field = _pick_name_column(col_names, id_field, reference)

            quoted_geom = preparer.quote(actual_geom_col)
            quoted_id = preparer.quote(id_field)
            quoted_name = preparer.quote(name_field)
            quoted_lft = preparer.quote("lft") if "lft" in col_names else None
            quoted_rght = preparer.quote("rght") if "rght" in col_names else None
            quoted_parent = (
                preparer.quote("parent_id") if "parent_id" in col_names else None
            )

            # Build query according to mode
            query_params: dict[str, Any] = {}
            if mode == "single":
                if not entity_id:
                    rep = pd.read_sql(
                        text(
                            f"SELECT {quoted_id} as id FROM {quoted_table} "
                            f"WHERE {quoted_geom} IS NOT NULL LIMIT 1"
                        ),
                        db.engine,
                    )
                    if not rep.empty:
                        entity_id = str(rep.iloc[0]["id"])

                if entity_id:
                    query = (
                        f"SELECT {quoted_id} as id, {quoted_name} as name, "
                        f"{quoted_geom} as geom FROM {quoted_table} "
                        f"WHERE {quoted_id} = :entity_id"
                    )
                    query_params["entity_id"] = str(entity_id)
                else:
                    query = (
                        f"SELECT {quoted_id} as id, {quoted_name} as name, "
                        f"{quoted_geom} as geom FROM {quoted_table} "
                        f"WHERE {quoted_geom} IS NOT NULL LIMIT 1"
                    )
            else:
                query = (
                    f"SELECT {quoted_id} as id, {quoted_name} as name, "
                    f"{quoted_geom} as geom FROM {quoted_table} "
                    f"WHERE {quoted_geom} IS NOT NULL LIMIT 500"
                )

            result = pd.read_sql(text(query), db.engine, params=query_params or None)
            if result.empty:
                return self._info_html("No geographic data available")

            # Convert to GeoJSON
            features = []
            for _, row in result.iterrows():
                geom_str = str(row["geom"])
                geometry = parse_wkt_to_geojson(geom_str)
                if not geometry:
                    continue
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "id": str(row["id"]),
                            "name": (
                                str(row["name"])
                                if pd.notna(row["name"])
                                else f"ID: {row['id']}"
                            ),
                        },
                        "geometry": geometry,
                    }
                )

            if (
                not features
                and mode == "single"
                and entity_id
                and (quoted_lft and quoted_rght or quoted_parent)
            ):
                descendant_query = None
                descendant_params: dict[str, Any] = {"entity_id": str(entity_id)}

                if quoted_lft and quoted_rght:
                    descendant_query = (
                        f"SELECT child.{quoted_id} as id, child.{quoted_name} as name, "
                        f"child.{quoted_geom} as geom "
                        f"FROM {quoted_table} parent "
                        f"JOIN {quoted_table} child "
                        f"ON child.{quoted_lft} > parent.{quoted_lft} "
                        f"AND child.{quoted_rght} < parent.{quoted_rght} "
                        f"WHERE parent.{quoted_id} = :entity_id "
                        f"AND child.{quoted_geom} IS NOT NULL "
                        f"LIMIT 500"
                    )
                elif quoted_parent:
                    descendant_query = (
                        f"SELECT {quoted_id} as id, {quoted_name} as name, "
                        f"{quoted_geom} as geom FROM {quoted_table} "
                        f"WHERE {quoted_parent} = :entity_id "
                        f"AND {quoted_geom} IS NOT NULL "
                        f"LIMIT 500"
                    )

                if descendant_query:
                    descendants = pd.read_sql(
                        text(descendant_query), db.engine, params=descendant_params
                    )
                    for _, row in descendants.iterrows():
                        geom_str = str(row["geom"])
                        geometry = parse_wkt_to_geojson(geom_str)
                        if not geometry:
                            continue
                        features.append(
                            {
                                "type": "Feature",
                                "properties": {
                                    "id": str(row["id"]),
                                    "name": (
                                        str(row["name"])
                                        if pd.notna(row["name"])
                                        else f"ID: {row['id']}"
                                    ),
                                },
                                "geometry": geometry,
                            }
                        )

            if not features:
                return self._info_html("No valid geometry found")

            geojson = {"type": "FeatureCollection", "features": features}

            title = (
                f"Position {reference.rstrip('s')}"
                if mode == "single"
                else f"Tous les {reference}"
            )
            map_config = MapConfig(
                title=title,
                zoom=10.0 if mode == "single" else 7.0,
                auto_zoom=True,
                style=MapStyle(
                    color="#3b82f6",
                    fill_color="#3b82f6",
                    fill_opacity=0.3,
                    stroke_width=2,
                    point_radius=8,
                ),
            )
            return MapRenderer.render(geojson, map_config, engine="plotly")

        except Exception as e:
            logger.exception("Entity map preview error: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # STANDARD branch (configured / dynamic / class_object / occurrence)
    # ------------------------------------------------------------------

    def _render_standard(
        self,
        request: PreviewRequest,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        """Handle cases 4-7: configured widget, dynamic, class_object, occurrence."""
        template_id = request.template_id
        group_by = request.group_by
        source = request.source
        entity_id = request.entity_id

        # Try to load a configured widget (transform.yml)
        detected_group_by = group_by
        if not detected_group_by:
            detected_group_by = find_widget_group(template_id)

        if detected_group_by:
            configured = load_configured_widget(template_id, detected_group_by)
            if configured:
                return self._render_configured_widget(
                    configured, detected_group_by, entity_id, db, warnings
                )

        # Parse the dynamic template_id
        parsed = parse_dynamic_template_id(template_id)
        if not parsed:
            return self._error_html(f"Invalid template_id format: '{template_id}'")

        # Check if the source is in transform.yml
        effective_source = source
        if not effective_source:
            cfg_group = group_by or find_widget_group(template_id)
            if cfg_group:
                configured = load_configured_widget(template_id, cfg_group)
                if configured:
                    cfg_source = (configured.get("transformer_params") or {}).get(
                        "source"
                    )
                    if (
                        cfg_source
                        and cfg_source != "occurrences"
                        and not is_class_object_template(parsed["transformer"])
                    ):
                        return self._render_configured_widget(
                            configured, cfg_group, entity_id, db, warnings
                        )

        # Load widget params from export.yml
        export_widget_params = None
        if group_by:
            export_widget_params = load_widget_params_from_export(template_id, group_by)

        column = parsed["column"]
        transformer = parsed["transformer"]
        widget_plugin = parsed["widget"]
        data_source = effective_source or "occurrences"

        # --- Class object (CSV) ---
        if is_class_object_template(transformer):
            return self._render_class_object(
                column, transformer, widget_plugin, group_by, db, warnings
            )

        # --- Entity table (non-occurrence) ---
        # --- Dynamic preview (occurrence or entity source) ---
        return self._render_dynamic_preview(
            template_id,
            column,
            transformer,
            widget_plugin,
            data_source,
            group_by,
            entity_id,
            export_widget_params,
            db,
            warnings,
        )

    # ------------------------------------------------------------------
    # Sub-branch: Configured widget (transform.yml)
    # ------------------------------------------------------------------

    def _render_configured_widget(
        self,
        configured: dict[str, Any],
        group_by: str,
        entity_id: str | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        transformer_plugin = configured["transformer_plugin"]
        transformer_params = configured["transformer_params"]
        widget_plugin = configured["widget_plugin"]
        widget_params = configured.get("widget_params", {})
        widget_title = configured["widget_title"]
        widget_id = configured.get("widget_id", "")

        # Verify the widget plugin
        try:
            PluginRegistry.get_plugin(widget_plugin, PluginType.WIDGET)
        except Exception:
            return self._error_html(f"Widget plugin '{widget_plugin}' not found")

        if not db:
            return self._info_html("Database not configured")

        try:
            if transformer_plugin.startswith("class_object_"):
                return self._render_configured_class_object(
                    db,
                    transformer_plugin,
                    transformer_params,
                    widget_plugin,
                    widget_params,
                    widget_title,
                    group_by,
                    warnings,
                )

            # Delegate to TransformerService.transform_single_widget()
            # which shares the exact same code path as `niamoto transform`.
            svc = self._get_transformer_service(db)

            group_config = self._load_group_config(group_by, svc)
            if not group_config:
                return self._info_html(f"Group '{group_by}' not found")

            # Pick a representative group_id
            group_ids = svc._get_group_ids(group_config)
            if not group_ids:
                return self._info_html("No entities available")
            gid = self._resolve_entity_id(entity_id, group_ids)
            if gid is None:
                return self._info_html(f"Entity '{entity_id}' not found in {group_by}")

            result = svc.transform_single_widget(group_config, widget_id, gid)

            # Adapt transformer output format to widget format if needed
            result = _preprocess_data_for_widget(
                result, transformer_plugin, widget_plugin
            )

            # Widget rendering
            return render_widget(db, widget_plugin, result, widget_params, widget_title)

        except (DataTransformError, DataLoadError) as e:
            # Data not available yet (e.g. CSV not generated, empty DB)
            logger.warning("Preview data unavailable for %s: %s", widget_id, e)
            return self._info_html(f"Data not available : {e}")
        except Exception as e:
            logger.exception("Configured widget preview error: %s", e)
            return self._error_html(str(e))

    # Transformers that ALWAYS need the raw CSV DataFrame.
    _RAW_DF_TRANSFORMERS = {
        "class_object_series_ratio_aggregator",
        "class_object_categories_mapper",
        "class_object_series_matrix_extractor",
        "class_object_series_by_axis_extractor",
    }

    # Widgets that need the real (nested) transformer output instead of
    # the flat {tops, counts} emulation.
    _WIDGETS_NEEDING_REAL_PLUGIN = {
        "concentric_rings",
    }

    def _render_configured_class_object(
        self,
        db: Database | None,
        transformer_plugin: str,
        transformer_params: dict[str, Any],
        widget_plugin: str,
        widget_params: dict[str, Any] | None,
        widget_title: str,
        group_by: str,
        warnings: list[str],
    ) -> str:
        """Render a configured widget based on class_object (CSV)."""

        use_real_plugin = (
            transformer_plugin in self._RAW_DF_TRANSFORMERS
            or widget_plugin in self._WIDGETS_NEEDING_REAL_PLUGIN
        )

        if use_real_plugin:
            result = self._transform_with_real_plugin(
                db, transformer_plugin, transformer_params, group_by
            )
        else:
            result = self._transform_with_emulation(
                transformer_plugin, transformer_params, group_by
            )

        if isinstance(result, str):
            # Error HTML returned by helper
            return result
        if not result:
            return self._info_html("Transformer returned no data")

        # Merge display params from transform.yml with widget_params from
        # export.yml -- fields like x_axis, y_axis, orientation, sort_order,
        # auto_color are in transformer_params but must be passed to the widget.
        _WIDGET_DISPLAY_KEYS = {
            "x_axis",
            "y_axis",
            "orientation",
            "sort_order",
            "auto_color",
            "gradient_color",
            "title",
        }
        merged_params = {
            k: v for k, v in transformer_params.items() if k in _WIDGET_DISPLAY_KEYS
        }
        if widget_params:
            merged_params.update(widget_params)

        # Remap data field names when transformer output (tops/counts) doesn't
        # match widget expected field names from export.yml.
        # Widgets reference fields via x_axis/y_axis (bar_plot) or
        # labels_field/values_field (donut_chart).  The real pipeline stores
        # {tops, counts} in JSON and the browser JS handles it; the Python
        # preview renderer needs exact field name matches.
        if isinstance(result, dict) and "tops" in result and "counts" in result:
            # bar_plot fields
            x_field = merged_params.get("x_axis", "tops")
            y_field = merged_params.get("y_axis", "counts")
            if x_field != "tops" and x_field not in result:
                result[x_field] = result["tops"]
            if y_field != "counts" and y_field not in result:
                result[y_field] = result["counts"]
            # donut_chart fields
            labels_field = merged_params.get("labels_field")
            values_field = merged_params.get("values_field")
            if labels_field and labels_field != "tops" and labels_field not in result:
                result[labels_field] = result["tops"]
            if values_field and values_field != "counts" and values_field not in result:
                result[values_field] = result["counts"]

        return _render_widget_for_configured(
            db,
            widget_plugin,
            result,
            transformer_plugin,
            widget_title,
            merged_params,
        )

    def _transform_with_real_plugin(
        self,
        db: Database | None,
        transformer_plugin: str,
        transformer_params: dict[str, Any],
        group_by: str,
    ) -> dict[str, Any] | str:
        """Load raw CSV and call the real transformer plugin.

        Returns transformer result dict, or an info/error HTML string.
        """
        source_name = transformer_params.get("source")
        raw_df = load_class_object_csv_dataframe(
            self._work_dir, group_by, source_name=source_name
        )
        if raw_df is None or raw_df.empty:
            return self._info_html(f"CSV data not found for group '{group_by}'")

        try:
            plugin_class = PluginRegistry.get_plugin(
                transformer_plugin, PluginType.TRANSFORMER
            )
            plugin_instance = plugin_class(db=db)
            config = {"plugin": transformer_plugin, "params": transformer_params}
            return plugin_instance.transform(raw_df, config)
        except (DataTransformError, DataLoadError) as e:
            logger.warning(
                "Real plugin transform failed for %s: %s", transformer_plugin, e
            )
            return self._info_html(f"Transform error: {e}")
        except Exception as e:
            logger.exception("Unexpected error in real plugin %s", transformer_plugin)
            return self._error_html(str(e))

    def _transform_with_emulation(
        self,
        transformer_plugin: str,
        transformer_params: dict[str, Any],
        group_by: str,
    ) -> dict[str, Any] | str | None:
        """Use the pre-aggregated {tops, counts} emulation path.

        Returns transformer result dict, info HTML string, or None.
        """
        class_objects = _extract_class_objects_from_params(transformer_params)
        if not class_objects:
            return self._info_html("No class objects configured")

        co_data = {}
        for co_name in class_objects:
            data = load_class_object_data_for_preview(self._work_dir, co_name, group_by)
            if data:
                co_data[co_name] = data

        if not co_data:
            return self._info_html(f"Data not found for: {', '.join(class_objects)}")

        return _execute_configured_transformer(
            transformer_plugin, transformer_params, co_data, group_by
        )

    # ------------------------------------------------------------------
    # Sub-branch: Class object (CSV, dynamic)
    # ------------------------------------------------------------------

    def _render_class_object(
        self,
        column: str,
        transformer: str,
        widget_plugin: str,
        group_by: str | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        reference_name = group_by
        if not reference_name:
            try:
                import_config = load_import_config(self._work_dir)
                hierarchy_info = get_hierarchy_info(import_config)
                reference_name = hierarchy_info["reference_name"]
            except Exception:
                reference_name = ""

        co_data = load_class_object_data_for_preview(
            self._work_dir, column, reference_name or ""
        )
        if not co_data:
            return self._info_html(f"Data '{column}' not found in CSV sources")

        try:
            title = column.replace("_", " ").title()
            return _render_widget_for_class_object(
                db, widget_plugin, co_data, transformer, title
            )
        except Exception as e:
            logger.exception("Class object preview error: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Sub-branch: Entity source (non-occurrence)
    # ------------------------------------------------------------------

    def _render_dynamic_preview(
        self,
        template_id: str,
        column: str,
        transformer_plugin: str,
        widget_plugin: str,
        data_source: str,
        group_by: str | None,
        entity_id: str | None,
        export_widget_params: dict[str, Any] | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        """Render a dynamic (not-yet-configured) widget preview.

        Tries TransformerService.transform_single_widget() first (same pipeline
        as configured widgets).  Falls back to ad-hoc execution only when no
        group_config is available (e.g. first init without transform.yml).
        """
        if not db:
            return self._error_html("Database not found")

        try:
            transformer_config = _build_transformer_config(
                column, transformer_plugin, data_source, db
            )

            # --- Primary path: use TransformerService (same as configured) ---
            preview_group = self._resolve_preview_group_context(group_by, entity_id, db)
            if preview_group:
                svc, group_config, gid = preview_group
                temp_group_config = self._build_preview_group_config(
                    group_config,
                    template_id,
                    transformer_plugin,
                    transformer_config,
                )
                result = svc.transform_single_widget(
                    temp_group_config, template_id, gid
                )

            # --- Fallback: ad-hoc execution (no group_config available) ---
            elif data_source != "occurrences":
                # Entity source fallback (non-occurrence table)
                entity_table = resolve_entity_table(db, data_source, kind=None)
                if not entity_table or not db.has_table(entity_table):
                    return self._info_html(f"No table for source '{data_source}'")

                preparer = inspect(db.engine).dialect.identifier_preparer
                quoted_table = preparer.quote(entity_table)
                entity_columns = set(self._get_column_names(db, quoted_table))

                if column not in entity_columns:
                    return self._info_html(
                        f"Field '{column}' not found in {entity_table}"
                    )

                quoted_field = preparer.quote(column)
                sample_data = pd.read_sql(
                    text(
                        f"SELECT {quoted_field} FROM {quoted_table} "
                        f"WHERE {quoted_field} IS NOT NULL"
                    ),
                    db.engine,
                )

                if sample_data.empty:
                    return self._info_html(f"No data for '{column}' in {entity_table}")

                transform_input: Any = sample_data
                if transformer_plugin == "field_aggregator":
                    transform_input = {data_source: sample_data}

                result = execute_transformer(
                    db, transformer_plugin, transformer_config, transform_input
                )
            else:
                # Occurrence source fallback
                import_config = load_import_config(self._work_dir)
                hierarchy_info = get_hierarchy_info(import_config, group_by)

                if entity_id:
                    representative = find_entity_by_id(db, hierarchy_info, entity_id)
                else:
                    representative = find_representative_entity(db, hierarchy_info)

                sample_data = load_sample_data(db, representative, transformer_config)
                if sample_data.empty:
                    return self._info_html("No data available")

                result = execute_transformer(
                    db, transformer_plugin, transformer_config, sample_data
                )

            # Adapt transformer output → widget format
            result = _preprocess_data_for_widget(
                result, transformer_plugin, widget_plugin
            )

            # Build widget display params for required fields (x_axis, y_axis)
            widget_params = _build_widget_params_for_preview(
                column, transformer_plugin, widget_plugin, data_source, db
            )
            if export_widget_params:
                widget_params.update(export_widget_params)

            title = column.replace("_", " ").title()
            return render_widget(
                db, widget_plugin, result, widget_params or None, title
            )

        except (DataTransformError, DataLoadError) as e:
            logger.warning("Preview data unavailable for %s: %s", template_id, e)
            return self._info_html(f"Data not available : {e}")
        except Exception as e:
            logger.exception("Dynamic preview error: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _open_db(self) -> Database | None:
        """Return the shared DB instance (read-only, lazy)."""
        if self._db is not None:
            return self._db
        if not os.path.exists(self._db_path):
            return None
        self._db = Database(self._db_path, read_only=True)
        return self._db


# --------------------------------------------------------------------------
# Factory (thread-safe)
# --------------------------------------------------------------------------

_engine_lock = threading.Lock()
_engine_instance: PreviewEngine | None = None


def get_preview_engine() -> PreviewEngine | None:
    """Return the shared preview engine instance.

    Lazily created on the first request (double-checked locking).
    """
    global _engine_instance
    if _engine_instance is not None:
        return _engine_instance

    with _engine_lock:
        if _engine_instance is not None:
            return _engine_instance

        db_path = get_database_path()
        work_dir = get_working_directory()

        if not db_path:
            return None

        config_dir = str(work_dir / "config") if work_dir else ""
        engine = PreviewEngine(
            db_path=str(db_path),
            config_dir=config_dir,
        )
        _engine_instance = engine
        return engine


def reset_preview_engine() -> None:
    """Reset the instance -- useful after switching projects."""
    global _engine_instance, _transformer_svc
    with _engine_lock:
        _engine_instance = None
        _transformer_svc = None
