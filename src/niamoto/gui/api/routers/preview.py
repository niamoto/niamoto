"""Router preview unifié — point d'entrée unique pour toutes les previews widgets.

Endpoints :
  GET  /api/preview/{template_id}             — preview par template_id
  POST /api/preview                           — preview inline (transformer + widget explicites)
  GET  /api/templates/preview/{template_id}   — alias rétrocompatible (→ supprimer Phase 5)
"""

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from niamoto.gui.api.services.preview_engine import (
    PreviewMode,
    PreviewRequest,
)
from niamoto.gui.api.services.preview_engine.engine import get_preview_engine
from niamoto.gui.api.services.preview_utils import error_html, wrap_html_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["preview"])


# ---------------------------------------------------------------------------
# Modèles Pydantic pour le body POST
# ---------------------------------------------------------------------------


class InlineConfig(BaseModel):
    """Configuration inline pour preview POST."""

    transformer_plugin: str
    transformer_params: dict[str, Any] = {}
    widget_plugin: str
    widget_params: dict[str, Any] | None = None
    widget_title: str = "Preview"


class InlinePreviewBody(BaseModel):
    """Body pour POST /api/preview."""

    template_id: str | None = None
    group_by: str | None = None
    source: str | None = None
    entity_id: str | None = None
    mode: PreviewMode = "full"
    inline: InlineConfig | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_html(message: str) -> HTMLResponse:
    """Retourne une réponse HTML d'erreur sans passer par le moteur."""
    return HTMLResponse(
        content=wrap_html_response(error_html(message)),
        status_code=500,
    )


def _build_headers(etag: str) -> dict:
    return {
        "ETag": f'"{etag}"',
        "Cache-Control": "no-cache",
    }


# ---------------------------------------------------------------------------
# GET /api/preview/{template_id}
# ---------------------------------------------------------------------------


@router.get("/preview/{template_id}", response_class=HTMLResponse)
async def get_preview(
    template_id: str,
    request: Request,
    group_by: str | None = Query(
        default=None,
        description="Group by reference (auto-detected if not provided)",
    ),
    source: str | None = Query(
        default=None,
        description="Data source (entity name like 'plots' for entity data)",
    ),
    entity_id: str | None = Query(
        default=None,
        description="Specific entity ID to use for preview",
    ),
    mode: PreviewMode = Query(default="full"),
):
    """Génère la preview HTML d'un widget identifié par template_id."""
    engine = get_preview_engine()
    if engine is None:
        return _error_html("Projet Niamoto non configuré")

    req = PreviewRequest(
        template_id=template_id,
        group_by=group_by,
        source=source,
        entity_id=entity_id,
        mode=mode,
    )

    # Vérifier ETag AVANT le rendu complet pour éviter un render inutile
    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match:
        etag = engine._compute_etag(req)
        if if_none_match.strip('"') == etag:
            return Response(status_code=304, headers={"ETag": f'"{etag}"'})

    result = await run_in_threadpool(engine.render, req)

    return HTMLResponse(
        content=result.html,
        headers=_build_headers(result.etag),
    )


# ---------------------------------------------------------------------------
# POST /api/preview
# ---------------------------------------------------------------------------


@router.post("/preview", response_class=HTMLResponse)
async def post_preview(body: InlinePreviewBody):
    """Génère une preview HTML à partir d'une config inline ou d'un template_id."""
    engine = get_preview_engine()
    if engine is None:
        return _error_html("Projet Niamoto non configuré")

    inline_dict = None
    if body.inline:
        inline_dict = body.inline.model_dump()

    req = PreviewRequest(
        template_id=body.template_id,
        group_by=body.group_by,
        source=body.source,
        entity_id=body.entity_id,
        mode=body.mode,
        inline=inline_dict,
    )

    result = await run_in_threadpool(engine.render, req)
    return HTMLResponse(
        content=result.html,
        headers=_build_headers(result.etag),
    )


# ---------------------------------------------------------------------------
# Legacy : GET /api/templates/preview/{template_id}
# Rétrocompatible — délègue à get_preview(). À supprimer en Phase 5.
# ---------------------------------------------------------------------------


@router.get("/templates/preview/{template_id}", response_class=HTMLResponse)
async def legacy_get_preview(
    template_id: str,
    request: Request,
    group_by: str | None = Query(default=None),
    source: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    mode: PreviewMode = Query(default="full"),
):
    """Alias rétrocompatible — délègue à get_preview(). À supprimer en Phase 5."""
    return await get_preview(
        template_id=template_id,
        request=request,
        group_by=group_by,
        source=source,
        entity_id=entity_id,
        mode=mode,
    )
