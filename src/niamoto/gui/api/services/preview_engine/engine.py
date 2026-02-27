"""Moteur de preview unifié pour les widgets Niamoto.

Pipeline synchrone : resolve -> load -> transform -> render -> wrap.
Appelé depuis les endpoints via `await run_in_threadpool(engine.render, req)`.

Utilise les mêmes utilitaires que templates.py pour la résolution,
le chargement de données, la transformation et le rendu.
"""

import hashlib
import html as html_module
import logging
import os
import threading
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import inspect, text

from niamoto.common.database import Database
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
    load_class_object_data_for_preview,
    load_sample_data,
)
from niamoto.gui.api.services.templates.utils.entity_finder import (
    find_entity_by_id,
    find_representative_entity,
)
from niamoto.gui.api.services.templates.utils.widget_utils import (
    find_widget_group,
    is_class_object_template,
    load_configured_widget,
    load_widget_params_from_export,
    parse_dynamic_template_id,
)

logger = logging.getLogger(__name__)

_plugins_loaded = False


def _ensure_plugins_loaded() -> None:
    """Charger les plugins transformer et widget si nécessaire."""
    global _plugins_loaded
    if _plugins_loaded:
        return

    from niamoto.core.plugins.transformers.distribution import (  # noqa: F401
        binned_distribution,
        categorical_distribution,
    )
    from niamoto.core.plugins.transformers.aggregation import (  # noqa: F401
        statistical_summary,
        field_aggregator,
        binary_counter,
        top_ranking,
    )
    from niamoto.core.plugins.transformers.extraction import (  # noqa: F401
        geospatial_extractor,
    )
    from niamoto.core.plugins.widgets import (  # noqa: F401
        bar_plot,
        donut_chart,
        info_grid,
        interactive_map,
        radial_gauge,
    )

    try:
        from niamoto.core.plugins.widgets import hierarchical_nav_widget  # noqa: F401
    except ImportError:
        pass

    _plugins_loaded = True


# ---------------------------------------------------------------------------
# Adaptateur de format transformer → widget
# ---------------------------------------------------------------------------
# Reproduit la logique de templates.py:_preprocess_data_for_widget pour
# les combinaisons transformer/widget dont le format de sortie ne correspond
# pas directement aux attentes du widget.


def _preprocess_data_for_widget(data: Any, transformer: str, widget: str) -> Any:
    """Adapte la sortie d'un transformer au format attendu par le widget."""
    if not isinstance(data, dict):
        return data

    # binned_distribution → donut_chart : convertir les bin edges en labels
    if transformer == "binned_distribution" and widget == "donut_chart":
        bins = data.get("bins", [])
        counts = data.get("counts", [])
        if len(bins) == len(counts) + 1:
            labels = [f"{int(bins[i])}-{int(bins[i + 1])}" for i in range(len(counts))]
            result: dict[str, Any] = {"labels": labels, "counts": counts}
            percentages = data.get("percentages", [])
            if percentages and len(percentages) == len(labels):
                result["percentages"] = percentages
            return result

    # field_aggregator → radial_gauge : aplatir le payload imbriqué
    if transformer == "field_aggregator" and widget == "radial_gauge":
        if "value" in data:
            return data
        scalar_value: Any = None
        scalar_unit: str | None = None
        for field_payload in data.values():
            if not isinstance(field_payload, dict):
                continue
            candidate = field_payload.get("value")
            if candidate is None:
                continue
            scalar_value = candidate
            units = field_payload.get("units") or field_payload.get("unit")
            if isinstance(units, str) and units:
                scalar_unit = units
            break
        if scalar_value is not None:
            flattened: dict[str, Any] = {"value": scalar_value}
            if scalar_unit:
                flattened["unit"] = scalar_unit
            return flattened

    return data


class PreviewEngine:
    """Moteur de preview unifié -- un seul pipeline pour tous les types de widgets.

    Le moteur est synchrone (I/O fichiers + DB). Les endpoints l'appellent
    via ``await run_in_threadpool(engine.render, req)``.
    """

    def __init__(self, db_path: str, config_dir: str):
        self._db_path = db_path
        self._config_dir = config_dir
        self._work_dir = Path(config_dir).parent
        self._data_fingerprint: str = self._compute_data_fingerprint()

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def render(self, request: PreviewRequest) -> PreviewResult:
        """Point d'entrée unique -- résout, charge, transforme, rend, emballe."""
        _ensure_plugins_loaded()

        warnings: list[str] = []
        template_id = request.template_id

        db = self._open_db()
        try:
            # --- Inline (POST) : transformer + widget explicites ---
            if request.inline:
                widget_plugin = request.inline.get("widget_plugin", "")
                widget_html = self._render_inline(request, db, warnings)
                return self._build_result(
                    request, widget_html, warnings, widget_plugin=widget_plugin
                )

            if not template_id:
                return self._error_result(request, "template_id requis", warnings)

            # --- Branche 1 : Navigation widget ---
            if template_id.endswith("_hierarchical_nav_widget"):
                reference = template_id.replace("_hierarchical_nav_widget", "")
                widget_html = self._render_navigation(reference, db, warnings)
                return self._build_result(
                    request,
                    widget_html,
                    warnings,
                    widget_plugin="hierarchical_nav_widget",
                )

            # --- Branche 2 : General info widget ---
            if template_id.startswith("general_info_") and template_id.endswith(
                "_field_aggregator_info_grid"
            ):
                reference = template_id.replace("general_info_", "").replace(
                    "_field_aggregator_info_grid", ""
                )
                widget_html = self._render_general_info(
                    reference, request.entity_id, db, warnings
                )
                return self._build_result(
                    request,
                    widget_html,
                    warnings,
                    widget_plugin="info_grid",
                )

            # --- Branche 3 : Entity map ---
            if template_id.endswith("_entity_map") or template_id.endswith("_all_map"):
                widget_html = self._render_entity_map(
                    template_id, request.entity_id, db, warnings
                )
                return self._build_result(
                    request,
                    widget_html,
                    warnings,
                    widget_plugin="interactive_map",
                )

            # --- Branche 4-7 : Configured / Dynamic / Class object / Occurrence ---
            widget_html = self._render_standard(request, db, warnings)
            # Extraire le plugin widget pour la résolution du bundle Plotly
            parsed = parse_dynamic_template_id(template_id)
            wp = parsed["widget"] if parsed else None
            return self._build_result(request, widget_html, warnings, widget_plugin=wp)
        finally:
            if db:
                db.close_db_session()

    def invalidate(self) -> None:
        """Recalcule le fingerprint -- appelé après import ou save config."""
        self._data_fingerprint = self._compute_data_fingerprint()

    # ------------------------------------------------------------------
    # Construction du résultat
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
        """Empreinte mtime(DB) + mtime(configs). Zéro I/O entre invalidate()."""
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
        """Document HTML complet pour injection dans un iframe via srcDoc."""
        return wrap_html_response(
            content,
            title="Preview",
            plotly_bundle=bundle,
            thumbnail=(mode == "thumbnail"),
        )

    # ------------------------------------------------------------------
    # Découverte de colonnes via DESCRIBE
    # ------------------------------------------------------------------

    def _get_column_names(self, db: Database, quoted_table: str) -> list[str]:
        """Découvrir les colonnes d'une table via DESCRIBE (plus efficace que SELECT * LIMIT 0)."""
        with db.engine.connect() as conn:
            result = conn.execute(text(f"DESCRIBE {quoted_table}"))
            return [row[0] for row in result.fetchall()]

    # ------------------------------------------------------------------
    # Branche INLINE (POST)
    # ------------------------------------------------------------------

    def _render_inline(
        self,
        request: PreviewRequest,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        inline = request.inline
        if not inline:
            return self._info_html("Configuration inline manquante")

        if not db:
            return self._info_html("Base de données non configurée")

        transformer_plugin = inline.get("transformer_plugin", "")
        transformer_params = inline.get("transformer_params", {})
        widget_plugin = inline.get("widget_plugin", "")
        widget_params = inline.get("widget_params")
        widget_title = inline.get("widget_title", "Preview")
        group_by = request.group_by or ""

        try:
            # Charger les données selon le type de transformer
            if transformer_plugin.startswith("class_object_"):
                co_data = load_class_object_data_for_preview(
                    self._work_dir,
                    transformer_params.get("source", ""),
                    group_by,
                )
                if not co_data:
                    return self._info_html("Données class_object non trouvées")
                data = co_data
            else:
                import_config = load_import_config(self._work_dir)
                hierarchy_info = get_hierarchy_info(import_config, group_by)
                representative = find_representative_entity(db, hierarchy_info)
                sample = load_sample_data(db, representative, transformer_params)
                if sample.empty:
                    return self._info_html("Pas de données disponibles")
                data = sample

            result = execute_transformer(
                db, transformer_plugin, transformer_params, data
            )
            if not result:
                return self._info_html("Le transformer n'a pas retourné de données")

            return render_widget(db, widget_plugin, result, widget_params, widget_title)
        except Exception as e:
            logger.exception("Erreur preview inline: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Branche NAVIGATION
    # ------------------------------------------------------------------

    def _render_navigation(
        self,
        reference_name: str,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        if not db:
            return self._info_html("Base de données non configurée")

        try:
            table_name = resolve_reference_table(db, reference_name)
            if not table_name:
                return self._info_html(f"Table '{reference_name}' non trouvée")

            quoted = quote_identifier(db, table_name)

            # Colonnes (exclure géométries)
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

            # Champ ID
            singular = (
                reference_name.rstrip("s")
                if reference_name.endswith("s")
                else reference_name
            )
            id_candidates = [
                f"id_{singular}",
                f"{singular}_id",
                f"id_{reference_name}",
                f"{reference_name}_id",
                "id",
            ]
            id_field = next((c for c in id_candidates if c in columns), None)
            if not id_field:
                id_field = next((c for c in columns if "id" in c.lower()), "id")

            # Champ nom
            name_candidates = ["full_name", "name", "plot", "label", "title"]
            name_field = next((c for c in name_candidates if c in columns), id_field)

            # Requête sample
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
                return self._info_html(f"Aucune donnée dans '{reference_name}'")

            # Rendu inline avec CSS/JS (le plugin render() suppose un
            # environnement externe avec les assets déjà chargés, ce qui
            # n'est pas le cas en preview iframe).
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
            logger.exception("Erreur preview navigation: %s", e)
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
        """Rendu navigation avec CSS/JS inlinés (autonome en preview iframe)."""
        import json

        # Charger les assets CSS/JS depuis publish/assets
        # engine.py est dans gui/api/services/preview_engine/ → 5 niveaux pour niamoto/
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

        # CSS Tailwind utilities utilisées par niamoto_hierarchical_nav.js
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
        <input type="text" id="{search_id}" class="search-input" placeholder="Rechercher...">
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

    def _render_navigation_fallback(
        self,
        df: pd.DataFrame,
        reference_name: str,
        id_field: str,
        name_field: str,
        is_hierarchical: bool,
    ) -> str:
        """Fallback HTML simple si le plugin nav n'est pas disponible."""
        items_html = ""
        for _, row in df.head(20).iterrows():
            label = html_module.escape(str(row.get(name_field, "")))
            items_html += f"<li>{label}</li>\n"
        title = html_module.escape(reference_name.title())
        return f"""
<div style="padding:8px;font-family:system-ui,sans-serif;font-size:13px;">
  <h4 style="margin:0 0 8px">{title}</h4>
  <ul style="margin:0;padding-left:16px;list-style:disc">{items_html}</ul>
</div>"""

    # ------------------------------------------------------------------
    # Branche GENERAL INFO
    # ------------------------------------------------------------------

    def _render_general_info(
        self,
        reference_name: str,
        entity_id: str | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        if not db:
            return self._info_html("Base de données non configurée")

        try:
            from niamoto.gui.api.services.templates.suggestion_service import (
                generate_general_info_suggestion,
            )

            suggestion = generate_general_info_suggestion(reference_name)
            if not suggestion:
                return self._info_html(f"Aucun champ détecté pour '{reference_name}'")

            field_configs = suggestion["config"]["fields"]

            # Trouver la table de référence
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
                    return self._info_html(f"Table '{reference_name}' non trouvée")

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(ref_table)
            col_names = [c.lower() for c in self._get_column_names(db, quoted_table)]

            # Détecter le champ ID
            singular = (
                reference_name.rstrip("s")
                if reference_name.endswith("s")
                else reference_name
            )
            id_candidates = [
                "id",
                f"id_{singular}",
                f"{singular}_id",
                f"id_{reference_name}",
                f"{reference_name}_id",
            ]
            id_field = next((c for c in id_candidates if c in col_names), None)
            if not id_field:
                id_field = next(
                    (c for c in col_names if c == "id" or c.endswith("_id")),
                    "id",
                )

            # Charger une entité sample
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
                return self._info_html(f"Aucune donnée dans '{reference_name}'")

            row = sample_df.iloc[0]

            # Construire les données pour info_grid
            items: list[dict[str, Any]] = []
            for field_cfg in field_configs:
                field_name = field_cfg.get("field", "")
                label = field_cfg.get("label", field_name.replace("_", " ").title())
                units = field_cfg.get("units", "")

                value = row.get(field_name)
                if pd.isna(value):
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

            # Rendre via info_grid
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
                # Valider via le schéma Pydantic du plugin
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
                logger.warning("Erreur rendu info_grid: %s", e)
                return self._render_general_info_fallback(items, reference_name)

        except Exception as e:
            logger.exception("Erreur preview general_info: %s", e)
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
    # Branche ENTITY MAP
    # ------------------------------------------------------------------

    def _render_entity_map(
        self,
        template_id: str,
        entity_id: str | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        """Rendu de carte entité via MapRenderer.render (classmethod)."""
        from niamoto.gui.api.services.map_renderer import (
            MapConfig,
            MapRenderer,
            MapStyle,
        )

        if not db:
            return self._error_html("Base de données non trouvée")

        try:
            # Parser le template_id
            if template_id.endswith("_entity_map"):
                mode = "single"
                prefix = template_id[:-11]
            elif template_id.endswith("_all_map"):
                mode = "all"
                prefix = template_id[:-8]
            else:
                return self._error_html(f"Format entity map invalide: {template_id}")

            parts = prefix.split("_")
            if len(parts) < 2:
                return self._error_html(f"Impossible de parser: {template_id}")

            reference = parts[0]
            geom_col = "_".join(parts[1:])

            entity_table = resolve_reference_table(db, reference)
            if not entity_table:
                return self._info_html(f"Table '{reference}' non trouvée")

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(entity_table)
            col_names = self._get_column_names(db, quoted_table)

            # Résoudre la colonne géométrique
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
                return self._info_html(f"Colonne géométrique '{geom_col}' non trouvée")

            # Détecter les champs nom et id
            name_candidates = [
                "full_name",
                "name",
                "plot",
                "label",
                "title",
                reference,
            ]
            name_field = next((c for c in name_candidates if c in col_names), None)
            if not name_field:
                name_field = next((c for c in col_names if "name" in c.lower()), "id")

            singular = reference.rstrip("s") if reference.endswith("s") else reference
            id_candidates = [
                f"id_{singular}",
                f"{singular}_id",
                f"id_{reference}",
                f"{reference}_id",
                "id",
            ]
            id_field = next((c for c in id_candidates if c in col_names), None)
            if not id_field:
                id_field = next(
                    (c for c in col_names if c.lower().startswith("id")),
                    col_names[0] if col_names else "id",
                )

            quoted_geom = preparer.quote(actual_geom_col)
            quoted_id = preparer.quote(id_field)
            quoted_name = preparer.quote(name_field)

            # Construire la requête selon le mode
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
                return self._info_html("Pas de données géographiques disponibles")

            # Convertir en GeoJSON
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

            if not features:
                return self._info_html("Pas de géométrie valide trouvée")

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
            logger.exception("Erreur preview entity_map: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Branche STANDARD (configured / dynamic / class_object / occurrence)
    # ------------------------------------------------------------------

    def _render_standard(
        self,
        request: PreviewRequest,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        """Gère les cas 4-7 : configured widget, dynamic, class_object, occurrence."""
        template_id = request.template_id
        group_by = request.group_by
        source = request.source
        entity_id = request.entity_id

        # Tenter de charger un widget configuré (transform.yml)
        detected_group_by = group_by
        if not detected_group_by:
            detected_group_by = find_widget_group(template_id)

        if detected_group_by:
            configured = load_configured_widget(template_id, detected_group_by)
            if configured:
                return self._render_configured_widget(
                    configured, detected_group_by, entity_id, db, warnings
                )

        # Parser le template_id dynamique
        parsed = parse_dynamic_template_id(template_id)
        if not parsed:
            return self._error_html(f"Format de template_id invalide: '{template_id}'")

        # Vérifier si la source est dans transform.yml
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

        # Charger les params widget depuis export.yml
        export_params = None
        if group_by:
            export_params = load_widget_params_from_export(template_id, group_by)

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
        if data_source != "occurrences":
            return self._render_entity_source(
                data_source,
                column,
                transformer,
                widget_plugin,
                group_by,
                entity_id,
                export_params,
                db,
                warnings,
            )

        # --- Occurrence (standard) ---
        return self._render_occurrence(
            column,
            transformer,
            widget_plugin,
            data_source,
            group_by,
            entity_id,
            export_params,
            db,
            warnings,
        )

    # ------------------------------------------------------------------
    # Sous-branche : Configured widget (transform.yml)
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

        # Vérifier le plugin widget
        try:
            PluginRegistry.get_plugin(widget_plugin, PluginType.WIDGET)
        except Exception:
            return self._error_html(f"Plugin widget '{widget_plugin}' non trouvé")

        if not db:
            return self._info_html("Base de données non configurée")

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

            # Flow standard (occurrence ou entity)
            data_source = transformer_params.get("source", "occurrences")
            if data_source and data_source != "occurrences":
                entity_table = resolve_entity_table(db, data_source, kind=None)
                if not entity_table or not db.has_table(entity_table):
                    return self._info_html(
                        f"Pas de table trouvée pour la source '{data_source}'"
                    )

                preparer = inspect(db.engine).dialect.identifier_preparer
                quoted = preparer.quote(entity_table)

                # Charger un échantillon
                entity_cols = self._get_column_names(db, quoted)
                where_clauses: list[str] = []
                params: dict[str, Any] = {}
                if entity_id and "id" in entity_cols:
                    where_clauses.append(f"{preparer.quote('id')} = :entity_id")
                    params["entity_id"] = str(entity_id)

                query = f"SELECT * FROM {quoted}"
                if where_clauses:
                    query += f" WHERE {' AND '.join(where_clauses)}"
                query += " LIMIT 1"
                sample_data = pd.read_sql(text(query), db.engine, params=params or None)
            else:
                import_config = load_import_config(self._work_dir)
                hierarchy_info = get_hierarchy_info(import_config, group_by)
                if entity_id:
                    representative = find_entity_by_id(db, hierarchy_info, entity_id)
                else:
                    representative = find_representative_entity(db, hierarchy_info)
                sample_data = load_sample_data(db, representative, transformer_params)

            if sample_data.empty:
                return self._info_html("Pas de données disponibles")

            # Exécuter le transformer
            effective_params = dict(transformer_params)
            if data_source != "occurrences":
                entity_table_name = resolve_entity_table(db, data_source, kind=None)
                if entity_table_name and effective_params.get("source") == data_source:
                    effective_params["source"] = entity_table_name
                if transformer_plugin == "field_aggregator":
                    for field_cfg in effective_params.get("fields", []):
                        if (
                            isinstance(field_cfg, dict)
                            and field_cfg.get("source") == data_source
                            and entity_table_name
                        ):
                            field_cfg["source"] = entity_table_name

            transform_config = {
                "plugin": transformer_plugin,
                "params": effective_params,
            }
            if "id" in sample_data.columns and not sample_data.empty:
                group_id = sample_data["id"].iloc[0]
                if hasattr(group_id, "item"):
                    group_id = group_id.item()
                transform_config["group_id"] = group_id

            transform_input: Any = sample_data
            if transformer_plugin == "field_aggregator":
                transform_input = {"main": sample_data}
                for field_cfg in effective_params.get("fields", []):
                    if isinstance(field_cfg, dict) and field_cfg.get("source"):
                        transform_input[field_cfg["source"]] = sample_data

            transformer_cls = PluginRegistry.get_plugin(
                transformer_plugin, PluginType.TRANSFORMER
            )
            transformer_inst = transformer_cls(db=db)
            result = transformer_inst.transform(transform_input, transform_config)

            # Adapter le format transformer → widget si nécessaire
            result = _preprocess_data_for_widget(
                result, transformer_plugin, widget_plugin
            )

            # Rendu widget
            return render_widget(db, widget_plugin, result, widget_params, widget_title)

        except Exception as e:
            logger.exception("Erreur preview configured widget: %s", e)
            return self._error_html(str(e))

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
        """Rendu d'un widget configuré basé sur class_object (CSV)."""
        class_objects = _extract_class_objects_from_params(transformer_params)
        if not class_objects:
            return self._info_html("Pas de class_objects configurés")

        co_data = {}
        for co_name in class_objects:
            data = load_class_object_data_for_preview(self._work_dir, co_name, group_by)
            if data:
                co_data[co_name] = data

        if not co_data:
            return self._info_html(
                f"Données non trouvées pour: {', '.join(class_objects)}"
            )

        result = _execute_configured_transformer(
            transformer_plugin, transformer_params, co_data, group_by
        )
        if not result:
            return self._info_html("Le transformer n'a pas retourné de données")

        # Fusionner les params d'affichage du transform.yml avec les
        # widget_params de l'export.yml — les champs comme x_axis, y_axis,
        # orientation, sort_order, auto_color sont dans transformer_params
        # mais doivent être transmis au widget.
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

        return _render_widget_for_configured(
            db,
            widget_plugin,
            result,
            transformer_plugin,
            widget_title,
            merged_params,
        )

    # ------------------------------------------------------------------
    # Sous-branche : Class object (CSV, dynamic)
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
            return self._info_html(
                f"Données '{column}' non trouvées dans les sources CSV"
            )

        try:
            title = column.replace("_", " ").title()
            return _render_widget_for_class_object(
                db, widget_plugin, co_data, transformer, title
            )
        except Exception as e:
            logger.exception("Erreur preview class_object: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Sous-branche : Entity source (non-occurrence)
    # ------------------------------------------------------------------

    def _render_entity_source(
        self,
        data_source: str,
        column: str,
        transformer_plugin: str,
        widget_plugin: str,
        group_by: str | None,
        entity_id: str | None,
        export_params: dict[str, Any] | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        if not db:
            return self._error_html("Base de données non trouvée")

        try:
            entity_table = resolve_entity_table(db, data_source, kind=None)
            if not entity_table or not db.has_table(entity_table):
                return self._info_html(f"Pas de table pour la source '{data_source}'")

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(entity_table)
            entity_columns = set(self._get_column_names(db, quoted_table))

            if column not in entity_columns:
                return self._info_html(
                    f"Champ '{column}' non trouvé dans {entity_table}"
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
                return self._info_html(
                    f"Pas de données pour '{column}' dans {entity_table}"
                )

            # Construire la config et exécuter le transformer
            config = {
                "source": data_source,
                "field": column,
            }

            transform_input: Any = sample_data
            if transformer_plugin == "field_aggregator":
                transform_input = {data_source: sample_data}

            result = execute_transformer(
                db, transformer_plugin, config, transform_input
            )

            # Adapter le format transformer → widget si nécessaire
            result = _preprocess_data_for_widget(
                result, transformer_plugin, widget_plugin
            )

            title = column.replace("_", " ").title()
            widget_html = render_widget(db, widget_plugin, result, export_params, title)
            return widget_html

        except Exception as e:
            logger.exception("Erreur preview entity source: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Sous-branche : Occurrence (standard)
    # ------------------------------------------------------------------

    def _render_occurrence(
        self,
        column: str,
        transformer_plugin: str,
        widget_plugin: str,
        data_source: str,
        group_by: str | None,
        entity_id: str | None,
        export_params: dict[str, Any] | None,
        db: Database | None,
        warnings: list[str],
    ) -> str:
        if not db:
            return self._error_html("Base de données non trouvée")

        try:
            import_config = load_import_config(self._work_dir)
            hierarchy_info = get_hierarchy_info(import_config, group_by)

            if entity_id:
                representative = find_entity_by_id(db, hierarchy_info, entity_id)
            else:
                representative = find_representative_entity(db, hierarchy_info)

            config = {
                "source": data_source,
                "field": column,
            }

            sample_data = load_sample_data(db, representative, config)
            if sample_data.empty:
                return self._info_html("Pas de données disponibles")

            result = execute_transformer(db, transformer_plugin, config, sample_data)

            # Adapter le format transformer → widget si nécessaire
            result = _preprocess_data_for_widget(
                result, transformer_plugin, widget_plugin
            )

            title = column.replace("_", " ").title()
            widget_html = render_widget(db, widget_plugin, result, export_params, title)
            return widget_html

        except Exception as e:
            logger.exception("Erreur preview occurrence: %s", e)
            return self._error_html(str(e))

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _open_db(self) -> Database | None:
        """Ouvrir la base de données en lecture seule."""
        if not os.path.exists(self._db_path):
            return None
        return Database(self._db_path)


# --------------------------------------------------------------------------
# Factory (thread-safe)
# --------------------------------------------------------------------------

_engine_lock = threading.Lock()
_engine_instance: PreviewEngine | None = None


def get_preview_engine() -> PreviewEngine | None:
    """Retourne l'instance partagée du moteur de preview.

    Créée paresseusement à la première requête (double-checked locking).
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
    """Réinitialiser l'instance -- utile après changement de projet."""
    global _engine_instance, _plugins_loaded
    with _engine_lock:
        _engine_instance = None
        _plugins_loaded = False
