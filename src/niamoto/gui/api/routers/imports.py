"""Generic import API endpoints using entity registry and typed configurations."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from pydantic import BaseModel
import uuid
from datetime import datetime, timezone

from niamoto.common.config import Config
from niamoto.common.exceptions import (
    ConfigurationError,
)
from niamoto.core.services.importer import ImporterService
from niamoto.core.imports.registry import EntityRegistry
from niamoto.core.imports.config_models import ConnectorType
from niamoto.common.table_resolver import quote_identifier
from ..utils.database import open_database

router = APIRouter()
logger = logging.getLogger(__name__)

# Import status tracking (in production, use a database)
import_jobs: Dict[str, Dict[str, Any]] = {}
MAX_IMPORT_EVENTS = 40


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_import_event(
    kind: str,
    message: str,
    *,
    phase: Optional[str] = None,
    entity_name: Optional[str] = None,
    entity_type: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "timestamp": _now_iso(),
        "kind": kind,
        "message": message,
        "phase": phase,
        "entity_name": entity_name,
        "entity_type": entity_type,
    }


def _append_import_event(job: Dict[str, Any], event: Dict[str, Any]) -> None:
    events = job.setdefault("events", [])
    events.append(event)
    if len(events) > MAX_IMPORT_EVENTS:
        del events[:-MAX_IMPORT_EVENTS]


def _set_job_state(
    job: Dict[str, Any],
    *,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    phase: Optional[str] = None,
    current_entity: Optional[str] = None,
    current_entity_type: Optional[str] = None,
) -> None:
    if message is not None:
        job["message"] = message
    if progress is not None:
        job["progress"] = progress
    if phase is not None:
        job["phase"] = phase
    if current_entity is not None:
        job["current_entity"] = current_entity
    if current_entity_type is not None:
        job["current_entity_type"] = current_entity_type


def _job_progress(processed_entities: int, total_entities: int) -> int:
    if total_entities <= 0:
        return 15
    ratio = min(max(processed_entities / total_entities, 0.0), 1.0)
    return 15 + int(ratio * 75)


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
        "phase": "pending",
        "message": "",
        "total_entities": 0,
        "processed_entities": 0,
        "current_entity": None,
        "current_entity_type": None,
        "errors": [],
        "warnings": [],
        "events": [],
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
        "phase": "pending",
        "message": "",
        "current_entity": None,
        "current_entity_type": None,
        "errors": [],
        "warnings": [],
        "events": [],
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
        "phase": "pending",
        "message": "",
        "current_entity": None,
        "current_entity_type": None,
        "errors": [],
        "warnings": [],
        "events": [],
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


class DeleteEntityRequest(BaseModel):
    """Request to delete an entity."""

    delete_table: bool = False  # Also drop the database table


@router.delete("/entities/{entity_type}/{entity_name}")
async def delete_entity(
    entity_type: str, entity_name: str, delete_table: bool = False
) -> Dict[str, Any]:
    """
    Delete an entity from import.yml configuration.

    Args:
        entity_type: Type of entity ('dataset' or 'reference')
        entity_name: Name of the entity to delete
        delete_table: If True, also drop the associated database table

    Returns:
        Success message
    """
    import yaml
    from ..context import get_working_directory

    if entity_type not in ["dataset", "reference"]:
        raise HTTPException(
            status_code=400,
            detail="entity_type must be 'dataset' or 'reference'",
        )

    work_dir = get_working_directory()
    if not work_dir:
        raise HTTPException(status_code=500, detail="Working directory not set")

    config_path = work_dir / "config" / "import.yml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="import.yml not found")

    try:
        # Read current config
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        entities = import_config.get("entities", {})
        section_key = "datasets" if entity_type == "dataset" else "references"
        section = entities.get(section_key, {})

        if entity_name not in section:
            raise HTTPException(
                status_code=404,
                detail=f"{entity_type.capitalize()} '{entity_name}' not found in configuration",
            )

        # Remove entity from config
        del section[entity_name]
        entities[section_key] = section
        import_config["entities"] = entities

        # Write updated config
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                import_config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        # Optionally drop the database table
        table_dropped = False
        if delete_table:
            try:
                config_dir = str(work_dir / "config")
                config = Config(config_dir=config_dir, create_default=False)
                with open_database(config.database_path) as db:
                    # Try different table naming conventions
                    table_names = [
                        entity_name,
                        f"reference_{entity_name}",
                        f"dataset_{entity_name}",
                    ]
                    for table_name in table_names:
                        if db.has_table(table_name):
                            quoted_table = quote_identifier(db, table_name)
                            db.execute_sql(f"DROP TABLE IF EXISTS {quoted_table}")
                            table_dropped = True
                            break
            except Exception as e:
                # Log but don't fail - config was already updated
                logger.warning(
                    "Could not drop table for entity '%s': %s", entity_name, e
                )

        return {
            "success": True,
            "message": f"{entity_type.capitalize()} '{entity_name}' deleted successfully",
            "table_dropped": table_dropped,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting entity: {str(e)}")


@router.get("/entities")
async def list_entities() -> Dict[str, Any]:
    """List all entities defined in import.yml configuration with their actual table names."""
    from pathlib import Path
    from ..context import get_working_directory

    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=500, detail="Working directory not set")

        config_dir = str(work_dir / "config")
        config = Config(config_dir=config_dir, create_default=False)
        generic_config = config.get_imports_config

        # Get table names from EntityRegistry if available
        table_name_map: Dict[str, str] = {}
        try:
            db_path = Path(config.database_path)
            if db_path.exists():
                with open_database(config.database_path) as db:
                    # Check if registry table exists before querying
                    if db.has_table(EntityRegistry.ENTITIES_TABLE):
                        registry = EntityRegistry(db)
                        for entity in registry.list_entities():
                            table_name_map[entity.name] = entity.table_name
        except Exception as exc:
            logger.debug("Could not read entity registry for list_entities: %s", exc)

        references = []
        datasets = []

        if generic_config.entities:
            # List references
            if generic_config.entities.references:
                for name, ref_config in generic_config.entities.references.items():
                    # Get actual table name from registry, fallback to convention
                    table_name = table_name_map.get(name, f"reference_{name}")
                    references.append(
                        {
                            "name": name,
                            "table_name": table_name,
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
                    # Get actual table name from registry, fallback to convention
                    table_name = table_name_map.get(name, f"dataset_{name}")
                    datasets.append(
                        {
                            "name": name,
                            "table_name": table_name,
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

    except ConfigurationError:
        # No import.yml or empty config - return empty lists
        return {
            "references": [],
            "datasets": [],
        }


@router.get("/status", response_model=ImportStatusResponse)
async def get_import_status() -> ImportStatusResponse:
    """Check which entities have been imported and their row counts."""
    from ..context import get_working_directory

    try:
        work_dir = get_working_directory()
        if not work_dir:
            raise HTTPException(status_code=500, detail="Working directory not set")

        config_dir = str(work_dir / "config")
        config = Config(config_dir=config_dir, create_default=False)
        references: List[ImportStatus] = []
        datasets: List[ImportStatus] = []

        with open_database(config.database_path) as db:
            registry = EntityRegistry(db)

            for entity in registry.list_all():
                row_count = 0
                is_imported = False

                if db.has_table(entity.table_name):
                    try:
                        quoted_table_name = quote_identifier(db, entity.table_name)
                        count_row = db.execute_sql(
                            f"SELECT COUNT(*) FROM {quoted_table_name}", fetch=True
                        )
                        row_count = count_row[0] if count_row else 0
                        is_imported = row_count > 0
                    except Exception as exc:
                        logger.debug(
                            "Could not count rows for entity '%s' (table '%s'): %s",
                            entity.name,
                            entity.table_name,
                            exc,
                        )

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

        return ImportStatusResponse(references=references, datasets=datasets)

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
    from ..context import get_working_directory

    # Disable progress bars in API mode
    set_progress_mode(use_progress_bar=False)

    job = import_jobs[job_id]

    try:
        # Update job status
        job["status"] = "running"
        job["started_at"] = _now_iso()
        _set_job_state(
            job, progress=5, phase="loading", message="Loading import configuration..."
        )
        _append_import_event(
            job,
            _make_import_event(
                "stage",
                "Loading import configuration...",
                phase="loading",
            ),
        )

        # Get config and create importer using working directory
        work_dir = get_working_directory()
        if not work_dir:
            raise ValueError("Working directory not set")

        config_dir = str(work_dir / "config")
        config = Config(config_dir=config_dir, create_default=False)
        generic_config = config.get_imports_config
        importer = ImporterService(config.database_path)

        try:
            entities = generic_config.entities
            datasets = entities.datasets if entities and entities.datasets else {}
            references = entities.references if entities and entities.references else {}

            derived_refs = {
                name: cfg
                for name, cfg in references.items()
                if cfg.connector.type == ConnectorType.DERIVED
            }
            direct_refs = {
                name: cfg
                for name, cfg in references.items()
                if cfg.connector.type != ConnectorType.DERIVED
            }

            execution_plan: List[tuple[str, str, Any]] = [
                *[("dataset", name, cfg) for name, cfg in datasets.items()],
                *[("reference", name, cfg) for name, cfg in derived_refs.items()],
                *[("reference", name, cfg) for name, cfg in direct_refs.items()],
            ]

            total_entities = len(execution_plan)
            job["total_entities"] = total_entities
            _set_job_state(
                job,
                progress=10,
                phase="importing",
                message=f"Starting import for {total_entities} entities...",
            )
            _append_import_event(
                job,
                _make_import_event(
                    "stage",
                    f"Starting import for {total_entities} entities...",
                    phase="importing",
                ),
            )

            if total_entities == 0:
                _append_import_event(
                    job,
                    _make_import_event(
                        "finding",
                        "No entities found to import.",
                        phase="completed",
                    ),
                )
                result = "No entities imported"
            else:
                results: List[str] = []
                for index, (entity_type, entity_name, entity_config) in enumerate(
                    execution_plan, start=1
                ):
                    _set_job_state(
                        job,
                        progress=_job_progress(index - 1, total_entities),
                        phase="importing",
                        message=f"Importing {entity_name} ({index}/{total_entities})...",
                        current_entity=entity_name,
                        current_entity_type=entity_type,
                    )
                    _append_import_event(
                        job,
                        _make_import_event(
                            "detail",
                            f"Importing {entity_name} ({index}/{total_entities})...",
                            phase="importing",
                            entity_name=entity_name,
                            entity_type=entity_type,
                        ),
                    )

                    if entity_type == "dataset":
                        entity_result = await asyncio.to_thread(
                            importer.import_dataset,
                            entity_name,
                            entity_config,
                            reset_table,
                        )
                    else:
                        entity_result = await asyncio.to_thread(
                            importer.import_reference,
                            entity_name,
                            entity_config,
                            reset_table,
                        )

                    results.append(entity_result)
                    job["processed_entities"] = index
                    _set_job_state(
                        job,
                        progress=_job_progress(index, total_entities),
                        phase="importing",
                        message=f"Imported {entity_name}",
                        current_entity=entity_name,
                        current_entity_type=entity_type,
                    )
                    _append_import_event(
                        job,
                        _make_import_event(
                            "finding",
                            f"Imported {entity_name}",
                            phase="importing",
                            entity_name=entity_name,
                            entity_type=entity_type,
                        ),
                    )

                db = importer.db
                if getattr(db, "is_duckdb", False):
                    _set_job_state(
                        job,
                        progress=95,
                        phase="finalizing",
                        message="Finalizing DuckDB database...",
                    )
                    _append_import_event(
                        job,
                        _make_import_event(
                            "detail",
                            "Finalizing DuckDB database...",
                            phase="finalizing",
                        ),
                    )
                    db.optimize_database()

                result = (
                    "Import completed successfully:\n" + "\n".join(results)
                    if results
                    else "No entities imported"
                )

            # Auto-scaffold transform.yml et export.yml (non-fatal)
            try:
                from niamoto.gui.api.services.templates.config_scaffold import (
                    scaffold_configs,
                )

                _set_job_state(
                    job,
                    progress=97,
                    phase="finalizing",
                    message="Updating transform and export configuration...",
                )
                _append_import_event(
                    job,
                    _make_import_event(
                        "detail",
                        "Updating transform and export configuration...",
                        phase="finalizing",
                    ),
                )
                changed, msg = scaffold_configs(work_dir)
                if changed:
                    logger.info("Auto-scaffold configs: %s", msg)
            except Exception as e:
                logger.warning("Config scaffold failed (non-fatal): %s", e)

            # Invalider le cache du moteur de preview (données changées)
            try:
                from niamoto.gui.api.services.preview_engine.engine import (
                    get_preview_engine,
                )

                engine = get_preview_engine()
                if engine:
                    engine.invalidate()
            except Exception as e:
                logger.warning("Preview engine invalidation failed (non-fatal): %s", e)

            # Mark as completed
            job["status"] = "completed"
            job["completed_at"] = _now_iso()
            _set_job_state(
                job,
                progress=100,
                phase="completed",
                message="Import completed successfully",
                current_entity=None,
                current_entity_type=None,
            )
            job["processed_entities"] = total_entities
            job["result"] = {"summary": result}
            _append_import_event(
                job,
                _make_import_event(
                    "complete",
                    "Import completed successfully",
                    phase="completed",
                ),
            )

        finally:
            # Always close database connections
            importer.close()

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = _now_iso()
        job["errors"].append(str(e))
        _set_job_state(job, phase="failed", message=f"Import failed: {str(e)}")
        _append_import_event(
            job,
            _make_import_event(
                "error",
                f"Import failed: {str(e)}",
                phase="failed",
                entity_name=job.get("current_entity"),
                entity_type=job.get("current_entity_type"),
            ),
        )

        logger.exception("Import-all job '%s' failed: %s", job_id, e)


async def process_generic_import_entity(
    job_id: str,
    entity_name: str,
    entity_type: str,  # 'reference' or 'dataset'
    reset_table: bool,
):
    """Process generic import of a single entity in background."""
    import asyncio
    from niamoto.common.progress import set_progress_mode
    from ..context import get_working_directory

    # Disable progress bars in API mode
    set_progress_mode(use_progress_bar=False)

    job = import_jobs[job_id]

    try:
        # Update job status
        job["status"] = "running"
        job["started_at"] = _now_iso()
        _set_job_state(
            job,
            progress=5,
            phase="loading",
            message=f"Loading configuration for {entity_name}...",
            current_entity=entity_name,
            current_entity_type=entity_type,
        )
        _append_import_event(
            job,
            _make_import_event(
                "stage",
                f"Loading configuration for {entity_name}...",
                phase="loading",
                entity_name=entity_name,
                entity_type=entity_type,
            ),
        )

        # Get config and create importer using working directory
        work_dir = get_working_directory()
        if not work_dir:
            raise ValueError("Working directory not set")

        config_dir = str(work_dir / "config")
        config = Config(config_dir=config_dir, create_default=False)
        generic_config = config.get_imports_config
        importer = ImporterService(config.database_path)

        try:
            _set_job_state(
                job,
                progress=20,
                phase="importing",
                message=f"Importing {entity_name}...",
                current_entity=entity_name,
                current_entity_type=entity_type,
            )
            _append_import_event(
                job,
                _make_import_event(
                    "detail",
                    f"Importing {entity_name}...",
                    phase="importing",
                    entity_name=entity_name,
                    entity_type=entity_type,
                ),
            )

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
            job["completed_at"] = _now_iso()
            _set_job_state(
                job,
                progress=100,
                phase="completed",
                message=f"Import of {entity_name} completed successfully",
            )
            job["result"] = {"summary": result}
            _append_import_event(
                job,
                _make_import_event(
                    "complete",
                    f"Import of {entity_name} completed successfully",
                    phase="completed",
                    entity_name=entity_name,
                    entity_type=entity_type,
                ),
            )

            # Invalider le cache du moteur de preview (données changées)
            try:
                from niamoto.gui.api.services.preview_engine.engine import (
                    get_preview_engine,
                )

                engine = get_preview_engine()
                if engine:
                    engine.invalidate()
            except Exception as e:
                logger.warning("Preview engine invalidation failed (non-fatal): %s", e)

        finally:
            # Always close database connections
            importer.close()

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = _now_iso()
        job["errors"].append(str(e))
        _set_job_state(job, phase="failed", message=f"Import failed: {str(e)}")
        _append_import_event(
            job,
            _make_import_event(
                "error",
                f"Import failed: {str(e)}",
                phase="failed",
                entity_name=entity_name,
                entity_type=entity_type,
            ),
        )

        logger.exception(
            "Import job '%s' failed for %s '%s': %s",
            job_id,
            entity_type,
            entity_name,
            e,
        )


# ---------------------------------------------------------------------------
# Pre-Import Impact Check
# ---------------------------------------------------------------------------


class ImpactCheckRequest(BaseModel):
    file_path: str  # relative to project root


class ImpactItemResponse(BaseModel):
    column: str
    level: str
    detail: str
    referenced_in: List[str] = []
    old_type: Optional[str] = None
    new_type: Optional[str] = None


class ColumnMatchResponse(BaseModel):
    name: str
    old_type: str
    new_type: str


class ImpactCheckResponse(BaseModel):
    entity_name: Optional[str] = None
    matched_columns: List[ColumnMatchResponse] = []
    impacts: List[ImpactItemResponse] = []
    error: Optional[str] = None
    skipped_reason: Optional[str] = None
    info_message: Optional[str] = None
    has_blockers: bool = False
    has_warnings: bool = False
    has_opportunities: bool = False


@router.post("/impact-check", response_model=ImpactCheckResponse)
async def impact_check(request: ImpactCheckRequest):
    """Check compatibility between a source file and existing configuration.

    Resolves the entity from the file path basename, then runs the impact
    check against import.yml + transform.yml.
    """
    from pathlib import Path

    from ..context import get_working_directory
    from niamoto.core.services.compatibility import CompatibilityService

    work_dir = get_working_directory()

    # Path validation FIRST
    resolved = (work_dir / request.file_path).resolve()
    if not resolved.is_relative_to(work_dir.resolve()):
        raise HTTPException(status_code=400, detail="Path outside project directory")

    service = CompatibilityService(work_dir)
    filename = Path(request.file_path).name
    entity_name = service.resolve_entity(filename)

    if entity_name is None:
        return ImpactCheckResponse()

    report = service.check_compatibility(entity_name, request.file_path)
    return ImpactCheckResponse(
        entity_name=report.entity_name,
        matched_columns=[
            ColumnMatchResponse(name=m.name, old_type=m.old_type, new_type=m.new_type)
            for m in report.matched_columns
        ],
        impacts=[
            ImpactItemResponse(
                column=i.column,
                level=i.level.value,
                detail=i.detail,
                referenced_in=i.referenced_in,
                old_type=i.old_type,
                new_type=i.new_type,
            )
            for i in report.impacts
        ],
        error=report.error,
        skipped_reason=report.skipped_reason,
        info_message=getattr(report, "info_message", None),
        has_blockers=report.has_blockers,
        has_warnings=report.has_warnings,
        has_opportunities=report.has_opportunities,
    )
