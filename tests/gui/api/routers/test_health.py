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


class TestHealthCheckEndpoint:
    """Test `/api/health` desktop startup probe behavior."""

    def test_returns_probe_token_only_when_requested(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        client = create_test_client()
        monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")

        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "message": "Niamoto API is running",
        }
        assert health.DESKTOP_TOKEN_HEADER not in response.headers

        probe_response = client.get(
            "/api/health", headers={health.DESKTOP_PROBE_HEADER: "1"}
        )
        assert probe_response.status_code == 200
        assert probe_response.headers[health.DESKTOP_TOKEN_HEADER] == "desktop-secret"


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
                message=None,
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
            "message": None,
        }
        assert client.app.state.job_store is None
        assert client.app.state.job_store_work_dir is None
        assert reset_calls == [True]


def test_runtime_mode_reports_shell_metadata(monkeypatch: pytest.MonkeyPatch):
    client = create_test_client()
    monkeypatch.setenv("NIAMOTO_RUNTIME_MODE", "desktop")
    monkeypatch.setenv("NIAMOTO_DESKTOP_SHELL", "tauri")
    monkeypatch.setenv("NIAMOTO_HOME", "/tmp/demo-project")

    response = client.get("/api/health/runtime-mode")

    assert response.status_code == 200
    assert response.json() == {
        "mode": "desktop",
        "shell": "tauri",
        "project": "/tmp/demo-project",
        "features": {
            "project_switching": True,
        },
    }


def test_debug_test_500_endpoint_returns_intentional_server_error():
    client = create_test_client()

    response = client.get("/api/health/debug/test-500")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Intentional test 500 for bug report CTA validation."
    }


def test_invalid_project_state_clears_job_store(monkeypatch: pytest.MonkeyPatch):
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
