"""Tests for the GitHub Pages deployer."""

import asyncio
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

from niamoto.core.plugins.deployers.github import (
    GITHUB_API_SAFE_FILE_LIMIT,
    GitHubDeployer,
)
from niamoto.core.plugins.deployers.models import DeployConfig


async def _collect_lines(generator):
    return [line async for line in generator]


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
