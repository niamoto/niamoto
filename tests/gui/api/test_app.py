"""Tests for GUI API app creation."""

from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
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
        assert app.docs_url == "/api/docs"
        assert app.redoc_url == "/api/redoc"

    def test_cors_middleware_configured(self):
        """Test CORS middleware is added."""
        app = create_app()

        # Check that CORS middleware is in the middleware stack
        # CORSMiddleware should be wrapped in a callable
        assert len(app.user_middleware) > 0

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

    @patch("niamoto.gui.api.app.get_working_directory")
    def test_preview_mount_when_exports_exist(self, mock_get_work_dir, tmp_path):
        """Test /preview mount when exports/web exists."""
        # Create exports/web directory
        exports_web = tmp_path / "exports" / "web"
        exports_web.mkdir(parents=True)
        (exports_web / "index.html").write_text("<html>Preview</html>")

        mock_get_work_dir.return_value = tmp_path

        app = create_app()

        # Check that /preview route exists
        route_paths = [route.path for route in app.routes]
        assert any("/preview" in path for path in route_paths)

    @patch("niamoto.gui.api.app.get_working_directory")
    def test_no_preview_mount_when_exports_missing(self, mock_get_work_dir, tmp_path):
        """Test /preview mount is not added when exports/web doesn't exist."""
        mock_get_work_dir.return_value = tmp_path

        app = create_app()

        # /preview should not be mounted
        route_paths = [route.path for route in app.routes]
        preview_routes = [path for path in route_paths if path.startswith("/preview")]
        assert len(preview_routes) == 0

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

        # Should not have /assets route
        assets_routes = [path for path in route_paths if "/assets" in path]
        assert len(assets_routes) == 0


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
            "niamoto.gui.api.app.get_working_directory", lambda: tmp_path
        )

        app = create_app()
        client = TestClient(app)

        # Request a non-existent path (should return index.html)
        response = client.get("/some/unknown/path")

        # Should get index.html content
        assert response.status_code == 200
        assert "Niamoto" in response.text


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
