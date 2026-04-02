"""Helpers for desktop startup diagnostics."""

from __future__ import annotations

import os
import time
from pathlib import Path


def log_desktop_startup(message: str) -> None:
    """Append a startup diagnostic line when desktop tracing is enabled."""
    log_path = os.environ.get("NIAMOTO_STARTUP_LOG")
    if not log_path:
        return

    session = os.environ.get("NIAMOTO_STARTUP_SESSION", "unknown")
    timestamp = time.time()
    pid = os.getpid()

    try:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp:.3f}] [{session}] [python:{pid}] {message}\n")
    except Exception:
        # Startup diagnostics must never block application launch.
        return
