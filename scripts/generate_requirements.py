#!/usr/bin/env python3
"""Script to generate requirements.txt and requirements-dev.txt files."""

import subprocess
import sys
from pathlib import Path


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


def main() -> int:
    """Generate requirements files."""
    project_root = Path(__file__).parent.parent
    venv_path = project_root / ".venv"

    if not venv_path.exists():
        print("Virtual environment not found. Please create it first.", file=sys.stderr)
        sys.exit(1)

    # Activate virtual environment
    activate_script = venv_path / "bin" / "activate"
    if not activate_script.exists():
        print("Activation script not found in virtual environment.", file=sys.stderr)
        sys.exit(1)

    # Generate main requirements.txt
    print("Generating main requirements.txt...")
    run_command(["uv", "pip", "compile", "pyproject.toml", "-o", "requirements.txt"])

    # Generate requirements-dev.txt
    print("Generating dev-requirements.txt...")
    run_command(
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            "--extra",
            "dev",
            "-o",
            "dev-requirements.txt",
        ]
    )

    print("Requirements files generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # type: ignore
