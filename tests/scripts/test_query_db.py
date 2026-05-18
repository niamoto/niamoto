"""Tests for scripts/data/query_db.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "data" / "query_db.py"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module():
    spec = importlib.util.spec_from_file_location("query_db", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["query_db"] = module
    spec.loader.exec_module(module)
    return module


def test_default_database_path_is_resolved_from_repo_root():
    module = _load_module()

    assert module.REPO_ROOT == REPO_ROOT
    assert module.get_default_db_path() == str(
        REPO_ROOT / "test-instance" / "niamoto-nc" / "db" / "niamoto.duckdb"
    )
