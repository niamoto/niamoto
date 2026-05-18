"""Tests for scripts/build/generate_requirements.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "build"
    / "generate_requirements.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_requirements", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_requirements"] = module
    spec.loader.exec_module(module)
    return module


def test_add_platform_markers_marks_uvloop_as_non_windows(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n".join(
            [
                "uvicorn==0.42.0",
                "uvloop==0.21.0",
                "    # via uvicorn",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    module = _load_module()
    module.add_platform_markers(requirements)

    assert 'uvloop==0.21.0 ; sys_platform != "win32"' in requirements.read_text(
        encoding="utf-8"
    )


def test_add_platform_markers_keeps_existing_marker(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        'uvloop==0.21.0 ; sys_platform != "win32"\n',
        encoding="utf-8",
    )

    module = _load_module()
    module.add_platform_markers(requirements)

    assert (
        requirements.read_text(encoding="utf-8")
        == 'uvloop==0.21.0 ; sys_platform != "win32"\n'
    )
