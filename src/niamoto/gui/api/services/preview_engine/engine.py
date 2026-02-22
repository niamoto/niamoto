"""Moteur de preview unifié pour les widgets Niamoto.

Pipeline synchrone : resolve → load → transform → render → wrap.
Appelé depuis les endpoints via `await run_in_threadpool(engine.render, req)`.

Utilise les mêmes utilitaires que templates.py pour la résolution,
le chargement de données, la transformation et le rendu.
"""

import hashlib
import html as html_module
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from niamoto.gui.api.services.preview_service import PreviewService
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


def _ensure_plugins_loaded() -> None:
    """Charger les plugins transformer et widget si nécessaire."""
    from niamoto.core.plugins.transformers.distribution import (  # noqa: F401
        binned_distribution,
        categorical_distribution,
    )
    from niamoto.core.plugins.transformers import (  # noqa: F401
        binary_counter,
        field_aggregator,
        geospatial_extractor,
        statistical_summary,
        top_ranking,
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


class PreviewEngine:
    """Moteur de preview unifié — un seul pipeline pour tous les types de widgets.

    Le moteur est synchrone (I/O fichiers + DB). Les endpoints l'appellent
    via ``await run_in_threadpool(engine.render, req)``.
    """

    def __init__(self, db_path: str, config_dir: str):
        self._db_path = db_path
        self._config_dir = config_dir
        self._work_dir = Path(config_dir).parent
        self._data_fingerprint: str = self._compute_data_fingerprint()
        # Cache assets navigation (chargés une seule fois)
        self._nav_css: Optional[str] = None
        self._nav_js: Optional[str] = None

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def render(self, request: PreviewRequest) -> PreviewResult:
        """Point d'entrée unique — résout, charge, transforme, rend, emballe."""
        _ensure_plugins_loaded()

        warnings: List[str] = []
        template_id = request.template_id

        # --- Inline (POST) : transformer + widget explicites ---
        if request.inline:
            widget_html = self._render_inline(request, warnings)
            return self._build_result(request, widget_html, warnings)

        if not template_id:
            return self._error_result(request, "template_id requis", warnings)

        # --- Branche 1 : Navigation widget ---
        if template_id.endswith("_hierarchical_nav_widget"):
            reference = template_id.replace("_hierarchical_nav_widget", "")
            widget_html = self._render_navigation(reference, warnings)
            return self._build_result(request, widget_html, warnings)

        # --- Branche 2 : General info widget ---
        if template_id.startswith("general_info_") and template_id.endswith(
            "_field_aggregator_info_grid"
        ):
            reference = template_id.replace("general_info_", "").replace(
                "_field_aggregator_info_grid", ""
            )
            widget_html = self._render_general_info(
                reference, request.entity_id, warnings
            )
            return self._build_result(request, widget_html, warnings)

        # --- Branche 3 : Entity map ---
        if template_id.endswith("_entity_map") or template_id.endswith("_all_map"):
            widget_html = self._render_entity_map(
                template_id, request.entity_id, warnings
            )
            return self._build_result(request, widget_html, warnings)

        # --- Branche 4-7 : Configured / Dynamic / Class object / Occurrence ---
        widget_html = self._render_standard(request, warnings)
        return self._build_result(request, widget_html, warnings)

    def invalidate(self) -> None:
        """Recalcule le fingerprint — appelé après import ou save config."""
        self._data_fingerprint = self._compute_data_fingerprint()

    # ------------------------------------------------------------------
    # Construction du résultat
    # ------------------------------------------------------------------

    def _build_result(
        self,
        request: PreviewRequest,
        widget_html: str,
        warnings: List[str],
    ) -> PreviewResult:
        html = self._wrap_html(widget_html, mode=request.mode)
        etag = self._compute_etag(request)
        preview_key = request.template_id or "inline"
        return PreviewResult(
            html=html,
            etag=etag,
            preview_key=preview_key,
            warnings=tuple(warnings),
        )

    def _error_result(
        self, request: PreviewRequest, message: str, warnings: List[str]
    ) -> PreviewResult:
        error_html = f"<p class='error'>{html_module.escape(message)}</p>"
        return self._build_result(request, error_html, warnings)

    def _info_html(self, message: str) -> str:
        return f"<p class='info'>{html_module.escape(message)}</p>"

    def _error_html(self, message: str) -> str:
        return f"<p class='error'>{html_module.escape(message)}</p>"

    # ------------------------------------------------------------------
    # ETag / fingerprint
    # ------------------------------------------------------------------

    def _compute_data_fingerprint(self) -> str:
        """Empreinte mtime(DB) + mtime(configs). Zéro I/O entre invalidate()."""
        parts: List[str] = []
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

    def _wrap_html(self, content: str, mode: PreviewMode = "full") -> str:
        """Document HTML complet pour injection dans un iframe via srcDoc."""
        plotly_src = "/api/site/assets/js/vendor/plotly/3.0.1_plotly.min.js"
        static_plot_js = ""
        if mode == "thumbnail":
            static_plot_js = """
    <script>
        // Mode thumbnail : désactiver l'interactivité Plotly
        window.__NIAMOTO_THUMBNAIL__ = true;
    </script>"""

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Preview</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: system-ui, -apple-system, sans-serif;
            background: transparent;
        }}
        .plotly-graph-div {{
            width: 100% !important;
            height: 100% !important;
        }}
        .error {{
            color: #ef4444;
            padding: 1rem;
            text-align: center;
        }}
        .info {{
            color: #6b7280;
            padding: 1rem;
            text-align: center;
        }}
    </style>
    <script>
        window.__NIAMOTO_PREVIEW__ = true;
    </script>{static_plot_js}
    <script src="{plotly_src}"></script>
</head>
<body>
{content}
</body>
</html>"""

    # ------------------------------------------------------------------
    # Branche INLINE (POST)
    # ------------------------------------------------------------------

    def _render_inline(
        self, request: PreviewRequest, warnings: List[str]
    ) -> str:
        inline = request.inline
        if not inline:
            return self._info_html("Configuration inline manquante")

        transformer_plugin = inline.get("transformer_plugin", "")
        transformer_params = inline.get("transformer_params", {})
        widget_plugin = inline.get("widget_plugin", "")
        widget_params = inline.get("widget_params")
        widget_title = inline.get("widget_title", "Preview")
        group_by = request.group_by or ""

        db = self._open_db()
        try:
            html = PreviewService.generate_preview(
                db=db,
                work_dir=self._work_dir,
                group_by=group_by,
                transformer_plugin=transformer_plugin,
                transformer_params=transformer_params,
                widget_plugin=widget_plugin,
                widget_params=widget_params,
                widget_title=widget_title,
            )
            # generate_preview retourne du HTML wrappé — extraire le body
            # Pour éviter un double wrapping, on retourne le HTML directement
            # et on skip le _wrap_html dans _build_result
            return self._extract_body(html)
        except Exception as e:
            logger.exception(f"Erreur preview inline: {e}")
            return self._error_html(str(e))
        finally:
            if db:
                db.close_db_session()

    def _extract_body(self, full_html: str) -> str:
        """Extrait le contenu <body> d'un document HTML complet."""
        body_start = full_html.find("<body>")
        body_end = full_html.find("</body>")
        if body_start >= 0 and body_end >= 0:
            return full_html[body_start + 6 : body_end].strip()
        return full_html

    # ------------------------------------------------------------------
    # Branche NAVIGATION
    # ------------------------------------------------------------------

    def _render_navigation(
        self, reference_name: str, warnings: List[str]
    ) -> str:
        db = self._open_db()
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
                id_field = next(
                    (c for c in columns if "id" in c.lower()), "id"
                )

            # Champ nom
            name_candidates = ["full_name", "name", "plot", "label", "title"]
            name_field = next(
                (c for c in name_candidates if c in columns), id_field
            )

            # Requête sample
            if is_hierarchical and has_nested_set:
                query = text(
                    f"SELECT {safe_sql} FROM {quoted} "
                    f'WHERE {quote_identifier(db, "level")} <= 3 '
                    f'ORDER BY {quote_identifier(db, "lft")} LIMIT 50'
                )
            elif is_hierarchical and has_parent:
                query = text(
                    f"SELECT {safe_sql} FROM {quoted} "
                    f'WHERE {quote_identifier(db, "level")} <= 3 LIMIT 50'
                )
            else:
                query = text(f"SELECT {safe_sql} FROM {quoted} LIMIT 30")

            df = pd.read_sql(query, db.engine)
            if df.empty:
                return self._info_html(
                    f"Aucune donnée dans '{reference_name}'"
                )

            # Rendu via le plugin widget
            try:
                plugin_class = PluginRegistry.get_plugin(
                    "hierarchical_nav_widget", PluginType.WIDGET
                )
                plugin_instance = plugin_class(db=db)

                widget_params = {
                    "title": f"Navigation - {reference_name.title()}",
                    "referential_data": reference_name,
                    "id_field": id_field,
                    "label_field": name_field,
                    "parent_field": "parent_id" if has_parent else None,
                    "level_field": "level" if has_level else None,
                }

                data = {
                    "items": df.to_dict("records"),
                    "total_count": len(df),
                    "reference_name": reference_name,
                    "is_hierarchical": is_hierarchical,
                    "id_field": id_field,
                    "label_field": name_field,
                }

                return plugin_instance.render(data, widget_params)
            except Exception as e:
                logger.warning(
                    "Plugin hierarchical_nav_widget indisponible: %s", e
                )
                return self._render_navigation_fallback(
                    df, reference_name, id_field, name_field, is_hierarchical
                )
        except Exception as e:
            logger.exception("Erreur preview navigation: %s", e)
            return self._error_html(str(e))
        finally:
            db.close_db_session()

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
        entity_id: Optional[str],
        warnings: List[str],
    ) -> str:
        db = self._open_db()
        if not db:
            return self._info_html("Base de données non configurée")

        try:
            from niamoto.gui.api.services.templates.suggestion_service import (
                generate_general_info_suggestion,
            )

            suggestion = generate_general_info_suggestion(reference_name)
            if not suggestion:
                return self._info_html(
                    f"Aucun champ détecté pour '{reference_name}'"
                )

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
                    return self._info_html(
                        f"Table '{reference_name}' non trouvée"
                    )

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(ref_table)
            col_names = [
                c.lower()
                for c in pd.read_sql(
                    text(f"SELECT * FROM {quoted_table} LIMIT 0"), db.engine
                ).columns
            ]

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
            id_field = next(
                (c for c in id_candidates if c in col_names), None
            )
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
                return self._info_html(
                    f"Aucune donnée dans '{reference_name}'"
                )

            row = sample_df.iloc[0]

            # Construire les données pour info_grid
            items: List[Dict[str, Any]] = []
            for field_cfg in field_configs:
                field_name = field_cfg.get("field", "")
                label = field_cfg.get("label", field_name.replace("_", " ").title())
                units = field_cfg.get("units", "")

                value = row.get(field_name)
                if pd.isna(value):
                    value = None
                elif hasattr(value, "item"):
                    value = value.item()

                items.append({
                    "label": label,
                    "value": value,
                    "units": units,
                })

            # Rendre via info_grid
            try:
                plugin_class = PluginRegistry.get_plugin(
                    "info_grid", PluginType.WIDGET
                )
                plugin_instance = plugin_class(db=db)
                widget_data = {
                    field_cfg.get("target", field_cfg.get("field", f"field_{i}")): {
                        "value": item["value"],
                        "units": item.get("units", ""),
                    }
                    for i, (field_cfg, item) in enumerate(
                        zip(field_configs, items)
                    )
                }
                widget_params = {
                    "title": f"Informations - {reference_name.title()}",
                    "items": items,
                    "grid_columns": 2,
                }
                return plugin_instance.render(widget_data, widget_params)
            except Exception as e:
                logger.warning("Erreur rendu info_grid: %s", e)
                return self._render_general_info_fallback(items, reference_name)

        except Exception as e:
            logger.exception("Erreur preview general_info: %s", e)
            return self._error_html(str(e))
        finally:
            db.close_db_session()

    def _render_general_info_fallback(
        self, items: List[Dict[str, Any]], reference_name: str
    ) -> str:
        rows = ""
        for item in items[:8]:
            label = html_module.escape(str(item.get("label", "")))
            value = html_module.escape(str(item.get("value", "—")))
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
        entity_id: Optional[str],
        warnings: List[str],
    ) -> str:
        """Rendu de carte entité. Délègue au MapRenderer existant."""
        from niamoto.gui.api.services.map_renderer import MapRenderer

        db = self._open_db()
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
                return self._error_html(
                    f"Format entity map invalide: {template_id}"
                )

            parts = prefix.split("_")
            if len(parts) < 2:
                return self._error_html(
                    f"Impossible de parser: {template_id}"
                )

            reference = parts[0]
            geom_col = "_".join(parts[1:])

            entity_table = resolve_reference_table(db, reference)
            if not entity_table:
                return self._info_html(
                    f"Table '{reference}' non trouvée"
                )

            # Vérifier que la colonne géométrie existe
            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(entity_table)
            col_names = pd.read_sql(
                text(f"SELECT * FROM {quoted_table} LIMIT 0"), db.engine
            ).columns.tolist()

            # Résoudre la colonne géométrique
            actual_geom_col = None
            if geom_col in col_names:
                actual_geom_col = geom_col
            elif f"{geom_col}_geom" in col_names:
                actual_geom_col = f"{geom_col}_geom"
            else:
                # Fallback : première colonne géométrique
                for c in col_names:
                    if c.endswith("_geom") or c in ("geometry", "geom"):
                        actual_geom_col = c
                        break

            if not actual_geom_col:
                return self._info_html(
                    f"Colonne géométrique '{geom_col}' non trouvée"
                )

            # Charger les données
            try:
                renderer = MapRenderer(db)
                map_html = renderer.render_entity_map(
                    entity_table=entity_table,
                    geom_column=actual_geom_col,
                    entity_id=entity_id,
                    mode=mode,
                )
                return map_html
            except Exception as e:
                logger.warning("MapRenderer indisponible, fallback: %s", e)
                return self._info_html(
                    f"Carte pour '{reference}' (colonne: {actual_geom_col})"
                )

        except Exception as e:
            logger.exception("Erreur preview entity_map: %s", e)
            return self._error_html(str(e))
        finally:
            db.close_db_session()

    # ------------------------------------------------------------------
    # Branche STANDARD (configured / dynamic / class_object / occurrence)
    # ------------------------------------------------------------------

    def _render_standard(
        self, request: PreviewRequest, warnings: List[str]
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
                    configured, detected_group_by, entity_id, warnings
                )

        # Parser le template_id dynamique
        parsed = parse_dynamic_template_id(template_id)
        if not parsed:
            return self._error_html(
                f"Format de template_id invalide: '{template_id}'"
            )

        # Vérifier si la source est dans transform.yml
        effective_source = source
        if not effective_source:
            cfg_group = group_by or find_widget_group(template_id)
            if cfg_group:
                configured = load_configured_widget(template_id, cfg_group)
                if configured:
                    cfg_source = (
                        configured.get("transformer_params") or {}
                    ).get("source")
                    if (
                        cfg_source
                        and cfg_source != "occurrences"
                        and not is_class_object_template(parsed["transformer"])
                    ):
                        return self._render_configured_widget(
                            configured, cfg_group, entity_id, warnings
                        )

        # Charger les params widget depuis export.yml
        export_params = None
        if group_by:
            export_params = load_widget_params_from_export(
                template_id, group_by
            )

        column = parsed["column"]
        transformer = parsed["transformer"]
        widget_plugin = parsed["widget"]
        data_source = effective_source or "occurrences"

        # --- Class object (CSV) ---
        if is_class_object_template(transformer):
            return self._render_class_object(
                column, transformer, widget_plugin, group_by, warnings
            )

        # --- Entity table (non-occurrence) ---
        if data_source != "occurrences":
            return self._render_entity_source(
                data_source, column, transformer, widget_plugin,
                group_by, entity_id, export_params, warnings,
            )

        # --- Occurrence (standard) ---
        return self._render_occurrence(
            column, transformer, widget_plugin, data_source,
            group_by, entity_id, export_params, warnings,
        )

    # ------------------------------------------------------------------
    # Sous-branche : Configured widget (transform.yml)
    # ------------------------------------------------------------------

    def _render_configured_widget(
        self,
        configured: Dict[str, Any],
        group_by: str,
        entity_id: Optional[str],
        warnings: List[str],
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
            return self._error_html(
                f"Plugin widget '{widget_plugin}' non trouvé"
            )

        db = self._open_db()
        try:
            if transformer_plugin.startswith("class_object_"):
                return self._render_configured_class_object(
                    db, transformer_plugin, transformer_params,
                    widget_plugin, widget_params, widget_title,
                    group_by, warnings,
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
                entity_cols = pd.read_sql(
                    text(f"SELECT * FROM {quoted} LIMIT 0"), db.engine
                ).columns.tolist()
                where_clauses: List[str] = []
                params: Dict[str, Any] = {}
                if entity_id and "id" in entity_cols:
                    where_clauses.append(f"{preparer.quote('id')} = :entity_id")
                    params["entity_id"] = str(entity_id)

                query = f"SELECT * FROM {quoted}"
                if where_clauses:
                    query += f" WHERE {' AND '.join(where_clauses)}"
                query += " LIMIT 1"
                sample_data = pd.read_sql(
                    text(query), db.engine, params=params or None
                )
            else:
                import_config = load_import_config(self._work_dir)
                hierarchy_info = get_hierarchy_info(import_config, group_by)
                if entity_id:
                    representative = find_entity_by_id(
                        db, hierarchy_info, entity_id
                    )
                else:
                    representative = find_representative_entity(
                        db, hierarchy_info
                    )
                sample_data = load_sample_data(
                    db, representative, transformer_params
                )

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

            # Rendu widget
            return PreviewService.render_widget(
                db, widget_plugin, result, widget_params, widget_title
            )

        except Exception as e:
            logger.exception("Erreur preview configured widget: %s", e)
            return self._error_html(str(e))
        finally:
            if db:
                db.close_db_session()

    def _render_configured_class_object(
        self,
        db: Optional[Database],
        transformer_plugin: str,
        transformer_params: Dict[str, Any],
        widget_plugin: str,
        widget_params: Optional[Dict[str, Any]],
        widget_title: str,
        group_by: str,
        warnings: List[str],
    ) -> str:
        """Rendu d'un widget configuré basé sur class_object (CSV)."""
        from niamoto.gui.api.routers.templates import (
            _extract_class_objects_from_params,
            _execute_configured_transformer,
            _render_widget_for_configured,
        )

        class_objects = _extract_class_objects_from_params(transformer_params)
        if not class_objects:
            return self._info_html("Pas de class_objects configurés")

        co_data = {}
        for co_name in class_objects:
            data = load_class_object_data_for_preview(
                self._work_dir, co_name, group_by
            )
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

        return _render_widget_for_configured(
            db, widget_plugin, result, transformer_plugin,
            widget_title, widget_params,
        )

    # ------------------------------------------------------------------
    # Sous-branche : Class object (CSV, dynamic)
    # ------------------------------------------------------------------

    def _render_class_object(
        self,
        column: str,
        transformer: str,
        widget_plugin: str,
        group_by: Optional[str],
        warnings: List[str],
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

        db = self._open_db()
        try:
            from niamoto.gui.api.routers.templates import (
                _render_widget_for_class_object,
            )

            title = column.replace("_", " ").title()
            return _render_widget_for_class_object(
                db, widget_plugin, co_data, transformer, title
            )
        except Exception as e:
            logger.exception("Erreur preview class_object: %s", e)
            return self._error_html(str(e))
        finally:
            if db:
                db.close_db_session()

    # ------------------------------------------------------------------
    # Sous-branche : Entity source (non-occurrence)
    # ------------------------------------------------------------------

    def _render_entity_source(
        self,
        data_source: str,
        column: str,
        transformer_plugin: str,
        widget_plugin: str,
        group_by: Optional[str],
        entity_id: Optional[str],
        export_params: Optional[Dict[str, Any]],
        warnings: List[str],
    ) -> str:
        db = self._open_db()
        if not db:
            return self._error_html("Base de données non trouvée")

        try:
            entity_table = resolve_entity_table(db, data_source, kind=None)
            if not entity_table or not db.has_table(entity_table):
                return self._info_html(
                    f"Pas de table pour la source '{data_source}'"
                )

            preparer = inspect(db.engine).dialect.identifier_preparer
            quoted_table = preparer.quote(entity_table)
            entity_columns = set(
                pd.read_sql(
                    text(f"SELECT * FROM {quoted_table} LIMIT 0"), db.engine
                ).columns.tolist()
            )

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

            result = PreviewService.execute_transformer(
                db, transformer_plugin, config, transform_input
            )

            title = column.replace("_", " ").title()
            widget_html = PreviewService.render_widget(
                db, widget_plugin, result, export_params, title
            )
            return widget_html

        except Exception as e:
            logger.exception("Erreur preview entity source: %s", e)
            return self._error_html(str(e))
        finally:
            db.close_db_session()

    # ------------------------------------------------------------------
    # Sous-branche : Occurrence (standard)
    # ------------------------------------------------------------------

    def _render_occurrence(
        self,
        column: str,
        transformer_plugin: str,
        widget_plugin: str,
        data_source: str,
        group_by: Optional[str],
        entity_id: Optional[str],
        export_params: Optional[Dict[str, Any]],
        warnings: List[str],
    ) -> str:
        db = self._open_db()
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

            result = PreviewService.execute_transformer(
                db, transformer_plugin, config, sample_data
            )

            title = column.replace("_", " ").title()
            widget_html = PreviewService.render_widget(
                db, widget_plugin, result, export_params, title
            )
            return widget_html

        except Exception as e:
            logger.exception("Erreur preview occurrence: %s", e)
            return self._error_html(str(e))
        finally:
            db.close_db_session()

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def _open_db(self) -> Optional[Database]:
        """Ouvrir la base de données en lecture seule."""
        if not os.path.exists(self._db_path):
            return None
        return Database(self._db_path, read_only=True)


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------

_engine_instance: Optional[PreviewEngine] = None


def get_preview_engine() -> Optional[PreviewEngine]:
    """Retourne l'instance partagée du moteur de preview.

    Créée paresseusement à la première requête.
    """
    global _engine_instance
    if _engine_instance is not None:
        return _engine_instance

    db_path = get_database_path()
    work_dir = get_working_directory()

    if not db_path:
        return None

    config_dir = str(work_dir / "config") if work_dir else ""
    _engine_instance = PreviewEngine(
        db_path=str(db_path),
        config_dir=config_dir,
    )
    return _engine_instance


def reset_preview_engine() -> None:
    """Réinitialiser l'instance — utile après changement de projet."""
    global _engine_instance
    _engine_instance = None
