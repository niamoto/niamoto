"""Smart configuration endpoints for auto-detecting and configuring entities.

All endpoints in this router use get_working_directory() from GUI context
to ensure file operations happen in the correct project directory.
"""

import asyncio
import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Literal, Optional
import shutil
import zipfile

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.datastructures import UploadFile as StarletteUploadFile
import yaml

from niamoto.core.imports.auto_config_service import AutoConfigService
from niamoto.gui.api.context import get_working_directory
from niamoto.gui.api.desktop_auth import require_desktop_mutation_auth

router = APIRouter()

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024


def _sanitize_file_analysis_response(
    analysis: Dict[str, Any], requested_filepath: str
) -> Dict[str, Any]:
    """Avoid leaking resolved server paths in file-analysis responses."""
    sanitized = dict(analysis)
    if "filepath" in sanitized:
        sanitized["filepath"] = requested_filepath
    return sanitized


class FileInfo(BaseModel):
    """Information about a file to analyze."""

    filepath: str
    entity_name: Optional[str] = None


class AutoConfigureRequest(BaseModel):
    """Request for auto-configuration of all files."""

    files: List[str]  # List of file paths relative to imports/


class AutoConfigureResponse(BaseModel):
    """Response from auto-configuration."""

    success: bool
    entities: Dict[str, Any]
    auxiliary_sources: List[Dict[str, Any]] = []
    detected_columns: Dict[str, List[str]] = {}  # Entity name -> columns
    ml_predictions: Dict[str, List[Dict[str, Any]]] = {}
    decision_summary: Dict[str, Dict[str, Any]] = {}
    semantic_evidence: Dict[str, Dict[str, Any]] = {}
    confidence: float
    warnings: List[str] = []


class AutoConfigureJobStartResponse(BaseModel):
    """Response returned when an auto-config job is created."""

    job_id: str
    status: Literal["pending", "running", "completed", "failed"]


class AutoConfigureProgressEvent(BaseModel):
    """Single progress event emitted during auto-configuration."""

    kind: Literal["stage", "detail", "finding", "complete", "error"]
    message: str
    timestamp: float
    file: Optional[str] = None
    entity: Optional[str] = None
    details: Dict[str, Any] = {}


class AutoConfigureJobStatusResponse(BaseModel):
    """Current status of an auto-config job."""

    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    events: List[AutoConfigureProgressEvent] = []
    result: Optional[AutoConfigureResponse] = None
    error: Optional[str] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    elapsed_seconds: float


class DetectRelationshipsRequest(BaseModel):
    """Request for detecting relationships between files."""

    source_file: str
    target_files: List[str]


class UploadedFileInfo(BaseModel):
    """Information about an uploaded file."""

    filename: str
    path: str  # Relative path from working directory
    size: int  # Size in bytes
    size_mb: float
    type: str  # File extension
    category: str  # csv, gpkg, tif, other


class _AutoConfigureJob:
    """In-memory auto-config job state."""

    def __init__(self, job_id: str, project_path: Optional[str] = None) -> None:
        self.job_id = job_id
        self.project_path = project_path
        self.status: Literal["pending", "running", "completed", "failed"] = "pending"
        self.events: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None


class _AutoConfigureJobStore:
    """Tiny in-memory job store for long-running auto-config analysis."""

    def __init__(
        self,
        *,
        terminal_ttl_seconds: float = 15 * 60,
        max_terminal_jobs: int = 100,
        max_events_per_job: int = 500,
        max_active_jobs_per_project: int = 1,
    ) -> None:
        self._jobs: Dict[str, _AutoConfigureJob] = {}
        self._lock = threading.Lock()
        self.terminal_ttl_seconds = terminal_ttl_seconds
        self.max_terminal_jobs = max_terminal_jobs
        self.max_events_per_job = max_events_per_job
        self.max_active_jobs_per_project = max_active_jobs_per_project

    def _now(self) -> float:
        return time.time()

    def _prune_locked(self) -> None:
        now = self._now()
        terminal_jobs = [
            job
            for job in self._jobs.values()
            if job.status in {"completed", "failed"} and job.completed_at is not None
        ]

        for job in terminal_jobs:
            if now - job.completed_at > self.terminal_ttl_seconds:
                self._jobs.pop(job.job_id, None)

        terminal_jobs = [
            job
            for job in self._jobs.values()
            if job.status in {"completed", "failed"} and job.completed_at is not None
        ]
        excess = len(terminal_jobs) - self.max_terminal_jobs
        if excess > 0:
            for job in sorted(terminal_jobs, key=lambda item: item.completed_at or 0)[
                :excess
            ]:
                self._jobs.pop(job.job_id, None)

    def _active_jobs_for_project_locked(
        self, project_path: Optional[str]
    ) -> list[_AutoConfigureJob]:
        if project_path is None:
            return []
        return [
            job
            for job in self._jobs.values()
            if job.project_path == project_path and job.status in {"pending", "running"}
        ]

    def create_job(self, project_path: Optional[str] = None) -> _AutoConfigureJob:
        resolved_project_path = (
            str(Path(project_path).resolve()) if project_path else None
        )
        job = _AutoConfigureJob(
            job_id=str(uuid.uuid4()),
            project_path=resolved_project_path,
        )
        with self._lock:
            self._prune_locked()
            active_jobs = self._active_jobs_for_project_locked(resolved_project_path)
            if len(active_jobs) >= self.max_active_jobs_per_project:
                active_job = sorted(active_jobs, key=lambda item: item.created_at)[0]
                raise ValueError(
                    "An auto-config job is already pending or running "
                    f"for this project: {active_job.job_id}"
                )
            self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[_AutoConfigureJob]:
        with self._lock:
            self._prune_locked()
            return self._jobs.get(job_id)

    def append_event(self, job_id: str, event: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.events.append(event)
            if len(job.events) > self.max_events_per_job:
                del job.events[: len(job.events) - self.max_events_per_job]

    def set_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "running"
                job.started_at = self._now()

    def complete(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.result = result
            job.completed_at = self._now()

    def complete_with_event(
        self, job_id: str, result: Dict[str, Any], event: Dict[str, Any]
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.events.append(event)
            job.result = result
            job.status = "completed"
            job.completed_at = self._now()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.error = error
            job.completed_at = self._now()

    def fail_with_event(self, job_id: str, error: str, event: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.events.append(event)
            job.error = error
            job.status = "failed"
            job.completed_at = self._now()


_AUTO_CONFIG_JOB_STORE = _AutoConfigureJobStore()


def _validate_import_file_paths(work_dir: Path, files: List[str]) -> None:
    """Ensure auto-config input files stay under the project imports directory."""
    imports_dir = (work_dir / "imports").resolve()
    for file_path in files:
        requested_path = Path(file_path)
        if requested_path.is_absolute() or any(
            part in {"", ".", ".."} for part in requested_path.parts
        ):
            raise HTTPException(
                status_code=400,
                detail="File path outside project imports directory",
            )

        resolved_path = (work_dir / file_path).resolve()
        try:
            resolved_path.relative_to(imports_dir)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="File path outside project imports directory",
            ) from exc


def _validate_bulk_config_paths(value: Any) -> None:
    """Reject absolute or traversing source paths before persisting import.yml."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"source", "data", "path", "file"} and isinstance(child, str):
                requested_path = Path(child)
                if requested_path.is_absolute() or ".." in requested_path.parts:
                    raise HTTPException(
                        status_code=400,
                        detail="Source paths must be relative project paths",
                    )
            _validate_bulk_config_paths(child)
    elif isinstance(value, list):
        for child in value:
            _validate_bulk_config_paths(child)


def _get_project_scoped_auto_config_job(job_id: str) -> _AutoConfigureJob:
    """Return a job only when it belongs to the current project."""
    job = _AUTO_CONFIG_JOB_STORE.get_job(job_id)
    work_dir = get_working_directory()
    current_project = str(Path(work_dir).resolve()) if work_dir else None
    if not job or job.project_path != current_project:
        raise HTTPException(status_code=404, detail="Auto-config job not found")
    return job


def _make_progress_event(
    *,
    kind: Literal["stage", "detail", "finding", "complete", "error"],
    message: str,
    file: Optional[str] = None,
    entity: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a progress event payload."""
    return {
        "kind": kind,
        "message": message,
        "timestamp": time.time(),
        "file": file,
        "entity": entity,
        "details": details or {},
    }


def _run_auto_config_job(job_id: str, work_dir_str: str, files: List[str]) -> None:
    """Execute auto-config in a background thread and persist progress."""
    _AUTO_CONFIG_JOB_STORE.set_running(job_id)
    _AUTO_CONFIG_JOB_STORE.append_event(
        job_id,
        _make_progress_event(
            kind="stage",
            message=f"Scanning {len(files)} file(s)",
            details={"file_count": len(files)},
        ),
    )

    try:
        service = AutoConfigService(
            Path(work_dir_str),
            event_sink=lambda event: _AUTO_CONFIG_JOB_STORE.append_event(job_id, event),
        )
        result = service.auto_configure(files)
        _AUTO_CONFIG_JOB_STORE.complete_with_event(
            job_id,
            result,
            _make_progress_event(
                kind="complete",
                message="Auto-configuration ready",
                details={
                    "dataset_count": len(
                        result.get("entities", {}).get("datasets", {})
                    ),
                    "reference_count": len(
                        result.get("entities", {}).get("references", {})
                    ),
                },
            ),
        )
    except Exception as exc:
        error_message = str(exc)
        _AUTO_CONFIG_JOB_STORE.fail_with_event(
            job_id,
            error_message,
            _make_progress_event(kind="error", message=error_message),
        )


def _sanitize_uploaded_filename(filename: str) -> str:
    """Return a safe leaf filename from a client-provided upload name."""
    sanitized = Path(filename.replace("\\", "/")).name.strip()
    if not sanitized or sanitized in {".", ".."}:
        raise ValueError("Invalid filename")
    return sanitized


def _validate_zip_member_name(filename: str) -> str:
    """Validate a ZIP entry path and return a safe extracted leaf name."""
    normalized = PurePosixPath(filename.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError("Invalid filename in archive")

    safe_name = normalized.name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("Invalid filename in archive")
    return safe_name


async def _read_uploaded_content(uploaded_file: UploadFile) -> bytes:
    """Read uploaded content with a hard size cap."""
    chunks: List[bytes] = []
    total_size = 0

    while chunk := await uploaded_file.read(1024 * 1024):
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("File exceeds maximum upload size (100 MB)")
        chunks.append(chunk)

    return b"".join(chunks)


@router.post("/upload-files")
async def upload_files(
    request: Request, files: List[Any] = File(...), overwrite: bool = False
) -> Dict[str, Any]:
    """Upload multiple files to the imports directory.

    All files are uploaded to imports/ at the root level for simplicity.

    Args:
        files: List of files to upload
        overwrite: If True, overwrite existing files. If False, skip and report existing files.

    Returns:
        Dict with uploaded file information, existing files, and any errors
    """
    require_desktop_mutation_auth(request)
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        imports_dir = work_dir / "imports"

        # Ensure directory exists
        imports_dir.mkdir(exist_ok=True)

        uploaded_files: List[UploadedFileInfo] = []
        existing_files: List[str] = []  # Track files that already exist
        errors: List[str] = []

        for uploaded_file in files:
            try:
                if not isinstance(uploaded_file, StarletteUploadFile):
                    errors.append("File without name skipped")
                    continue
                raw_filename = uploaded_file.filename
                if not raw_filename:
                    errors.append("File without name skipped")
                    continue
                filename = _sanitize_uploaded_filename(raw_filename)

                # Determine file type
                file_ext = Path(filename).suffix.lower()
                file_category = _categorize_file(file_ext)

                # All files go to imports/ root
                target_path = imports_dir / filename
                relative_path = f"imports/{filename}"

                if target_path.exists() and not overwrite:
                    existing_files.append(filename)
                    continue

                # Read and validate before replacing an existing destination.
                content = await _read_uploaded_content(uploaded_file)
                file_size = len(content)

                # Handle ZIP extraction
                if file_ext == ".zip":
                    await _handle_zip_upload(
                        content,
                        filename,
                        imports_dir,
                        uploaded_files,
                        existing_files,
                        errors,
                        overwrite=overwrite,
                    )
                else:
                    tmp_path = target_path.with_name(
                        f".{target_path.name}.{uuid.uuid4().hex}.tmp"
                    )
                    try:
                        with open(tmp_path, "xb") as f:
                            f.write(content)
                        tmp_path.replace(target_path)
                    except Exception:
                        tmp_path.unlink(missing_ok=True)
                        raise

                    uploaded_files.append(
                        UploadedFileInfo(
                            filename=filename,
                            path=relative_path,
                            size=file_size,
                            size_mb=round(file_size / (1024 * 1024), 2),
                            type=file_ext.lstrip("."),
                            category=file_category,
                        )
                    )

            except Exception as e:
                errors.append(f"Error uploading {uploaded_file.filename}: {str(e)}")

        return {
            "success": len(uploaded_files) > 0 or len(existing_files) > 0,
            "uploaded_files": [f.model_dump() for f in uploaded_files],
            "uploaded_count": len(uploaded_files),
            "existing_files": existing_files,  # List of files that already exist
            "existing_count": len(existing_files),
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def _handle_zip_upload(
    content: bytes,
    filename: str,
    target_dir: Path,
    uploaded_files: List[UploadedFileInfo],
    existing_files: List[str],
    errors: List[str],
    *,
    overwrite: bool = False,
) -> None:
    """Handle ZIP file upload (typically shapefiles)."""
    import tempfile

    # Extract ZIP to temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        with open(tmp_path, "wb") as f:
            f.write(content)

        # Extract
        try:
            with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                extracted_names = set()
                declared_uncompressed_size = 0
                extracted_size = 0
                for member in zip_ref.infolist():
                    if member.is_dir():
                        continue

                    safe_name = _validate_zip_member_name(member.filename)
                    if safe_name in extracted_names:
                        raise ValueError(f"Duplicate file name in archive: {safe_name}")

                    extracted_names.add(safe_name)
                    declared_uncompressed_size += member.file_size
                    if declared_uncompressed_size > MAX_UPLOAD_SIZE_BYTES:
                        raise ValueError("Archive exceeds maximum upload size (100 MB)")

                    dest_path = Path(tmp_dir) / safe_name
                    with (
                        zip_ref.open(member, "r") as source,
                        open(dest_path, "wb") as dest,
                    ):
                        while chunk := source.read(1024 * 1024):
                            extracted_size += len(chunk)
                            if extracted_size > MAX_UPLOAD_SIZE_BYTES:
                                raise ValueError(
                                    "Archive exceeds maximum upload size (100 MB)"
                                )
                            dest.write(chunk)

            # Find extracted files
            extracted_files = list(Path(tmp_dir).glob("*"))
            extracted_files = [
                f for f in extracted_files if f.is_file() and f.name != filename
            ]

            if not extracted_files:
                errors.append(f"No files found in {filename}")
                return

            # Create subdirectory for shapefile components
            shapefile_name = Path(filename).stem
            shapefile_dir = target_dir / shapefile_name
            shapefile_dir.mkdir(exist_ok=True)

            # Copy extracted files
            shapefile_dir_resolved = shapefile_dir.resolve()
            for extracted_file in extracted_files:
                dest = shapefile_dir / extracted_file.name
                try:
                    dest.resolve(strict=False).relative_to(shapefile_dir_resolved)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid destination path in archive: {extracted_file.name}"
                    ) from exc

                if dest.is_symlink():
                    raise ValueError(
                        f"Cannot overwrite symlinked archive member: {extracted_file.name}"
                    )

                relative_extracted_path = f"{shapefile_name}/{extracted_file.name}"
                if dest.exists() and not overwrite:
                    existing_files.append(relative_extracted_path)
                    continue

                temp_dest: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        "wb",
                        dir=shapefile_dir,
                        prefix=f".{extracted_file.name}.",
                        suffix=".tmp",
                        delete=False,
                    ) as temp_file:
                        temp_dest = Path(temp_file.name)
                        with extracted_file.open("rb") as source:
                            shutil.copyfileobj(source, temp_file)
                        temp_file.flush()
                        os.fsync(temp_file.fileno())
                    temp_dest.replace(dest)
                    shutil.copystat(extracted_file, dest)
                finally:
                    if temp_dest and temp_dest.exists():
                        temp_dest.unlink()

                uploaded_files.append(
                    UploadedFileInfo(
                        filename=extracted_file.name,
                        path=f"imports/{shapefile_name}/{extracted_file.name}",
                        size=extracted_file.stat().st_size,
                        size_mb=round(extracted_file.stat().st_size / (1024 * 1024), 2),
                        type=extracted_file.suffix.lstrip("."),
                        category="shapefile",
                    )
                )

        except zipfile.BadZipFile:
            errors.append(f"{filename} is not a valid ZIP file")
        except ValueError as exc:
            errors.append(f"{filename}: {str(exc)}")


def _categorize_file(file_ext: str) -> str:
    """Categorize file by extension."""
    ext = file_ext.lower()
    if ext == ".csv":
        return "csv"
    elif ext in [".gpkg", ".geojson"]:
        return "gpkg"
    elif ext in [".tif", ".tiff"]:
        return "tif"
    elif ext == ".zip":
        return "shapefile"
    else:
        return "other"


@router.post("/analyze-file")
async def analyze_file_smart(request: FileInfo) -> Dict[str, Any]:
    """Analyze a single file with smart pattern detection.

    Args:
        request: File information

    Returns:
        Detailed analysis with detected patterns
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir))
        analysis = await asyncio.to_thread(
            service.analyze_file,
            request.filepath,
            entity_name=request.entity_name,
        )
        return _sanitize_file_analysis_response(analysis, request.filepath)

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing file: {str(e)}")


@router.post("/detect-hierarchy")
async def detect_hierarchy(request: FileInfo) -> Dict[str, Any]:
    """Detect hierarchical patterns in a file.

    Args:
        request: File information

    Returns:
        Detected hierarchy information
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir))
        return service.detect_hierarchy(request.filepath)

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error detecting hierarchy: {str(e)}"
        )


@router.post("/detect-relationships")
async def detect_relationships(
    request: DetectRelationshipsRequest,
) -> Dict[str, Any]:
    """Detect relationships between a source file and target files.

    Args:
        request: Request containing source_file and target_files

    Returns:
        Dictionary with detected relationships
    """
    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=400, detail="Working directory not set")

        service = AutoConfigService(Path(work_dir))
        return await asyncio.to_thread(
            service.detect_relationships,
            source_file=request.source_file,
            target_files=request.target_files,
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error detecting relationships: {str(e)}"
        )


@router.post("/auto-configure", response_model=AutoConfigureResponse)
async def auto_configure(request: AutoConfigureRequest) -> AutoConfigureResponse:
    """Auto-configure entities from multiple files (CSV, GPKG, TIF).

    This is the main "magic" endpoint that analyzes all files and generates
    a complete import.yml configuration including:
    - entities.datasets (CSV with data)
    - entities.references (taxonomies, plots, shapes from GPKG)
    - metadata.layers (raster/vector layers from GPKG/TIF)

    Args:
        request: List of files to configure

    Returns:
        Complete entity configuration with spatial matching
    """
    try:
        work_dir_str = get_working_directory()
        if not work_dir_str:
            raise HTTPException(status_code=400, detail="Working directory not set")

        work_dir = Path(work_dir_str)
        _validate_import_file_paths(work_dir, request.files)

        service = AutoConfigService(work_dir)
        result = await asyncio.to_thread(service.auto_configure, request.files)
        return AutoConfigureResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in auto-configuration: {str(e)}"
        )


@router.post("/auto-configure/jobs", response_model=AutoConfigureJobStartResponse)
async def start_auto_configure_job(
    request: AutoConfigureRequest,
) -> AutoConfigureJobStartResponse:
    """Start an auto-config job and return its identifier."""
    work_dir_str = get_working_directory()
    if not work_dir_str:
        raise HTTPException(status_code=400, detail="Working directory not set")

    work_dir = Path(work_dir_str)
    _validate_import_file_paths(work_dir, request.files)

    try:
        job = _AUTO_CONFIG_JOB_STORE.create_job(str(work_dir))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    thread = threading.Thread(
        target=_run_auto_config_job,
        args=(job.job_id, str(work_dir_str), request.files),
        daemon=True,
    )
    thread.start()
    return AutoConfigureJobStartResponse(job_id=job.job_id, status=job.status)


@router.get(
    "/auto-configure/jobs/{job_id}", response_model=AutoConfigureJobStatusResponse
)
async def get_auto_configure_job(job_id: str) -> AutoConfigureJobStatusResponse:
    """Return the latest status and result for an auto-config job."""
    job = _get_project_scoped_auto_config_job(job_id)

    result = AutoConfigureResponse(**job.result) if job.result else None
    events = [AutoConfigureProgressEvent(**event) for event in job.events]
    elapsed_from = job.started_at or job.created_at
    elapsed_until = job.completed_at or time.time()
    return AutoConfigureJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        events=events,
        result=result,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        elapsed_seconds=max(0.0, elapsed_until - elapsed_from),
    )


@router.get("/auto-configure/jobs/{job_id}/events")
async def stream_auto_configure_job_events(job_id: str, request: Request):
    """Stream auto-config progress events as server-sent events."""
    _get_project_scoped_auto_config_job(job_id)

    async def event_stream():
        next_index = 0
        while True:
            try:
                current_job = _get_project_scoped_auto_config_job(job_id)
            except HTTPException:
                break

            pending_events = current_job.events[next_index:]
            for event in pending_events:
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
                next_index += 1

            if current_job.status in {"completed", "failed"} and next_index >= len(
                current_job.events
            ):
                break

            if await request.is_disconnected():
                break

            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class CreateEntitiesBulkRequest(BaseModel):
    """Request to create entities in bulk and save to import.yml."""

    entities: Dict[str, Any]  # Contains datasets, references, metadata
    auxiliary_sources: List[Dict[str, Any]] = []


@router.post("/management/entities/bulk")
async def create_entities_bulk(
    http_request: Request, request: CreateEntitiesBulkRequest
):
    """
    Create entities in bulk by saving them to config/import.yml.

    This endpoint takes the auto-configured entities and writes them
    to the config/import.yml file.

    Args:
        request: Contains entities dict with datasets, references, metadata

    Returns:
        Success status and message
    """
    require_desktop_mutation_auth(http_request)
    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    work_dir_path = Path(work_dir)
    config_dir = work_dir_path / "config"
    import_yml_path = config_dir / "import.yml"

    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    try:
        _validate_bulk_config_paths(request.entities)
        _validate_bulk_config_paths(request.auxiliary_sources)

        # Build the import.yml structure
        import_config = {
            "version": "1.0",
            "entities": {
                "datasets": request.entities.get("datasets", {}),
                "references": request.entities.get("references", {}),
            },
        }

        # Add metadata if present
        if "metadata" in request.entities:
            import_config["metadata"] = request.entities["metadata"]
        if request.auxiliary_sources:
            import_config["auxiliary_sources"] = request.auxiliary_sources

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=config_dir,
                prefix=".import.yml.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                yaml.dump(
                    import_config,
                    temp_file,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
                temp_file.flush()
                os.fsync(temp_file.fileno())

            temp_path.replace(import_yml_path)
        except Exception:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise

        dataset_count = len(request.entities.get("datasets", {}))
        reference_count = len(request.entities.get("references", {}))

        return {
            "success": True,
            "message": f"Successfully created {dataset_count} dataset(s) and {reference_count} reference(s)",
            "config_path": "config/import.yml",
            "dataset_count": dataset_count,
            "reference_count": reference_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save import configuration: {str(e)}"
        )
