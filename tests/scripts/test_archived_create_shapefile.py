from __future__ import annotations

import importlib.util
import io
import types
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_create_shapefile_module():
    script_path = REPO_ROOT / "scripts" / "_archive" / "create_shapefile.py"
    spec = importlib.util.spec_from_file_location(
        "archived_create_shapefile", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_download_extract_zip_rejects_traversal_members(tmp_path, monkeypatch):
    module = _load_create_shapefile_module()
    archive_bytes = _zip_bytes({"safe.dbf": b"dbf", "../evil.shp": b"outside"})

    response = types.SimpleNamespace(
        content=archive_bytes,
        raise_for_status=lambda: None,
    )
    monkeypatch.setattr(module.requests, "get", lambda _url: response)

    with pytest.raises(ValueError, match="Unsafe ZIP member path"):
        module.download_extract_zip(
            "https://example.invalid/archive.zip",
            tmp_path / "out",
        )

    assert not (tmp_path / "evil.shp").exists()
    assert not (tmp_path / "out" / "safe.dbf").exists()


def test_download_extract_zip_extracts_shapefile_members_only(tmp_path, monkeypatch):
    module = _load_create_shapefile_module()
    archive_bytes = _zip_bytes(
        {
            "nested/countries.shp": b"shape",
            "nested/countries.dbf": b"dbf",
            "nested/ignore.txt": b"ignore",
        }
    )

    response = types.SimpleNamespace(
        content=archive_bytes,
        raise_for_status=lambda: None,
    )
    monkeypatch.setattr(module.requests, "get", lambda _url: response)

    shp_path = module.download_extract_zip(
        "https://example.invalid/archive.zip",
        tmp_path / "out",
    )

    assert Path(shp_path).read_bytes() == b"shape"
    assert (tmp_path / "out" / "nested" / "countries.dbf").read_bytes() == b"dbf"
    assert not (tmp_path / "out" / "nested" / "ignore.txt").exists()
