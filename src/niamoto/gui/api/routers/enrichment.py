"""API Enrichment management endpoints.

Provides background job execution for API-based data enrichment with:
- Job management (start, pause, resume, cancel)
- Progress tracking
- Results persisted to database (extra_data column)
- Preview functionality
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import yaml
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..context import get_working_directory

router = APIRouter()


# =============================================================================
# Models
# =============================================================================


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EnrichmentConfig(BaseModel):
    """Enrichment configuration from import.yml."""

    plugin: str = "api_taxonomy_enricher"
    enabled: bool = False
    api_url: str = ""
    query_field: str = "full_name"
    query_param_name: str = "q"
    response_mapping: Dict[str, str] = {}
    rate_limit: float = 1.0
    cache_results: bool = True
    auth_method: Optional[str] = None
    auth_params: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    chained_endpoints: Optional[List[Any]] = None


class EnrichmentJob(BaseModel):
    """Current enrichment job state."""

    id: str
    status: JobStatus
    total: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    started_at: str
    updated_at: str
    error: Optional[str] = None
    current_taxon: Optional[str] = None


class EnrichmentResult(BaseModel):
    """Single taxon enrichment result."""

    taxon_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processed_at: str


class PreviewRequest(BaseModel):
    """Preview request for single taxon."""

    taxon_name: str


class PreviewResponse(BaseModel):
    """Preview response with enrichment data."""

    success: bool
    taxon_name: str
    api_enrichment: Dict[str, Any] = {}
    config_used: Dict[str, str] = {}
    error: Optional[str] = None


class ResultsResponse(BaseModel):
    """Paginated results response."""

    results: List[EnrichmentResult]
    total: int
    page: int
    limit: int


# =============================================================================
# In-Memory Job State (single job at a time)
# =============================================================================

_current_job: Optional[EnrichmentJob] = None
_job_results: List[EnrichmentResult] = []
_job_cancel_flag: bool = False
_job_pause_flag: bool = False
_job_task: Optional[asyncio.Task] = None


def _get_current_job() -> Optional[EnrichmentJob]:
    """Get current job state."""
    global _current_job
    return _current_job


def _set_current_job(job: Optional[EnrichmentJob]) -> None:
    """Set current job state."""
    global _current_job
    _current_job = job


# =============================================================================
# Helpers
# =============================================================================


def _load_enrichment_config() -> Optional[EnrichmentConfig]:
    """Load enrichment configuration from import.yml."""
    work_dir = get_working_directory()
    if not work_dir:
        return None

    config_path = work_dir / "config" / "import.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        # Check EntityRegistry v2 format first
        entities = import_config.get("entities", {})
        references = entities.get("references", {})

        # Look for enrichment in taxons reference
        for ref_name, ref_config in references.items():
            if not isinstance(ref_config, dict):
                continue

            enrichment = ref_config.get("enrichment")
            if enrichment:
                # Can be a list or single config
                if isinstance(enrichment, list):
                    for e in enrichment:
                        if e.get("enabled", False):
                            return EnrichmentConfig(
                                plugin=e.get("plugin", "api_taxonomy_enricher"),
                                enabled=e.get("enabled", False),
                                api_url=e.get("config", {}).get("api_url", ""),
                                query_field=e.get("config", {}).get(
                                    "query_field", "full_name"
                                ),
                                query_param_name=e.get("config", {}).get(
                                    "query_param_name", "q"
                                ),
                                response_mapping=e.get("config", {}).get(
                                    "response_mapping", {}
                                ),
                                rate_limit=e.get("config", {}).get("rate_limit", 1.0),
                                cache_results=e.get("config", {}).get(
                                    "cache_results", True
                                ),
                                auth_method=e.get("config", {}).get("auth_method"),
                                auth_params=e.get("config", {}).get("auth_params"),
                                query_params=e.get("config", {}).get("query_params"),
                                chained_endpoints=e.get("config", {}).get(
                                    "chained_endpoints"
                                ),
                            )
                elif isinstance(enrichment, dict):
                    if enrichment.get("enabled", False):
                        return EnrichmentConfig(
                            plugin=enrichment.get("plugin", "api_taxonomy_enricher"),
                            enabled=enrichment.get("enabled", False),
                            api_url=enrichment.get("config", {}).get("api_url", ""),
                            query_field=enrichment.get("config", {}).get(
                                "query_field", "full_name"
                            ),
                            query_param_name=enrichment.get("config", {}).get(
                                "query_param_name", "q"
                            ),
                            response_mapping=enrichment.get("config", {}).get(
                                "response_mapping", {}
                            ),
                            rate_limit=enrichment.get("config", {}).get(
                                "rate_limit", 1.0
                            ),
                            cache_results=enrichment.get("config", {}).get(
                                "cache_results", True
                            ),
                            auth_method=enrichment.get("config", {}).get("auth_method"),
                            auth_params=enrichment.get("config", {}).get("auth_params"),
                            query_params=enrichment.get("config", {}).get(
                                "query_params"
                            ),
                            chained_endpoints=enrichment.get("config", {}).get(
                                "chained_endpoints"
                            ),
                        )

        # Fallback: Legacy format (taxonomy.api_enrichment)
        taxonomy = import_config.get("taxonomy", {})
        api_enrichment = taxonomy.get("api_enrichment", {})
        if api_enrichment:
            return EnrichmentConfig(
                plugin=api_enrichment.get("plugin", "api_taxonomy_enricher"),
                enabled=api_enrichment.get("enabled", False),
                api_url=api_enrichment.get("api_url", ""),
                query_field=api_enrichment.get("query_field", "full_name"),
                query_param_name=api_enrichment.get("query_param_name", "q"),
                response_mapping=api_enrichment.get("response_mapping", {}),
                rate_limit=api_enrichment.get("rate_limit", 1.0),
                cache_results=api_enrichment.get("cache_results", True),
                auth_method=api_enrichment.get("auth_method"),
                auth_params=api_enrichment.get("auth_params"),
                query_params=api_enrichment.get("query_params"),
                chained_endpoints=api_enrichment.get("chained_endpoints"),
            )

        return None
    except Exception as e:
        print(f"Error loading enrichment config: {e}")
        return None


def _get_taxons_table_name() -> Optional[str]:
    """Get the taxons table name from database.

    Returns:
        Table name or None if not found
    """
    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    if not db_path.exists():
        return None

    try:
        from niamoto.common.database import Database

        db = Database(str(db_path), read_only=True)
        try:
            table_name = None

            # Try to get table name from EntityRegistry
            try:
                from niamoto.core.imports.registry import EntityRegistry

                if db.has_table(EntityRegistry.ENTITIES_TABLE):
                    registry = EntityRegistry(db)
                    for entity in registry.list_entities():
                        if entity.name == "taxons":
                            table_name = entity.table_name
                            break
            except Exception:
                pass

            # Fallback: try common naming patterns
            if not table_name:
                patterns = ["entity_taxons", "reference_taxons", "taxons", "taxonomy"]
                for pattern in patterns:
                    if db.has_table(pattern):
                        table_name = pattern
                        break

            return table_name
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error getting taxons table: {e}")
        return None


def _get_taxons_to_enrich(only_unenriched: bool = True) -> List[Dict[str, Any]]:
    """Get list of taxons to enrich from database.

    Args:
        only_unenriched: If True, only return taxons without enrichment data

    Returns:
        List of taxon dictionaries
    """
    work_dir = get_working_directory()
    if not work_dir:
        return []

    db_path = work_dir / "db" / "niamoto.duckdb"
    if not db_path.exists():
        return []

    table_name = _get_taxons_table_name()
    if not table_name:
        return []

    try:
        from niamoto.common.database import Database
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            if only_unenriched:
                # Only get taxons that don't have enrichment data yet
                # Use LIKE to check for api_enrichment key presence
                query = f"""
                    SELECT * FROM {table_name}
                    WHERE extra_data IS NULL
                       OR CAST(extra_data AS VARCHAR) NOT LIKE '%api_enrichment%'
                """
            else:
                query = f"SELECT * FROM {table_name}"

            df = pd.read_sql(query, db.engine)
            return df.to_dict("records")
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error loading taxons: {e}")
        return []


def _save_enrichment_to_db(taxon_id: int, enrichment_data: Dict[str, Any]) -> bool:
    """Save enrichment data to the taxon's extra_data column.

    Args:
        taxon_id: ID of the taxon to update
        enrichment_data: Enrichment data to save

    Returns:
        True if successful, False otherwise
    """
    work_dir = get_working_directory()
    if not work_dir:
        return False

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_taxons_table_name()
    if not table_name:
        return False

    try:
        from niamoto.common.database import Database
        from sqlalchemy import text

        db = Database(str(db_path))
        try:
            # Build extra_data JSON with enrichment
            extra_data = {
                "api_enrichment": enrichment_data,
                "enriched_at": datetime.now().isoformat(),
            }
            extra_data_json = json.dumps(extra_data)

            # Use parameterized query to avoid SQL injection and escaping issues
            with db.engine.connect() as conn:
                conn.execute(
                    text(f"UPDATE {table_name} SET extra_data = :data WHERE id = :id"),
                    {"data": extra_data_json, "id": taxon_id},
                )
                conn.commit()
            return True
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error saving enrichment for taxon {taxon_id}: {e}")
        return False


def _get_enrichment_stats() -> Dict[str, int]:
    """Get statistics about enriched taxons.

    Returns:
        Dict with total, enriched, and pending counts
    """
    work_dir = get_working_directory()
    if not work_dir:
        return {"total": 0, "enriched": 0, "pending": 0}

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_taxons_table_name()
    if not table_name:
        return {"total": 0, "enriched": 0, "pending": 0}

    try:
        from niamoto.common.database import Database
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            # Count total
            total_df = pd.read_sql(
                f"SELECT COUNT(*) as count FROM {table_name}", db.engine
            )
            total = int(total_df.iloc[0]["count"])

            # Count enriched - use LIKE to check for api_enrichment key
            enriched_df = pd.read_sql(
                f"""
                SELECT COUNT(*) as count FROM {table_name}
                WHERE extra_data IS NOT NULL
                  AND CAST(extra_data AS VARCHAR) LIKE '%api_enrichment%'
                """,
                db.engine,
            )
            enriched = int(enriched_df.iloc[0]["count"])

            return {"total": total, "enriched": enriched, "pending": total - enriched}
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error getting enrichment stats: {e}")
        return {"total": 0, "enriched": 0, "pending": 0}


async def _run_enrichment_job(job_id: str, config: EnrichmentConfig):
    """Background task to run enrichment on all taxons.

    Enriched data is persisted to the database's extra_data column.
    Only taxons without existing enrichment are processed.
    """
    global _current_job, _job_results, _job_cancel_flag, _job_pause_flag

    try:
        # Get only taxons that haven't been enriched yet
        taxons = _get_taxons_to_enrich(only_unenriched=True)

        if not taxons:
            # Check if all taxons are already enriched
            stats = _get_enrichment_stats()
            if stats["enriched"] > 0:
                _current_job.status = JobStatus.COMPLETED
                _current_job.total = stats["total"]
                _current_job.processed = stats["enriched"]
                _current_job.successful = stats["enriched"]
                _current_job.error = None
                _current_job.updated_at = datetime.now().isoformat()
                return

            _current_job.status = JobStatus.FAILED
            _current_job.error = "No taxons found to enrich"
            _current_job.updated_at = datetime.now().isoformat()
            return

        # Get total stats (including already enriched)
        stats = _get_enrichment_stats()
        _current_job.total = stats["total"]
        _current_job.processed = stats["enriched"]
        _current_job.successful = stats["enriched"]
        _current_job.updated_at = datetime.now().isoformat()

        # Import enricher plugin
        try:
            from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                ApiTaxonomyEnricher,
            )

            enricher = ApiTaxonomyEnricher()
        except ImportError:
            _current_job.status = JobStatus.FAILED
            _current_job.error = "ApiTaxonomyEnricher plugin not found"
            _current_job.updated_at = datetime.now().isoformat()
            return

        # Prepare plugin config
        plugin_config = {
            "plugin": config.plugin,
            "params": {
                "api_url": config.api_url,
                "query_field": config.query_field,
                "query_param_name": config.query_param_name,
                "response_mapping": config.response_mapping,
                "rate_limit": config.rate_limit,
                "cache_results": config.cache_results,
                "auth_method": config.auth_method,
                "auth_params": config.auth_params or {},
                "query_params": config.query_params or {},
                "chained_endpoints": config.chained_endpoints or [],
            },
        }

        # Process each unenriched taxon
        for taxon in taxons:
            # Check cancel flag
            if _job_cancel_flag:
                _current_job.status = JobStatus.CANCELLED
                _current_job.updated_at = datetime.now().isoformat()
                return

            # Check pause flag - wait while paused
            while _job_pause_flag:
                _current_job.status = JobStatus.PAUSED
                if _job_cancel_flag:
                    _current_job.status = JobStatus.CANCELLED
                    _current_job.updated_at = datetime.now().isoformat()
                    return
                await asyncio.sleep(0.5)

            # Restore running status after pause
            if _current_job.status == JobStatus.PAUSED:
                _current_job.status = JobStatus.RUNNING

            taxon_id = taxon.get("id")
            taxon_name = taxon.get("full_name") or taxon.get("name") or str(taxon)
            _current_job.current_taxon = taxon_name
            _current_job.updated_at = datetime.now().isoformat()

            try:
                # Enrich taxon using load_data method
                result = enricher.load_data(taxon, plugin_config)
                enrichment_data = result.get("api_enrichment", {})

                # Persist to database
                if enrichment_data and taxon_id is not None:
                    saved = _save_enrichment_to_db(taxon_id, enrichment_data)
                    if not saved:
                        print(
                            f"Warning: Could not save enrichment for taxon {taxon_id}"
                        )

                _job_results.append(
                    EnrichmentResult(
                        taxon_name=taxon_name,
                        success=True,
                        data=enrichment_data,
                        processed_at=datetime.now().isoformat(),
                    )
                )
                _current_job.successful += 1

            except Exception as e:
                _job_results.append(
                    EnrichmentResult(
                        taxon_name=taxon_name,
                        success=False,
                        error=str(e),
                        processed_at=datetime.now().isoformat(),
                    )
                )
                _current_job.failed += 1

            _current_job.processed += 1
            _current_job.updated_at = datetime.now().isoformat()

            # Rate limiting
            await asyncio.sleep(1.0 / config.rate_limit)

        _current_job.status = JobStatus.COMPLETED
        _current_job.current_taxon = None
        _current_job.updated_at = datetime.now().isoformat()

    except Exception as e:
        _current_job.status = JobStatus.FAILED
        _current_job.error = str(e)
        _current_job.updated_at = datetime.now().isoformat()


# =============================================================================
# Endpoints
# =============================================================================


def _load_enrichment_config_for_reference(
    reference_name: str,
) -> Optional[EnrichmentConfig]:
    """Load enrichment configuration for a specific reference from import.yml.

    Args:
        reference_name: Name of the reference to get enrichment config for

    Returns:
        EnrichmentConfig if found and enabled, None otherwise
    """
    work_dir = get_working_directory()
    if not work_dir:
        return None

    config_path = work_dir / "config" / "import.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            import_config = yaml.safe_load(f) or {}

        entities = import_config.get("entities", {})
        references = entities.get("references", {})

        ref_config = references.get(reference_name)
        if not ref_config or not isinstance(ref_config, dict):
            return None

        enrichment = ref_config.get("enrichment")
        if not enrichment:
            return None

        # Can be a list or single config
        if isinstance(enrichment, list):
            for e in enrichment:
                if e.get("enabled", False):
                    return EnrichmentConfig(
                        plugin=e.get("plugin", "api_taxonomy_enricher"),
                        enabled=e.get("enabled", False),
                        api_url=e.get("config", {}).get("api_url", ""),
                        query_field=e.get("config", {}).get("query_field", "full_name"),
                        query_param_name=e.get("config", {}).get(
                            "query_param_name", "q"
                        ),
                        response_mapping=e.get("config", {}).get(
                            "response_mapping", {}
                        ),
                        rate_limit=e.get("config", {}).get("rate_limit", 1.0),
                        cache_results=e.get("config", {}).get("cache_results", True),
                        auth_method=e.get("config", {}).get("auth_method"),
                        auth_params=e.get("config", {}).get("auth_params"),
                        query_params=e.get("config", {}).get("query_params"),
                        chained_endpoints=e.get("config", {}).get("chained_endpoints"),
                    )
        elif isinstance(enrichment, dict):
            if enrichment.get("enabled", False):
                return EnrichmentConfig(
                    plugin=enrichment.get("plugin", "api_taxonomy_enricher"),
                    enabled=enrichment.get("enabled", False),
                    api_url=enrichment.get("config", {}).get("api_url", ""),
                    query_field=enrichment.get("config", {}).get(
                        "query_field", "full_name"
                    ),
                    query_param_name=enrichment.get("config", {}).get(
                        "query_param_name", "q"
                    ),
                    response_mapping=enrichment.get("config", {}).get(
                        "response_mapping", {}
                    ),
                    rate_limit=enrichment.get("config", {}).get("rate_limit", 1.0),
                    cache_results=enrichment.get("config", {}).get(
                        "cache_results", True
                    ),
                    auth_method=enrichment.get("config", {}).get("auth_method"),
                    auth_params=enrichment.get("config", {}).get("auth_params"),
                    query_params=enrichment.get("config", {}).get("query_params"),
                    chained_endpoints=enrichment.get("config", {}).get(
                        "chained_endpoints"
                    ),
                )

        return None
    except Exception as e:
        print(f"Error loading enrichment config for {reference_name}: {e}")
        return None


@router.get("/config/{reference_name}", response_model=EnrichmentConfig)
async def get_enrichment_config_for_reference(reference_name: str):
    """Get enrichment configuration for a specific reference from import.yml.

    Args:
        reference_name: Name of the reference to get config for

    Returns:
        EnrichmentConfig if found
    """
    config = _load_enrichment_config_for_reference(reference_name)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No enrichment configuration found for reference '{reference_name}'",
        )
    return config


@router.get("/config", response_model=EnrichmentConfig)
async def get_enrichment_config():
    """Get current enrichment configuration from import.yml (first enabled config found)."""
    config = _load_enrichment_config()
    if not config:
        raise HTTPException(
            status_code=404, detail="No enrichment configuration found in import.yml"
        )
    return config


@router.get("/stats")
async def get_enrichment_stats():
    """Get enrichment statistics from database.

    Returns:
        Dict with total, enriched, and pending counts
    """
    return _get_enrichment_stats()


@router.get("/job")
async def get_job_status():
    """Get current job status."""
    job = _get_current_job()
    if not job:
        raise HTTPException(status_code=404, detail="No active job")
    return job


@router.post("/start", response_model=EnrichmentJob)
async def start_enrichment(background_tasks: BackgroundTasks):
    """Start a new enrichment job."""
    global _current_job, _job_results, _job_cancel_flag, _job_pause_flag, _job_task

    # Check if job is already running
    if _current_job and _current_job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="A job is already running")

    # Load config
    config = _load_enrichment_config()
    if not config:
        raise HTTPException(status_code=404, detail="No enrichment configuration found")

    if not config.enabled:
        raise HTTPException(status_code=400, detail="Enrichment is not enabled")

    if not config.api_url:
        raise HTTPException(status_code=400, detail="No API URL configured")

    # Reset state
    _job_cancel_flag = False
    _job_pause_flag = False
    _job_results = []

    # Create new job
    now = datetime.now().isoformat()
    _current_job = EnrichmentJob(
        id=str(uuid.uuid4()),
        status=JobStatus.RUNNING,
        total=0,
        processed=0,
        successful=0,
        failed=0,
        started_at=now,
        updated_at=now,
    )

    # Start background task
    _job_task = asyncio.create_task(_run_enrichment_job(_current_job.id, config))

    return _current_job


@router.post("/pause")
async def pause_enrichment():
    """Pause the current enrichment job."""
    global _job_pause_flag, _current_job

    if not _current_job or _current_job.status != JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="No running job to pause")

    _job_pause_flag = True
    _current_job.status = JobStatus.PAUSED
    _current_job.updated_at = datetime.now().isoformat()

    return {"message": "Job paused", "job": _current_job}


@router.post("/resume")
async def resume_enrichment():
    """Resume a paused enrichment job."""
    global _job_pause_flag, _current_job

    if not _current_job or _current_job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail="No paused job to resume")

    _job_pause_flag = False
    _current_job.status = JobStatus.RUNNING
    _current_job.updated_at = datetime.now().isoformat()

    return {"message": "Job resumed", "job": _current_job}


@router.post("/cancel")
async def cancel_enrichment():
    """Cancel the current enrichment job."""
    global _job_cancel_flag, _current_job

    if not _current_job or _current_job.status not in [
        JobStatus.RUNNING,
        JobStatus.PAUSED,
    ]:
        raise HTTPException(status_code=400, detail="No active job to cancel")

    _job_cancel_flag = True
    _current_job.status = JobStatus.CANCELLED
    _current_job.updated_at = datetime.now().isoformat()

    return {"message": "Job cancelled", "job": _current_job}


@router.get("/results", response_model=ResultsResponse)
async def get_results(page: int = 0, limit: int = 50):
    """Get enrichment results with pagination (most recent first)."""
    global _job_results

    # Reverse to show most recent results first
    reversed_results = list(reversed(_job_results))
    start = page * limit
    end = start + limit
    paginated = reversed_results[start:end]

    return ResultsResponse(
        results=paginated, total=len(_job_results), page=page, limit=limit
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview_enrichment(request: PreviewRequest):
    """Preview enrichment for a single taxon without saving."""
    config = _load_enrichment_config()
    if not config:
        return PreviewResponse(
            success=False,
            taxon_name=request.taxon_name,
            error="No enrichment configuration found",
        )

    if not config.api_url:
        return PreviewResponse(
            success=False, taxon_name=request.taxon_name, error="No API URL configured"
        )

    try:
        from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
            ApiTaxonomyEnricher,
        )

        enricher = ApiTaxonomyEnricher()

        # Build plugin config
        plugin_config = {
            "plugin": "api_taxonomy_enricher",
            "params": {
                "api_url": config.api_url,
                "query_field": config.query_field,
                "query_param_name": config.query_param_name,
                "response_mapping": config.response_mapping,
                "rate_limit": config.rate_limit,
                "cache_results": False,  # Don't cache for preview
                "auth_method": config.auth_method,
                "auth_params": config.auth_params or {},
                "query_params": config.query_params or {},
                "chained_endpoints": config.chained_endpoints or [],
            },
        }

        # Create taxon data for query
        taxon_data = {config.query_field: request.taxon_name}

        result = enricher.load_data(taxon_data, plugin_config)

        return PreviewResponse(
            success=True,
            taxon_name=request.taxon_name,
            api_enrichment=result.get("api_enrichment", {}),
            config_used={"api_url": config.api_url, "query_field": config.query_field},
        )

    except Exception as e:
        return PreviewResponse(
            success=False, taxon_name=request.taxon_name, error=str(e)
        )


# =============================================================================
# Reference-specific endpoints
# =============================================================================


def _get_reference_table_name(reference_name: str) -> Optional[str]:
    """Get the table name for a specific reference from database.

    Args:
        reference_name: Name of the reference

    Returns:
        Table name or None if not found
    """
    work_dir = get_working_directory()
    if not work_dir:
        return None

    db_path = work_dir / "db" / "niamoto.duckdb"
    if not db_path.exists():
        return None

    try:
        from niamoto.common.database import Database

        db = Database(str(db_path), read_only=True)
        try:
            table_name = None

            # Try to get table name from EntityRegistry
            try:
                from niamoto.core.imports.registry import EntityRegistry

                if db.has_table(EntityRegistry.ENTITIES_TABLE):
                    registry = EntityRegistry(db)
                    for entity in registry.list_entities():
                        if entity.name == reference_name:
                            table_name = entity.table_name
                            break
            except Exception:
                pass

            # Fallback: try common naming patterns
            if not table_name:
                patterns = [
                    f"entity_{reference_name}",
                    f"reference_{reference_name}",
                    reference_name,
                ]
                for pattern in patterns:
                    if db.has_table(pattern):
                        table_name = pattern
                        break

            return table_name
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error getting table for {reference_name}: {e}")
        return None


def _get_enrichment_stats_for_reference(reference_name: str) -> Dict[str, int]:
    """Get statistics about enriched entities for a specific reference.

    Args:
        reference_name: Name of the reference

    Returns:
        Dict with total, enriched, and pending counts
    """
    work_dir = get_working_directory()
    if not work_dir:
        return {"total": 0, "enriched": 0, "pending": 0}

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not table_name:
        return {"total": 0, "enriched": 0, "pending": 0}

    try:
        from niamoto.common.database import Database
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            # Count total
            total_df = pd.read_sql(
                f"SELECT COUNT(*) as count FROM {table_name}", db.engine
            )
            total = int(total_df.iloc[0]["count"])

            # Count enriched - use LIKE to check for api_enrichment key
            enriched_df = pd.read_sql(
                f"""
                SELECT COUNT(*) as count FROM {table_name}
                WHERE extra_data IS NOT NULL
                  AND CAST(extra_data AS VARCHAR) LIKE '%api_enrichment%'
                """,
                db.engine,
            )
            enriched = int(enriched_df.iloc[0]["count"])

            return {"total": total, "enriched": enriched, "pending": total - enriched}
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error getting enrichment stats for {reference_name}: {e}")
        return {"total": 0, "enriched": 0, "pending": 0}


@router.get("/stats/{reference_name}")
async def get_enrichment_stats_for_reference(reference_name: str):
    """Get enrichment statistics for a specific reference.

    Args:
        reference_name: Name of the reference

    Returns:
        Dict with total, enriched, and pending counts
    """
    return _get_enrichment_stats_for_reference(reference_name)


@router.get("/job/{reference_name}")
async def get_job_status_for_reference(reference_name: str):
    """Get current job status for a specific reference.

    Note: Currently uses global job state. Future enhancement could
    support per-reference job tracking.
    """
    job = _get_current_job()
    if not job:
        raise HTTPException(status_code=404, detail="No active job")
    return job


@router.post("/start/{reference_name}", response_model=EnrichmentJob)
async def start_enrichment_for_reference(
    reference_name: str, background_tasks: BackgroundTasks
):
    """Start a new enrichment job for a specific reference."""
    global _current_job, _job_results, _job_cancel_flag, _job_pause_flag, _job_task

    # Check if job is already running
    if _current_job and _current_job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=409, detail="A job is already running")

    # Load config for this reference
    config = _load_enrichment_config_for_reference(reference_name)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No enrichment configuration found for reference '{reference_name}'",
        )

    if not config.enabled:
        raise HTTPException(
            status_code=400, detail="Enrichment is not enabled for this reference"
        )

    if not config.api_url:
        raise HTTPException(status_code=400, detail="No API URL configured")

    # Reset state
    _job_cancel_flag = False
    _job_pause_flag = False
    _job_results = []

    # Create new job
    now = datetime.now().isoformat()
    _current_job = EnrichmentJob(
        id=str(uuid.uuid4()),
        status=JobStatus.RUNNING,
        total=0,
        processed=0,
        successful=0,
        failed=0,
        started_at=now,
        updated_at=now,
    )

    # Start background task
    _job_task = asyncio.create_task(_run_enrichment_job(_current_job.id, config))

    return _current_job


@router.post("/pause/{reference_name}")
async def pause_enrichment_for_reference(reference_name: str):
    """Pause the current enrichment job."""
    global _job_pause_flag, _current_job

    if not _current_job or _current_job.status != JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="No running job to pause")

    _job_pause_flag = True
    _current_job.status = JobStatus.PAUSED
    _current_job.updated_at = datetime.now().isoformat()

    return {"message": "Job paused", "job": _current_job}


@router.post("/resume/{reference_name}")
async def resume_enrichment_for_reference(reference_name: str):
    """Resume a paused enrichment job."""
    global _job_pause_flag, _current_job

    if not _current_job or _current_job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail="No paused job to resume")

    _job_pause_flag = False
    _current_job.status = JobStatus.RUNNING
    _current_job.updated_at = datetime.now().isoformat()

    return {"message": "Job resumed", "job": _current_job}


@router.post("/cancel/{reference_name}")
async def cancel_enrichment_for_reference(reference_name: str):
    """Cancel the current enrichment job."""
    global _job_cancel_flag, _current_job

    if not _current_job or _current_job.status not in [
        JobStatus.RUNNING,
        JobStatus.PAUSED,
    ]:
        raise HTTPException(status_code=400, detail="No active job to cancel")

    _job_cancel_flag = True
    _current_job.status = JobStatus.CANCELLED
    _current_job.updated_at = datetime.now().isoformat()

    return {"message": "Job cancelled", "job": _current_job}


@router.get("/results/{reference_name}")
async def get_results_for_reference(
    reference_name: str, page: int = 0, limit: int = 50
):
    """Get enrichment results for a specific reference (most recent first)."""
    global _job_results

    # Reverse to show most recent results first
    reversed_results = list(reversed(_job_results))
    start = page * limit
    end = start + limit
    paginated = reversed_results[start:end]

    return {
        "results": [r.model_dump() for r in paginated],
        "total": len(_job_results),
        "page": page,
        "limit": limit,
    }


class ReferencePreviewRequest(BaseModel):
    """Preview request for a reference entity."""

    query: str


@router.post("/preview/{reference_name}")
async def preview_enrichment_for_reference(
    reference_name: str, request: ReferencePreviewRequest
):
    """Preview enrichment for a single entity without saving."""
    config = _load_enrichment_config_for_reference(reference_name)
    if not config:
        return {
            "success": False,
            "entity_name": request.query,
            "error": f"No enrichment configuration found for reference '{reference_name}'",
        }

    if not config.api_url:
        return {
            "success": False,
            "entity_name": request.query,
            "error": "No API URL configured",
        }

    try:
        # Select enricher based on plugin type
        enricher = None
        plugin_name = config.plugin or "api_taxonomy_enricher"

        if plugin_name == "api_taxonomy_enricher":
            from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                ApiTaxonomyEnricher,
            )

            enricher = ApiTaxonomyEnricher()
        elif plugin_name == "api_elevation_enricher":
            # Try to import elevation enricher if it exists
            try:
                from niamoto.core.plugins.loaders.api_elevation_enricher import (
                    ApiElevationEnricher,
                )

                enricher = ApiElevationEnricher()
            except ImportError:
                # Fallback to taxonomy enricher for generic API calls
                from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                    ApiTaxonomyEnricher,
                )

                enricher = ApiTaxonomyEnricher()
        elif plugin_name == "api_spatial_enricher":
            # Try to import spatial enricher if it exists
            try:
                from niamoto.core.plugins.loaders.api_spatial_enricher import (
                    ApiSpatialEnricher,
                )

                enricher = ApiSpatialEnricher()
            except ImportError:
                # Fallback to taxonomy enricher for generic API calls
                from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                    ApiTaxonomyEnricher,
                )

                enricher = ApiTaxonomyEnricher()
        else:
            # Default to taxonomy enricher for unknown plugins
            from niamoto.core.plugins.loaders.api_taxonomy_enricher import (
                ApiTaxonomyEnricher,
            )

            enricher = ApiTaxonomyEnricher()

        # Build plugin config
        plugin_config = {
            "plugin": plugin_name,
            "params": {
                "api_url": config.api_url,
                "query_field": config.query_field,
                "query_param_name": config.query_param_name,
                "response_mapping": config.response_mapping,
                "rate_limit": config.rate_limit,
                "cache_results": False,  # Don't cache for preview
                "auth_method": config.auth_method,
                "auth_params": config.auth_params or {},
                "query_params": config.query_params or {},
                "chained_endpoints": config.chained_endpoints or [],
            },
        }

        # Create entity data for query
        entity_data = {config.query_field: request.query}

        result = enricher.load_data(entity_data, plugin_config)

        return {
            "success": True,
            "entity_name": request.query,
            "api_enrichment": result.get("api_enrichment", {}),
            "config_used": {
                "api_url": config.api_url,
                "query_field": config.query_field,
            },
        }

    except Exception as e:
        return {"success": False, "entity_name": request.query, "error": str(e)}


@router.get("/entities/{reference_name}")
async def get_entities_for_reference(
    reference_name: str, limit: int = 100, offset: int = 0, search: str = ""
):
    """Get entities from a reference for the entity selector.

    Args:
        reference_name: Name of the reference
        limit: Maximum number of entities to return
        offset: Number of entities to skip
        search: Optional search filter

    Returns:
        List of entities with id, name, and enriched status
    """
    work_dir = get_working_directory()
    if not work_dir:
        return {"entities": [], "total": 0}

    db_path = work_dir / "db" / "niamoto.duckdb"
    table_name = _get_reference_table_name(reference_name)
    if not table_name:
        return {"entities": [], "total": 0}

    # Get the query_field from enrichment config
    config = _load_enrichment_config_for_reference(reference_name)
    query_field = config.query_field if config else "full_name"

    try:
        from niamoto.common.database import Database
        import pandas as pd

        db = Database(str(db_path), read_only=True)
        try:
            # Build search clause
            search_clause = ""
            if search:
                search_clause = f"WHERE {query_field} ILIKE '%{search}%'"

            # Count total
            count_query = f"SELECT COUNT(*) as count FROM {table_name} {search_clause}"
            total_df = pd.read_sql(count_query, db.engine)
            total = int(total_df.iloc[0]["count"])

            # Get entities with enriched status
            query = f"""
                SELECT
                    id,
                    {query_field} as name,
                    CASE
                        WHEN extra_data IS NOT NULL
                             AND CAST(extra_data AS VARCHAR) LIKE '%api_enrichment%'
                        THEN true
                        ELSE false
                    END as enriched
                FROM {table_name}
                {search_clause}
                ORDER BY {query_field}
                LIMIT {limit} OFFSET {offset}
            """
            df = pd.read_sql(query, db.engine)
            entities = df.to_dict("records")

            return {"entities": entities, "total": total, "query_field": query_field}
        finally:
            db.close_db_session()
    except Exception as e:
        print(f"Error getting entities for {reference_name}: {e}")
        return {"entities": [], "total": 0, "error": str(e)}
