"""Generated in-app documentation routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..services.help_content import HelpContentService

router = APIRouter()


@router.get("/help/manifest")
def get_help_manifest():
    """Return the generated documentation manifest."""

    return HelpContentService().load_manifest()


@router.get("/help/search-index")
def get_help_search_index():
    """Return the generated documentation search index."""

    return HelpContentService().load_search_index()


@router.get("/help/pages/{page_slug:path}")
def get_help_page(page_slug: str):
    """Return one generated documentation page payload."""

    return HelpContentService().load_page(page_slug)


@router.get("/help/assets/{asset_path:path}")
def get_help_asset(asset_path: str):
    """Serve one generated documentation asset."""

    asset = HelpContentService().resolve_asset_path(asset_path)
    return FileResponse(asset)
