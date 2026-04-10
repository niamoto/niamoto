"""API endpoints for multi-source reference enrichment."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from niamoto.gui.api.services.enrichment_service import (
    EnrichmentJob,
    EnrichmentReferenceConfigResponse,
    EnrichmentStatsResponse,
    PreviewResponse,
    ResultsResponse,
    cancel_default_enrichment,
    cancel_reference_enrichment,
    get_current_job,
    get_default_enrichment_config,
    get_default_enrichment_stats,
    get_entities_for_reference,
    get_reference_enrichment_config,
    get_reference_enrichment_stats,
    get_results,
    pause_default_enrichment,
    pause_reference_enrichment,
    preview_default_enrichment,
    preview_reference_enrichment,
    resume_default_enrichment,
    resume_reference_enrichment,
    start_default_enrichment,
    start_reference_enrichment,
)

router = APIRouter()


class PreviewRequest(BaseModel):
    """Legacy preview request model."""

    taxon_name: str
    source_id: Optional[str] = None


class ReferencePreviewRequest(BaseModel):
    """Reference-scoped preview request model."""

    query: str
    source_id: Optional[str] = None
    source_config: Optional[dict[str, Any]] = None
    entity_id: Optional[Any] = None


def _raise_http_error(message: str) -> None:
    """Convert service validation errors into HTTP responses."""

    if "already active" in message:
        raise HTTPException(status_code=409, detail=message)
    if "No enrichment configuration found" in message:
        raise HTTPException(status_code=404, detail=message)
    if "No enrichment source" in message:
        raise HTTPException(status_code=404, detail=message)
    raise HTTPException(status_code=400, detail=message)


@router.get(
    "/config/{reference_name}", response_model=EnrichmentReferenceConfigResponse
)
async def get_enrichment_config_for_reference(reference_name: str):
    """Return all enrichment sources configured for one reference."""

    return get_reference_enrichment_config(reference_name)


@router.get("/config", response_model=EnrichmentReferenceConfigResponse)
async def get_enrichment_config():
    """Return the default enrichment config for legacy callers."""

    return get_default_enrichment_config()


@router.get("/stats/{reference_name}", response_model=EnrichmentStatsResponse)
async def get_enrichment_stats_for_reference(reference_name: str):
    """Return per-source and aggregate stats for one reference."""

    return get_reference_enrichment_stats(reference_name)


@router.get("/stats", response_model=EnrichmentStatsResponse)
async def get_enrichment_stats():
    """Return aggregate stats for the default reference."""

    return get_default_enrichment_stats()


@router.get("/job/{reference_name}", response_model=EnrichmentJob)
async def get_job_status_for_reference(reference_name: str):
    """Return the active job for one reference."""

    job = get_current_job(reference_name)
    if not job:
        raise HTTPException(status_code=404, detail="No active job")
    return job


@router.get("/job", response_model=EnrichmentJob)
async def get_job_status():
    """Return the active enrichment job."""

    job = get_current_job()
    if not job:
        raise HTTPException(status_code=404, detail="No active job")
    return job


@router.post("/start/{reference_name}/{source_id}", response_model=EnrichmentJob)
async def start_enrichment_for_reference_source(
    reference_name: str, source_id: str, background_tasks: BackgroundTasks
):
    """Start enrichment for one source of a reference."""

    del background_tasks
    try:
        return start_reference_enrichment(reference_name, source_id=source_id)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/start/{reference_name}", response_model=EnrichmentJob)
async def start_enrichment_for_reference(
    reference_name: str, background_tasks: BackgroundTasks
):
    """Start enrichment for all enabled sources of a reference."""

    del background_tasks
    try:
        return start_reference_enrichment(reference_name)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/start", response_model=EnrichmentJob)
async def start_enrichment(background_tasks: BackgroundTasks):
    """Start enrichment for the default reference."""

    del background_tasks
    try:
        return start_default_enrichment()
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/pause/{reference_name}/{source_id}")
async def pause_enrichment_for_reference_source(reference_name: str, source_id: str):
    """Pause an individual source job."""

    try:
        return pause_reference_enrichment(reference_name, source_id=source_id)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/pause/{reference_name}")
async def pause_enrichment_for_reference(reference_name: str):
    """Pause the current job for a reference."""

    try:
        return pause_reference_enrichment(reference_name)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/pause")
async def pause_enrichment():
    """Pause the active default enrichment job."""

    try:
        return pause_default_enrichment()
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/resume/{reference_name}/{source_id}")
async def resume_enrichment_for_reference_source(reference_name: str, source_id: str):
    """Resume an individual source job."""

    try:
        return resume_reference_enrichment(reference_name, source_id=source_id)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/resume/{reference_name}")
async def resume_enrichment_for_reference(reference_name: str):
    """Resume the current job for a reference."""

    try:
        return resume_reference_enrichment(reference_name)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/resume")
async def resume_enrichment():
    """Resume the active default enrichment job."""

    try:
        return resume_default_enrichment()
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/cancel/{reference_name}/{source_id}")
async def cancel_enrichment_for_reference_source(reference_name: str, source_id: str):
    """Cancel an individual source job."""

    try:
        return cancel_reference_enrichment(reference_name, source_id=source_id)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/cancel/{reference_name}")
async def cancel_enrichment_for_reference(reference_name: str):
    """Cancel the current job for a reference."""

    try:
        return cancel_reference_enrichment(reference_name)
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.post("/cancel")
async def cancel_enrichment():
    """Cancel the active default enrichment job."""

    try:
        return cancel_default_enrichment()
    except ValueError as exc:
        _raise_http_error(str(exc))


@router.get("/results/{reference_name}", response_model=ResultsResponse)
async def get_results_for_reference(
    reference_name: str, page: int = 0, limit: int = 50
):
    """Return recent enrichment results for one reference."""

    return get_results(reference_name=reference_name, page=page, limit=limit)


@router.get("/results", response_model=ResultsResponse)
async def get_all_results(page: int = 0, limit: int = 50):
    """Return recent enrichment results for the default reference/job."""

    return get_results(page=page, limit=limit)


@router.post("/preview/{reference_name}", response_model=PreviewResponse)
async def preview_enrichment_for_reference(
    reference_name: str, request: ReferencePreviewRequest
):
    """Preview one query against one or many configured sources."""

    return await preview_reference_enrichment(
        reference_name,
        request.query,
        source_id=request.source_id,
        source_override=request.source_config,
        entity_id=request.entity_id,
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview_enrichment(request: PreviewRequest):
    """Legacy preview endpoint using the default reference."""

    return await preview_default_enrichment(
        request.taxon_name, source_id=request.source_id
    )


@router.get("/entities/{reference_name}")
async def list_entities_for_reference(
    reference_name: str, limit: int = 100, offset: int = 0, search: str = ""
):
    """Return reference entities with aggregate enrichment completion metadata."""

    return get_entities_for_reference(
        reference_name, limit=limit, offset=offset, search=search
    )
