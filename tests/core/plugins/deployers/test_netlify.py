from __future__ import annotations

import asyncio
import io
import zipfile
from pathlib import Path

import httpx

from niamoto.core.plugins.deployers.models import DeployConfig
from niamoto.core.plugins.deployers.netlify import NetlifyDeployer


async def _collect_lines(generator):
    return [line async for line in generator]


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.request = httpx.Request("POST", "https://api.netlify.com")

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=self.request, response=self)


class _FakeClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        return self._response

    async def delete(self, *args, **kwargs):
        self.calls.append(("delete", args, kwargs))
        return self._response


class _FailingClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def delete(self, *_args, **_kwargs):
        raise httpx.ConnectError("network down")


def test_netlify_create_zip_preserves_relative_paths(tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    (exports_dir / "fr").mkdir(parents=True)
    (exports_dir / "index.html").write_text("hello", encoding="utf-8")
    (exports_dir / "fr" / "taxons.html").write_text("taxons", encoding="utf-8")

    buffer = NetlifyDeployer._create_zip(exports_dir)

    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
        assert sorted(archive.namelist()) == ["fr/taxons.html", "index.html"]


def test_netlify_deployer_reports_live_url(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    (exports_dir / "index.html").write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.netlify.CredentialService.get",
        lambda *_args, **_kwargs: "netlify-token",
    )
    created_clients = []

    def fake_async_client(**kwargs):
        client = _FakeClient(_FakeResponse(201, {"id": "deploy-123"}))
        client.init_kwargs = kwargs
        created_clients.append(client)
        return client

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.netlify.httpx.AsyncClient",
        fake_async_client,
    )

    async def fake_poll(*_args, **_kwargs):
        return {
            "state": "ready",
            "ssl_url": "https://niamoto-test.netlify.app",
        }

    monkeypatch.setattr(NetlifyDeployer, "_poll_deploy", staticmethod(fake_poll))

    deployer = NetlifyDeployer()
    config = DeployConfig(
        platform="netlify",
        exports_dir=exports_dir,
        project_name="niamoto-test",
        extra={"site_id": "site-123"},
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("Deploy created: deploy-123" in line for line in lines)
    assert any("SUCCESS: Deployment is live!" in line for line in lines)
    assert any("URL: https://niamoto-test.netlify.app" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
    client = created_clients[0]
    assert client.init_kwargs["base_url"] == "https://api.netlify.com"
    assert client.init_kwargs["headers"] == {"Authorization": "Bearer netlify-token"}
    method, args, kwargs = client.calls[0]
    assert method == "post"
    assert args == ("/api/v1/sites/site-123/deploys",)
    assert kwargs["headers"] == {"Content-Type": "application/zip"}
    with zipfile.ZipFile(io.BytesIO(kwargs["content"])) as archive:
        assert archive.read("index.html") == b"hello"


def test_netlify_deployer_rejects_missing_exports_before_http(
    monkeypatch, tmp_path: Path
) -> None:
    calls = []

    def fail_async_client(**_kwargs):
        calls.append("called")
        raise AssertionError("Netlify client should not be created")

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.netlify.httpx.AsyncClient",
        fail_async_client,
    )

    deployer = NetlifyDeployer()
    config = DeployConfig(
        platform="netlify",
        exports_dir=tmp_path / "missing",
        project_name="niamoto-test",
        extra={"site_id": "site-123"},
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("ERROR: Export directory not found" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
    assert calls == []


def test_netlify_unpublish_reports_network_errors(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.netlify.CredentialService.get",
        lambda *_args, **_kwargs: "netlify-token",
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.netlify.httpx.AsyncClient",
        lambda **_kwargs: _FailingClient(),
    )

    deployer = NetlifyDeployer()
    config = DeployConfig(
        platform="netlify",
        exports_dir=exports_dir,
        project_name="niamoto-test",
        extra={"site_id": "site-123"},
    )

    lines = asyncio.run(_collect_lines(deployer.unpublish(config)))

    assert any("ERROR: Failed to delete site" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
