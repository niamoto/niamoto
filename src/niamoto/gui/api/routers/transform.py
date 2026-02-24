"""Transform API endpoints for executing data transformations."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import yaml
import copy

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Request
from pydantic import BaseModel

from niamoto.core.services.transformer import TransformerService
from niamoto.common.config import Config
from niamoto.gui.api.context import (
    get_database_path,
    get_config_path,
    get_working_directory,
)
from niamoto.gui.api.services.job_file_store import JobFileStore

logger = logging.getLogger(__name__)

router = APIRouter()


class TransformRequest(BaseModel):
    """Request model for executing transformations."""

    config_path: Optional[str] = "config/transform.yml"
    transformations: Optional[List[str]] = None  # Specific transformations to run
    group_by: Optional[str] = (
        None  # Filter by aggregation group (taxons, plots, shapes)
    )


class TransformResponse(BaseModel):
    """Response model for transform execution."""

    job_id: str
    status: str
    message: str
    started_at: datetime


class TransformStatus(BaseModel):
    """Status model for transform jobs."""

    job_id: str
    status: str  # "running", "completed", "failed"
    progress: int  # 0-100
    message: str
    phase: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TransformMetrics(BaseModel):
    """Metrics for completed transformations."""

    total_transformations: int
    completed_transformations: int
    failed_transformations: int
    total_widgets: int
    generated_files: List[str]
    execution_time: float


def get_transform_config(config_path: str) -> Dict[str, Any]:
    """Load and parse transform configuration."""
    path = get_config_path(config_path)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Transform configuration not found at {config_path}",
        )

    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse transform configuration: {str(e)}"
        )


def _get_job_store(request: Request) -> JobFileStore:
    """Récupère le JobFileStore depuis app.state."""
    store = getattr(request.app.state, "job_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="JobFileStore non initialisé")
    return store


async def execute_transform_background(
    job_id: str,
    job_store: JobFileStore,
    config_path: str,
    transformations: Optional[List[str]] = None,
    group_by: Optional[str] = None,
):
    """Execute transformations in the background."""

    try:
        job_store.update_progress(job_id, 0, "Loading configuration...")

        # Load configuration
        config = get_transform_config(config_path)

        # Initialize transformer service
        db_path = get_database_path()
        if not db_path:
            raise ValueError(
                "Database not found. Please ensure the database is initialized."
            )

        # Initialize Config with the correct config directory
        work_dir = get_working_directory()
        config_dir = str(work_dir / "config")
        app_config = Config(config_dir=config_dir, create_default=False)
        transformer_service = TransformerService(
            str(db_path),
            app_config,
            enable_cli_integration=False,
        )

        # Prepare configuration for the transformer service
        prepared_config: List[Dict[str, Any]] = []

        def normalize_group(group: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(group, dict):
                return None

            group_copy = copy.deepcopy(group)
            widgets = group_copy.get("widgets_data", {}) or {}

            if not isinstance(widgets, dict):
                widgets = {}

            if transformations:
                widgets = {
                    name: cfg
                    for name, cfg in widgets.items()
                    if name in transformations
                }

            if transformations and not widgets:
                return None

            group_copy["widgets_data"] = widgets
            return group_copy

        if isinstance(config, list):
            for group in config:
                normalized = normalize_group(group)
                if normalized is not None:
                    prepared_config.append(normalized)
        elif isinstance(config, dict):
            normalized = normalize_group(config)
            if normalized is not None:
                prepared_config.append(normalized)
        else:
            raise ValueError("Unsupported transform configuration format")

        # Collect metadata about expected transformations
        expected_transformations: List[Dict[str, str]] = []
        widget_name_counts: Dict[str, int] = {}
        for group in prepared_config:
            group_name = group.get("group_by", "default")
            widgets = group.get("widgets_data", {}) or {}
            for widget_name in widgets.keys():
                occurrence = widget_name_counts.get(widget_name, 0)
                widget_name_counts[widget_name] = occurrence + 1

                if occurrence > 0:
                    key = f"{group_name}:{widget_name}"
                else:
                    key = widget_name

                expected_transformations.append(
                    {
                        "key": key,
                        "group": group_name,
                        "widget": widget_name,
                    }
                )

        total_transforms = len(expected_transformations)

        if total_transforms == 0:
            job_store.complete_job(
                job_id,
                result={
                    "metrics": {
                        "total_transformations": 0,
                        "completed_transformations": 0,
                        "failed_transformations": 0,
                        "total_widgets": 0,
                        "generated_files": [],
                        "execution_time": 0.0,
                    },
                    "transformations": {},
                },
            )
            return

        # Inject filtered config into service
        transformer_service.transforms_config = prepared_config
        transformer_service.config.transforms = prepared_config

        job_store.update_progress(
            job_id, 10, "Executing transformations from configuration"
        )

        start_time = datetime.now()

        def handle_progress(update: Dict[str, Any]) -> None:
            processed = update.get("processed") or 0
            total = update.get("total") or total_transforms
            progress_value = 10
            if total:
                ratio = min(max(processed / total, 0.0), 1.0)
                progress_value = max(10, 10 + int(ratio * 80))
            message = (
                f"Processing {update.get('group', 'group')} · "
                f"{update.get('widget', 'widget')}"
            )
            job_store.update_progress(job_id, progress_value, message)

        transform_results = await asyncio.to_thread(
            transformer_service.transform_data,
            group_by,
            None,
            True,
            handle_progress,
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        transformations_status: Dict[str, Dict[str, Any]] = {}
        successful = 0

        for item in expected_transformations:
            group_name = item["group"]
            widget_name = item["widget"]
            key = item["key"]

            group_info = (
                transform_results.get(group_name, {})
                if isinstance(transform_results, dict)
                else {}
            )
            widgets_info = (
                group_info.get("widgets", {}) if isinstance(group_info, dict) else {}
            )

            generated = widgets_info.get(widget_name)
            if generated is not None:
                successful += 1
                status = "success"
                generated_count = generated
            else:
                status = "warning"
                generated_count = 0

            transformations_status[key] = {
                "status": status,
                "generated": generated_count,
                "group": group_name,
                "widget": widget_name,
            }

        failed = total_transforms - successful

        job_store.complete_job(
            job_id,
            result={
                "metrics": {
                    "total_transformations": total_transforms,
                    "completed_transformations": successful,
                    "failed_transformations": failed,
                    "total_widgets": total_transforms,
                    "generated_files": [],
                    "execution_time": execution_time,
                },
                "transformations": transformations_status,
            },
        )

    except Exception as e:
        logger.exception("Transform job %s failed", job_id)
        job_store.fail_job(job_id, str(e))


def _job_to_status(job: dict) -> dict:
    """Convertit un job JobFileStore en format compatible TransformStatus."""
    return {
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "message": job.get("message", ""),
        "phase": job.get("phase"),
        "started_at": job["started_at"],
        "completed_at": job.get("completed_at"),
        "result": job.get("result"),
        "error": job.get("error"),
    }


@router.post("/execute", response_model=TransformResponse)
async def execute_transform(
    request: TransformRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    """
    Execute data transformations based on configuration.

    This starts a background job that processes the transformations
    defined in the transform.yml configuration file.
    """
    job_store = _get_job_store(http_request)

    # Vérifier qu'aucun job n'est déjà en cours
    running = job_store.get_running_job()
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"Un calcul est déjà en cours ({running['type']} — {running['progress']}%)",
        )

    try:
        job = job_store.create_job("transform", group_by=request.group_by)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # Start background task
    background_tasks.add_task(
        execute_transform_background,
        job["id"],
        job_store,
        request.config_path,
        request.transformations,
        request.group_by,
    )

    return TransformResponse(
        job_id=job["id"],
        status="running",
        message="Transform job started",
        started_at=job["started_at"],
    )


@router.get("/status/{job_id}", response_model=TransformStatus)
async def get_transform_status(job_id: str, http_request: Request):
    """
    Get the status of a transform job.

    Returns the current status, progress, and result (if completed)
    of the specified transform job.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Transform job {job_id} not found")

    return TransformStatus(**_job_to_status(job))


@router.get("/jobs")
async def list_transform_jobs(http_request: Request):
    """
    List all transform jobs.

    Returns a list of all transform jobs with their current status.
    """
    job_store = _get_job_store(http_request)
    jobs = []

    # Job actif (filtré par type)
    active = job_store.get_active_job(job_type="transform")
    if active:
        jobs.append(
            {
                "job_id": active["id"],
                "status": active["status"],
                "started_at": active["started_at"],
                "completed_at": active.get("completed_at"),
                "progress": active["progress"],
                "message": active.get("message", ""),
            }
        )

    # Historique récent
    for entry in job_store.get_history(limit=10):
        if entry.get("type") == "transform":
            jobs.append(
                {
                    "job_id": entry["id"],
                    "status": entry["status"],
                    "started_at": entry["started_at"],
                    "completed_at": entry.get("completed_at"),
                    "progress": entry.get("progress", 100),
                    "message": entry.get("message", ""),
                }
            )

    return {"jobs": jobs}


@router.delete("/jobs/{job_id}")
async def cancel_transform_job(job_id: str, http_request: Request):
    """
    Cancel a running transform job.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Transform job {job_id} not found")

    # L'annulation réelle n'est pas implémentée en v1
    raise HTTPException(
        status_code=501, detail=f"Annulation non implémentée en v1 (job {job_id})"
    )


@router.get("/config")
async def get_transform_config_endpoint():
    """
    Get the current transform configuration.

    Returns the parsed content of the transform.yml file.
    """

    try:
        config = get_transform_config("config/transform.yml")

        # Handle both list and dict formats
        widget_types = {}
        total_widgets = 0
        all_widgets_data = {}

        if isinstance(config, list):
            # If config is a list of transform groups
            for group in config:
                if isinstance(group, dict):
                    widgets_data = group.get("widgets_data", {})
                    if isinstance(widgets_data, dict):
                        all_widgets_data.update(widgets_data)
                        total_widgets += len(widgets_data)
                        for widget_config in widgets_data.values():
                            if isinstance(widget_config, dict):
                                plugin_type = widget_config.get("plugin", "unknown")
                                widget_types[plugin_type] = (
                                    widget_types.get(plugin_type, 0) + 1
                                )
        elif isinstance(config, dict):
            # If config is a dict with widgets_data at root
            widgets_data = config.get("widgets_data", {})
            if widgets_data is None:
                widgets_data = {}
            elif not isinstance(widgets_data, dict):
                widgets_data = {}

            all_widgets_data = widgets_data
            total_widgets = len(widgets_data)
            for widget_config in widgets_data.values():
                if isinstance(widget_config, dict):
                    plugin_type = widget_config.get("plugin", "unknown")
                    widget_types[plugin_type] = widget_types.get(plugin_type, 0) + 1

        # Return a unified format that works for the frontend
        return {
            "config": {"widgets_data": all_widgets_data},
            "summary": {"total_widgets": total_widgets, "widget_types": widget_types},
            "raw_config": config,  # Keep raw config for debugging
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read transform configuration: {str(e)}"
        )


@router.get("/metrics")
async def get_transform_metrics(http_request: Request):
    """
    Get metrics from the last completed transform.

    Returns statistics about the transformations performed.
    """
    job_store = _get_job_store(http_request)
    last = job_store.get_last_run("transform")

    if not last or not last.get("result"):
        return {
            "metrics": {
                "total_transformations": 0,
                "completed_transformations": 0,
                "failed_transformations": 0,
                "total_widgets": 0,
                "generated_files": [],
                "execution_time": 0,
            },
            "last_run": None,
        }

    return {
        "metrics": last["result"]["metrics"],
        "last_run": last.get("completed_at"),
        "job_id": last["id"],
    }


@router.get("/active")
async def get_active_transform_job(http_request: Request):
    """
    Get the currently active job (running or recently completed).

    Returns the active job or null if none.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_active_job(job_type="transform")

    if not job:
        return None

    return _job_to_status(job)


@router.get("/last-run/{group_by}")
async def get_last_transform_run(group_by: str, http_request: Request):
    """
    Get the last completed transform for a specific group.

    Returns the last terminal job for this group_by or null.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_last_run("transform", group_by=group_by)

    if not job:
        return None

    return _job_to_status(job)


@router.get("/sources")
async def get_transform_sources(
    group_by: Optional[str] = Query(None, description="Filter sources by group_by"),
) -> Dict[str, List[str]]:
    """
    Get available transform sources from transform.yml.

    Transform sources are intermediate data files loaded via stats_loader
    that are used by class_objects plugins.

    Args:
        group_by: Optional filter - return only sources for this specific group_by

    Returns:
        Dictionary with 'sources' key containing list of source names

    Example:
        GET /api/transform/sources?group_by=shapes
        Returns: {"sources": ["raw_shape_stats", "shape_stats"]}
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=500, detail="Working directory not found")

        # Load transform.yml
        transform_config_path = work_dir / "config" / "transform.yml"
        if not transform_config_path.exists():
            return {"sources": []}

        with open(transform_config_path, "r", encoding="utf-8") as f:
            transform_config = yaml.safe_load(f) or []

        # Handle both list format (root level) and dict format (with 'transforms' key)
        if isinstance(transform_config, list):
            transforms = transform_config
        elif isinstance(transform_config, dict):
            transforms = transform_config.get("transforms", [])
        else:
            transforms = []

        sources = []

        for transform in transforms:
            transform_group = transform.get("group_by")

            # If group_by filter specified, skip non-matching groups
            if group_by and transform_group != group_by:
                continue

            # Extract source names
            for source in transform.get("sources", []):
                source_name = source.get("name")
                if source_name:
                    sources.append(source_name)

        # Return sorted unique sources
        return {"sources": sorted(list(set(sources)))}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading transform sources: {str(e)}"
        )
