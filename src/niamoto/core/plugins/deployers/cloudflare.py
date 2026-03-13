"""Cloudflare Workers Static Assets deployer plugin.

Deploys static sites using the Cloudflare Workers Assets Upload API
(not the deprecated Pages API).

Flow: create upload session → upload file buckets → deploy worker script.
"""

import base64
import hashlib
import json
import logging
import os
from typing import AsyncIterator

import httpx

from niamoto.core.plugins.base import DeployerPlugin, register
from .models import DeployConfig
from niamoto.core.services.credential import CredentialService

logger = logging.getLogger(__name__)

CF_API_BASE = "https://api.cloudflare.com/client/v4"

WORKER_SCRIPT = (
    'import { WorkerEntrypoint } from "cloudflare:workers";'
    " export default class extends WorkerEntrypoint"
    " { async fetch() { return this.env.ASSETS.fetch(this.ctx.request); } }"
)

WORKER_METADATA = {
    "main_module": "worker.js",
    "bindings": [{"name": "ASSETS", "type": "assets"}],
    "compatibility_date": "2024-09-23",
}


def _hash_file(path: str) -> str:
    """Compute SHA-256 of a file, truncated to first 16 bytes (32 hex chars)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


@register("cloudflare")
class CloudflareDeployer(DeployerPlugin):
    """Deploy static assets to Cloudflare Workers."""

    platform = "cloudflare"

    async def unpublish(self, config: DeployConfig) -> AsyncIterator[str]:
        """Remove a Cloudflare Worker."""
        api_token = CredentialService.get("cloudflare", "api-token")
        account_id = CredentialService.get("cloudflare", "account-id")

        if not api_token or not account_id:
            yield self.sse_error("Missing Cloudflare credentials.")
            yield self.sse_done()
            return

        script_name = config.project_name
        yield self.sse_log(f"Deleting Worker '{script_name}'...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(
                f"{CF_API_BASE}/accounts/{account_id}/workers/scripts/{script_name}",
                headers={"Authorization": f"Bearer {api_token}"},
            )

            if resp.status_code == 200:
                yield self.sse_success(f"Worker '{script_name}' deleted.")
            elif resp.status_code == 404:
                yield self.sse_error(f"Worker '{script_name}' not found.")
            else:
                yield self.sse_error(
                    f"Failed to delete Worker: HTTP {resp.status_code} — {resp.text[:200]}"
                )

        yield self.sse_done()

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files to Cloudflare Workers Static Assets."""

        # --- Retrieve credentials ------------------------------------------------
        api_token = CredentialService.get("cloudflare", "api-token")
        account_id = CredentialService.get("cloudflare", "account-id")

        if not api_token or not account_id:
            yield self.sse_error(
                "Missing Cloudflare credentials. "
                "Set them with: niamoto deploy credentials cloudflare"
            )
            yield self.sse_done()
            return

        script_name = config.project_name

        # --- Validate export directory -------------------------------------------
        errors = self.validate_exports(config)
        if errors:
            for err in errors:
                yield self.sse_error(err)
            yield self.sse_done()
            return

        # --- Step 1: Build manifest & create upload session ----------------------
        yield self.sse_log("Building file manifest...")

        exports_dir = str(config.exports_dir)
        manifest: dict[str, dict] = {}
        # Map hash -> absolute file path for upload
        hash_to_path: dict[str, str] = {}

        for root, _dirs, files in os.walk(exports_dir):
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = "/" + os.path.relpath(abs_path, exports_dir).replace(
                    "\\", "/"
                )
                file_hash = _hash_file(abs_path)
                file_size = os.path.getsize(abs_path)
                manifest[rel_path] = {"hash": file_hash, "size": file_size}
                hash_to_path[file_hash] = abs_path

        total_files = len(manifest)
        yield self.sse_log(f"Manifest ready: {total_files} files")

        auth_headers = {"Authorization": f"Bearer {api_token}"}
        session_url = (
            f"{CF_API_BASE}/accounts/{account_id}"
            f"/workers/scripts/{script_name}/assets-upload-session"
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    session_url,
                    headers=auth_headers,
                    json={"manifest": manifest},
                )
            except httpx.HTTPError as exc:
                yield self.sse_error(f"Failed to create upload session: {exc}")
                yield self.sse_done()
                return

            if resp.status_code not in (200, 201):
                yield self.sse_error(
                    f"Upload session failed ({resp.status_code}): {resp.text[:300]}"
                )
                yield self.sse_done()
                return

            session_data = resp.json()
            if not session_data.get("success"):
                msg = session_data.get("errors", [{}])[0].get(
                    "message", resp.text[:300]
                )
                yield self.sse_error(f"Upload session error: {msg}")
                yield self.sse_done()
                return

            jwt = session_data["result"]["jwt"]
            buckets = session_data["result"].get("buckets", [])

            # --- Step 2: Upload files in buckets ---------------------------------
            files_to_upload = sum(len(b) for b in buckets)
            if files_to_upload == 0:
                yield self.sse_log("All files already on CDN, skipping upload")
            else:
                yield self.sse_log(
                    f"Uploading {files_to_upload} files in {len(buckets)} bucket(s)..."
                )

            uploaded = 0
            completion_jwt = jwt  # Fallback if no buckets need uploading

            upload_url = (
                f"{CF_API_BASE}/accounts/{account_id}/workers/assets/upload?base64=true"
            )

            for bucket_idx, bucket in enumerate(buckets):
                upload_headers = {"Authorization": f"Bearer {jwt}"}

                # Build multipart payload for this bucket
                files_payload: list[tuple[str, tuple[str, str, str]]] = []
                for file_hash in bucket:
                    file_path = hash_to_path.get(file_hash)
                    if file_path is None:
                        yield self.sse_error(f"Hash {file_hash} not found in manifest")
                        continue
                    with open(file_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("ascii")
                    files_payload.append(
                        (file_hash, (file_hash, encoded, "application/octet-stream"))
                    )

                try:
                    resp = await client.post(
                        upload_url,
                        headers=upload_headers,
                        files=files_payload,
                    )
                except httpx.HTTPError as exc:
                    yield self.sse_error(
                        f"Upload failed for bucket {bucket_idx + 1}: {exc}"
                    )
                    yield self.sse_done()
                    return

                if resp.status_code not in (200, 201):
                    yield self.sse_error(
                        f"Upload bucket {bucket_idx + 1} failed "
                        f"({resp.status_code}): {resp.text[:300]}"
                    )
                    yield self.sse_done()
                    return

                uploaded += len(bucket)
                yield self.sse_log(f"Uploading files: {uploaded}/{files_to_upload}")

                # The last bucket upload (201) returns the completion JWT
                if resp.status_code == 201:
                    upload_result = resp.json()
                    completion_jwt = upload_result.get("result", {}).get(
                        "jwt", completion_jwt
                    )

            if files_to_upload > 0:
                yield self.sse_log("All files uploaded")

            # --- Step 3: Deploy the worker script --------------------------------
            yield self.sse_log("Deploying worker script...")

            deploy_url = (
                f"{CF_API_BASE}/accounts/{account_id}/workers/scripts/{script_name}"
            )

            metadata = {
                **WORKER_METADATA,
                "assets": {
                    "jwt": completion_jwt,
                    "config": {
                        "html_handling": "auto-trailing-slash",
                        "not_found_handling": "single-page-application",
                    },
                },
            }

            deploy_files = {
                "metadata": (
                    "metadata",
                    json.dumps(metadata),
                    "application/json",
                ),
                "worker.js": (
                    "worker.js",
                    WORKER_SCRIPT,
                    "application/javascript+module",
                ),
            }

            try:
                resp = await client.put(
                    deploy_url,
                    headers=auth_headers,
                    files=deploy_files,
                )
            except httpx.HTTPError as exc:
                yield self.sse_error(f"Worker deployment failed: {exc}")
                yield self.sse_done()
                return

            if resp.status_code not in (200, 201):
                yield self.sse_error(
                    f"Worker deployment failed ({resp.status_code}): {resp.text[:300]}"
                )
                yield self.sse_done()
                return

            deploy_result = resp.json()
            if not deploy_result.get("success"):
                msg = deploy_result.get("errors", [{}])[0].get(
                    "message", resp.text[:300]
                )
                yield self.sse_error(f"Worker deployment error: {msg}")
                yield self.sse_done()
                return

        # --- Done ----------------------------------------------------------------
        if config.branch:
            site_url = f"https://{config.branch}.{script_name}.workers.dev"
        else:
            site_url = f"https://{script_name}.workers.dev"

        yield self.sse_success(f"Deployed {total_files} files to Cloudflare Workers")
        yield self.sse_url(site_url)
        yield self.sse_done()
