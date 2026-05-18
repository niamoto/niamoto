"""Tests for archived preview validation helpers."""

import importlib.util
from pathlib import Path


def _load_validate_preview_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "_archive"
        / "validate_preview.py"
    )
    spec = importlib.util.spec_from_file_location(
        "validate_preview_archive", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_sample_data_parameterizes_family_name(monkeypatch):
    """Family names containing quotes are passed as SQL parameters."""
    module = _load_validate_preview_module()

    class FakeDatabase:
        def __init__(self, path, read_only=False):
            self.path = path
            self.read_only = read_only
            self.engine = object()
            self.closed = False

        def has_table(self, name):
            return name == "occurrences"

        def close_db_session(self):
            self.closed = True

    captured = {}

    def fake_read_sql(query, engine, params=None):
        captured["query"] = str(query)
        captured["params"] = params
        captured["engine"] = engine
        return "rows"

    monkeypatch.setattr("niamoto.common.database.Database", FakeDatabase)
    monkeypatch.setattr(module.pd, "read_sql", fake_read_sql)

    result = module.load_sample_data("Myrta' OR 1=1 --", limit=10)

    assert result == "rows"
    assert 'WHERE "family" = :family_name' in captured["query"]
    assert "ORDER BY RANDOM() LIMIT 10" in captured["query"]
    assert "Myrta' OR 1=1 --" not in captured["query"]
    assert captured["params"] == {"family_name": "Myrta' OR 1=1 --"}
