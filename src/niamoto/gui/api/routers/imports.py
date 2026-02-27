"""Generic import API endpoints using entity registry and typed configurations."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from pydantic import BaseModel
import uuid
from datetime import datetime

from niamoto.common.config import Config
from niamoto.common.exceptions import (
    ConfigurationError,
)
from niamoto.core.services.importer import ImporterService
from niamoto.core.imports.registry import EntityRegistry
from niamoto.common.table_resolver import quote_identifier
from ..utils.database import open_database

router = APIRouter()
logger = logging.getLogger(__name__)

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
        job["started_at"] = datetime.utcnow().isoformat()
        job["progress"] = 10
        job["message"] = "Loading configuration..."

        # Get config and create importer using working directory
        work_dir = get_working_directory()
        if not work_dir:
            raise ValueError("Working directory not set")

        config_dir = str(work_dir / "config")
        config = Config(config_dir=config_dir, create_default=False)
        generic_config = config.get_imports_config
        importer = ImporterService(config.database_path)

        try:
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

            # Auto-scaffold transform.yml et export.yml (non-fatal)
            try:
                from niamoto.gui.api.services.templates.config_scaffold import (
                    scaffold_configs,
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

        finally:
            # Always close database connections
            importer.close()

    except Exception as e:
        # Mark as failed
        job["status"] = "failed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["errors"].append(str(e))
        job["message"] = f"Import failed: {str(e)}"

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
        job["started_at"] = datetime.utcnow().isoformat()
        job["progress"] = 10
        job["message"] = f"Loading configuration for {entity_name}..."

        # Get config and create importer using working directory
        work_dir = get_working_directory()
        if not work_dir:
            raise ValueError("Working directory not set")

        config_dir = str(work_dir / "config")
        config = Config(config_dir=config_dir, create_default=False)
        generic_config = config.get_imports_config
        importer = ImporterService(config.database_path)

        try:
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
        job["completed_at"] = datetime.utcnow().isoformat()
        job["errors"].append(str(e))
        job["message"] = f"Import failed: {str(e)}"

        logger.exception(
            "Import job '%s' failed for %s '%s': %s",
            job_id,
            entity_type,
            entity_name,
            e,
        )
