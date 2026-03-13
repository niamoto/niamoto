"""Vercel deployer using the Deployments API."""

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import AsyncIterator

import httpx

from niamoto.core.services.credential import CredentialService

from .base import BaseDeployer, DeployConfig

logger = logging.getLogger(__name__)

VERCEL_API = "https://api.vercel.com"


class VercelDeployer(BaseDeployer):
    """Deploy static sites to Vercel via the Deployments API."""

    platform = "vercel"

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files to Vercel and yield SSE log lines."""
        yield self.sse_log("Starting Vercel deployment...")

        # 1. Get token
        token = CredentialService.get("vercel", "token")
        if not token:
            yield self.sse_error(
                "No Vercel token configured. Use credentials settings to add one."
            )
            yield self.sse_done()
            return

        headers = {
            "Authorization": f"Bearer {token}",
        }

        # 2. Walk exports directory and compute SHA-1 hashes
        exports_dir = config.exports_dir
        if not exports_dir.exists():
            yield self.sse_error(f"Export directory not found: {exports_dir}")
            yield self.sse_done()
            return

        file_manifest: list[dict] = []
        for root, _dirs, files in os.walk(exports_dir):
            for filename in files:
                file_path = Path(root) / filename
                content = file_path.read_bytes()
                sha1_hex = hashlib.sha1(content).hexdigest()
                relative = file_path.relative_to(exports_dir).as_posix()
                file_manifest.append(
                    {
                        "path": file_path,
                        "file": relative,
                        "sha": sha1_hex,
                        "size": len(content),
                    }
                )

        total_files = len(file_manifest)
        if total_files == 0:
            yield self.sse_error("No files found in export directory.")
            yield self.sse_done()
            return

        yield self.sse_log(f"Found {total_files} files to deploy.")

        # 3. Upload files with concurrency limit
        semaphore = asyncio.Semaphore(10)
        uploaded = 0
        upload_errors: list[str] = []

        async def upload_file(client: httpx.AsyncClient, entry: dict) -> None:
            nonlocal uploaded
            async with semaphore:
                try:
                    content = entry["path"].read_bytes()
                    resp = await client.post(
                        f"{VERCEL_API}/v2/files",
                        headers={
                            **headers,
                            "Content-Type": "application/octet-stream",
                            "x-vercel-digest": entry["sha"],
                        },
                        content=content,
                        timeout=60.0,
                    )
                    if resp.status_code not in (200, 201):
                        upload_errors.append(
                            f"{entry['file']}: HTTP {resp.status_code}"
                        )
                except httpx.HTTPError as e:
                    upload_errors.append(f"{entry['file']}: {e}")
                finally:
                    uploaded += 1

        async with httpx.AsyncClient() as client:
            tasks = [upload_file(client, entry) for entry in file_manifest]

            # Run uploads and yield progress
            gather_task = asyncio.gather(*tasks)

            # Yield progress while uploads run
            while not gather_task.done():
                await asyncio.sleep(0.5)
                yield self.sse_log(f"Uploading files: {uploaded}/{total_files}")
                if uploaded >= total_files:
                    break

            await gather_task

        yield self.sse_log(f"Uploading files: {uploaded}/{total_files}")

        if upload_errors:
            for err in upload_errors[:5]:
                yield self.sse_error(f"Upload failed: {err}")
            if len(upload_errors) > 5:
                yield self.sse_error(
                    f"...and {len(upload_errors) - 5} more upload errors"
                )
            yield self.sse_done()
            return

        yield self.sse_log("All files uploaded. Creating deployment...")

        # 4. Create deployment
        deployment_body = {
            "name": config.project_name,
            "files": [
                {
                    "file": entry["file"],
                    "sha": entry["sha"],
                    "size": entry["size"],
                }
                for entry in file_manifest
            ],
            "projectSettings": {"framework": None},
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{VERCEL_API}/v13/deployments",
                    headers={**headers, "Content-Type": "application/json"},
                    json=deployment_body,
                )

                if resp.status_code not in (200, 201):
                    yield self.sse_error(
                        f"Deployment creation failed: HTTP {resp.status_code} — {resp.text[:300]}"
                    )
                    yield self.sse_done()
                    return

                data = resp.json()
        except httpx.HTTPError as e:
            yield self.sse_error(f"Deployment request failed: {e}")
            yield self.sse_done()
            return

        # 5. Extract deployment URL
        url = data.get("url", "")
        if url and not url.startswith("https://"):
            url = f"https://{url}"

        if url:
            yield self.sse_url(url)
            yield self.sse_success(f"Deployed to Vercel: {url}")
        else:
            yield self.sse_success("Deployment created on Vercel.")

        yield self.sse_done()
