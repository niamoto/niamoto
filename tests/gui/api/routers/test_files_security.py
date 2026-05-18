"""Security regression tests for file router path containment."""

from __future__ import annotations

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


def test_read_export_file_rejects_sibling_prefix_escape(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    exports_dir = work_dir / "exports"
    sibling_dir = work_dir / "exports-backup"
    exports_dir.mkdir(parents=True)
    sibling_dir.mkdir()
    (sibling_dir / "secret.json").write_text('{"secret": true}', encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/files/exports/read",
        params={"file_path": "../exports-backup/secret.json"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: file outside exports directory"


def test_serve_file_rejects_sibling_prefix_escape(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    sibling_dir = tmp_path / "project-backup"
    work_dir.mkdir()
    sibling_dir.mkdir()
    (sibling_dir / "secret.txt").write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/files/serve/%2E%2E/project-backup/secret.txt")

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


def test_browse_files_rejects_paths_outside_project(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    sibling_dir = tmp_path / "project-backup"
    work_dir.mkdir()
    sibling_dir.mkdir()
    (sibling_dir / "secret.txt").write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get(
        "/api/files/browse",
        params={"path": "../project-backup"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: path outside project directory"


def test_browse_files_preserves_missing_project_path_404(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    work_dir.mkdir()

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/files/browse", params={"path": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Path not found"
