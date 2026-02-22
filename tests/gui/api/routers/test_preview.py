"""Tests d'intégration pour le router preview unifié."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.services.preview_engine.models import PreviewRequest, PreviewResult


@pytest.fixture
def mock_engine():
    """Moteur de preview mocké qui retourne un résultat stable."""
    engine = MagicMock()
    engine.render.return_value = PreviewResult(
        html="<!DOCTYPE html><html><body><p>Preview OK</p></body></html>",
        etag="test-etag-123",
        preview_key="test_widget:full",
        warnings=(),
    )
    engine._compute_etag.return_value = "test-etag-123"
    return engine


@pytest.fixture
def client(mock_engine):
    """TestClient avec moteur de preview mocké."""
    with patch(
        "niamoto.gui.api.routers.preview.get_preview_engine",
        return_value=mock_engine,
    ):
        with patch("niamoto.gui.api.context.get_working_directory") as mock_wd:
            mock_wd.return_value = None
            app = create_app()
            yield TestClient(app)


class TestGetPreview:
    """Tests GET /api/preview/{template_id}."""

    def test_basic_preview(self, client, mock_engine):
        response = client.get("/api/preview/elevation_binned_distribution_bar_plot")
        assert response.status_code == 200
        assert "Preview OK" in response.text
        assert response.headers.get("etag") == '"test-etag-123"'
        assert response.headers.get("cache-control") == "no-cache"

        # Vérifier que le moteur a reçu la bonne requête
        mock_engine.render.assert_called_once()
        req = mock_engine.render.call_args[0][0]
        assert isinstance(req, PreviewRequest)
        assert req.template_id == "elevation_binned_distribution_bar_plot"
        assert req.mode == "full"

    def test_preview_with_params(self, client, mock_engine):
        response = client.get(
            "/api/preview/test_widget",
            params={
                "group_by": "taxons",
                "source": "plots",
                "entity_id": "42",
                "mode": "thumbnail",
            },
        )
        assert response.status_code == 200

        req = mock_engine.render.call_args[0][0]
        assert req.group_by == "taxons"
        assert req.source == "plots"
        assert req.entity_id == "42"
        assert req.mode == "thumbnail"

    def test_etag_304(self, client, mock_engine):
        """Si le client envoie If-None-Match avec le bon ETag, retour 304."""
        response = client.get(
            "/api/preview/test_widget",
            headers={"If-None-Match": '"test-etag-123"'},
        )
        assert response.status_code == 304

    def test_etag_mismatch(self, client, mock_engine):
        """Si l'ETag ne matche pas, retour 200 avec le contenu."""
        response = client.get(
            "/api/preview/test_widget",
            headers={"If-None-Match": '"old-etag"'},
        )
        assert response.status_code == 200
        assert "Preview OK" in response.text


class TestPostPreview:
    """Tests POST /api/preview."""

    def test_inline_preview(self, client, mock_engine):
        response = client.post(
            "/api/preview",
            json={
                "group_by": "taxons",
                "inline": {
                    "transformer_plugin": "binned_distribution",
                    "transformer_params": {"field": "elevation"},
                    "widget_plugin": "bar_plot",
                },
            },
        )
        assert response.status_code == 200

        req = mock_engine.render.call_args[0][0]
        assert req.group_by == "taxons"
        assert req.inline is not None
        assert req.inline["transformer_plugin"] == "binned_distribution"

    def test_post_with_template_id(self, client, mock_engine):
        response = client.post(
            "/api/preview",
            json={"template_id": "test_widget", "mode": "thumbnail"},
        )
        assert response.status_code == 200

        req = mock_engine.render.call_args[0][0]
        assert req.template_id == "test_widget"
        assert req.mode == "thumbnail"
        assert req.inline is None


class TestLegacyRoute:
    """Tests GET /api/templates/preview/{template_id} (rétrocompatibilité)."""

    def test_legacy_route_works(self, client, mock_engine):
        """L'ancienne route doit retourner le même résultat."""
        response = client.get("/api/templates/preview/test_widget")
        assert response.status_code == 200
        assert "Preview OK" in response.text
        assert response.headers.get("etag") == '"test-etag-123"'

    def test_legacy_route_with_params(self, client, mock_engine):
        response = client.get(
            "/api/templates/preview/test_widget",
            params={"group_by": "taxons", "entity_id": "42"},
        )
        assert response.status_code == 200

        req = mock_engine.render.call_args[0][0]
        assert req.group_by == "taxons"
        assert req.entity_id == "42"


class TestEngineUnavailable:
    """Tests quand le moteur n'est pas disponible."""

    def test_no_engine_returns_error(self):
        with patch(
            "niamoto.gui.api.routers.preview.get_preview_engine",
            return_value=None,
        ):
            with patch("niamoto.gui.api.context.get_working_directory") as mock_wd:
                mock_wd.return_value = None
                app = create_app()
                client = TestClient(app)
                response = client.get("/api/preview/test_widget")
                assert response.status_code == 500
                assert "non configuré" in response.text
