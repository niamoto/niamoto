"""Render deployer plugin using Deploy Hook or API."""

import asyncio
import logging
from typing import AsyncIterator

import httpx

from niamoto.core.plugins.base import DeployerPlugin, register
from .models import DeployConfig
from niamoto.core.services.credential import CredentialService

logger = logging.getLogger(__name__)

RENDER_API = "https://api.render.com/v1"

# Polling configuration
POLL_INTERVAL = 5  # seconds
POLL_TIMEOUT = 600  # 10 minutes max


@register("render")
class RenderDeployer(DeployerPlugin):
    """Deploy to Render via Deploy Hook or API."""

    platform = "render"

    async def unpublish(self, config: DeployConfig) -> AsyncIterator[str]:
        """Suspend a Render service."""
        token = CredentialService.get("render", "token")
        if not token:
            yield self.sse_error("No Render token configured.")
            yield self.sse_done()
            return

        service_id = config.extra.get("service_id")
        if not service_id:
            yield self.sse_error("No service_id configured.")
            yield self.sse_done()
            return

        yield self.sse_log(f"Suspending Render service {service_id}...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{RENDER_API}/services/{service_id}/suspend",
                headers={"Authorization": f"Bearer {token}"},
            )

            if resp.status_code in (200, 202):
                yield self.sse_success("Render service suspended.")
            elif resp.status_code == 404:
                yield self.sse_error(f"Service '{service_id}' not found.")
            else:
                yield self.sse_error(
                    f"Failed to suspend service: HTTP {resp.status_code} — {resp.text[:200]}"
                )

        yield self.sse_done()

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy to Render and yield SSE log lines."""
        yield self.sse_log("Starting Render deployment...")

        deploy_hook_url = config.extra.get("deploy_hook_url")

        if deploy_hook_url:
            async for line in self._deploy_via_hook(config, deploy_hook_url):
                yield line
        else:
            async for line in self._deploy_via_api(config):
                yield line

    async def _deploy_via_hook(
        self, config: DeployConfig, hook_url: str
    ) -> AsyncIterator[str]:
        """Deploy by triggering a Render deploy hook (no auth needed)."""
        yield self.sse_log("Triggering deploy hook...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(hook_url)

                if resp.status_code not in (200, 201):
                    yield self.sse_error(
                        f"Deploy hook failed: HTTP {resp.status_code} — {resp.text[:300]}"
                    )
                    yield self.sse_done()
                    return
        except httpx.HTTPError as e:
            yield self.sse_error(f"Deploy hook request failed: {e}")
            yield self.sse_done()
            return

        url = f"https://{config.project_name}.onrender.com"
        yield self.sse_log("Deploy hook triggered. Build started on Render.")
        yield self.sse_url(url)
        yield self.sse_success(f"Deployment triggered: {url}")
        yield self.sse_done()

    async def _deploy_via_api(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy using the Render REST API with token authentication."""
        token = CredentialService.get("render", "token")
        if not token:
            yield self.sse_error(
                "No Render token configured. Use credentials settings to add one."
            )
            yield self.sse_done()
            return

        service_id = config.extra.get("service_id")
        if not service_id:
            yield self.sse_error("No service_id configured. Set it in extra config.")
            yield self.sse_done()
            return

        headers = {"Authorization": f"Bearer {token}"}

        # Create deploy
        yield self.sse_log(f"Creating deployment for service {service_id}...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{RENDER_API}/services/{service_id}/deploys",
                    headers=headers,
                )

                if resp.status_code not in (200, 201):
                    yield self.sse_error(
                        f"Deploy creation failed: HTTP {resp.status_code} — {resp.text[:300]}"
                    )
                    yield self.sse_done()
                    return

                data = resp.json()
                deploy_id = data.get("id")

                if not deploy_id:
                    yield self.sse_error("No deploy ID in response.")
                    yield self.sse_done()
                    return

                yield self.sse_log(f"Deploy {deploy_id} created. Polling status...")

                # Poll for deploy completion
                elapsed = 0
                while elapsed < POLL_TIMEOUT:
                    await asyncio.sleep(POLL_INTERVAL)
                    elapsed += POLL_INTERVAL

                    try:
                        status_resp = await client.get(
                            f"{RENDER_API}/services/{service_id}/deploys/{deploy_id}",
                            headers=headers,
                            timeout=15.0,
                        )

                        if status_resp.status_code != 200:
                            yield self.sse_log(
                                f"Status check returned HTTP {status_resp.status_code}, retrying..."
                            )
                            continue

                        status_data = status_resp.json()
                        status = status_data.get("status", "unknown")

                        yield self.sse_log(f"Deploy status: {status}")

                        if status == "live":
                            url = f"https://{config.project_name}.onrender.com"
                            yield self.sse_url(url)
                            yield self.sse_success(f"Deployed to Render: {url}")
                            yield self.sse_done()
                            return

                        if status in (
                            "deactivated",
                            "build_failed",
                            "update_failed",
                            "canceled",
                        ):
                            yield self.sse_error(
                                f"Deployment failed with status: {status}"
                            )
                            yield self.sse_done()
                            return

                    except httpx.HTTPError as e:
                        yield self.sse_log(f"Status poll error: {e}, retrying...")
                        continue

                # Timeout reached
                yield self.sse_error(
                    f"Deployment timed out after {POLL_TIMEOUT}s. "
                    f"Check Render dashboard for deploy {deploy_id}."
                )
                yield self.sse_done()

        except httpx.HTTPError as e:
            yield self.sse_error(f"Render API request failed: {e}")
            yield self.sse_done()
