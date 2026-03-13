"""Deploy router for the Niamoto GUI API.

Supports deployment to Cloudflare Workers, GitHub Pages, Netlify,
Vercel, Render, and SSH/SFTP — all via direct HTTP APIs (no CLI deps).
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from niamoto.core.services.credential import CredentialService
from ..context import get_working_directory

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PLATFORMS = ["cloudflare", "github", "netlify", "vercel", "render", "ssh"]


# --- Request Models ---


class CredentialSaveRequest(BaseModel):
    key: str
    value: str


class DeployRequest(BaseModel):
    platform: str
    project_name: str
    branch: str | None = None
    extra: dict[str, Any] = {}


# --- Credential Endpoints ---


@router.post("/credentials/{platform}")
async def save_credential(platform: str, request: CredentialSaveRequest):
    """Save a credential to the OS keyring."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    success = CredentialService.save(platform, request.key, request.value)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to save credential to keyring"
        )
    return {"saved": True}


@router.get("/credentials/{platform}/check")
async def check_credentials(platform: str):
    """Check if a platform has credentials configured."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    has_creds = CredentialService.has_credentials(platform)
    masked = CredentialService.get_all_for_platform(platform)
    return {"configured": has_creds, "credentials": masked}


@router.delete("/credentials/{platform}/{key}")
async def delete_credential(platform: str, key: str):
    """Delete a credential from the OS keyring."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    success = CredentialService.delete(platform, key)
    return {"deleted": success}


@router.post("/credentials/{platform}/validate")
async def validate_credentials(platform: str):
    """Validate credentials by making a test API call."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
    result = await CredentialService.validate(platform)
    return result


# --- Deploy Endpoint ---


def _get_deployer(platform: str):
    """Get the deployer instance for a platform."""
    if platform == "cloudflare":
        from niamoto.core.services.deployers.cloudflare import CloudflareDeployer

        return CloudflareDeployer()
    elif platform == "github":
        from niamoto.core.services.deployers.github import GitHubDeployer

        return GitHubDeployer()
    elif platform == "netlify":
        from niamoto.core.services.deployers.netlify import NetlifyDeployer

        return NetlifyDeployer()
    elif platform == "vercel":
        from niamoto.core.services.deployers.vercel import VercelDeployer

        return VercelDeployer()
    elif platform == "render":
        from niamoto.core.services.deployers.render import RenderDeployer

        return RenderDeployer()
    elif platform == "ssh":
        from niamoto.core.services.deployers.ssh import SshDeployer

        return SshDeployer()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")


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

    from niamoto.core.services.deployers.base import DeployConfig

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
        # Return errors as SSE stream so the UI can display them
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

    from niamoto.core.services.deployers.base import DeployConfig

    config = DeployConfig(
        platform=request.platform,
        exports_dir=exports_dir,
        project_name=request.project_name,
        branch=request.branch,
    )

    errors = deployer.validate_exports(config)
    return {"valid": len(errors) == 0, "errors": errors}
