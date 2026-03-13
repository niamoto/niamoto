"""SSH/rsync deployer plugin using subprocess."""

import asyncio
import logging
import shutil
from typing import AsyncIterator

from niamoto.core.plugins.base import DeployerPlugin, register
from .models import DeployConfig

logger = logging.getLogger(__name__)


@register("ssh")
class SSHDeployer(DeployerPlugin):
    """Deploy static sites via rsync over SSH."""

    platform = "ssh"

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files via rsync/SSH and yield SSE log lines."""
        yield self.sse_log("Starting SSH/rsync deployment...")

        # 1. Extract config
        host = config.extra.get("host")
        path = config.extra.get("path")
        port = config.extra.get("port", 22)
        key_path = config.extra.get("key_path")

        if not host:
            yield self.sse_error("No host configured. Set 'host' in extra config.")
            yield self.sse_done()
            return

        if not path:
            yield self.sse_error(
                "No remote path configured. Set 'path' in extra config."
            )
            yield self.sse_done()
            return

        exports_dir = config.exports_dir
        if not exports_dir.exists():
            yield self.sse_error(f"Export directory not found: {exports_dir}")
            yield self.sse_done()
            return

        # Check rsync is available
        if not shutil.which("rsync"):
            yield self.sse_error(
                "rsync not found on this system. Please install rsync."
            )
            yield self.sse_done()
            return

        # 2. Build rsync command
        ssh_cmd = f"ssh -p {port}"
        if key_path:
            ssh_cmd += f" -i {key_path}"

        # Trailing slash on source ensures contents are synced, not the directory itself
        source = f"{exports_dir}/"
        destination = f"{host}:{path}/"

        cmd = [
            "rsync",
            "-avz",
            "--delete",
            "-e",
            ssh_cmd,
            source,
            destination,
        ]

        yield self.sse_log(f"Syncing to {host}:{path} (port {port})...")

        # 3. Run as async subprocess
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as e:
            yield self.sse_error(f"Failed to start rsync: {e}")
            yield self.sse_done()
            return

        # 4. Stream stdout lines
        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="replace").strip()
            if decoded:
                yield self.sse_log(decoded)

        # Wait for process to finish
        await process.wait()

        # Check for stderr on failure
        if process.returncode != 0:
            assert process.stderr is not None
            stderr_data = await process.stderr.read()
            stderr_text = stderr_data.decode("utf-8", errors="replace").strip()
            if stderr_text:
                # Yield last few lines of stderr
                for err_line in stderr_text.splitlines()[-5:]:
                    yield self.sse_error(err_line)
            yield self.sse_error(f"rsync exited with code {process.returncode}")
            yield self.sse_done()
            return

        # 5. Success
        url = config.extra.get("url")
        if url:
            yield self.sse_url(url)
            yield self.sse_success(f"Deployed via SSH to {host}:{path}")
        else:
            yield self.sse_success(f"Deployed via SSH to {host}:{path}")

        yield self.sse_done()
