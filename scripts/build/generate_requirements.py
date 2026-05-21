#!/usr/bin/env python3
"""Script to generate requirements.txt and dev-requirements.txt files."""

import subprocess
import sys
import tomllib
from pathlib import Path


UVLOOP_WINDOWS_MARKER = '; sys_platform != "win32"'


def add_platform_markers(requirements_path: Path) -> None:
    """Add markers for dependencies that cannot install on every platform."""
    if not requirements_path.exists():
        return

    lines = requirements_path.read_text(encoding="utf-8").splitlines()
    updated_lines = []
    for line in lines:
        if line.startswith("uvloop==") and ";" not in line:
            line = f"{line} {UVLOOP_WINDOWS_MARKER}"
        updated_lines.append(line)

    requirements_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def run_command(cmd):
    """Run a command and return its output."""
    if not isinstance(cmd, list):
        raise ValueError("Command must be a list of strings")

    # Validate each argument is a string
    if not all(isinstance(arg, str) for arg in cmd):
        raise ValueError("All command arguments must be strings")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            shell=False,  # Explicitly disable shell to prevent command injection
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}", file=sys.stderr)
        print(f"Command output: {e.output}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def uv_resolution_args(lock_path: Path) -> list[str]:
    """Return uv resolver options captured in uv.lock."""
    if not lock_path.exists():
        return []

    lock_data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    options = lock_data.get("options", {})
    args = []

    exclude_newer = options.get("exclude-newer")
    if isinstance(exclude_newer, str):
        args.extend(["--exclude-newer", exclude_newer])

    exclude_newer_packages = options.get("exclude-newer-package", {})
    if isinstance(exclude_newer_packages, dict):
        for package_name in sorted(exclude_newer_packages):
            cutoff = exclude_newer_packages[package_name]
            if isinstance(cutoff, str):
                args.extend(["--exclude-newer-package", f"{package_name}={cutoff}"])

    return args


def main() -> int:
    """Generate requirements files."""
    project_root = Path(__file__).parent.parent.parent
    venv_path = project_root / ".venv"

    if not venv_path.exists():
        print("Virtual environment not found. Please create it first.", file=sys.stderr)
        sys.exit(1)

    # Activate virtual environment
    activate_script = venv_path / "bin" / "activate"
    if not activate_script.exists():
        print("Activation script not found in virtual environment.", file=sys.stderr)
        sys.exit(1)

    resolution_args = uv_resolution_args(project_root / "uv.lock")

    # Generate main requirements.txt
    print("Generating main requirements.txt...")
    run_command(
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            *resolution_args,
            "-o",
            "requirements.txt",
        ]
    )
    add_platform_markers(project_root / "requirements.txt")

    # Generate dev-requirements.txt from the shared development dependency group.
    print("Generating dev-requirements.txt...")
    run_command(
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "--group",
            "dev",
            *resolution_args,
            "-o",
            "dev-requirements.txt",
        ]
    )
    add_platform_markers(project_root / "dev-requirements.txt")

    print("Requirements files generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # type: ignore
