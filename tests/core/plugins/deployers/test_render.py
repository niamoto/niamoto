from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from niamoto.core.plugins.deployers.models import DeployConfig
from niamoto.core.plugins.deployers.render import RenderDeployer


async def _collect_lines(generator):
    return [line async for line in generator]


class _FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        return _FakeResponse(200)


class _FailingClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *_args, **_kwargs):
        raise httpx.ConnectError("network down")


def test_render_deployer_triggers_hook_and_returns_url(
    monkeypatch, tmp_path: Path
) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    fake_client = _FakeClient()
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.render.httpx.AsyncClient",
        lambda **_kwargs: fake_client,
    )

    deployer = RenderDeployer()
    config = DeployConfig(
        platform="render",
        exports_dir=exports_dir,
        project_name="niamoto-site",
        extra={"deploy_hook_url": "https://render.com/hook"},
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("Triggering deploy hook" in line for line in lines)
    assert any(
        "SUCCESS: Deployment triggered: https://niamoto-site.onrender.com" in line
        for line in lines
    )
    assert any("URL: https://niamoto-site.onrender.com" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
    assert fake_client.calls == [("post", ("https://render.com/hook",), {})]


def test_render_unpublish_reports_network_errors(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.render.CredentialService.get",
        lambda *_args, **_kwargs: "render-token",
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.render.httpx.AsyncClient",
        lambda **_kwargs: _FailingClient(),
    )

    deployer = RenderDeployer()
    config = DeployConfig(
        platform="render",
        exports_dir=exports_dir,
        project_name="niamoto-site",
        extra={"service_id": "service-123"},
    )

    lines = asyncio.run(_collect_lines(deployer.unpublish(config)))

    assert any("ERROR: Failed to suspend service" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
