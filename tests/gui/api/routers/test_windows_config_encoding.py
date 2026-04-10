"""Regression tests for UTF-8 config loading on Windows-style locales."""

from __future__ import annotations

import builtins
import io
from pathlib import Path

import niamoto.gui.api.routers.export as export_router
import niamoto.gui.api.routers.transform as transform_router
from niamoto.gui.api.services.job_file_store import JobFileStore


def _simulate_non_utf8_system_open(monkeypatch) -> None:
    """Mimic a Windows locale defaulting text mode reads to cp1252."""

    real_open = builtins.open

    def open_with_cp1252_default(file, mode="r", *args, **kwargs):
        if "b" not in mode and "encoding" not in kwargs:
            kwargs["encoding"] = "cp1252"
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_with_cp1252_default)


def _simulate_non_utf8_pathlib_open(monkeypatch) -> None:
    """Mimic a Windows locale for pathlib text helpers backed by io.open."""

    real_open = io.open

    def open_with_cp1252_default(file, mode="r", *args, **kwargs):
        positional_encoding = args[1] if len(args) > 1 else None
        if "b" not in mode and "encoding" not in kwargs and positional_encoding is None:
            kwargs["encoding"] = "cp1252"
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", open_with_cp1252_default)


def test_export_config_loader_forces_utf8(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "export.yml"
    config_path.write_text("exports:\n  - name: Árbre\n", encoding="utf-8")

    monkeypatch.setattr(export_router, "get_config_path", lambda _: config_path)
    _simulate_non_utf8_system_open(monkeypatch)

    config = export_router.get_export_config("config/export.yml")

    assert config["exports"][0]["name"] == "Árbre"


def test_transform_config_loader_forces_utf8(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "transform.yml"
    config_path.write_text(
        "- group_by: plots\n  widgets_data:\n    Árbre:\n      plugin: top_ranking\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(transform_router, "get_config_path", lambda _: config_path)
    _simulate_non_utf8_system_open(monkeypatch)

    config = transform_router.get_transform_config("config/transform.yml")

    assert config[0]["widgets_data"]["Árbre"]["plugin"] == "top_ranking"


def test_job_file_store_forces_utf8_for_json_files(monkeypatch, tmp_path: Path):
    _simulate_non_utf8_pathlib_open(monkeypatch)
    store = JobFileStore(tmp_path)

    first_job = store.create_job("export")
    store.update_progress(first_job["id"], 50, "Création forêt")
    store.complete_job(first_job["id"], result={"label": "Été"})

    store.create_job("export")

    history = store.get_history()

    assert history[0]["message"] == "Création forêt"
    assert history[0]["result"]["label"] == "Été"
