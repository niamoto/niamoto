"""Collection catalog API endpoints."""

from __future__ import annotations

import threading
from typing import Any, NoReturn

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from niamoto.core.collections import CollectionCatalogService
from niamoto.core.collections.models import (
    CollectionCatalog,
    CollectionCatalogEntry,
    CollectionRole,
    CollectionSourceType,
)
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.services.collection_data_options import (
    CollectionDataOptionsResponse,
    CollectionDataOptionsService,
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
    return _catalog_service().list_collections()


@router.get(
    "/{collection_name}/data-options",
    response_model=CollectionDataOptionsResponse,
)
async def get_collection_data_options(
    collection_name: str,
) -> CollectionDataOptionsResponse:
    """Return configured and available reusable data outputs for a collection."""
    try:
        return _data_options_service().get_options(collection_name)
    except KeyError as exc:
        message = str(exc.args[0]) if exc.args else str(exc)
        raise HTTPException(status_code=404, detail=message) from exc


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
            raise HTTPException(status_code=404, detail=str(exc)) from exc
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
