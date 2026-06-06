"""Tests for GUI API app creation."""

from pathlib import Path
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app, UI_BUILD_DIR


class TestCreateApp:
    """Test create_app function."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_metadata(self):
        """Test app has correct metadata."""
        app = create_app()
        assert app.title == "Niamoto GUI API"
        assert "Niamoto visual configuration" in app.description
        assert app.version == "1.0.0"

    def test_app_docs_urls(self):
        """Test API documentation URLs."""
        app = create_app()
        assert app.openapi_url == "/api/openapi.json"
        assert app.docs_url == "/api/docs"
        assert app.redoc_url == "/api/redoc"

    def test_docs_ui_points_to_api_scoped_openapi_url(self):
        """Swagger UI should load the API-scoped OpenAPI schema."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/api/docs")

        assert response.status_code == 200
        assert "url: '/api/openapi.json'" in response.text

    def test_openapi_schema_is_available_on_api_and_legacy_urls(self):
        """Keep the schema available on both URLs while the UI migrates."""
        app = create_app()
        client = TestClient(app)

        api_scoped = client.get("/api/openapi.json")
        legacy = client.get("/openapi.json")

        assert api_scoped.status_code == 200
        assert api_scoped.json()["openapi"] == "3.1.0"
        assert legacy.status_code == 200
        assert legacy.json()["openapi"] == "3.1.0"

    def test_cors_middleware_configured(self):
        """Test CORS middleware is added."""
        app = create_app()

        # Check that CORS middleware is in the middleware stack
        # CORSMiddleware should be wrapped in a callable
        assert len(app.user_middleware) > 0

    def test_cors_rejects_null_origin(self):
        """Sandboxed previews with origin null must not read GUI APIs via CORS."""
        app = create_app()
        client = TestClient(app)

        response = client.options(
            "/api/health",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_configured_cors_origins_ignore_wildcards_and_untrusted_hosts(
        self, monkeypatch
    ):
        """Configured CORS origins should stay limited to local desktop contexts."""
        monkeypatch.setenv(
            "NIAMOTO_CORS_ORIGINS",
            "*,https://evil.example,http://localhost:5173,tauri://localhost",
        )
        app = create_app()
        client = TestClient(app)

        rejected = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        allowed = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert rejected.status_code == 400
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_desktop_token_protects_api_mutations_globally(self, monkeypatch, tmp_path):
        """Mutating API routes should require the desktop token when it is set."""
        monkeypatch.setenv("NIAMOTO_DESKTOP_AUTH_TOKEN", "desktop-secret")
        monkeypatch.setattr(
            "niamoto.gui.api.services.job_store_runtime.get_working_directory",
            lambda: tmp_path,
        )
        app = create_app()
        client = TestClient(app)

        unauthorized = client.post("/api/transform/execute", json={})
        authorized = client.post(
            "/api/transform/execute",
            headers={"x-niamoto-desktop-token": "desktop-secret"},
            json={},
        )

        assert unauthorized.status_code == 401
        assert authorized.status_code != 401

    def test_api_routers_included(self):
        """Test that all API routers are included."""
        app = create_app()

        # Get all route paths
        route_paths = [route.path for route in app.routes]

        # Check that API prefixes are present
        api_prefixes = [
            "/api/config",
            "/api/database",
            "/api/files",
            "/api/imports",
            "/api/plugins",
            "/api/transform",
            "/api/export",
            "/api/data",
            "/api/entities",
            "/api/deploy",
            "/api/smart",
            "/api",  # bootstrap router
        ]

        # At least some routes from each router should be present
        for prefix in api_prefixes:
            matching_routes = [path for path in route_paths if path.startswith(prefix)]
            assert len(matching_routes) > 0, f"No routes found for prefix {prefix}"

    def test_feedback_proxy_route_is_not_registered(self):
        """The GUI no longer exposes the legacy remote feedback proxy."""
        app = create_app()

        route_paths = [route.path for route in app.routes]

        assert "/api/feedback/submit" not in route_paths

    def test_preview_export_route_is_available(self):
        """Test dynamic exported preview route is included."""
        app = create_app()

        route_paths = [route.path for route in app.routes]
        assert "/api/site/preview-exported" in route_paths
        assert "/api/site/preview-exported/{requested_path:path}" in route_paths

    def test_static_files_mount_when_ui_build_exists(self, tmp_path, monkeypatch):
        """Test static files are mounted when UI build exists."""
        # Create REAL UI build directory structure
        ui_build = tmp_path / "ui" / "dist"
        ui_build.mkdir(parents=True)

        # Create assets directory with a file
        assets_dir = ui_build / "assets"
        assets_dir.mkdir()
        (assets_dir / "app.js").write_text("// app code")
        (ui_build / "index.html").write_text("<html>App</html>")

        # Point UI_BUILD_DIR to real temp directory
        monkeypatch.setattr("niamoto.gui.api.app.UI_BUILD_DIR", ui_build)

        app = create_app()

        # Check app has routes (at least API routes + static)
        assert len(app.routes) > 10
        assert app.title == "Niamoto GUI API"

        # Verify static files can actually be served
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/assets/app.js")
        assert response.status_code == 200
        assert "// app code" in response.text

    def test_no_static_mount_when_ui_build_missing(self, tmp_path, monkeypatch):
        """Test static files are not mounted when UI build doesn't exist."""
        # Point to a non-existent directory
        non_existent = tmp_path / "nonexistent" / "ui" / "dist"
        monkeypatch.setattr("niamoto.gui.api.app.UI_BUILD_DIR", non_existent)

        app = create_app()

        route_paths = [route.path for route in app.routes]

        # Should not have /assets route mounted at root level
        # Use startswith to avoid matching API routes that might contain 'assets'
        assets_routes = [path for path in route_paths if path.startswith("/assets")]
        assert len(assets_routes) == 0

    def test_partial_ui_build_without_assets_does_not_crash(
        self, tmp_path, monkeypatch
    ):
        """A dist directory with only index.html should still mount the SPA."""
        ui_build = tmp_path / "ui" / "dist"
        ui_build.mkdir(parents=True)
        (ui_build / "index.html").write_text("<html>App</html>", encoding="utf-8")
        monkeypatch.setattr("niamoto.gui.api.app.UI_BUILD_DIR", ui_build)

        app = create_app()
        client = TestClient(app)

        route_paths = [route.path for route in app.routes]
        assets_routes = [path for path in route_paths if path.startswith("/assets")]
        assert assets_routes == []
        assert client.get("/").status_code == 200

    def test_create_app_without_explicit_project_keeps_job_store_disabled(
        self, monkeypatch
    ):
        """Desktop welcome mode should not initialize a project-scoped job store."""
        monkeypatch.setattr(
            "niamoto.gui.api.app.get_valid_optional_working_directory", lambda: None
        )

        app = create_app()

        assert app.state.job_store is None
        assert app.state.job_store_work_dir is None


class TestSPAStaticFiles:
    """Test SPAStaticFiles custom handler."""

    def test_spa_serves_index_for_unknown_routes(self, tmp_path, monkeypatch):
        """Test that SPA handler serves index.html for unknown routes."""
        # Create REAL UI build structure
        ui_build = tmp_path / "ui" / "dist"
        ui_build.mkdir(parents=True)
        (ui_build / "index.html").write_text("<html><body>Niamoto</body></html>")
        assets_dir = ui_build / "assets"
        assets_dir.mkdir()

        # Use monkeypatch instead of nested patches
        monkeypatch.setattr("niamoto.gui.api.app.UI_BUILD_DIR", ui_build)
        monkeypatch.setattr(
            "niamoto.gui.api.app.get_valid_optional_working_directory",
            lambda: tmp_path,
        )
        monkeypatch.setattr(
            "niamoto.gui.api.services.job_store_runtime.get_working_directory",
            lambda: tmp_path,
        )

        app = create_app()
        client = TestClient(app)

        # Request a non-existent path (should return index.html)
        response = client.get("/some/unknown/path")

        # Should get index.html content
        assert response.status_code == 200
        assert "Niamoto" in response.text

    def test_spa_does_not_swallow_non_404_static_errors(self, tmp_path, monkeypatch):
        """Only missing SPA routes should fall back to index.html."""
        ui_build = tmp_path / "ui" / "dist"
        ui_build.mkdir(parents=True)
        (ui_build / "index.html").write_text("<html><body>Niamoto</body></html>")
        monkeypatch.setattr("niamoto.gui.api.app.UI_BUILD_DIR", ui_build)

        async def fail_with_forbidden(self, path, scope):
            raise StarletteHTTPException(status_code=403, detail="Forbidden")

        monkeypatch.setattr(
            "starlette.staticfiles.StaticFiles.get_response",
            fail_with_forbidden,
        )

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/forbidden.js")

        assert response.status_code == 403


class TestAppInstance:
    """Test the app instance created at module level."""

    def test_app_instance_exists(self):
        """Test that app instance is created."""
        from niamoto.gui.api.app import app

        assert isinstance(app, FastAPI)

    def test_app_instance_is_configured(self):
        """Test that the app instance is properly configured."""
        from niamoto.gui.api.app import app

        assert app.title == "Niamoto GUI API"
        assert app.docs_url == "/api/docs"


class TestUIBuildDir:
    """Test UI_BUILD_DIR constant."""

    def test_ui_build_dir_path(self):
        """Test UI_BUILD_DIR points to correct location."""
        assert isinstance(UI_BUILD_DIR, Path)
        assert "ui" in str(UI_BUILD_DIR)
        assert "dist" in str(UI_BUILD_DIR)

    def test_ui_build_dir_is_relative_to_app(self):
        """Test UI_BUILD_DIR is relative to app.py location."""
        # UI_BUILD_DIR should be ../ui/dist relative to app.py
        assert UI_BUILD_DIR.name == "dist"
        assert UI_BUILD_DIR.parent.name == "ui"
