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

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *_args, **_kwargs):
        return self._response


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
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.netlify.httpx.AsyncClient",
        lambda **_kwargs: _FakeClient(_FakeResponse(201, {"id": "deploy-123"})),
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
