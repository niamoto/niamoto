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


def test_archived_debug_scripts_use_repository_root():
    for script_name in (
        "trace_flow.py",
        "test_auto_detection.py",
        "test_auto_suggestions.py",
        "test_pattern_matching.py",
    ):
        script_path = REPO_ROOT / "scripts" / "_archive" / "debug" / script_name
        script_source = script_path.read_text(encoding="utf-8")

        assert "REPO_ROOT = Path(__file__).resolve().parents[3]" in script_source
        assert 'REPO_ROOT / "src"' in script_source
