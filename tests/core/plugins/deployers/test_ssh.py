from __future__ import annotations

import asyncio
from pathlib import Path

from niamoto.core.plugins.deployers.models import DeployConfig
from niamoto.core.plugins.deployers.ssh import SSHDeployer


async def _collect_lines(generator):
    return [line async for line in generator]


class _FakeStream:
    def __init__(self, lines: list[bytes]):
        self._lines = lines

    async def readline(self) -> bytes:
        if self._lines:
            return self._lines.pop(0)
        return b""

    async def read(self) -> bytes:
        return b""


class _FakeProcess:
    def __init__(self):
        self.stdout = _FakeStream([b"sending incremental file list\n", b"index.html\n"])
        self.stderr = _FakeStream([])
        self.returncode = 0

    async def wait(self) -> int:
        return self.returncode


def test_ssh_deployer_reports_missing_rsync(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.ssh.shutil.which", lambda _name: None
    )

    deployer = SSHDeployer()
    config = DeployConfig(
        platform="ssh",
        exports_dir=exports_dir,
        project_name="niamoto-site",
        extra={"host": "example.org", "path": "/srv/www"},
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("rsync not found on this system" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"


def test_ssh_deployer_streams_successful_rsync(monkeypatch, tmp_path: Path) -> None:
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    (exports_dir / "index.html").write_text("hello", encoding="utf-8")

    async def fake_create_subprocess_exec(*_args, **_kwargs):
        return _FakeProcess()

    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.ssh.shutil.which",
        lambda _name: "/usr/bin/rsync",
    )
    monkeypatch.setattr(
        "niamoto.core.plugins.deployers.ssh.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    deployer = SSHDeployer()
    config = DeployConfig(
        platform="ssh",
        exports_dir=exports_dir,
        project_name="niamoto-site",
        extra={
            "host": "example.org",
            "path": "/srv/www",
            "url": "https://example.org",
        },
    )

    lines = asyncio.run(_collect_lines(deployer.deploy(config)))

    assert any("sending incremental file list" in line for line in lines)
    assert any(
        "SUCCESS: Deployed via SSH to example.org:/srv/www" in line for line in lines
    )
    assert any("URL: https://example.org" in line for line in lines)
    assert lines[-1].strip() == "data: DONE"
