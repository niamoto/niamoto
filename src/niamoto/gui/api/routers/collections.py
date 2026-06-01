"""Collection catalog API endpoints."""

from __future__ import annotations

import threading
from typing import Any, NoReturn

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from niamoto.core.collections import CollectionCatalogService
from niamoto.core.collections.models import (
    CollectionCatalog,
    CollectionCatalogEntry,
    CollectionRole,
    CollectionSourceType,
)
from niamoto.core.collections.widget_proposal_models import WidgetProposalGroups
from niamoto.core.collections.widget_candidate_models import WidgetCandidateGroups
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.desktop_auth import require_desktop_mutation_auth
from niamoto.gui.api.models.widget_candidates import (
    WidgetCandidateApplyRequest,
    WidgetCandidateApplyResponse,
    WidgetCandidatePreviewRequest,
    WidgetCandidatePreviewResponse,
)
from niamoto.gui.api.models.widget_proposals import (
    WidgetProposalApplyRequest,
    WidgetProposalApplyResponse,
    WidgetProposalPreviewRequest,
    WidgetProposalPreviewResponse,
)
from niamoto.gui.api.services.collection_data_options import (
    CollectionDataOptionsResponse,
    CollectionDataOptionsService,
)
from niamoto.gui.api.services.collection_widget_proposals import (
    CollectionWidgetProposalService,
)
from niamoto.gui.api.services.collection_widget_candidates import (
    CollectionWidgetCandidateService,
)
from niamoto.gui.api.services.templates.config_service import (
    load_export_config,
    load_import_config,
    load_transform_config,
    save_import_config,
)

router = APIRouter()
COLLECTION_CONFIG_LOCK = threading.RLock()


class CollectionUpdateRequest(BaseModel):
    """Payload for updating collection review metadata."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    roles: list[CollectionRole] | None = None
    visible: bool | None = None
    review_status: str | None = None
    grain: str | None = None
    description: str | None = None


class CollectionCreateRequest(BaseModel):
    """Payload for creating a manual collection."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    source_type: CollectionSourceType
    source_name: str = Field(min_length=1)
    grain: str = Field(min_length=1)
    roles: list[CollectionRole] = Field(min_length=1)
    visible: bool = True
    label: str | None = None


class CollectionMutationResponse(BaseModel):
    """Response for collection mutations."""

    collection: CollectionCatalogEntry


def _catalog_service() -> CollectionCatalogService:
    work_dir = get_working_directory()
    return CollectionCatalogService(
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
        export_config=load_export_config(work_dir),
    )


def _data_options_service() -> CollectionDataOptionsService:
    work_dir = get_working_directory()
    return CollectionDataOptionsService(
        work_dir=work_dir,
        db_path=get_database_path(),
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
        export_config=load_export_config(work_dir),
    )


def _widget_proposal_service() -> CollectionWidgetProposalService:
    work_dir = get_working_directory()
    return CollectionWidgetProposalService(
        work_dir=work_dir,
        db_path=get_database_path(),
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
        export_config=load_export_config(work_dir),
    )


def _widget_candidate_service() -> CollectionWidgetCandidateService:
    work_dir = get_working_directory()
    return CollectionWidgetCandidateService(
        work_dir=work_dir,
        db_path=get_database_path(),
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
        export_config=load_export_config(work_dir),
    )


def _save_service_config(service: CollectionCatalogService) -> None:
    save_import_config(
        get_working_directory(), service.import_config, create_backup=True
    )


def _raise_catalog_error(exc: ValueError) -> NoReturn:
    message = str(exc)
    if message.startswith("Unknown "):
        raise HTTPException(status_code=404, detail=message) from exc
    if "already exists" in message:
        raise HTTPException(status_code=409, detail=message) from exc
    raise HTTPException(status_code=400, detail=message) from exc


@router.get("", response_model=CollectionCatalog)
async def list_collections() -> CollectionCatalog:
    """List reviewable collection candidates and manual source options."""
    with COLLECTION_CONFIG_LOCK:
        try:
            return _catalog_service().list_collections()
        except ValueError as exc:
            _raise_catalog_error(exc)


@router.get(
    "/{collection_name}/data-options",
    response_model=CollectionDataOptionsResponse,
)
async def get_collection_data_options(
    collection_name: str,
) -> CollectionDataOptionsResponse:
    """Return configured and available reusable data outputs for a collection."""
    with COLLECTION_CONFIG_LOCK:
        try:
            return _data_options_service().get_options(collection_name)
        except KeyError as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            raise HTTPException(status_code=404, detail=message) from exc


@router.get(
    "/{collection_name}/widget-candidates",
    response_model=WidgetCandidateGroups,
)
async def get_collection_widget_candidates(
    collection_name: str,
) -> WidgetCandidateGroups:
    """Return unified widget candidates for a collection."""
    with COLLECTION_CONFIG_LOCK:
        try:
            return _widget_candidate_service().get_candidates(collection_name)
        except KeyError as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            raise HTTPException(status_code=404, detail=message) from exc


@router.post(
    "/{collection_name}/widget-candidates/preview",
    response_model=WidgetCandidatePreviewResponse,
)
async def preview_collection_widget_candidates(
    collection_name: str,
    request: WidgetCandidatePreviewRequest,
) -> WidgetCandidatePreviewResponse:
    """Preview selected widget candidate config changes without writing files."""
    with COLLECTION_CONFIG_LOCK:
        try:
            return _widget_candidate_service().preview_apply(
                collection_name,
                request.selections,
            )
        except KeyError as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            raise HTTPException(status_code=404, detail=message) from exc


@router.post(
    "/{collection_name}/widget-candidates/apply",
    response_model=WidgetCandidateApplyResponse,
)
async def apply_collection_widget_candidates(
    collection_name: str,
    request: WidgetCandidateApplyRequest,
    http_request: Request,
) -> WidgetCandidateApplyResponse:
    """Apply selected widget candidates to transform.yml and export.yml."""
    require_desktop_mutation_auth(http_request)
    try:
        with COLLECTION_CONFIG_LOCK:
            return _widget_candidate_service().apply(
                collection_name,
                request.selections,
                preview_token=request.preview_token,
            )
    except KeyError as exc:
        message = str(exc.args[0]) if exc.args else str(exc)
        raise HTTPException(status_code=404, detail=message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{collection_name}/widget-proposals",
    response_model=WidgetProposalGroups,
)
async def get_collection_widget_proposals(
    collection_name: str,
) -> WidgetProposalGroups:
    """Return transformation-first widget proposals for a collection."""
    with COLLECTION_CONFIG_LOCK:
        try:
            return _widget_proposal_service().get_proposals(collection_name)
        except KeyError as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            raise HTTPException(status_code=404, detail=message) from exc


@router.post(
    "/{collection_name}/widget-proposals/preview",
    response_model=WidgetProposalPreviewResponse,
)
async def preview_collection_widget_proposals(
    collection_name: str,
    request: WidgetProposalPreviewRequest,
) -> WidgetProposalPreviewResponse:
    """Preview selected widget proposal config changes without writing files."""
    with COLLECTION_CONFIG_LOCK:
        try:
            return _widget_proposal_service().preview_apply(
                collection_name,
                request.selections,
            )
        except KeyError as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            raise HTTPException(status_code=404, detail=message) from exc


@router.post(
    "/{collection_name}/widget-proposals/apply",
    response_model=WidgetProposalApplyResponse,
)
async def apply_collection_widget_proposals(
    collection_name: str,
    request: WidgetProposalApplyRequest,
    http_request: Request,
) -> WidgetProposalApplyResponse:
    """Apply selected widget proposals to transform.yml and export.yml."""
    require_desktop_mutation_auth(http_request)
    try:
        with COLLECTION_CONFIG_LOCK:
            return _widget_proposal_service().apply(
                collection_name,
                request.selections,
                preview_token=request.preview_token,
            )
    except KeyError as exc:
        message = str(exc.args[0]) if exc.args else str(exc)
        raise HTTPException(status_code=404, detail=message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{collection_name}", response_model=CollectionMutationResponse)
async def update_collection(
    collection_name: str,
    update: CollectionUpdateRequest,
) -> dict[str, Any]:
    """Update review metadata for an inferred or explicit collection."""
    payload = update.model_dump(exclude_unset=True, exclude_none=True)
    if not payload:
        raise HTTPException(
            status_code=400,
            detail="Collection update must include at least one field",
        )

    with COLLECTION_CONFIG_LOCK:
        service = _catalog_service()
        try:
            collection = service.update_collection(collection_name, **payload)
        except KeyError as exc:
            message = str(exc.args[0]) if exc.args else str(exc)
            raise HTTPException(status_code=404, detail=message) from exc
        except ValueError as exc:
            _raise_catalog_error(exc)
        _save_service_config(service)
    return {"collection": collection}


@router.post(
    "",
    response_model=CollectionMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    request: CollectionCreateRequest,
) -> dict[str, Any]:
    """Create a manual collection backed by a known source."""
    with COLLECTION_CONFIG_LOCK:
        service = _catalog_service()
        try:
            collection = service.create_collection(**request.model_dump())
        except ValueError as exc:
            _raise_catalog_error(exc)
        _save_service_config(service)
    return {"collection": collection}
