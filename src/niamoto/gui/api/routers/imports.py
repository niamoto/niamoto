"""Generic import API endpoints using entity registry and typed configurations."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from pydantic import BaseModel
import uuid
from datetime import datetime

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import (
    ConfigurationError,
)
from niamoto.core.services.importer import ImporterService
from niamoto.core.imports.registry import EntityRegistry

router = APIRouter()

# Import status tracking (in production, use a database)
import_jobs: Dict[str, Dict[str, Any]] = {}


class ImportStatus(BaseModel):
    """Status of a particular entity import."""

    entity_name: str
    entity_type: str  # 'reference' or 'dataset'
    is_imported: bool
    row_count: int = 0


class ImportStatusResponse(BaseModel):
    """Response containing status of all imports."""

    references: List[ImportStatus] = []
    datasets: List[ImportStatus] = []


class ImportJobResponse(BaseModel):
    """Response model for import job creation."""

    job_id: str
    status: str
    created_at: str
    message: str


@router.post("/execute/all", response_model=ImportJobResponse)
async def execute_import_all(
    background_tasks: BackgroundTasks,
    reset_table: bool = Form(False),
) -> ImportJobResponse:
    """Execute import of all entities from generic configuration."""

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create job record
    job = {
        "id": job_id,
        "status": "pending",
        "import_type": "all",
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "total_entities": 0,
        "processed_entities": 0,
        "errors": [],
        "warnings": [],
    }

    import_jobs[job_id] = job

    # Queue background import task
    background_tasks.add_task(
        process_generic_import_all,
        job_id,
        reset_table,
    )

    return ImportJobResponse(
        job_id=job_id,
        status="pending",
        created_at=job["created_at"],
        message=f"Import job {job_id} created successfully",
    )


@router.post("/execute/reference/{entity_name}", response_model=ImportJobResponse)
async def execute_import_reference(
    entity_name: str,
    background_tasks: BackgroundTasks,
    reset_table: bool = Form(False),
) -> ImportJobResponse:
    """Execute import of a specific reference entity."""

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create job record
    job = {
        "id": job_id,
        "status": "pending",
        "import_type": "reference",
        "entity_name": entity_name,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "errors": [],
        "warnings": [],
    }

    import_jobs[job_id] = job

    # Queue background import task
    background_tasks.add_task(
        process_generic_import_entity,
        job_id,
        entity_name,
        "reference",
        reset_table,
    )

    return ImportJobResponse(
        job_id=job_id,
        status="pending",
        created_at=job["created_at"],
        message=f"Import job {job_id} for reference '{entity_name}' created",
    )


@router.post("/execute/dataset/{entity_name}", response_model=ImportJobResponse)
async def execute_import_dataset(
    entity_name: str,
    background_tasks: BackgroundTasks,
    reset_table: bool = Form(False),
) -> ImportJobResponse:
    """Execute import of a specific dataset entity."""

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create job record
    job = {
        "id": job_id,
        "status": "pending",
        "import_type": "dataset",
        "entity_name": entity_name,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "progress": 0,
        "errors": [],
        "warnings": [],
    }

    import_jobs[job_id] = job

    # Queue background import task
    background_tasks.add_task(
        process_generic_import_entity,
        job_id,
        entity_name,
        "dataset",
        reset_table,
    )

    return ImportJobResponse(
        job_id=job_id,
        status="pending",
        created_at=job["created_at"],
        message=f"Import job {job_id} for dataset '{entity_name}' created",
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
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


@router.get("/entities")
async def list_entities() -> Dict[str, Any]:
    """List all entities defined in import.yml configuration."""

    try:
        config = Config()
        generic_config = config.get_imports_config

        references = []
        datasets = []

        if generic_config.entities:
            # List references
            if generic_config.entities.references:
                for name, ref_config in generic_config.entities.references.items():
                    references.append(
                        {
                            "name": name,
                            "kind": ref_config.kind or "generic",
                            "connector_type": ref_config.connector.type
                            if ref_config.connector
                            else "N/A",
                            "path": ref_config.connector.path
                            if ref_config.connector
                            else "N/A",
                        }
                    )

            # List datasets
            if generic_config.entities.datasets:
                for name, ds_config in generic_config.entities.datasets.items():
                    datasets.append(
                        {
                            "name": name,
                            "connector_type": ds_config.connector.type
                            if ds_config.connector
                            else "N/A",
                            "path": ds_config.connector.path
                            if ds_config.connector
                            else "N/A",
                            "links": len(ds_config.links) if ds_config.links else 0,
                        }
                    )

        return {
            "references": references,
            "datasets": datasets,
        }

    except ConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration error: {e.message}. Details: {e.details}",
        )


@router.get("/status", response_model=ImportStatusResponse)
async def get_import_status() -> ImportStatusResponse:
    """Check which entities have been imported and their row counts."""

    try:
        config = Config()
        db = Database(config.database_path)
        registry = EntityRegistry(db)

        references = []
        datasets = []

        # Get all registered entities from registry
        for entity in registry.list_all():
            row_count = 0
            is_imported = False

            if db.has_table(entity.table_name):
                try:
                    count_row = db.execute_sql(
                        f"SELECT COUNT(*) FROM {entity.table_name}", fetch=True
                    )
                    row_count = count_row[0] if count_row else 0
                    is_imported = row_count > 0
                except Exception:
                    pass

            status = ImportStatus(
                entity_name=entity.name,
                entity_type=entity.kind.value if entity.kind else "unknown",
                is_imported=is_imported,
                row_count=row_count,
            )

            if entity.kind.value == "REFERENCE":
                references.append(status)
            else:
                datasets.append(status)

        return ImportStatusResponse(
            references=references,
            datasets=datasets,
        )

    except Exception:
        # Return empty status on error
        return ImportStatusResponse(
            references=[],
            datasets=[],
        )


async def process_generic_import_all(
    job_id: str,
    reset_table: bool,
):
    """Process generic import of all entities in background."""
    import asyncio
    from niamoto.common.progress import set_progress_mode

    # Disable progress bars in API mode
    set_progress_mode(use_progress_bar=False)

    job = import_jobs[job_id]

    try:
        # Update job status
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat()
        job["progress"] = 10
        job["message"] = "Loading configuration..."

        # Get config and create importer
        config = Config()
        generic_config = config.get_imports_config
        importer = ImporterService(config.database_path)

        # Count total entities
        total_entities = 0
        if generic_config.entities:
            if generic_config.entities.references:
                total_entities += len(generic_config.entities.references)
            if generic_config.entities.datasets:
                total_entities += len(generic_config.entities.datasets)

        job["total_entities"] = total_entities
        job["progress"] = 20
        job["message"] = f"Importing {total_entities} entities..."

        # Import all entities
        result = await asyncio.to_thread(
            importer.import_all,
            generic_config,
            reset_table=reset_table,
        )

        # Mark as completed
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["progress"] = 100
        job["processed_entities"] = total_entities
        job["message"] = "Import completed successfully"
        job["result"] = {"summary": result}

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["errors"].append(str(e))
        job["message"] = f"Import failed: {str(e)}"

        import traceback

        print(f"Import failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")


async def process_generic_import_entity(
    job_id: str,
    entity_name: str,
    entity_type: str,  # 'reference' or 'dataset'
    reset_table: bool,
):
    """Process generic import of a single entity in background."""
    import asyncio
    from niamoto.common.progress import set_progress_mode

    # Disable progress bars in API mode
    set_progress_mode(use_progress_bar=False)

    job = import_jobs[job_id]

    try:
        # Update job status
        job["status"] = "running"
        job["started_at"] = datetime.utcnow().isoformat()
        job["progress"] = 10
        job["message"] = f"Loading configuration for {entity_name}..."

        # Get config and create importer
        config = Config()
        generic_config = config.get_imports_config
        importer = ImporterService(config.database_path)

        job["progress"] = 30
        job["message"] = f"Importing {entity_name}..."

        # Import based on type
        if entity_type == "reference":
            if (
                not generic_config.entities
                or entity_name not in generic_config.entities.references
            ):
                raise ConfigurationError(
                    config_key=f"entities.references.{entity_name}",
                    message=f"Reference '{entity_name}' not found in configuration",
                )

            ref_config = generic_config.entities.references[entity_name]
            result = await asyncio.to_thread(
                importer.import_reference,
                entity_name,
                ref_config,
                reset_table=reset_table,
            )
        else:  # dataset
            if (
                not generic_config.entities
                or entity_name not in generic_config.entities.datasets
            ):
                raise ConfigurationError(
                    config_key=f"entities.datasets.{entity_name}",
                    message=f"Dataset '{entity_name}' not found in configuration",
                )

            ds_config = generic_config.entities.datasets[entity_name]
            result = await asyncio.to_thread(
                importer.import_dataset,
                entity_name,
                ds_config,
                reset_table=reset_table,
            )

        # Mark as completed
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["progress"] = 100
        job["message"] = f"Import of {entity_name} completed successfully"
        job["result"] = {"summary": result}

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["errors"].append(str(e))
        job["message"] = f"Import failed: {str(e)}"

        import traceback

        print(f"Import failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
