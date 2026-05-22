#!/usr/bin/env python3
"""Smoke-test a packaged Niamoto desktop sidecar by launching its GUI API."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Launch a packaged Niamoto sidecar and fail if /api/health never "
            "becomes ready."
        )
    )
    parser.add_argument(
        "--sidecar-path",
        required=True,
        help="Path to the packaged sidecar executable",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Existing NIAMOTO_HOME fixture directory to expose during startup",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="Maximum time, in seconds, to wait for the API health endpoint",
    )
    return parser.parse_args()


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(url: str, process: subprocess.Popen[str], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Sidecar exited early with code {process.returncode}")

        try:
            with urllib.request.urlopen(url, timeout=1.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass

        time.sleep(0.5)

    raise TimeoutError(f"Timed out waiting for {url}")


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def print_log_tail(log_path: Path) -> None:
    if not log_path.exists():
        return

    print("\n---- Sidecar log tail ----", file=sys.stderr)
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-80:]:
        print(line, file=sys.stderr)
    print("---- End sidecar log tail ----", file=sys.stderr)


def main() -> int:
    args = parse_args()

    sidecar_path = Path(args.sidecar_path).resolve()
    project_dir = Path(args.project_dir).resolve()

    if not sidecar_path.exists():
        print(f"Sidecar executable not found: {sidecar_path}", file=sys.stderr)
        return 1
    if not project_dir.is_dir():
        print(f"Project fixture directory not found: {project_dir}", file=sys.stderr)
        return 1

    port = pick_free_port()
    health_url = f"http://127.0.0.1:{port}/api/health"

    with tempfile.TemporaryDirectory(prefix="niamoto-sidecar-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        log_path = temp_root / "sidecar.log"
        env = os.environ.copy()
        env["NIAMOTO_HOME"] = str(project_dir)
        env["NIAMOTO_LOGS"] = str(temp_root / "logs")
        env["NIAMOTO_RUNTIME_MODE"] = "desktop"
        env["NIAMOTO_DESKTOP_SHELL"] = "tauri"
        env["NIAMOTO_DESKTOP_AUTH_TOKEN"] = "smoke-test-token"

        command = [
            str(sidecar_path),
            "gui",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-browser",
        ]

        print(f"Launching packaged sidecar: {' '.join(command)}")
        print(f"Using project fixture: {project_dir}")

        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )

            try:
                wait_for_health(health_url, process, args.timeout)
                print(f"Health check succeeded: {health_url}")
                return 0
            except Exception as exc:
                print(f"Packaged sidecar smoke test failed: {exc}", file=sys.stderr)
                print_log_tail(log_path)
                return 1
            finally:
                terminate_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
