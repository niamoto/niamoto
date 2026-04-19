"""Pipeline status API — freshness/staleness tracking.

Returns the freshness status of each pipeline stage (data, groups, site,
publication) so the frontend can show what needs to be recalculated.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ValidationError

from niamoto.core.plugins.models import HtmlExporterParams
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.services.job_file_store import JobFileStore
from niamoto.gui.api.services.job_store_runtime import resolve_job_store

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class EntityStatus(BaseModel):
    name: str
    status: str  # "fresh", "stale", "never_run", "unconfigured", "error", "running"
    last_run_at: Optional[str] = None
    reason: Optional[str] = None


class StageStatus(BaseModel):
    status: str  # "fresh", "stale", "never_run", "unconfigured", "running"
    last_run_at: Optional[str] = None
    items: list[EntityStatus] = []
    summary: Optional[dict] = None
    last_job_duration_s: Optional[int] = None


class PipelineStatusResponse(BaseModel):
    data: StageStatus
    groups: StageStatus
    site: StageStatus
    publication: StageStatus
    running_job: Optional[dict] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config_hash(path: Path) -> Optional[str]:
    """MD5 hash of a config file, or None if missing."""
    if not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def _iso(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string, tolerant of None."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def _get_transform_group_configs(work_dir: Path) -> list[dict]:
    """Read transform.yml and return the list of group configs."""
    config_path = work_dir / "config" / "transform.yml"
    if not config_path.exists():
        return []
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if isinstance(config, list):
            return [g for g in config if isinstance(g, dict) and g.get("group_by")]
        return []
    except Exception:
        logger.exception("Error reading transform.yml")
        return []


def _get_transform_groups(work_dir: Path) -> list[str]:
    """Return the list of group_by names declared in transform.yml."""
    return [
        group.get("group_by", "default")
        for group in _get_transform_group_configs(work_dir)
    ]


def _has_configured_transform_widgets(group_config: dict) -> bool:
    """Return True when a transform group has widgets_data to compute.

    Auto-scaffolded groups exist as soon as data is imported, but they are not
    actually calculable until at least one transform widget is configured.
    """
    widgets_data = group_config.get("widgets_data")
    if isinstance(widgets_data, dict):
        return len(widgets_data) > 0
    if isinstance(widgets_data, list):
        return len(widgets_data) > 0
    return bool(widgets_data)


def _has_valid_site_export_params(export_entry: dict) -> bool:
    """Return True when an html_page_exporter has all required params."""
    try:
        HtmlExporterParams.model_validate(export_entry.get("params") or {})
    except ValidationError:
        return False
    return True


def _get_entities_last_updated() -> Optional[datetime]:
    """Query niamoto_metadata_entities for the most recent updated_at.

    This covers imports done via CLI (not tracked in job_file_store).
    """
    db_path = get_database_path()
    if not db_path or not db_path.exists():
        return None
    try:
        import duckdb

        con = duckdb.connect(str(db_path), read_only=True)
        result = con.sql(
            "SELECT MAX(updated_at) FROM niamoto_metadata_entities"
        ).fetchone()
        con.close()
        if result and result[0]:
            return result[0]
    except Exception:
        logger.debug("Could not read entity metadata", exc_info=True)
    return None


def _get_export_mtime(work_dir: Path) -> Optional[datetime]:
    """Check exports/web/index.html mtime as fallback for CLI exports."""
    index_html = work_dir / "exports" / "web" / "index.html"
    if index_html.exists():
        return datetime.fromtimestamp(index_html.stat().st_mtime)
    return None


def _get_data_summary() -> Optional[dict]:
    """Gather entity names with row counts from the database."""
    db_path = get_database_path()
    if not db_path or not db_path.exists():
        return None
    try:
        import duckdb

        con = duckdb.connect(str(db_path), read_only=True)
        rows = con.sql(
            "SELECT name, table_name FROM niamoto_metadata_entities ORDER BY name"
        ).fetchall()

        if not rows:
            con.close()
            return None

        entities = []
        for name, table_name in rows:
            try:
                count_row = con.sql(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                row_count = count_row[0] if count_row else 0
            except Exception:
                row_count = 0
            entities.append({"name": name, "row_count": row_count})

        con.close()
        return {"entities": entities}
    except Exception:
        logger.debug("Could not read entity summary", exc_info=True)
    return None


def _get_groups_summary(work_dir: Path) -> Optional[dict]:
    """Count entities per group from the database."""
    db_path = get_database_path()
    config_path = work_dir / "config" / "transform.yml"
    if not config_path.exists():
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if not isinstance(config, list):
            return None

        groups = []
        for group in config:
            if not isinstance(group, dict):
                continue
            name = group.get("group_by", "default")
            # Try to get entity count from the group results table
            entity_count = None
            if db_path and db_path.exists():
                try:
                    import duckdb

                    con = duckdb.connect(str(db_path), read_only=True)
                    result = con.sql(f'SELECT COUNT(*) FROM "{name}"').fetchone()
                    con.close()
                    entity_count = result[0] if result else None
                except Exception:
                    pass
            groups.append({"name": name, "entity_count": entity_count})

        return {"groups": groups}
    except Exception:
        logger.debug("Could not read groups summary", exc_info=True)
    return None


def _get_site_summary(work_dir: Path) -> Optional[dict]:
    """Extract site config summary from export.yml."""
    config_path = work_dir / "config" / "export.yml"
    if not config_path.exists():
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            export_config = yaml.safe_load(f)
        if not isinstance(export_config, dict):
            return None

        for exp in export_config.get("exports", []):
            if not isinstance(exp, dict):
                continue
            if exp.get("exporter") != "html_page_exporter":
                continue
            if not exp.get("enabled", True):
                continue

            params = exp.get("params", {})
            site = params.get("site", {})
            static_pages = exp.get("static_pages", [])

            languages = site.get("languages") or []
            lang = site.get("lang", "en")
            if not languages:
                languages = [lang]

            # Resolve title (may be localized dict or plain string)
            raw_title = site.get("title", "")
            if isinstance(raw_title, dict):
                title = raw_title.get(lang, next(iter(raw_title.values()), ""))
            else:
                title = str(raw_title) if raw_title else ""

            return {
                "title": title,
                "page_count": len(static_pages)
                if isinstance(static_pages, list)
                else 0,
                "language_count": len(languages),
                "languages": languages,
            }
        return None
    except Exception:
        logger.debug("Could not read site summary", exc_info=True)
    return None


def _get_publication_summary(work_dir: Path) -> Optional[dict]:
    """Count generated HTML files and total size in exports/web/."""
    web_dir = work_dir / "exports" / "web"
    if not web_dir.exists():
        return None
    try:
        html_files = list(web_dir.rglob("*.html"))
        if not html_files:
            return None
        total_bytes = sum(f.stat().st_size for f in web_dir.rglob("*") if f.is_file())
        return {
            "html_page_count": len(html_files),
            "total_size_mb": round(total_bytes / (1024 * 1024), 1),
        }
    except Exception:
        logger.debug("Could not read publication summary", exc_info=True)
    return None


def _job_duration_s(job: Optional[dict]) -> Optional[int]:
    """Compute duration in seconds from a completed job dict."""
    if not job:
        return None
    started = _iso(job.get("started_at"))
    completed = _iso(job.get("completed_at"))
    if started and completed:
        return max(int((completed - started).total_seconds()), 1)
    return None


def _compute_stage_status(items: list[EntityStatus]) -> str:
    """Derive aggregate status from item statuses."""
    if not items:
        return "never_run"
    statuses = {item.status for item in items}
    if statuses == {"never_run"}:
        return "never_run"
    if "running" in statuses:
        return "running"
    if "error" in statuses:
        return "stale"
    if "stale" in statuses or "never_run" in statuses:
        return "stale"
    return "fresh"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/history")
async def get_pipeline_history(
    http_request: Request,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    """Return the N most recent completed jobs (newest first).

    ``limit`` is clamped to [1, 100] to prevent unbounded slices or
    surprising responses when ``limit=0`` or negative values are passed.
    """
    try:
        job_store: Optional[JobFileStore] = resolve_job_store(http_request.app)
    except Exception:
        return []
    return job_store.get_history(limit=limit)


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(http_request: Request):
    """Return freshness status for every pipeline stage."""
    try:
        job_store: Optional[JobFileStore] = resolve_job_store(http_request.app)
    except Exception:
        return PipelineStatusResponse(
            data=StageStatus(status="never_run"),
            groups=StageStatus(status="never_run"),
            site=StageStatus(status="never_run"),
            publication=StageStatus(status="never_run"),
        )

    work_dir = get_working_directory()
    running = job_store.get_running_job()

    # ------------------------------------------------------------------
    # 1. DATA stage — last import (job store OR entity metadata fallback)
    # ------------------------------------------------------------------
    last_import = job_store.get_last_run("import", status="completed")
    last_import_at = last_import.get("completed_at") if last_import else None
    import_dt = _iso(last_import_at)

    # Fallback: if no GUI import job, check DB entity metadata (CLI imports)
    if not import_dt:
        entity_dt = _get_entities_last_updated()
        if entity_dt:
            import_dt = entity_dt
            last_import_at = entity_dt.isoformat()

    data_items: list[EntityStatus] = []
    if running and running.get("type") == "import":
        data_items.append(
            EntityStatus(name="import", status="running", reason="Import en cours")
        )

    data_summary = _get_data_summary()

    data_status = StageStatus(
        status="running"
        if (running and running.get("type") == "import")
        else ("fresh" if import_dt else "never_run"),
        last_run_at=last_import_at,
        items=data_items,
        summary=data_summary,
        last_job_duration_s=_job_duration_s(last_import),
    )

    # ------------------------------------------------------------------
    # 2. GROUPS stage — per-group transform freshness
    # ------------------------------------------------------------------
    group_configs = _get_transform_group_configs(work_dir)
    configured_group_configs = [
        group for group in group_configs if _has_configured_transform_widgets(group)
    ]
    group_items: list[EntityStatus] = []

    for group_config in configured_group_configs:
        group_name = group_config.get("group_by", "default")
        last_transform = job_store.get_last_run(
            "transform", group_by=group_name, status="completed"
        )
        transform_at = _iso(
            last_transform.get("completed_at") if last_transform else None
        )

        if (
            running
            and running.get("type") == "transform"
            and (
                running.get("group_by") == group_name
                or group_name in (running.get("group_bys") or [])
            )
        ):
            group_items.append(
                EntityStatus(
                    name=group_name, status="running", reason="Calcul en cours"
                )
            )
        elif not transform_at:
            group_items.append(
                EntityStatus(
                    name=group_name, status="never_run", reason="Jamais calculé"
                )
            )
        elif import_dt and transform_at < import_dt:
            group_items.append(
                EntityStatus(
                    name=group_name,
                    status="stale",
                    last_run_at=last_transform.get("completed_at"),
                    reason="Données modifiées depuis le dernier calcul",
                )
            )
        else:
            group_items.append(
                EntityStatus(
                    name=group_name,
                    status="fresh",
                    last_run_at=last_transform.get("completed_at"),
                )
            )

    # Check for "all groups" transform (group_by=None)
    if not configured_group_configs:
        last_transform_all = job_store.get_last_run("transform", status="completed")
        if last_transform_all:
            t_at = _iso(last_transform_all.get("completed_at"))
            if t_at and import_dt and t_at < import_dt:
                group_items.append(
                    EntityStatus(
                        name="all",
                        status="stale",
                        last_run_at=last_transform_all.get("completed_at"),
                        reason="Données modifiées depuis le dernier calcul",
                    )
                )
            elif t_at:
                group_items.append(
                    EntityStatus(
                        name="all",
                        status="fresh",
                        last_run_at=last_transform_all.get("completed_at"),
                    )
                )

    if group_configs and not configured_group_configs:
        groups_stage_status = "unconfigured"
    else:
        groups_stage_status = _compute_stage_status(group_items)
    last_group_run = max(
        (item.last_run_at for item in group_items if item.last_run_at),
        default=None,
    )

    groups_summary = _get_groups_summary(work_dir)

    # Duration of last group transform (any group)
    last_any_transform = job_store.get_last_run("transform", status="completed")

    groups_status = StageStatus(
        status=groups_stage_status,
        last_run_at=last_group_run,
        items=group_items,
        summary=groups_summary,
        last_job_duration_s=_job_duration_s(last_any_transform),
    )

    # ------------------------------------------------------------------
    # 3. SITE stage — configuration status (not a "run", just editing)
    # ------------------------------------------------------------------
    # Site is about config editing (pages, nav, appearance).
    # Status = "configured" if export.yml has an html_page_exporter
    # with a site config block, else "never_run".
    site_config_path = work_dir / "config" / "export.yml"
    site_configured = False
    site_unconfigured = False
    if site_config_path.exists():
        try:
            with open(site_config_path, "r", encoding="utf-8") as f:
                export_config = yaml.safe_load(f)
            if isinstance(export_config, dict):
                for exp in export_config.get("exports", []):
                    if not isinstance(exp, dict):
                        continue
                    if exp.get("exporter") == "html_page_exporter" and exp.get(
                        "enabled", True
                    ):
                        if _has_valid_site_export_params(exp):
                            site_configured = True
                            break
                        site_unconfigured = True
        except Exception:
            pass

    site_summary = _get_site_summary(work_dir)

    site_status = StageStatus(
        status=(
            "fresh"
            if site_configured
            else "unconfigured"
            if site_unconfigured
            else "never_run"
        ),
        last_run_at=None,
        items=[],
        summary=site_summary,
    )

    # ------------------------------------------------------------------
    # 4. PUBLICATION stage — build (export) + deploy
    # ------------------------------------------------------------------
    last_export = job_store.get_last_run("export", status="completed")
    last_export_at = last_export.get("completed_at") if last_export else None
    export_dt = _iso(last_export_at)

    # Fallback: if no GUI export job, check exports/web/index.html mtime
    if not export_dt:
        file_dt = _get_export_mtime(work_dir)
        if file_dt:
            export_dt = file_dt
            last_export_at = file_dt.isoformat()

    # Publication is stale if groups were recalculated after last build
    pub_stale = False
    if export_dt and last_group_run:
        last_group_dt = _iso(last_group_run)
        if last_group_dt and last_group_dt > export_dt:
            pub_stale = True

    if running and running.get("type") == "export":
        pub_status_val = "running"
    elif not export_dt:
        pub_status_val = "never_run"
    elif pub_stale:
        pub_status_val = "stale"
    else:
        pub_status_val = "fresh"

    pub_summary = _get_publication_summary(work_dir)

    publication_status = StageStatus(
        status=pub_status_val,
        last_run_at=last_export_at,
        summary=pub_summary,
        last_job_duration_s=_job_duration_s(last_export),
    )

    # ------------------------------------------------------------------
    # Running job info
    # ------------------------------------------------------------------
    running_info = None
    if running:
        running_info = {
            "id": running.get("id"),
            "type": running.get("type"),
            "group_by": running.get("group_by"),
            "group_bys": running.get("group_bys"),
            "progress": running.get("progress", 0),
            "message": running.get("message", ""),
            "started_at": running.get("started_at"),
        }

    return PipelineStatusResponse(
        data=data_status,
        groups=groups_status,
        site=site_status,
        publication=publication_status,
        running_job=running_info,
    )
