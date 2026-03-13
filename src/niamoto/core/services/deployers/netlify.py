"""Netlify deployer using ZIP upload API."""

import io
import logging
import os
import zipfile
from typing import AsyncIterator

import httpx

from .base import BaseDeployer, DeployConfig
from niamoto.core.services.credential import CredentialService

logger = logging.getLogger(__name__)

BASE_URL = "https://api.netlify.com"


class NetlifyDeployer(BaseDeployer):
    """Deploy static sites to Netlify via ZIP upload."""

    platform = "netlify"

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files to Netlify.

        Flow:
        1. Authenticate and get site_id
        2. Create ZIP archive of exports directory
        3. Upload ZIP to Netlify deploy endpoint
        4. Poll deploy status until ready or error
        """
        # --- Credentials ---
        token = CredentialService.get("netlify", "token")
        if not token:
            yield self.sse_error(
                "No Netlify token configured. Use credentials settings to add one."
            )
            yield self.sse_done()
            return

        # --- Parse config ---
        site_id = config.extra.get("site_id")
        if not site_id:
            yield self.sse_error("Missing 'site_id' in deployment configuration.")
            yield self.sse_done()
            return

        exports_dir = config.exports_dir
        yield self.sse_log(f"Deploying to Netlify site {site_id}")

        # --- Create ZIP archive ---
        yield self.sse_log("Creating ZIP archive...")
        try:
            zip_buffer = self._create_zip(exports_dir)
        except Exception as exc:
            yield self.sse_error(f"Failed to create ZIP archive: {exc}")
            yield self.sse_done()
            return

        zip_bytes = zip_buffer.getvalue()
        size_mb = len(zip_bytes) / (1024 * 1024)
        yield self.sse_log(f"ZIP archive ready ({size_mb:.1f} MiB)")

        # --- Upload ZIP ---
        yield self.sse_log("Uploading to Netlify...")

        async with httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120.0,
        ) as client:
            try:
                resp = await client.post(
                    f"/api/v1/sites/{site_id}/deploys",
                    content=zip_bytes,
                    headers={"Content-Type": "application/zip"},
                )
                resp.raise_for_status()
                deploy_data = resp.json()
                deploy_id = deploy_data["id"]
            except httpx.HTTPStatusError as exc:
                yield self.sse_error(
                    f"Upload failed (HTTP {exc.response.status_code}): "
                    f"{exc.response.text[:200]}"
                )
                yield self.sse_done()
                return
            except Exception as exc:
                yield self.sse_error(f"Upload failed: {exc}")
                yield self.sse_done()
                return

            yield self.sse_log(f"Deploy created: {deploy_id}")

            # --- Poll status ---
            yield self.sse_log("Processing deployment...")
            final_data = await self._poll_deploy(client, deploy_id)

            if final_data is None:
                yield self.sse_error("Timed out waiting for deployment to finish.")
                yield self.sse_done()
                return

            state = final_data.get("state", "unknown")

            if state == "ready":
                url = final_data.get("ssl_url") or final_data.get("url", "")
                yield self.sse_success("Deployment is live!")
                yield self.sse_url(url)
            elif state == "error":
                error_msg = final_data.get("error_message", "Unknown error")
                yield self.sse_error(f"Deployment failed: {error_msg}")
            else:
                yield self.sse_error(f"Unexpected deploy state: {state}")

            yield self.sse_done()

    @staticmethod
    def _create_zip(exports_dir) -> io.BytesIO:
        """Create an in-memory ZIP archive of the exports directory."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(exports_dir):
                for fname in files:
                    abs_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(abs_path, exports_dir)
                    zf.write(abs_path, rel_path)
        buf.seek(0)
        return buf

    @staticmethod
    async def _poll_deploy(
        client: httpx.AsyncClient,
        deploy_id: str,
        max_attempts: int = 60,
        interval: float = 3.0,
    ) -> dict | None:
        """Poll the deploy status until it reaches a terminal state.

        Returns the deploy data dict when state is 'ready' or 'error',
        or None if we exhaust all attempts.
        """
        import asyncio

        for _ in range(max_attempts):
            try:
                resp = await client.get(f"/api/v1/deploys/{deploy_id}")
                resp.raise_for_status()
                data = resp.json()
                state = data.get("state", "")

                if state in ("ready", "error"):
                    return data

            except httpx.HTTPStatusError:
                pass  # Transient error, keep polling

            await asyncio.sleep(interval)

        return None
