from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from niamoto.core.plugins.deployers.models import DeployConfig
from niamoto.core.plugins.deployers.vercel import VercelDeployer


async def _collect_lines(generator):
    return [line async for line in generator]


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json_data


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = responses
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        return self._responses.pop(0)

    async def delete(self, *args, **kwargs):
        self.calls.append(("delete", args, kwargs))
        return self._responses.pop(0)


class _FailingClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def delete(self, *_args, **_kwargs):
        raise httpx.ConnectError("network down")


def test_vercel_deployer_reports_missing_token(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.vercel.CredentialService.get",
        lambda *_args, **_kwargs: None,
    )

    deployer = VercelDeployer()
    config = DeployConfig(
        platform="vercel",
        exports_dir=exports_dir,
        project_name="niamoto-site",
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("No Vercel token configured" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"


def test_vercel_deployer_uploads_files_and_returns_https_url(
    monkeypatch, tmp_path: Path
) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    (exports_dir / "index.html").write_text("hello", encoding="utf-8")

    upload_client = _FakeClient([_FakeResponse(200)])
    deploy_client = _FakeClient(
        [_FakeResponse(201, {"url": "niamoto-site.vercel.app"})]
    )
    client_queue = [upload_client, deploy_client]

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.vercel.CredentialService.get",
        lambda *_args, **_kwargs: "vercel-token",
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.vercel.httpx.AsyncClient",
        lambda **_kwargs: client_queue.pop(0),
    )

    original_sleep = asyncio.sleep

    async def immediate_sleep(_seconds: float) -> None:
        await original_sleep(0)

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.vercel.asyncio.sleep", immediate_sleep
    )

    deployer = VercelDeployer()
    config = DeployConfig(
        platform="vercel",
        exports_dir=exports_dir,
        project_name="niamoto-site",
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("Found 1 files to deploy." in line for line in lines)
    assert any("All files uploaded. Creating deployment..." in line for line in lines)
    assert any(
        "SUCCESS: Deployed to Vercel: https://niamoto-site.vercel.app" in line
        for line in lines
    )
    assert any("URL: https://niamoto-site.vercel.app" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
    upload_method, upload_args, upload_kwargs = upload_client.calls[0]
    assert upload_method == "post"
    assert upload_args == ("https://api.vercel.com/v2/files",)
    assert upload_kwargs["headers"]["Authorization"] == "Bearer vercel-token"
    assert upload_kwargs["headers"]["Content-Type"] == "application/octet-stream"
    assert upload_kwargs["headers"]["x-vercel-digest"]
    assert upload_kwargs["content"] == b"hello"

    deploy_method, deploy_args, deploy_kwargs = deploy_client.calls[0]
    assert deploy_method == "post"
    assert deploy_args == ("https://api.vercel.com/v13/deployments",)
    assert deploy_kwargs["headers"] == {
        "Authorization": "Bearer vercel-token",
        "Content-Type": "application/json",
    }
    assert deploy_kwargs["json"]["name"] == "niamoto-site"
    assert deploy_kwargs["json"]["files"][0]["file"] == "index.html"
    assert (
        deploy_kwargs["json"]["files"][0]["sha"]
        == upload_kwargs["headers"]["x-vercel-digest"]
    )


def test_vercel_unpublish_reports_network_errors(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.vercel.CredentialService.get",
        lambda *_args, **_kwargs: "vercel-token",
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.vercel.httpx.AsyncClient",
        lambda **_kwargs: _FailingClient(),
    )

    deployer = VercelDeployer()
    config = DeployConfig(
        platform="vercel",
        exports_dir=exports_dir,
        project_name="niamoto-site",
    )

    lines = asyncio.run(_collect_lines(deployer.unpublish(config)))

    assert any("ERROR: Failed to delete project" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
