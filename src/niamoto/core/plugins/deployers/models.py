"""Shared models and configuration for deployer plugins."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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
