"""
Tests for layout API endpoints.

Vérifie que layout.preview_widget délègue correctement au moteur
de preview unifié (PreviewEngine).
"""

import inspect
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest
import yaml
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


def test_hierarchical_representatives_uses_configured_source_levels(tmp_path: Path):
    work_dir = tmp_path / "plots-hierarchy-project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {
                                "type": "file",
                                "format": "csv",
                                "path": "imports/occurrences.csv",
                            }
                        },
                        "plots": {
                            "connector": {
                                "type": "file",
                                "format": "csv",
                                "path": "imports/plots.csv",
                            }
                        },
                    },
                    "references": {
                        "plots_hierarchy": {
                            "kind": "hierarchical",
                            "connector": {
                                "type": "derived",
                                "source": "plots",
                                "extraction": {
                                    "levels": [
                                        {"name": "country", "column": "country"},
                                        {"name": "locality", "column": "locality"},
                                        {"name": "plot", "column": "plot_name"},
                                    ],
                                    "id_column": "id_liste_plots",
                                    "name_column": "plot_name",
                                },
                            },
                            "relation": {
                                "dataset": "occurrences",
                                "foreign_key": "id_table_liste_plots_n",
                                "reference_key": "plots_hierarchy_id",
                            },
                            "hierarchy": {
                                "levels": ["country", "locality", "plot"],
                            },
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE dataset_occurrences (
                id INTEGER,
                id_table_liste_plots_n INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO dataset_occurrences VALUES
                (1, 10),
                (2, 10),
                (3, 20)
            """
        )
        conn.execute(
            """
            CREATE TABLE dataset_plots (
                id_liste_plots INTEGER,
                country VARCHAR,
                locality VARCHAR,
                plot_name VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO dataset_plots VALUES
                (10, 'NC', 'Aoupinié', 'Plot A'),
                (20, 'NC', 'Tiwaka', 'Plot B'),
                (30, 'AU', 'Sydney', 'Plot C')
            """
        )
        conn.execute(
            """
            CREATE TABLE entity_plots_hierarchy (
                id VARCHAR,
                rank_name VARCHAR,
                rank_value VARCHAR,
                full_name VARCHAR,
                full_path VARCHAR,
                parent_id VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_plots_hierarchy VALUES
                ('country-nc', 'country', 'NC', 'NC', 'NC', NULL),
                ('country-au', 'country', 'AU', 'AU', 'AU', NULL),
                ('locality-aoupinie', 'locality', 'Aoupinié', 'Aoupinié', 'NC|Aoupinié', 'country-nc'),
                ('locality-tiwaka', 'locality', 'Tiwaka', 'Tiwaka', 'NC|Tiwaka', 'country-nc'),
                ('plot-a', 'plot', 'Plot A', 'Plot A', 'NC|Aoupinié|Plot A', 'locality-aoupinie'),
                ('plot-b', 'plot', 'Plot B', 'Plot B', 'NC|Tiwaka|Plot B', 'locality-tiwaka'),
                ('plot-c', 'plot', 'Plot C', 'Plot C', 'AU|Sydney|Plot C', NULL)
            """
        )
    finally:
        conn.close()

    with patch.object(context, "_working_directory", work_dir):
        client = TestClient(create_app())
        response = client.get("/api/layout/plots_hierarchy/representatives")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["group_by"] == "plots_hierarchy"
    assert payload["total"] > 0
    assert payload["entities"][0]["name"].startswith("[")
    assert any(entity["name"].startswith("[Country]") for entity in payload["entities"])
    assert any(entity["name"].startswith("[Plot]") for entity in payload["entities"])
