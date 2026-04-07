"""Tests for health router desktop reload behavior."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from niamoto.gui.api.context import DesktopProjectReloadResult
from niamoto.gui.api.routers import health


def create_test_client() -> TestClient:
    """Create a minimal app that only mounts the health router."""
    app = FastAPI()
    app.include_router(health.router)
    app.state.job_store = "sentinel"
    app.state.job_store_work_dir = "sentinel"
    return TestClient(app)


class TestReloadProjectEndpoint:
    """Test `/api/health/reload-project` contract."""

    def test_loaded_state_resolves_job_store(self, monkeypatch: pytest.MonkeyPatch):
        client = create_test_client()
        loaded_project = Path("/tmp/niamoto-project")
        resolve_calls = []
        reset_calls = []

        monkeypatch.setattr(
            health,
            "reload_project_from_desktop_config",
            lambda: DesktopProjectReloadResult(
                state="loaded", project_path=loaded_project, message=None
            ),
        )
        monkeypatch.setattr(
            health, "resolve_job_store", lambda app: resolve_calls.append(app)
        )
        monkeypatch.setattr(
            health, "reset_preview_engine", lambda: reset_calls.append(True)
        )

        response = client.post("/api/health/reload-project")

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "state": "loaded",
            "project": str(loaded_project),
            "message": None,
        }
        assert resolve_calls == [client.app]
        assert reset_calls == [True]

    def test_welcome_state_clears_job_store(self, monkeypatch: pytest.MonkeyPatch):
        client = create_test_client()
        reset_calls = []

        monkeypatch.setattr(
            health,
            "reload_project_from_desktop_config",
            lambda: DesktopProjectReloadResult(
                state="welcome",
                project_path=None,
                message="No desktop project selected.",
            ),
        )
        monkeypatch.setattr(
            health,
            "resolve_job_store",
            lambda app: pytest.fail("resolve_job_store should not be called"),
        )
        monkeypatch.setattr(
            health, "reset_preview_engine", lambda: reset_calls.append(True)
        )

        response = client.post("/api/health/reload-project")

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "state": "welcome",
            "project": None,
            "message": "No desktop project selected.",
        }
        assert client.app.state.job_store is None
        assert client.app.state.job_store_work_dir is None
        assert reset_calls == [True]


def test_debug_test_500_endpoint_returns_intentional_server_error():
    client = create_test_client()

    response = client.get("/api/health/debug/test-500")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Intentional test 500 for bug report CTA validation."
    }

    def test_invalid_project_state_clears_job_store(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        client = create_test_client()
        reset_calls = []

        monkeypatch.setattr(
            health,
            "reload_project_from_desktop_config",
            lambda: DesktopProjectReloadResult(
                state="invalid-project",
                project_path=None,
                message="The selected desktop project is no longer available.",
            ),
        )
        monkeypatch.setattr(
            health,
            "resolve_job_store",
            lambda app: pytest.fail("resolve_job_store should not be called"),
        )
        monkeypatch.setattr(
            health, "reset_preview_engine", lambda: reset_calls.append(True)
        )

        response = client.post("/api/health/reload-project")

        assert response.status_code == 200
        assert response.json() == {
            "success": False,
            "state": "invalid-project",
            "project": None,
            "message": "The selected desktop project is no longer available.",
        }
        assert client.app.state.job_store is None
        assert client.app.state.job_store_work_dir is None
        assert reset_calls == [True]
