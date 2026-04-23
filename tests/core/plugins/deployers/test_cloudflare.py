from __future__ import annotations

import asyncio
from pathlib import Path

from niamoto.core.plugins.deployers.cloudflare import CloudflareDeployer
from niamoto.core.plugins.deployers.models import DeployConfig


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

    async def put(self, *_args, **_kwargs):
        return self._responses.pop(0)


def test_cloudflare_deployer_reports_missing_credentials(
    monkeypatch, tmp_path: Path
) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.cloudflare.CredentialService.get",
        lambda *_args, **_kwargs: None,
    )

    deployer = CloudflareDeployer()
    config = DeployConfig(
        platform="cloudflare",
        exports_dir=exports_dir,
        project_name="niamoto-test",
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("Missing Cloudflare credentials" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"


def test_cloudflare_deployer_uploads_manifest_and_returns_branch_url(
    monkeypatch, tmp_path: Path
) -> None:
    exports_dir = tmp_path / "exports"
    (exports_dir / "nested").mkdir(parents=True)
    (exports_dir / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
    (exports_dir / "nested" / "page.html").write_text(
        "<h1>Nested</h1>", encoding="utf-8"
    )

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.cloudflare.CredentialService.get",
        lambda _platform, key: {
            "api-token": "cf-token",
            "account-id": "account-123",
        }.get(key),
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.cloudflare.httpx.AsyncClient",
        lambda **_kwargs: _FakeClient(
            [
                _FakeResponse(
                    200,
                    {
                        "success": True,
                        "result": {
                            "jwt": "upload-jwt",
                            "buckets": [["bucket-hash"]],
                        },
                    },
                ),
                _FakeResponse(201, {"result": {"jwt": "completion-jwt"}}),
                _FakeResponse(200, {"success": True}),
            ]
        ),
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.cloudflare._hash_file",
        lambda _path: "bucket-hash",
    )

    deployer = CloudflareDeployer()
    config = DeployConfig(
        platform="cloudflare",
        exports_dir=exports_dir,
        project_name="niamoto-site",
        branch="preview",
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("Manifest ready: 2 files" in line for line in lines)
    assert any("Uploading 1 files in 1 bucket(s)" in line for line in lines)
    assert any(
        "SUCCESS: Deployed 2 files to Cloudflare Workers" in line for line in lines
    )
    assert any(
        "URL: https://preview.niamoto-site.workers.dev" in line for line in lines
    )
    assert lines[-1].strip() == "data: DONE"
