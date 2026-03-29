"""Export API endpoints for generating static sites and exports."""

import logging
import os
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import yaml

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel

from niamoto.core.services.exporter import ExporterService
from niamoto.core.services.transformer import TransformerService
from niamoto.common.config import Config
from niamoto.gui.api.context import (
    get_database_path,
    get_config_path,
    get_working_directory,
)
from niamoto.gui.api.services.job_file_store import JobFileStore
from niamoto.gui.api.services.job_store_runtime import resolve_job_store

logger = logging.getLogger(__name__)

router = APIRouter()

# Lock global pour protéger os.chdir() (thread-unsafe)
_cwd_lock = threading.Lock()


class ExportRequest(BaseModel):
    """Request model for executing exports."""

    config_path: Optional[str] = "config/export.yml"
    export_types: Optional[List[str]] = None  # Specific exports to run
    include_transform: bool = False  # Run transform before export


class ExportResponse(BaseModel):
    """Response model for export execution."""

    job_id: str
    status: str
    message: str
    started_at: datetime


class ExportStatus(BaseModel):
    """Status model for export jobs."""

    job_id: str
    status: str  # "running", "completed", "failed"
    progress: int  # 0-100
    message: str
    phase: Optional[str] = None  # "transform" or "export"
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExportMetrics(BaseModel):
    """Metrics for completed exports."""

    total_exports: int
    completed_exports: int
    failed_exports: int
    generated_pages: int
    static_site_path: Optional[str]
    execution_time: float


def _get_job_store(request: Request) -> JobFileStore:
    """Resolve the project-scoped JobFileStore for the current request."""
    try:
        return resolve_job_store(request.app)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"JobFileStore unavailable: {exc}")


def _job_to_status(job: dict) -> dict:
    """Convertit un job JobFileStore en format compatible ExportStatus."""
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


def get_export_config(config_path: str) -> Dict[str, Any]:
    """Load and parse export configuration."""
    path = get_config_path(config_path)

    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Export configuration not found at {config_path}"
        )

    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse export configuration: {str(e)}"
        )


async def execute_export_background(
    job_id: str,
    job_store: JobFileStore,
    config_path: str,
    export_types: Optional[List[str]] = None,
    include_transform: bool = False,
):
    """Execute exports in the background, optionally preceded by transform."""

    original_cwd: Optional[str] = None
    cwd_locked = False

    try:
        logger.info("Starting export job %s", job_id)
        job_store.update_progress(job_id, 0, "Loading configuration...")
        logger.info("Job %s: Loading configuration from %s", job_id, config_path)

        # Load configuration
        config = get_export_config(config_path)

        # Initialize services
        db_path = get_database_path()
        if not db_path:
            raise ValueError(
                "Database not found. Please ensure the database is initialized."
            )

        logger.info("Job %s: Initializing Config", job_id)
        work_dir = get_working_directory()
        config_dir = str(work_dir / "config")
        app_config = Config(config_dir=config_dir, create_default=False)

        # Change to working directory so relative paths (output_dir, template_dir)
        # resolve correctly within the instance.
        # Protégé par un lock car os.chdir() affecte tout le process (thread-unsafe).
        original_cwd = os.getcwd()
        _cwd_lock.acquire()
        cwd_locked = True
        os.chdir(work_dir)
        logger.info("Job %s: Changed cwd to %s", job_id, work_dir)

        start_time = datetime.now()

        # Phase 1 (optionnelle) : Transform
        if include_transform:
            job_store.update_progress(job_id, 0, "transform.running", phase="transform")
            logger.info("Job %s: Running transform phase", job_id)

            transformer_service = TransformerService(
                str(db_path), app_config, enable_cli_integration=False
            )

            def transform_progress_callback(update: Dict[str, Any]) -> None:
                processed = update.get("processed") or 0
                total = update.get("total") or 1
                ratio = min(max(processed / total, 0.0), 1.0)
                pct = int(ratio * 50)  # Transform = 0-50%
                item_label = update.get("item_label", "")
                message = f"transform:{update.get('group', '')}:{update.get('widget', '')}:{item_label}"
                job_store.update_progress(job_id, pct, message, phase="transform")

            await asyncio.to_thread(
                transformer_service.transform_data,
                None,
                None,
                True,
                transform_progress_callback,
            )
            logger.info("Job %s: Transform phase completed", job_id)
            job_store.update_progress(job_id, 50, "export.starting", phase="export")
        else:
            job_store.update_progress(job_id, 0, "export.starting", phase="export")

        # Phase 2 : Export
        # Offset de progression : 50-100% si composite, 0-100% si export seul
        progress_base = 50 if include_transform else 0
        progress_range = 50 if include_transform else 90
        # Réserve les premiers 10% de la plage pour l'initialisation
        init_offset = int(progress_range * 0.1)
        export_range = progress_range - init_offset

        logger.info("Job %s: Creating ExporterService", job_id)
        exporter_service = ExporterService(str(db_path), app_config)

        job_store.update_progress(
            job_id, progress_base + init_offset, "Executing exports...", phase="export"
        )
        logger.info("Job %s: Starting export execution", job_id)

        results = {}
        completed = 0
        failed = 0
        generated_paths: list[str] = []

        if export_types:
            total_exports = len(export_types)
            logger.info(
                "Job %s: Running %d specific exports: %s",
                job_id,
                total_exports,
                export_types,
            )
            for idx, export_name in enumerate(export_types):
                pct = (
                    progress_base
                    + init_offset
                    + int(idx / total_exports * export_range)
                )
                job_store.update_progress(
                    job_id,
                    pct,
                    f"Executing export: {export_name}",
                    phase="export",
                )
                logger.info(
                    "Job %s: Executing export %s (%d/%d)",
                    job_id,
                    export_name,
                    idx + 1,
                    total_exports,
                )

                try:
                    result = await asyncio.to_thread(
                        exporter_service.run_export, target_name=export_name
                    )
                    logger.info(
                        "Job %s: Export %s completed successfully",
                        job_id,
                        export_name,
                    )
                    results[export_name] = {"status": "success", "data": result}
                    completed += 1
                except Exception as e:
                    results[export_name] = {"status": "error", "error": str(e)}
                    failed += 1

                pct = (
                    progress_base
                    + init_offset
                    + int((idx + 1) / total_exports * export_range)
                )
                job_store.update_progress(
                    job_id,
                    pct,
                    f"export.done:{export_name}:{idx + 1}/{total_exports}",
                    phase="export",
                )
        else:
            logger.info("Job %s: Running all exports", job_id)

            export_task = asyncio.create_task(
                asyncio.to_thread(exporter_service.run_export)
            )

            # Progression simulée dans la plage [progress_base+init_offset, progress_base+progress_range]
            steps = [0.2, 0.35, 0.5, 0.65, 0.75, 0.85, 0.9, 0.95]
            step_idx = 0

            while not export_task.done():
                await asyncio.sleep(5)
                if step_idx < len(steps) and not export_task.done():
                    pct = (
                        progress_base
                        + init_offset
                        + int(steps[step_idx] * export_range)
                    )
                    job_store.update_progress(
                        job_id,
                        pct,
                        f"export.generating:{pct}",
                        phase="export",
                    )
                    step_idx += 1

            try:
                result = await export_task
                logger.info("Job %s: All exports completed successfully", job_id)

                for export_name, export_result in result.items():
                    results[export_name] = {"status": "success", "data": export_result}
                    completed += 1

            except Exception as e:
                results["all"] = {"status": "error", "error": str(e)}
                failed += 1

        # Determine static site path from config
        static_site_path = None
        try:
            config_exports = config.get("exports", [])
            if isinstance(config_exports, list):
                for export_config in config_exports:
                    if isinstance(export_config, dict):
                        if export_config.get("exporter") == "static_site":
                            static_site_path = export_config.get("params", {}).get(
                                "output_dir", "exports/web"
                            )
                            break
        except Exception:
            pass

        total_exports = completed + failed
        execution_time = (datetime.now() - start_time).total_seconds()

        job_store.complete_job(
            job_id,
            result={
                "metrics": {
                    "total_exports": total_exports,
                    "completed_exports": completed,
                    "failed_exports": failed,
                    "generated_pages": len(generated_paths),
                    "static_site_path": static_site_path,
                    "execution_time": execution_time,
                },
                "exports": results,
                "generated_paths": generated_paths,
            },
        )

    except Exception as e:
        logger.exception("Export job %s failed with exception", job_id)
        job_store.fail_job(job_id, str(e))
    finally:
        # Restaurer le répertoire de travail et libérer le lock
        if original_cwd is not None:
            try:
                os.chdir(original_cwd)
            except Exception:
                pass
        if cwd_locked:
            _cwd_lock.release()


@router.post("/execute", response_model=ExportResponse)
async def execute_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    """
    Execute exports based on configuration.

    This starts a background job that processes the exports
    defined in the export.yml configuration file.
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
        job = job_store.create_job("export")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    background_tasks.add_task(
        execute_export_background,
        job["id"],
        job_store,
        request.config_path,
        request.export_types,
        request.include_transform,
    )

    return ExportResponse(
        job_id=job["id"],
        status="running",
        message="Export job started",
        started_at=job["started_at"],
    )


@router.get("/status/{job_id}", response_model=ExportStatus)
async def get_export_status(job_id: str, http_request: Request):
    """
    Get the status of an export job.

    Returns the current status, progress, and result (if completed)
    of the specified export job.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    return ExportStatus(**_job_to_status(job))


@router.get("/jobs")
async def list_export_jobs(http_request: Request):
    """
    List all export jobs.

    Returns a list of all export jobs with their current status.
    """
    job_store = _get_job_store(http_request)
    jobs = []

    active = job_store.get_active_job(job_type="export")
    if active:
        jobs.append(
            {
                "job_id": active["id"],
                "status": active["status"],
                "started_at": active["started_at"],
                "completed_at": active.get("completed_at"),
                "progress": active["progress"],
                "message": active.get("message", ""),
                "phase": active.get("phase"),
                "result": active.get("result"),
                "error": active.get("error"),
            }
        )

    for entry in job_store.get_history(limit=10):
        if entry.get("type") == "export":
            jobs.append(
                {
                    "job_id": entry["id"],
                    "status": entry["status"],
                    "started_at": entry["started_at"],
                    "completed_at": entry.get("completed_at"),
                    "progress": entry.get("progress", 100),
                    "message": entry.get("message", ""),
                    "phase": entry.get("phase"),
                    "result": entry.get("result"),
                    "error": entry.get("error"),
                }
            )

    return {"jobs": jobs}


@router.delete("/jobs/{job_id}")
async def cancel_export_job(job_id: str, http_request: Request):
    """
    Cancel a running export job.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    raise HTTPException(
        status_code=501, detail=f"Annulation non implémentée en v1 (job {job_id})"
    )


@router.delete("/history")
async def clear_export_history(http_request: Request):
    """Clear persisted export history for the current project."""
    job_store = _get_job_store(http_request)
    removed = job_store.clear_history(job_type="export")
    return {"removed": removed}


@router.get("/config")
async def get_export_config_endpoint():
    """
    Get the current export configuration.

    Returns the parsed content of the export.yml file.
    """

    try:
        config = get_export_config("config/export.yml")

        # Get export counts by type
        exports = config.get("exports", [])
        export_types = {}
        total_exports = 0
        all_exports = {}

        # Handle different export configuration formats
        if exports is None:
            exports = []

        if isinstance(exports, list):
            total_exports = len(exports)
            for idx, export_config in enumerate(exports):
                if isinstance(export_config, dict):
                    exporter_type = export_config.get("exporter", "unknown")
                    export_types[exporter_type] = export_types.get(exporter_type, 0) + 1
                    export_name = export_config.get("name", f"export_{idx}")
                    all_exports[export_name] = export_config
        elif isinstance(exports, dict):
            all_exports = exports
            total_exports = len(exports)
            for export_config in exports.values():
                if isinstance(export_config, dict):
                    exporter_type = export_config.get("exporter", "unknown")
                    export_types[exporter_type] = export_types.get(exporter_type, 0) + 1

        return {
            "config": {"exports": all_exports},
            "summary": {"total_exports": total_exports, "export_types": export_types},
            "raw_config": config,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read export configuration: {str(e)}"
        )


@router.get("/active")
async def get_active_export_job(http_request: Request):
    """
    Get the currently active job (running or recently completed).

    Returns the active job or null if none.
    """
    job_store = _get_job_store(http_request)
    job = job_store.get_active_job(job_type="export")

    if not job:
        return None

    return _job_to_status(job)


@router.get("/metrics")
async def get_export_metrics(http_request: Request):
    """
    Get metrics from the last completed export.

    Returns statistics about the exports performed.
    """
    job_store = _get_job_store(http_request)
    last = job_store.get_last_run("export", status="completed")

    if not last or not last.get("result"):
        return {
            "metrics": {
                "total_exports": 0,
                "completed_exports": 0,
                "failed_exports": 0,
                "generated_pages": 0,
                "static_site_path": None,
                "execution_time": 0,
            },
            "last_run": None,
        }

    return {
        "metrics": last["result"]["metrics"],
        "last_run": last.get("completed_at"),
        "job_id": last["id"],
    }


@router.post("/execute-cli")
async def execute_export_cli(
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    """
    Execute export using the Niamoto CLI command.

    This runs 'niamoto export' in the background and returns immediately.
    """
    job_store = _get_job_store(http_request)

    running = job_store.get_running_job()
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"Un calcul est déjà en cours ({running['type']} — {running['progress']}%)",
        )

    try:
        job = job_store.create_job("export-cli")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    job_id = job["id"]

    async def run_export_command():
        """Run the niamoto export command."""
        try:
            job_store.update_progress(job_id, 0, "Running niamoto export command...")

            process = await asyncio.create_subprocess_exec(
                "niamoto",
                "export",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                job_store.complete_job(
                    job_id,
                    result={
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                    },
                )
            else:
                job_store.fail_job(
                    job_id,
                    stderr.decode() if stderr else "Unknown error",
                )

        except Exception as e:
            job_store.fail_job(job_id, str(e))

    background_tasks.add_task(run_export_command)

    return {
        "job_id": job_id,
        "status": "started",
        "message": "Export CLI command started in background",
    }
