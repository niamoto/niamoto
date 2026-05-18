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


def test_serve_file_allows_images_under_files(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    image_path = work_dir / "files" / "logo.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/files/serve/files/logo.png")

    assert response.status_code == 200
    assert response.content == b"\x89PNG\r\n\x1a\n"


def test_serve_file_rejects_project_config_files(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    config_path = work_dir / "config" / "import.yml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("secret: value", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/files/serve/config/import.yml")

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: file outside files directory"


def test_serve_file_rejects_non_image_files_under_files(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    text_path = work_dir / "files" / "secret.txt"
    text_path.parent.mkdir(parents=True)
    text_path.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(
        "niamoto.gui.api.routers.files.get_working_directory",
        lambda: work_dir,
    )

    client = TestClient(create_app())
    response = client.get("/api/files/serve/files/secret.txt")

    assert response.status_code == 403
    assert response.json()["detail"] == "Unsupported file type"


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
