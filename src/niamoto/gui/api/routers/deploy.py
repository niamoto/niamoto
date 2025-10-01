"""Deploy router for the Niamoto GUI API."""

import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..context import get_working_directory

router = APIRouter()


async def run_command_with_streaming(
    command: list[str], cwd: Path, project_name: str = None, branch: str = None
):
    """Run a command and stream its output."""
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(cwd),
    )

    deployment_urls = []

    while True:
        line = await process.stdout.readline()
        if not line:
            break

        decoded_line = line.decode("utf-8", errors="replace").strip()

        # Extract deployment URLs from output
        if "https://" in decoded_line and "pages.dev" in decoded_line:
            # Try to extract URL
            parts = decoded_line.split()
            for part in parts:
                if part.startswith("https://") and "pages.dev" in part:
                    url = part.strip()
                    if url not in deployment_urls:
                        deployment_urls.append(url)

        # Yield log line
        yield f"data: {decoded_line}\n\n"

    await process.wait()

    if process.returncode != 0:
        yield f"data: ERROR: Deployment failed with exit code {process.returncode}\n\n"
    else:
        yield "data: SUCCESS: Deployment completed\n\n"

        # Determine the production URL
        production_url = None

        # If no branch specified and we have a project name, construct production URL
        if project_name and (not branch or not branch.strip()):
            production_url = f"https://{project_name}.pages.dev"
        elif branch and branch.strip():
            # With a branch, construct the branch alias URL
            production_url = f"https://{branch}.{project_name}.pages.dev"
        else:
            # Try to find non-preview URL from logs
            for url in deployment_urls:
                hostname = url.replace("https://", "").split("/")[0]
                # Check if it starts with a hex hash (8 chars) followed by a dot
                if not (
                    len(hostname.split(".")[0]) == 8
                    and all(c in "0123456789abcdef" for c in hostname.split(".")[0])
                ):
                    production_url = url
                    break

        if production_url:
            yield f"data: URL: {production_url}\n\n"

    yield "data: DONE\n\n"


@router.get("/cloudflare/deploy")
async def deploy_to_cloudflare(project_name: str, branch: str = ""):
    """Deploy to Cloudflare Pages with streaming logs."""
    working_dir = get_working_directory()
    if not working_dir:
        raise HTTPException(status_code=400, detail="Working directory not set")

    exports_dir = working_dir / "exports" / "web"
    if not exports_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Exports directory not found: {exports_dir}"
        )

    # Build wrangler command
    command = [
        "npx",
        "wrangler",
        "pages",
        "deploy",
        str(exports_dir),
        "--project-name",
        project_name,
        "--commit-message",
        "Deploy from Niamoto GUI",
        "--commit-dirty=true",
    ]

    # Add branch parameter only if specified and not empty
    if branch and branch.strip():
        command.insert(-2, "--branch")
        command.insert(-2, branch)

    return StreamingResponse(
        run_command_with_streaming(command, working_dir, project_name, branch),
        media_type="text/event-stream",
    )


@router.get("/cloudflare/check")
async def check_wrangler_installed() -> Dict[str, Any]:
    """Check if Wrangler CLI is installed."""
    try:
        result = subprocess.run(
            ["npx", "wrangler", "--version"], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return {"installed": True, "version": version}
        else:
            return {"installed": False, "error": result.stderr}
    except FileNotFoundError:
        return {"installed": False, "error": "npx not found"}
    except subprocess.TimeoutExpired:
        return {"installed": False, "error": "Command timeout"}
    except Exception as e:
        return {"installed": False, "error": str(e)}
