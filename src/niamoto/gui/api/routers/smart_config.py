"""Smart configuration endpoints for auto-detecting and configuring entities.

All endpoints in this router use get_working_directory() from GUI context
to ensure file operations happen in the correct project directory.
"""

import asyncio
import json
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

from niamoto.core.imports.auto_config_service import AutoConfigService
from niamoto.gui.api.context import get_working_directory

router = APIRouter()

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024


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

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status: Literal["pending", "running", "completed", "failed"] = "pending"
        self.events: List[Dict[str, Any]] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None


class _AutoConfigureJobStore:
    """Tiny in-memory job store for long-running auto-config analysis."""

    def __init__(self):
        self._jobs: Dict[str, _AutoConfigureJob] = {}
        self._lock = threading.Lock()

    def create_job(self) -> _AutoConfigureJob:
        job = _AutoConfigureJob(job_id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[_AutoConfigureJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def append_event(self, job_id: str, event: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.events.append(event)

    def set_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "running"

    def complete(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.error = error


_AUTO_CONFIG_JOB_STORE = _AutoConfigureJobStore()


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
        _AUTO_CONFIG_JOB_STORE.complete(job_id, result)
        _AUTO_CONFIG_JOB_STORE.append_event(
            job_id,
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
        _AUTO_CONFIG_JOB_STORE.fail(job_id, error_message)
        _AUTO_CONFIG_JOB_STORE.append_event(
            job_id,
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
    files: List[UploadFile] = File(...), overwrite: bool = False
) -> Dict[str, Any]:
    """Upload multiple files to the imports directory.

    All files are uploaded to imports/ at the root level for simplicity.

    Args:
        files: List of files to upload
        overwrite: If True, overwrite existing files. If False, skip and report existing files.

    Returns:
        Dict with uploaded file information, existing files, and any errors
    """
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

                # Check if file already exists BEFORE reading content (performance optimization)
                if target_path.exists():
                    if not overwrite:
                        # Don't overwrite - add to existing_files list
                        existing_files.append(filename)
                        continue
                    else:
                        # Overwrite - delete existing file first
                        target_path.unlink()

                # Save file - only read if file doesn't exist or we're overwriting
                content = await _read_uploaded_content(uploaded_file)
                file_size = len(content)

                # Handle ZIP extraction
                if file_ext == ".zip":
                    await _handle_zip_upload(
                        content, filename, imports_dir, uploaded_files, errors
                    )
                else:
                    # Write file to disk
                    with open(target_path, "wb") as f:
                        f.write(content)

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
    errors: List[str],
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
                for member in zip_ref.infolist():
                    if member.is_dir():
                        continue

                    safe_name = _validate_zip_member_name(member.filename)
                    if safe_name in extracted_names:
                        raise ValueError(f"Duplicate file name in archive: {safe_name}")

                    extracted_names.add(safe_name)
                    dest_path = Path(tmp_dir) / safe_name
                    with (
                        zip_ref.open(member, "r") as source,
                        open(dest_path, "wb") as dest,
                    ):
                        shutil.copyfileobj(source, dest)

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
            for extracted_file in extracted_files:
                dest = shapefile_dir / extracted_file.name
                shutil.copy2(extracted_file, dest)

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
        return service.analyze_file(request.filepath)

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
        return service.detect_relationships(
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

        service = AutoConfigService(Path(work_dir_str))
        result = service.auto_configure(request.files)
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

    job = _AUTO_CONFIG_JOB_STORE.create_job()
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
    job = _AUTO_CONFIG_JOB_STORE.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Auto-config job not found")

    result = AutoConfigureResponse(**job.result) if job.result else None
    events = [AutoConfigureProgressEvent(**event) for event in job.events]
    return AutoConfigureJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        events=events,
        result=result,
        error=job.error,
    )


@router.get("/auto-configure/jobs/{job_id}/events")
async def stream_auto_configure_job_events(job_id: str, request: Request):
    """Stream auto-config progress events as server-sent events."""
    job = _AUTO_CONFIG_JOB_STORE.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Auto-config job not found")

    async def event_stream():
        next_index = 0
        while True:
            current_job = _AUTO_CONFIG_JOB_STORE.get_job(job_id)
            if not current_job:
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
async def create_entities_bulk(request: CreateEntitiesBulkRequest):
    """
    Create entities in bulk by saving them to config/import.yml.

    This endpoint takes the auto-configured entities and writes them
    to the config/import.yml file.

    Args:
        request: Contains entities dict with datasets, references, metadata

    Returns:
        Success status and message
    """
    import yaml

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    work_dir_path = Path(work_dir)
    config_dir = work_dir_path / "config"
    import_yml_path = config_dir / "import.yml"

    # Ensure config directory exists
    config_dir.mkdir(parents=True, exist_ok=True)

    try:
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

        # Write to import.yml
        with open(import_yml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                import_config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        dataset_count = len(request.entities.get("datasets", {}))
        reference_count = len(request.entities.get("references", {}))

        return {
            "success": True,
            "message": f"Successfully created {dataset_count} dataset(s) and {reference_count} reference(s)",
            "config_path": str(import_yml_path),
            "dataset_count": dataset_count,
            "reference_count": reference_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save import configuration: {str(e)}"
        )
