"""Export API endpoints for generating static sites and exports."""

from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime
import asyncio
import yaml
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from niamoto.core.services.exporter import ExporterService
from niamoto.common.config import Config
from niamoto.gui.api.context import (
    get_database_path,
    get_config_path,
    get_working_directory,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Store for background jobs
export_jobs: Dict[str, Dict[str, Any]] = {}


class ExportRequest(BaseModel):
    """Request model for executing exports."""

    config_path: Optional[str] = "config/export.yml"
    export_types: Optional[List[str]] = None  # Specific exports to run


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
    job_id: str, config_path: str, export_types: Optional[List[str]] = None
):
    """Execute exports in the background."""

    job = export_jobs[job_id]

    try:
        logger.info(f"Starting export job {job_id}")
        # Update status to running
        job["status"] = "running"
        job["progress"] = 0
        job["message"] = "Loading configuration..."
        logger.info(f"Job {job_id}: Loading configuration from {config_path}")

        # Load configuration
        config = get_export_config(config_path)

        # Initialize exporter service
        db_path = get_database_path()
        if not db_path:
            raise ValueError(
                "Database not found. Please ensure the database is initialized."
            )

        # Initialize Config with the correct config directory
        logger.info(f"Job {job_id}: Initializing Config")
        work_dir = get_working_directory()
        config_dir = str(work_dir / "config")
        app_config = Config(config_dir=config_dir, create_default=False)

        logger.info(f"Job {job_id}: Creating ExporterService")
        exporter_service = ExporterService(str(db_path), app_config)

        job["message"] = "Executing exports..."
        job["progress"] = 10
        logger.info(f"Job {job_id}: Starting export execution")

        # Execute exports using the service's run_export method
        # If export_types is specified, run each one individually
        # Otherwise, run all exports at once
        results = {}
        completed = 0
        failed = 0
        generated_paths = []

        if export_types:
            # Run specific exports one by one
            total_exports = len(export_types)
            logger.info(
                f"Job {job_id}: Running {total_exports} specific exports: {export_types}"
            )
            for idx, export_name in enumerate(export_types):
                job["message"] = f"Executing export: {export_name}"
                logger.info(
                    f"Job {job_id}: Executing export {export_name} ({idx + 1}/{total_exports})"
                )

                try:
                    result = await asyncio.to_thread(
                        exporter_service.run_export, target_name=export_name
                    )
                    logger.info(
                        f"Job {job_id}: Export {export_name} completed successfully"
                    )

                    results[export_name] = {"status": "success", "data": result}
                    completed += 1

                except Exception as e:
                    results[export_name] = {"status": "error", "error": str(e)}
                    failed += 1

                # Update progress
                progress = 10 + int((idx + 1) / total_exports * 80)
                job["progress"] = progress
        else:
            # Run all exports at once with progress updates
            logger.info(f"Job {job_id}: Running all exports")

            # Get list of exports from config to estimate progress
            config_exports = config.get("exports", [])
            total_exports = (
                len(config_exports) if isinstance(config_exports, list) else 1
            )

            # Start export in a separate task and update progress periodically
            export_task = asyncio.create_task(
                asyncio.to_thread(exporter_service.run_export)
            )

            # Update progress while waiting
            progress_steps = [20, 30, 40, 50, 60, 70, 80, 85, 90]
            step_idx = 0

            while not export_task.done():
                await asyncio.sleep(5)  # Check every 5 seconds
                if step_idx < len(progress_steps) and not export_task.done():
                    job["progress"] = progress_steps[step_idx]
                    job["message"] = (
                        f"Génération en cours... ({progress_steps[step_idx]}%)"
                    )
                    step_idx += 1
                    logger.info(
                        f"Job {job_id}: Progress updated to {progress_steps[step_idx - 1]}%"
                    )

            try:
                result = await export_task
                logger.info(f"Job {job_id}: All exports completed successfully")

                # Process results from run_export
                for export_name, export_result in result.items():
                    results[export_name] = {"status": "success", "data": export_result}
                    completed += 1

                job["progress"] = 95

            except Exception as e:
                results["all"] = {"status": "error", "error": str(e)}
                failed += 1
                job["progress"] = 50

        # Try to determine static site path from config
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
            pass  # Ignore errors getting static site path

        # Calculate total exports
        total_exports = completed + failed

        # Mark as completed
        job["status"] = "completed"
        job["progress"] = 100
        job["completed_at"] = datetime.now()
        job["message"] = f"Export completed: {completed} successful, {failed} failed"
        job["result"] = {
            "metrics": {
                "total_exports": total_exports,
                "completed_exports": completed,
                "failed_exports": failed,
                "generated_pages": len(generated_paths),
                "static_site_path": static_site_path,
                "execution_time": (datetime.now() - job["started_at"]).total_seconds(),
            },
            "exports": results,
            "generated_paths": generated_paths,
        }

    except Exception as e:
        logger.exception(f"Export job {job_id} failed with exception")
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.now()
        job["message"] = f"Export failed: {str(e)}"
        job["progress"] = 0


@router.post("/execute", response_model=ExportResponse)
async def execute_export(request: ExportRequest, background_tasks: BackgroundTasks):
    """
    Execute exports based on configuration.

    This starts a background job that processes the exports
    defined in the export.yml configuration file.
    """

    # Create job ID
    job_id = str(uuid4())

    # Initialize job record
    job = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Export job created",
        "started_at": datetime.now(),
        "completed_at": None,
        "result": None,
        "error": None,
    }

    export_jobs[job_id] = job

    # Start background task
    background_tasks.add_task(
        execute_export_background, job_id, request.config_path, request.export_types
    )

    return ExportResponse(
        job_id=job_id,
        status="pending",
        message="Export job started",
        started_at=job["started_at"],
    )


@router.get("/status/{job_id}", response_model=ExportStatus)
async def get_export_status(job_id: str):
    """
    Get the status of an export job.

    Returns the current status, progress, and result (if completed)
    of the specified export job.
    """

    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    job = export_jobs[job_id]

    # Return the job status without modification (progress updates happen in background task)
    return ExportStatus(**job)


@router.get("/jobs")
async def list_export_jobs():
    """
    List all export jobs.

    Returns a list of all export jobs with their current status.
    """

    return {
        "jobs": [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "started_at": job["started_at"],
                "completed_at": job.get("completed_at"),
                "progress": job["progress"],
                "message": job["message"],
            }
            for job in export_jobs.values()
        ]
    }


@router.delete("/jobs/{job_id}")
async def cancel_export_job(job_id: str):
    """
    Cancel a running export job.
    """

    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")

    job = export_jobs[job_id]

    if job["status"] == "running":
        # TODO: Implement actual cancellation logic
        job["status"] = "cancelled"
        job["completed_at"] = datetime.now()
        job["message"] = "Export job cancelled"

    return {"message": f"Export job {job_id} cancelled"}


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
            # If exports is a list (the normal case)
            total_exports = len(exports)
            for idx, export_config in enumerate(exports):
                if isinstance(export_config, dict):
                    # Use 'exporter' key instead of 'plugin' for exports
                    exporter_type = export_config.get("exporter", "unknown")
                    export_types[exporter_type] = export_types.get(exporter_type, 0) + 1
                    # Create a dict from list for consistency
                    export_name = export_config.get("name", f"export_{idx}")
                    all_exports[export_name] = export_config
        elif isinstance(exports, dict):
            # If exports is a dict, use as is
            all_exports = exports
            total_exports = len(exports)
            for export_config in exports.values():
                if isinstance(export_config, dict):
                    exporter_type = export_config.get("exporter", "unknown")
                    export_types[exporter_type] = export_types.get(exporter_type, 0) + 1

        # Return a unified format that works for the frontend
        return {
            "config": {"exports": all_exports},
            "summary": {"total_exports": total_exports, "export_types": export_types},
            "raw_config": config,  # Keep raw config for debugging
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read export configuration: {str(e)}"
        )


@router.get("/metrics")
async def get_export_metrics():
    """
    Get metrics from the last completed export.

    Returns statistics about the exports performed.
    """

    # Find the most recent completed job
    completed_jobs = [
        job for job in export_jobs.values() if job["status"] == "completed"
    ]

    if not completed_jobs:
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

    # Sort by completion time
    latest_job = max(completed_jobs, key=lambda j: j["completed_at"])

    return {
        "metrics": latest_job["result"]["metrics"],
        "last_run": latest_job["completed_at"],
        "job_id": latest_job["job_id"],
    }


@router.post("/execute-cli")
async def execute_export_cli(background_tasks: BackgroundTasks):
    """
    Execute export using the Niamoto CLI command.

    This runs 'niamoto export' in the background and returns immediately.
    """

    # Create job ID
    job_id = str(uuid4())

    async def run_export_command():
        """Run the niamoto export command."""
        try:
            # Update job status
            export_jobs[job_id]["status"] = "running"
            export_jobs[job_id]["message"] = "Running niamoto export command..."

            # Run the command
            process = await asyncio.create_subprocess_exec(
                "niamoto",
                "export",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                export_jobs[job_id]["status"] = "completed"
                export_jobs[job_id]["message"] = "Export completed successfully"
                export_jobs[job_id]["result"] = {
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                }
            else:
                export_jobs[job_id]["status"] = "failed"
                export_jobs[job_id]["message"] = "Export failed"
                export_jobs[job_id]["error"] = (
                    stderr.decode() if stderr else "Unknown error"
                )

            export_jobs[job_id]["completed_at"] = datetime.now()
            export_jobs[job_id]["progress"] = 100

        except Exception as e:
            export_jobs[job_id]["status"] = "failed"
            export_jobs[job_id]["error"] = str(e)
            export_jobs[job_id]["completed_at"] = datetime.now()

    # Initialize job record
    export_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "message": "Export CLI job created",
        "started_at": datetime.now(),
        "completed_at": None,
        "result": None,
        "error": None,
    }

    # Start background task
    background_tasks.add_task(run_export_command)

    return {
        "job_id": job_id,
        "status": "started",
        "message": "Export CLI command started in background",
    }
