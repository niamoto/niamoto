"""Deploy router for the Niamoto GUI API.

Supports deployment to any platform registered as a deployer plugin.
Built-in: Cloudflare Workers, GitHub Pages, Netlify, Vercel, Render, SSH/SFTP.
"""

import logging
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from niamoto.core.plugins.base import PluginType
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.deployers.models import DeployConfig
from niamoto.core.services.credential import CredentialService
from ..context import get_working_directory

# Import deployer modules to trigger @register decorators at startup
import niamoto.core.plugins.deployers.cloudflare  # noqa: F401
import niamoto.core.plugins.deployers.github  # noqa: F401
import niamoto.core.plugins.deployers.netlify  # noqa: F401
import niamoto.core.plugins.deployers.vercel  # noqa: F401
import niamoto.core.plugins.deployers.render  # noqa: F401
import niamoto.core.plugins.deployers.ssh  # noqa: F401

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_supported_platforms() -> list[str]:
    """Get list of registered deployer platform names."""
    return list(PluginRegistry.get_plugins_by_type(PluginType.DEPLOYER).keys())


def _check_platform(platform: str) -> None:
    """Raise 400 if platform is not a registered deployer."""
    if not PluginRegistry.has_plugin(platform, PluginType.DEPLOYER):
        available = _get_supported_platforms()
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {platform}. Available: {available}",
        )


def _get_deployer(platform: str):
    """Get a deployer plugin instance by platform name."""
    _check_platform(platform)
    deployer_class = PluginRegistry.get_plugin(platform, PluginType.DEPLOYER)
    return deployer_class()


# --- Request Models ---


class CredentialSaveRequest(BaseModel):
    key: str
    value: str


class DeployRequest(BaseModel):
    platform: str
    project_name: str
    branch: str | None = None
    extra: dict[str, Any] = {}


# --- Platform Discovery ---


@router.get("/platforms")
async def list_platforms():
    """List all registered deployer platforms."""
    return {"platforms": _get_supported_platforms()}


# --- Credential Endpoints ---


@router.post("/credentials/{platform}")
async def save_credential(platform: str, request: CredentialSaveRequest):
    """Save a credential to the OS keyring."""
    _check_platform(platform)
    success = CredentialService.save(platform, request.key, request.value)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to save credential to keyring"
        )
    return {"saved": True}


@router.get("/credentials/{platform}/check")
async def check_credentials(platform: str):
    """Check if a platform has credentials configured."""
    _check_platform(platform)
    has_creds = CredentialService.has_credentials(platform)
    masked = CredentialService.get_all_for_platform(platform)
    return {"configured": has_creds, "credentials": masked}


@router.delete("/credentials/{platform}/{key}")
async def delete_credential(platform: str, key: str):
    """Delete a credential from the OS keyring."""
    _check_platform(platform)
    success = CredentialService.delete(platform, key)
    return {"deleted": success}


@router.post("/credentials/{platform}/validate")
async def validate_credentials(platform: str):
    """Validate credentials by making a test API call."""
    _check_platform(platform)
    result = await CredentialService.validate(platform)
    return result


# --- Deploy Endpoints ---


@router.post("/execute")
async def deploy(request: DeployRequest):
    """Deploy to any platform with SSE streaming logs."""
    working_dir = get_working_directory()
    if not working_dir:
        raise HTTPException(status_code=400, detail="Working directory not set")

    exports_dir = working_dir / "exports" / "web"
    if not exports_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Exports directory not found: {exports_dir}"
        )

    deployer = _get_deployer(request.platform)

    config = DeployConfig(
        platform=request.platform,
        exports_dir=exports_dir,
        project_name=request.project_name,
        branch=request.branch,
        extra=request.extra,
    )

    # Pre-flight validation
    errors = deployer.validate_exports(config)
    if errors:

        async def error_stream():
            for err in errors:
                yield f"data: ERROR: {err}\n\n"
            yield "data: DONE\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    return StreamingResponse(deployer.deploy(config), media_type="text/event-stream")


@router.post("/validate")
async def validate_exports(request: DeployRequest):
    """Validate exports directory before deployment (dry run)."""
    working_dir = get_working_directory()
    if not working_dir:
        raise HTTPException(status_code=400, detail="Working directory not set")

    exports_dir = working_dir / "exports" / "web"
    if not exports_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Exports directory not found: {exports_dir}"
        )

    deployer = _get_deployer(request.platform)

    config = DeployConfig(
        platform=request.platform,
        exports_dir=exports_dir,
        project_name=request.project_name,
        branch=request.branch,
    )

    errors = deployer.validate_exports(config)
    return {"valid": len(errors) == 0, "errors": errors}


# --- Health Check ---


@router.get("/health")
async def check_site_health(url: str = Query(..., description="URL to check")):
    """Check if a deployed site is online.

    Performs a GET request and follows both HTTP and HTML meta-refresh redirects
    to catch cases where the landing page returns 200 but redirects to a 404 page
    (common with GitHub Pages after branch deletion).
    """
    import re

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url)
            final_code = resp.status_code

            # If the page returns 200, check for meta-refresh redirects
            # that may lead to a broken page
            if final_code == 200 and len(resp.content) < 5000:
                body = resp.text
                match = re.search(
                    r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+url=([^"\'\s>]+)',
                    body,
                    re.IGNORECASE,
                )
                if match:
                    redirect_target = match.group(1).rstrip("\"'>")
                    # Resolve relative URL
                    if not redirect_target.startswith("http"):
                        base = str(resp.url).rstrip("/")
                        redirect_target = f"{base}/{redirect_target.lstrip('/')}"
                    # Follow the meta-refresh
                    resp2 = await client.get(redirect_target)
                    final_code = resp2.status_code

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if final_code < 400:
            return {
                "status": "up",
                "statusCode": final_code,
                "responseTime": elapsed_ms,
            }
        else:
            return {
                "status": "down",
                "statusCode": final_code,
                "responseTime": elapsed_ms,
            }
    except Exception:
        return {"status": "down", "statusCode": None, "responseTime": None}


# --- Unpublish ---


class UnpublishRequest(BaseModel):
    platform: str
    project_name: str
    branch: str | None = None
    extra: dict[str, Any] = {}


@router.post("/unpublish")
async def unpublish(request: UnpublishRequest):
    """Unpublish a site from a platform with SSE streaming logs."""
    deployer = _get_deployer(request.platform)

    # exports_dir is not needed for unpublish but DeployConfig requires it
    working_dir = get_working_directory()
    exports_dir = (working_dir / "exports" / "web") if working_dir else Path(".")

    config = DeployConfig(
        platform=request.platform,
        exports_dir=exports_dir,
        project_name=request.project_name,
        branch=request.branch,
        extra=request.extra,
    )

    return StreamingResponse(deployer.unpublish(config), media_type="text/event-stream")
