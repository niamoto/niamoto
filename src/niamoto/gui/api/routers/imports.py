"""Import API endpoints for validating and executing imports."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Form
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile
import uuid
import json
from datetime import datetime

router = APIRouter()

# Import status tracking (in production, use a database)
import_jobs: Dict[str, Dict[str, Any]] = {}


class ImportValidationRequest(BaseModel):
    """Request model for import validation."""

    import_type: str = Field(
        ..., description="Type of import: taxonomy, plots, occurrences, shapes"
    )
    file_name: str = Field(..., description="Name of the file to import")
    field_mappings: Dict[str, str] = Field(
        ..., description="Mapping of database fields to file columns"
    )
    advanced_options: Optional[Dict[str, Any]] = Field(
        default=None, description="Advanced import options"
    )


class ImportExecutionRequest(BaseModel):
    """Request model for import execution."""

    import_type: str
    file_name: str
    field_mappings: Dict[str, str]
    advanced_options: Optional[Dict[str, Any]] = None
    validate_only: bool = Field(
        default=False, description="Only validate without executing"
    )


class ImportValidationResponse(BaseModel):
    """Response model for import validation."""

    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    summary: Dict[str, Any] = {}


class ImportJobResponse(BaseModel):
    """Response model for import job creation."""

    job_id: str
    status: str
    created_at: str
    message: str


@router.post("/validate", response_model=ImportValidationResponse)
async def validate_import(
    file: UploadFile = File(...),
    import_type: str = Form(...),
    file_name: str = Form(...),
    field_mappings: str = Form(...),
    advanced_options: Optional[str] = Form(None),
) -> ImportValidationResponse:
    """Validate an import configuration without executing it."""

    # Parse JSON fields
    try:
        field_mappings_dict = json.loads(field_mappings) if field_mappings else {}
        advanced_options_dict = json.loads(advanced_options) if advanced_options else {}
    except json.JSONDecodeError:
        return ImportValidationResponse(
            valid=False,
            errors=["Invalid JSON in field mappings or advanced options"],
            summary={},
        )

    errors = []
    warnings = []
    summary = {
        "import_type": import_type,
        "file_name": file_name,
        "mapped_fields": len(field_mappings_dict),
    }

    # Validate import type
    valid_types = ["taxonomy", "plots", "occurrences", "shapes"]
    if import_type not in valid_types:
        errors.append(f"Invalid import type: {import_type}")

    # Validate required fields are mapped
    required_fields = get_required_fields(import_type)
    missing_fields = []

    for field in required_fields:
        if field not in field_mappings_dict:
            missing_fields.append(field)

    if missing_fields:
        errors.append(f"Missing required field mappings: {', '.join(missing_fields)}")

    # Validate file
    if file.size == 0:
        errors.append("File is empty")
    elif file.size > 100 * 1024 * 1024:  # 100MB limit
        warnings.append(
            f"Large file size ({file.size / 1024 / 1024:.1f}MB) may take time to process"
        )

    # Type-specific validation
    if import_type == "taxonomy":
        validate_taxonomy_options(advanced_options_dict, errors, warnings)
    elif import_type == "plots":
        validate_plots_options(advanced_options_dict, errors, warnings)
    elif import_type == "occurrences":
        validate_occurrences_options(advanced_options_dict, errors, warnings)
    elif import_type == "shapes":
        validate_shapes_options(advanced_options_dict, errors, warnings)

    # Add summary statistics
    summary["validation_errors"] = len(errors)
    summary["validation_warnings"] = len(warnings)

    return ImportValidationResponse(
        valid=len(errors) == 0, errors=errors, warnings=warnings, summary=summary
    )


@router.post("/execute", response_model=ImportJobResponse)
async def execute_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    import_type: str = Form(...),
    file_name: str = Form(...),
    field_mappings: str = Form(...),
    advanced_options: Optional[str] = Form(None),
    validate_only: bool = Form(False),
) -> ImportJobResponse:
    """Execute an import job asynchronously."""

    # Parse JSON fields
    try:
        field_mappings_dict = json.loads(field_mappings) if field_mappings else {}
        advanced_options_dict = json.loads(advanced_options) if advanced_options else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid JSON in field mappings or advanced options"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file temporarily
    temp_dir = Path(tempfile.gettempdir()) / "niamoto_imports"
    temp_dir.mkdir(exist_ok=True)

    file_path = temp_dir / f"{job_id}_{file.filename}"
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    # Create job record
    job = {
        "id": job_id,
        "status": "pending",
        "import_type": import_type,
        "file_name": file_name,
        "file_path": str(file_path),
        "field_mappings": field_mappings_dict,
        "advanced_options": advanced_options_dict,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "total_records": 0,
        "processed_records": 0,
        "errors": [],
        "warnings": [],
    }

    import_jobs[job_id] = job

    # Queue background import task
    background_tasks.add_task(
        process_import,
        job_id,
        import_type,
        str(file_path),
        field_mappings_dict,
        advanced_options_dict,
    )

    return ImportJobResponse(
        job_id=job_id,
        status="pending",
        created_at=job["created_at"],
        message=f"Import job {job_id} created successfully",
    )


@router.get("/jobs/{job_id}")
async def get_import_status(job_id: str) -> Dict[str, Any]:
    """Get the status of an import job."""

    if job_id not in import_jobs:
        raise HTTPException(status_code=404, detail=f"Import job {job_id} not found")

    return import_jobs[job_id]


@router.get("/jobs")
async def list_import_jobs(
    limit: int = 10, offset: int = 0, status: Optional[str] = None
) -> Dict[str, Any]:
    """List all import jobs with optional filtering."""

    jobs = list(import_jobs.values())

    # Filter by status if provided
    if status:
        jobs = [j for j in jobs if j["status"] == status]

    # Sort by created_at descending
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    # Apply pagination
    total = len(jobs)
    jobs = jobs[offset : offset + limit]

    return {"total": total, "limit": limit, "offset": offset, "jobs": jobs}


def get_required_fields(import_type: str) -> List[str]:
    """Get required fields for each import type."""

    required_fields = {
        "taxonomy": ["taxon_id", "full_name"],
        "plots": ["identifier", "locality"],
        "occurrences": ["taxon_id"],
        "shapes": ["name"],
    }

    return required_fields.get(import_type, [])


def validate_taxonomy_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate taxonomy-specific options."""

    if not options:
        return

    if options.get("useApiEnrichment"):
        api_provider = options.get("apiProvider")
        if api_provider not in ["gbif", "powo", "none"]:
            errors.append(f"Invalid API provider: {api_provider}")

        rate_limit = options.get("rateLimit", 1)
        if rate_limit > 5:
            warnings.append("High API rate limit may cause rate limiting from provider")


def validate_plots_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate plots-specific options."""

    if not options:
        return

    if options.get("importHierarchy"):
        delimiter = options.get("hierarchyDelimiter")
        if not delimiter:
            errors.append("Hierarchy delimiter is required when importing hierarchy")


def validate_occurrences_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate occurrences-specific options."""

    if not options:
        return

    duplicate_strategy = options.get("duplicateStrategy", "skip")
    if duplicate_strategy not in ["skip", "update", "error"]:
        errors.append(f"Invalid duplicate strategy: {duplicate_strategy}")


def validate_shapes_options(
    options: Optional[Dict[str, Any]], errors: List[str], warnings: List[str]
):
    """Validate shapes-specific options."""

    if not options:
        return

    if options.get("simplifyGeometry"):
        tolerance = options.get("toleranceMeters", 10)
        if tolerance > 100:
            warnings.append(
                "High simplification tolerance may result in loss of detail"
            )


async def process_import(
    job_id: str,
    import_type: str,
    file_path: str,
    field_mappings: Dict[str, str],
    advanced_options: Optional[Dict[str, Any]],
):
    """Process import in background (placeholder implementation)."""

    import asyncio
    import random

    job = import_jobs[job_id]

    try:
        # Update job status
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat()

        # Simulate processing with progress updates
        total_records = random.randint(100, 1000)
        job["total_records"] = total_records

        for i in range(0, total_records, 10):
            # Simulate processing delay
            await asyncio.sleep(0.1)

            # Update progress
            job["processed_records"] = min(i + 10, total_records)
            job["progress"] = int((job["processed_records"] / total_records) * 100)

            # Simulate occasional warnings
            if random.random() < 0.1:
                job["warnings"].append(f"Warning at record {i}: Sample warning message")

        # Mark as completed
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["progress"] = 100

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["errors"].append(str(e))

    finally:
        # Clean up temporary file
        try:
            Path(file_path).unlink()
        except OSError:
            pass
