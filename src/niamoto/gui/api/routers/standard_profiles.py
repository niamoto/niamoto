"""Standard publication profile API endpoints."""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from niamoto.core.collections import CollectionCatalogService
from niamoto.core.plugins.models import ExportConfig as ExportConfigModel
from niamoto.core.standards import (
    StandardCompatibilityReport,
    StandardProfileConfig,
    StandardProfileOutputResult,
    StandardProfileStore,
    StandardValidationReport,
)
from niamoto.core.standards.compatibility import StandardCompatibilityService
from niamoto.core.standards.models import (
    StandardProfileOutput,
    StandardProfileOutputType,
    StandardProfileSource,
    StandardProfileType,
    StandardProfileValidationStatus,
)
from niamoto.core.standards.output_service import StandardProfileOutputService
from niamoto.core.standards.validation import StandardProfileValidationService
from niamoto.gui.api.context import get_database_path, get_working_directory
from niamoto.gui.api.services.templates.config_service import (
    load_export_config,
    load_import_config,
    load_transform_config,
    save_export_config,
)

router = APIRouter()


class StandardProfileListResponse(BaseModel):
    """Response for listing standard profiles."""

    profiles: list[StandardProfileConfig]
    legacy_hints: list[dict[str, Any]] = Field(default_factory=list)
    total: int


class StandardProfileCreateRequest(BaseModel):
    """Payload for creating a standard publication profile."""

    name: str = Field(min_length=1)
    enabled: bool = True
    standard: StandardProfileType
    target_grain: str = Field(min_length=1)
    source: StandardProfileSource
    context: StandardProfileSource | None = None
    mappings: dict[str, Any] = Field(default_factory=dict)
    outputs: list[StandardProfileOutput] = Field(default_factory=list)
    validation_status: StandardProfileValidationStatus = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)


class StandardProfileUpdateRequest(BaseModel):
    """Payload for updating a standard publication profile."""

    enabled: bool | None = None
    standard: StandardProfileType | None = None
    target_grain: str | None = None
    source: StandardProfileSource | None = None
    context: StandardProfileSource | None = None
    mappings: dict[str, Any] | None = None
    outputs: list[StandardProfileOutput] | None = None
    validation_status: StandardProfileValidationStatus | None = None
    metadata: dict[str, Any] | None = None


class StandardProfileMutationResponse(BaseModel):
    """Response for profile mutations."""

    profile: StandardProfileConfig


def _known_sources() -> list[dict[str, str]]:
    work_dir = get_working_directory()
    catalog = CollectionCatalogService(
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
    ).list_collections()
    sources = [
        {"type": "collection", "name": collection.name}
        for collection in catalog.collections
    ]
    sources.extend(
        {"type": source.type, "name": source.name} for source in catalog.sources
    )
    return sources


def _profile_store() -> StandardProfileStore:
    return StandardProfileStore(
        load_export_config(get_working_directory()),
        known_sources=_known_sources(),
    )


def _compatibility_service() -> StandardCompatibilityService:
    work_dir = get_working_directory()
    return StandardCompatibilityService(
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
    )


def _validation_service() -> StandardProfileValidationService:
    work_dir = get_working_directory()
    return StandardProfileValidationService(
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
    )


def _output_service() -> StandardProfileOutputService:
    work_dir = get_working_directory()
    return StandardProfileOutputService(
        work_dir,
        db_path=get_database_path(),
        import_config=load_import_config(work_dir),
        transform_config=load_transform_config(work_dir),
    )


def _save_store_config(store: StandardProfileStore) -> None:
    try:
        ExportConfigModel.model_validate(store.export_config)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid export configuration: {str(exc)}",
        ) from exc
    save_export_config(get_working_directory(), store.export_config, create_backup=True)


def _raise_profile_error(exc: ValueError) -> NoReturn:
    message = str(exc)
    if message.startswith("Unknown "):
        raise HTTPException(status_code=404, detail=message) from exc
    if "already exists" in message:
        raise HTTPException(status_code=409, detail=message) from exc
    raise HTTPException(status_code=400, detail=message) from exc


@router.get("", response_model=StandardProfileListResponse)
async def list_standard_profiles() -> StandardProfileListResponse:
    """List standard publication profiles and legacy profile hints."""
    store = _profile_store()
    profiles = store.list_profiles()
    return StandardProfileListResponse(
        profiles=profiles,
        legacy_hints=store.list_legacy_hints(),
        total=len(profiles),
    )


@router.get("/{profile_name}", response_model=StandardProfileMutationResponse)
async def get_standard_profile(profile_name: str) -> dict[str, Any]:
    """Return a single standard profile."""
    store = _profile_store()
    try:
        return {"profile": store.get_profile(profile_name)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{profile_name}/compatibility",
    response_model=StandardCompatibilityReport,
)
async def get_standard_profile_compatibility(
    profile_name: str,
) -> StandardCompatibilityReport:
    """Return grain compatibility for a configured standard profile."""
    store = _profile_store()
    try:
        profile = store.get_profile(profile_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _compatibility_service().evaluate(profile)


@router.get(
    "/{profile_name}/validation",
    response_model=StandardValidationReport,
)
async def get_standard_profile_validation(
    profile_name: str,
) -> StandardValidationReport:
    """Return validation checklist and detailed report for a standard profile."""
    store = _profile_store()
    try:
        profile = store.get_profile(profile_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _validation_service().validate(profile)


@router.post(
    "/{profile_name}/outputs/{output_type}",
    response_model=StandardProfileOutputResult,
)
async def execute_standard_profile_output(
    profile_name: str,
    output_type: StandardProfileOutputType,
) -> StandardProfileOutputResult:
    """Generate one configured output for a standard profile."""
    store = _profile_store()
    try:
        profile = store.get_profile(profile_name)
        return _output_service().execute_profile(profile, output_type=output_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "",
    response_model=StandardProfileMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_standard_profile(
    request: StandardProfileCreateRequest,
) -> dict[str, Any]:
    """Create a standard profile in export.yml."""
    store = _profile_store()
    try:
        profile = store.create_profile(request.model_dump(mode="json"))
    except ValueError as exc:
        _raise_profile_error(exc)
    _save_store_config(store)
    return {"profile": profile}


@router.patch("/{profile_name}", response_model=StandardProfileMutationResponse)
async def update_standard_profile(
    profile_name: str,
    update: StandardProfileUpdateRequest,
) -> dict[str, Any]:
    """Update a standard profile in export.yml."""
    store = _profile_store()
    try:
        profile = store.update_profile(
            profile_name, update.model_dump(mode="json", exclude_unset=True)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        _raise_profile_error(exc)
    _save_store_config(store)
    return {"profile": profile}


@router.delete("/{profile_name}")
async def delete_standard_profile(profile_name: str) -> dict[str, Any]:
    """Delete a standard profile from export.yml."""
    store = _profile_store()
    try:
        store.delete_profile(profile_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _save_store_config(store)
    return {"success": True, "deleted": profile_name}
