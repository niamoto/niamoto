import asyncio
from pathlib import Path

import yaml

from niamoto.gui.api.routers import config as config_router


def _write_project_config(work_dir: Path, project_name: str) -> None:
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yml").write_text(
        yaml.safe_dump(
            {
                "project": {
                    "name": project_name,
                    "version": "1.0.0",
                    "created_at": "2026-05-01T12:00:00",
                }
            }
        ),
        encoding="utf-8",
    )


def test_project_info_exposes_active_instance_identity(tmp_path, monkeypatch):
    work_dir = tmp_path / "nouvelle-caledonie"
    _write_project_config(work_dir, "niamoto-subset")

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = asyncio.run(config_router.get_project_info())

    assert response["name"] == "niamoto-subset"
    assert response["working_directory"] == str(work_dir)
    assert response["instance_name"] == "nouvelle-caledonie"


def test_project_info_default_includes_active_instance_identity(tmp_path, monkeypatch):
    work_dir = tmp_path / "project-without-config-name"
    (work_dir / "config").mkdir(parents=True)

    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = asyncio.run(config_router.get_project_info())

    assert response["name"] == "Niamoto Project"
    assert response["working_directory"] == str(work_dir)
    assert response["instance_name"] == "project-without-config-name"
