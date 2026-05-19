"""Tests for the GitHub Pages deployer."""

import asyncio
from pathlib import Path
import shutil
import subprocess
import tempfile

import httpx
import pytest

from niamoto.core.plugins.deployers.github import (
    GITHUB_API_SAFE_FILE_LIMIT,
    GitHubDeployer,
)
from niamoto.core.plugins.deployers.models import DeployConfig


async def _collect_lines(generator):
    return [line async for line in generator]


class _FakeGitHubResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.github.com/test")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("GitHub API error", request, response)


def _run_git(git_binary: str, *args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        [git_binary, *args],
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is required for this test")
def test_github_deployer_pushes_exports_with_local_git(monkeypatch):
    git_binary = shutil.which("git")
    assert git_binary is not None

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        exports_dir = root / "exports"
        remote_dir = root / "remote.git"

        (exports_dir / "fr" / "taxons").mkdir(parents=True, exist_ok=True)
        (exports_dir / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")
        (exports_dir / "fr" / "taxons" / "42.html").write_text(
            "<h1>Taxon</h1>", encoding="utf-8"
        )

        _run_git(git_binary, "init", "--bare", str(remote_dir))

        monkeypatch.setattr(
            "niamoto.core.plugins.deployers.github.CredentialService.get",
            lambda platform, key: "github_pat_test",
        )
        monkeypatch.setattr(
            GitHubDeployer,
            "_get_git_remote_url",
            staticmethod(lambda owner, repo: str(remote_dir)),
        )
        monkeypatch.setattr(
            GitHubDeployer,
            "_configure_git_credentials",
            staticmethod(lambda credential_file, owner, repo, token: None),
        )

        deployer = GitHubDeployer()
        config = DeployConfig(
            platform="github",
            exports_dir=exports_dir,
            project_name="niamoto-test",
            extra={"repo": "arsis-dev/niamoto-test", "branch": "gh-pages"},
        )

        lines = asyncio.run(_collect_lines(deployer.deploy(config)))

        assert any("Using local git transport" in line for line in lines)
        assert any("SUCCESS: Deployed to GitHub Pages" in line for line in lines)
        assert "<h1>Hello</h1>" in _run_git(
            git_binary,
            f"--git-dir={remote_dir}",
            "show",
            "gh-pages:index.html",
        )
        assert "<h1>Taxon</h1>" in _run_git(
            git_binary,
            f"--git-dir={remote_dir}",
            "show",
            "gh-pages:fr/taxons/42.html",
        )
        assert (
            _run_git(
                git_binary,
                f"--git-dir={remote_dir}",
                "show",
                "gh-pages:.nojekyll",
            )
            == ""
        )


def test_github_deployer_blocks_large_api_fallback_without_git(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        exports_dir = Path(temp_dir) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        for index in range(GITHUB_API_SAFE_FILE_LIMIT + 1):
            (exports_dir / f"page-{index}.html").write_text("ok", encoding="utf-8")

        monkeypatch.setattr(
            "niamoto.core.plugins.deployers.github.CredentialService.get",
            lambda platform, key: "github_pat_test",
        )
        monkeypatch.setattr(
            "niamoto.core.plugins.deployers.github.shutil.which", lambda name: None
        )

        deployer = GitHubDeployer()
        config = DeployConfig(
            platform="github",
            exports_dir=exports_dir,
            project_name="niamoto-test",
            extra={"repo": "arsis-dev/niamoto-test"},
        )

        lines = asyncio.run(_collect_lines(deployer.deploy(config)))

        assert any("Git is not available on this system" in line for line in lines)
        assert any(line.strip() == "data: DONE" for line in lines)


def test_github_deployer_api_fallback_preserves_nojekyll(monkeypatch):
    captured_tree_entries = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.blob_index = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            if url == "/repos/arsis-dev/niamoto-test":
                return _FakeGitHubResponse(payload={"size": 1})
            if url == "/repos/arsis-dev/niamoto-test/git/refs/heads/gh-pages":
                return _FakeGitHubResponse(payload={"object": {"sha": "parent-sha"}})
            return _FakeGitHubResponse(status_code=404)

        async def post(self, url, json):
            if url == "/repos/arsis-dev/niamoto-test/git/blobs":
                self.blob_index += 1
                return _FakeGitHubResponse(payload={"sha": f"blob-{self.blob_index}"})
            if url == "/repos/arsis-dev/niamoto-test/git/trees":
                captured_tree_entries.extend(json["tree"])
                return _FakeGitHubResponse(payload={"sha": "tree-sha"})
            if url == "/repos/arsis-dev/niamoto-test/git/commits":
                return _FakeGitHubResponse(payload={"sha": "commit-sha-12345678"})
            return _FakeGitHubResponse(status_code=404)

        async def patch(self, url, json):
            if url == "/repos/arsis-dev/niamoto-test/git/refs/heads/gh-pages":
                return _FakeGitHubResponse()
            return _FakeGitHubResponse(status_code=404)

    with tempfile.TemporaryDirectory() as temp_dir:
        exports_dir = Path(temp_dir) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        (exports_dir / "index.html").write_text("<h1>Hello</h1>", encoding="utf-8")

        monkeypatch.setattr(
            "niamoto.core.plugins.deployers.github.httpx.AsyncClient",
            FakeAsyncClient,
        )

        deployer = GitHubDeployer()
        config = DeployConfig(
            platform="github",
            exports_dir=exports_dir,
            project_name="niamoto-test",
            extra={"repo": "arsis-dev/niamoto-test", "branch": "gh-pages"},
        )

        lines = asyncio.run(
            _collect_lines(
                deployer._deploy_with_api(
                    config=config,
                    owner="arsis-dev",
                    repo="niamoto-test",
                    branch="gh-pages",
                    token="github_pat_test",
                    file_paths=[("index.html", str(exports_dir / "index.html"))],
                )
            )
        )

        nojekyll_entry = next(
            entry for entry in captured_tree_entries if entry["path"] == ".nojekyll"
        )
        assert [entry["path"] for entry in captured_tree_entries] == [
            "index.html",
            ".nojekyll",
        ]
        assert nojekyll_entry["mode"] == "100644"
        assert nojekyll_entry["type"] == "blob"
        assert any("SUCCESS: Deployed to GitHub Pages" in line for line in lines)


def test_github_deployer_api_fallback_reports_network_errors(monkeypatch, tmp_path):
    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            request = httpx.Request("GET", f"https://api.github.com{url}")
            raise httpx.ConnectError("network down", request=request)

    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    (exports_dir / "index.html").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.github.httpx.AsyncClient",
        FailingAsyncClient,
    )

    deployer = GitHubDeployer()
    config = DeployConfig(
        platform="github",
        exports_dir=exports_dir,
        project_name="niamoto-test",
        extra={"repo": "arsis-dev/niamoto-test", "branch": "gh-pages"},
    )

    lines = asyncio.run(
        _collect_lines(
            deployer._deploy_with_api(
                config=config,
                owner="arsis-dev",
                repo="niamoto-test",
                branch="gh-pages",
                token="github_pat_test",
                file_paths=[("index.html", str(exports_dir / "index.html"))],
            )
        )
    )

    assert any("ERROR: GitHub API request failed" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"


def test_github_deployer_unpublish_reports_network_errors(monkeypatch, tmp_path):
    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def delete(self, url):
            request = httpx.Request("DELETE", f"https://api.github.com{url}")
            raise httpx.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.github.CredentialService.get",
        lambda platform, key: "github_pat_test",
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.github.httpx.AsyncClient",
        FailingAsyncClient,
    )

    deployer = GitHubDeployer()
    config = DeployConfig(
        platform="github",
        exports_dir=tmp_path,
        project_name="niamoto-test",
        extra={"repo": "arsis-dev/niamoto-test", "branch": "gh-pages"},
    )

    lines = asyncio.run(_collect_lines(deployer.unpublish(config)))

    assert any("ERROR: GitHub API request failed" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
