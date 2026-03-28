"""
Tests for layout API endpoints.

Vérifie que layout.preview_widget délègue correctement au moteur
de preview unifié (PreviewEngine).
"""

import inspect
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from niamoto.gui.api import context
from niamoto.gui.api.app import create_app


INSTANCE_DIR = Path(__file__).parents[4] / "test-instance" / "niamoto-nc"


class TestLayoutPreviewDelegation:
    """Vérifie que layout.preview_widget utilise le moteur de preview unifié."""

    def test_layout_preview_widget_signature(self):
        """Vérifie que preview_widget a les paramètres attendus."""
        from niamoto.gui.api.routers.layout import preview_widget

        sig = inspect.signature(preview_widget)
        params = list(sig.parameters.keys())

        assert "group_by" in params, "Missing group_by parameter"
        assert "widget_index" in params, "Missing widget_index parameter"
        assert "entity_id" in params, "Missing entity_id parameter"

    def test_layout_uses_preview_engine(self):
        """Vérifie que preview_widget utilise get_preview_engine au lieu de templates.py."""
        from niamoto.gui.api.routers import layout

        # La logique sync est extraite dans _preview_widget_sync
        source_code = inspect.getsource(layout._preview_widget_sync)

        # Doit utiliser le moteur de preview unifié
        assert "get_preview_engine" in source_code, (
            "preview_widget doit déléguer au moteur de preview unifié (get_preview_engine)"
        )
        assert "PreviewRequest" in source_code, (
            "preview_widget doit construire un PreviewRequest"
        )

        # Ne doit plus appeler templates.preview_template directement
        assert (
            "from niamoto.gui.api.routers.templates import preview_template"
            not in source_code
        ), "preview_widget ne doit plus importer preview_template de templates.py"

    def test_layout_handles_navigation_widget(self):
        """Vérifie que les navigation widgets sont résolus en template_id convention."""
        from niamoto.gui.api.routers import layout

        # La logique sync est extraite dans _preview_widget_sync
        source_code = inspect.getsource(layout._preview_widget_sync)

        # Le convention pour les navigation widgets est _hierarchical_nav_widget
        assert "hierarchical_nav_widget" in source_code, (
            "preview_widget doit gérer le cas spécial hierarchical_nav_widget"
        )


@pytest.mark.skipif(
    not INSTANCE_DIR.exists(),
    reason="test-instance/niamoto-nc not available",
)
def test_plots_representatives_falls_back_when_label_column_is_invalid():
    context.set_working_directory(INSTANCE_DIR)
    client = TestClient(create_app())

    response = client.get("/api/layout/plots/representatives")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["group_by"] == "plots"
    assert payload["total"] > 0
    assert payload["entities"][0]["id"]
    assert payload["entities"][0]["name"]
