"""Base deployer interface for all deployment platforms."""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeployConfig:
    """Configuration for a deployment."""

    platform: str
    exports_dir: Path
    project_name: str
    branch: Optional[str] = None
    # Platform-specific extra config
    extra: dict = field(default_factory=dict)


@dataclass
class DeployResult:
    """Result of a deployment."""

    success: bool
    url: Optional[str] = None
    error: Optional[str] = None


# File size limits per platform (in bytes)
PLATFORM_LIMITS = {
    "cloudflare": {"max_file_size": 25 * 1024 * 1024, "max_files": 20_000},
    "github": {"max_file_size": 100 * 1024 * 1024, "max_files": None},
    "netlify": {"max_file_size": 100 * 1024 * 1024, "max_files": None},
    "vercel": {"max_file_size": 50 * 1024 * 1024, "max_files": None},
    "render": {"max_file_size": None, "max_files": None},
    "ssh": {"max_file_size": None, "max_files": None},
}


class BaseDeployer(ABC):
    """Abstract base class for all deployment platforms."""

    platform: str = ""

    @abstractmethod
    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        """Deploy files and yield SSE log lines.

        Yields strings in the format:
        - Regular log: "data: some message\\n\\n"
        - Error: "data: ERROR: message\\n\\n"
        - Success: "data: SUCCESS: message\\n\\n"
        - URL: "data: URL: https://...\\n\\n"
        - Done: "data: DONE\\n\\n"
        """
        yield ""  # pragma: no cover

    def validate_exports(self, config: DeployConfig) -> list[str]:
        """Pre-flight validation of export directory. Returns list of warnings/errors."""
        errors = []
        exports_dir = config.exports_dir

        if not exports_dir.exists():
            errors.append(f"Export directory not found: {exports_dir}")
            return errors

        if not (exports_dir / "index.html").exists():
            errors.append("No index.html found in export directory")

        limits = PLATFORM_LIMITS.get(config.platform, {})
        max_file_size = limits.get("max_file_size")
        max_files = limits.get("max_files")

        file_count = 0
        for root, _dirs, files in os.walk(exports_dir):
            for f in files:
                file_count += 1
                if max_file_size:
                    file_path = Path(root) / f
                    size = file_path.stat().st_size
                    if size > max_file_size:
                        size_mb = size / (1024 * 1024)
                        limit_mb = max_file_size / (1024 * 1024)
                        errors.append(
                            f"File too large for {config.platform}: "
                            f"{file_path.relative_to(exports_dir)} "
                            f"({size_mb:.1f} MiB > {limit_mb:.0f} MiB limit)"
                        )

        if max_files and file_count > max_files:
            errors.append(
                f"Too many files for {config.platform}: "
                f"{file_count} files (limit: {max_files})"
            )

        return errors

    @staticmethod
    def sse_log(message: str) -> str:
        """Format a message as an SSE data line."""
        return f"data: {message}\n\n"

    @staticmethod
    def sse_error(message: str) -> str:
        """Format an error as an SSE data line."""
        return f"data: ERROR: {message}\n\n"

    @staticmethod
    def sse_success(message: str) -> str:
        """Format a success as an SSE data line."""
        return f"data: SUCCESS: {message}\n\n"

    @staticmethod
    def sse_url(url: str) -> str:
        """Format a URL as an SSE data line."""
        return f"data: URL: {url}\n\n"

    @staticmethod
    def sse_done() -> str:
        """Format the done signal as an SSE data line."""
        return "data: DONE\n\n"
