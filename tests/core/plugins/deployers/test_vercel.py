from __future__ import annotations

import asyncio
from pathlib import Path

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

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *_args, **_kwargs):
        return self._responses.pop(0)


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

    client_queue = [
        _FakeClient([_FakeResponse(200)]),
        _FakeClient([_FakeResponse(201, {"url": "niamoto-site.vercel.app"})]),
    ]

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
