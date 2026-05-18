from __future__ import annotations

import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dev_api_uses_repository_root_for_relative_paths():
    script_globals = runpy.run_path(str(REPO_ROOT / "scripts" / "dev" / "dev_api.py"))

    assert script_globals["repo_root"] == REPO_ROOT


def test_evaluate_pipeline_uses_repository_root_for_imports():
    script_globals = runpy.run_path(
        str(REPO_ROOT / "scripts" / "dev" / "evaluate_pipeline.py")
    )

    assert script_globals["REPO_ROOT"] == REPO_ROOT
    assert script_globals["SRC_DIR"] == REPO_ROOT / "src"


def test_archived_optimized_test_runner_uses_repository_root():
    script_globals = runpy.run_path(
        str(REPO_ROOT / "scripts" / "_archive" / "run_tests_optimized.py")
    )

    assert script_globals["repository_root"]() == REPO_ROOT
