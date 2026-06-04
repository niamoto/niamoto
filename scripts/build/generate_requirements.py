#!/usr/bin/env python3
"""Script to generate requirements.txt and dev-requirements.txt files."""

import subprocess
import sys
import tempfile
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


def ensure_requirements_has_packages(requirements_path: Path) -> None:
    """Ensure a generated requirements file contains at least one package."""
    lines = requirements_path.read_text(encoding="utf-8").splitlines()
    has_package = any(
        line and not line.startswith("#") and not line.startswith(" ") for line in lines
    )
    if not has_package:
        raise RuntimeError(
            f"Generated requirements file has no package entries: {requirements_path}"
        )


def command_with_output_path(cmd: list[str], output_path: Path) -> list[str]:
    """Return a copy of a uv compile command that writes to output_path."""
    if "-o" not in cmd:
        raise ValueError("Command must include an -o output argument")

    output_index = cmd.index("-o") + 1
    if output_index >= len(cmd):
        raise ValueError("Command -o argument must include an output path")

    updated_cmd = [*cmd]
    updated_cmd[output_index] = str(output_path)
    return updated_cmd


def restore_compile_command_output_path(
    requirements_path: Path,
    temp_output_path: Path,
    original_cmd: list[str],
) -> None:
    """Keep uv's generated header stable when compiling through a temp file."""
    if "-o" not in original_cmd:
        return

    output_index = original_cmd.index("-o") + 1
    if output_index >= len(original_cmd):
        return

    original_output = original_cmd[output_index]
    content = requirements_path.read_text(encoding="utf-8")
    requirements_path.write_text(
        content.replace(str(temp_output_path), original_output),
        encoding="utf-8",
    )


def compile_requirements_file(cmd: list[str], output_path: Path) -> None:
    """Compile requirements atomically without clobbering existing output."""
    output_path = Path(output_path)
    with tempfile.NamedTemporaryFile(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        run_command(command_with_output_path(cmd, temp_path))
        restore_compile_command_output_path(temp_path, temp_path, cmd)
        add_platform_markers(temp_path)
        ensure_requirements_has_packages(temp_path)
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


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
    compile_requirements_file(
        [
            "uv",
            "pip",
            "compile",
            "pyproject.toml",
            *resolution_args,
            "-o",
            "requirements.txt",
        ],
        project_root / "requirements.txt",
    )

    # Generate dev-requirements.txt from the shared development dependency group.
    print("Generating dev-requirements.txt...")
    compile_requirements_file(
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
        ],
        project_root / "dev-requirements.txt",
    )

    print("Requirements files generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # type: ignore
