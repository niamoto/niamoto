"""
Tests for layout API endpoints.

Vérifie que layout.preview_widget délègue correctement au moteur
de preview unifié (PreviewEngine).
"""

import asyncio
import inspect
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import duckdb
import pytest
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api import context
from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import layout as layout_router


INSTANCE_DIR = Path(__file__).parents[4] / "test-instance" / "niamoto-nc"


class FakePreviewEngine:
    """Minimal preview engine that captures layout preview requests."""

    def __init__(self):
        self.requests = []

    def render(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            html="<html><body><main>Layout preview</main></body></html>",
            etag="layout-preview-etag",
        )


def _write_layout_export_config(work_dir: Path, widgets: list[dict]) -> None:
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": widgets,
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_layout_accepts_localized_widget_metadata(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [
                                    {
                                        "plugin": "bar_plot",
                                        "data_source": "richness",
                                        "title": {
                                            "fr": "Richesse spécifique",
                                            "en": "Species richness",
                                        },
                                        "description": {
                                            "fr": "Nombre d'espèces",
                                            "en": "Number of species",
                                        },
                                        "layout": {"order": 0, "colspan": 2},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/layout/taxons")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["widgets"][0]["title"] == {
        "fr": "Richesse spécifique",
        "en": "Species richness",
    }
    assert payload["widgets"][0]["description"] == {
        "fr": "Nombre d'espèces",
        "en": "Number of species",
    }


def test_layout_groups_endpoint_documents_path_parameter(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [{"data_source": "richness"}],
                            },
                            {"group_by": "plots", "widgets": []},
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    response = gui_duckdb_client.get("/api/layout/taxons/groups")

    assert response.status_code == 200, response.text
    assert response.json() == {
        "groups": [
            {"name": "taxons", "widget_count": 1},
            {"name": "plots", "widget_count": 0},
        ],
        "total": 2,
    }

    openapi = gui_duckdb_client.get("/openapi.json").json()
    parameters = openapi["paths"]["/api/layout/{group_by}/groups"]["get"]["parameters"]
    assert {
        "name": "group_by",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "title": "Group By"},
    } in parameters


def test_layout_update_preserves_widget_index_identity(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [
                                    {
                                        "plugin": "bar_plot",
                                        "data_source": "richness",
                                        "title": "Original first",
                                        "layout": {"order": 0, "colspan": 1},
                                    },
                                    {
                                        "plugin": "donut_chart",
                                        "data_source": "status",
                                        "title": "Original second",
                                        "layout": {"order": 1, "colspan": 1},
                                    },
                                ],
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    reorder_response = gui_duckdb_client.put(
        "/api/layout/taxons",
        json={
            "widgets": [
                {"index": 0, "order": 1},
                {"index": 1, "order": 0},
            ]
        },
    )
    assert reorder_response.status_code == 200, reorder_response.text

    stale_update_response = gui_duckdb_client.put(
        "/api/layout/taxons",
        json={"widgets": [{"index": 0, "order": 1, "title": "Updated first"}]},
    )
    assert stale_update_response.status_code == 200, stale_update_response.text

    export_config = yaml.safe_load(export_path.read_text(encoding="utf-8"))
    widgets = export_config["exports"][0]["groups"][0]["widgets"]
    assert [widget["plugin"] for widget in widgets] == ["bar_plot", "donut_chart"]
    assert widgets[0]["title"] == "Updated first"
    assert widgets[1]["title"] == "Original second"
    assert [widget["layout"]["order"] for widget in widgets] == [1, 0]


def test_layout_update_uses_export_write_lock(monkeypatch, tmp_path):
    widgets = [
        {
            "plugin": "bar_plot",
            "data_source": "richness",
            "title": "Original",
            "layout": {"order": 0, "colspan": 1},
        }
    ]
    _write_layout_export_config(tmp_path, widgets)
    writes = []
    response_holder = {}

    monkeypatch.setattr(layout_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(
        layout_router,
        "_write_yaml_atomic",
        lambda path, content: writes.append((path, content)),
    )

    client = TestClient(create_app())
    layout_router.EXPORT_CONFIG_WRITE_LOCK.acquire()

    def update_layout():
        response_holder["response"] = client.put(
            "/api/layout/taxons",
            json={"widgets": [{"index": 0, "order": 1, "title": "Updated"}]},
        )

    thread = threading.Thread(target=update_layout)
    try:
        thread.start()
        time.sleep(0.05)
        assert writes == []
    finally:
        layout_router.EXPORT_CONFIG_WRITE_LOCK.release()

    thread.join(timeout=2)

    assert not thread.is_alive()
    assert response_holder["response"].status_code == 200
    assert len(writes) == 1
    saved_widgets = writes[0][1]["exports"][0]["groups"][0]["widgets"]
    assert saved_widgets[0]["title"] == "Updated"


def test_layout_update_rejects_invalid_widget_indices_without_saving(
    gui_duckdb_client, gui_duckdb_context
):
    export_path = gui_duckdb_context / "config" / "export.yml"
    export_path.write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "exporter": "html_page_exporter",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [
                                    {
                                        "plugin": "bar_plot",
                                        "data_source": "richness",
                                        "title": "Original",
                                        "layout": {"order": 0, "colspan": 1},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    original_export = export_path.read_text(encoding="utf-8")

    response = gui_duckdb_client.put(
        "/api/layout/taxons",
        json={
            "widgets": [
                {"index": 0, "order": 1, "title": "Changed"},
                {"index": 4, "order": 0},
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid widget indices: [4]"
    assert export_path.read_text(encoding="utf-8") == original_export


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

    def test_layout_uses_preview_engine(self, tmp_path):
        """Le endpoint layout preview délègue au moteur de preview unifié."""
        work_dir = tmp_path / "layout-project"
        _write_layout_export_config(
            work_dir,
            [
                {
                    "plugin": "bar_plot",
                    "data_source": "richness",
                    "title": "Richness",
                    "layout": {"order": 0, "colspan": 1},
                }
            ],
        )
        preview_engine = FakePreviewEngine()

        with (
            patch(
                "niamoto.gui.api.routers.layout.get_working_directory",
                return_value=work_dir,
            ),
            patch(
                "niamoto.gui.api.services.preview_engine.engine.get_preview_engine",
                return_value=preview_engine,
            ),
        ):
            response = TestClient(create_app()).get(
                "/api/layout/taxons/preview/0",
                params={"entity_id": "taxon-42"},
            )

        assert response.status_code == 200, response.text
        assert "Layout preview" in response.text
        assert response.headers["etag"] == '"layout-preview-etag"'
        assert len(preview_engine.requests) == 1
        request = preview_engine.requests[0]
        assert request.template_id == "richness"
        assert request.group_by == "taxons"
        assert request.entity_id == "taxon-42"
        assert request.mode == "full"

    def test_layout_handles_navigation_widget(self, tmp_path):
        """Les navigation widgets utilisent le template_id conventionnel."""
        work_dir = tmp_path / "layout-project"
        _write_layout_export_config(
            work_dir,
            [
                {
                    "plugin": "hierarchical_nav_widget",
                    "data_source": "navigation",
                    "title": "Navigation",
                    "params": {"referential_data": "taxons"},
                    "layout": {"order": 0, "colspan": 1},
                }
            ],
        )
        preview_engine = FakePreviewEngine()

        with (
            patch(
                "niamoto.gui.api.routers.layout.get_working_directory",
                return_value=work_dir,
            ),
            patch(
                "niamoto.gui.api.services.preview_engine.engine.get_preview_engine",
                return_value=preview_engine,
            ),
        ):
            response = TestClient(create_app()).get("/api/layout/taxons/preview/0")

        assert response.status_code == 200, response.text
        assert len(preview_engine.requests) == 1
        request = preview_engine.requests[0]
        assert request.template_id == "taxons_hierarchical_nav_widget"
        assert request.group_by == "taxons"
        assert request.entity_id is None
        assert request.mode == "full"

    def test_layout_preview_missing_export_config_returns_html_error(self, tmp_path):
        work_dir = tmp_path / "layout-project"
        (work_dir / "config").mkdir(parents=True)

        with patch(
            "niamoto.gui.api.routers.layout.get_working_directory",
            return_value=work_dir,
        ):
            response = TestClient(create_app()).get("/api/layout/taxons/preview/0")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")
        assert "export.yml not found" in response.text
        assert "detail" not in response.text


@pytest.mark.skipif(
    not INSTANCE_DIR.exists(),
    reason="test-instance/niamoto-nc not available",
)
def test_plots_representatives_falls_back_when_label_column_is_invalid(monkeypatch):
    monkeypatch.setattr(context, "_working_directory", INSTANCE_DIR)
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
    country_nc = next(
        entity for entity in payload["entities"] if entity["id"] == "country-nc"
    )
    assert country_nc["count"] == 3


def test_representatives_route_uses_worker_thread(monkeypatch, tmp_path: Path):
    captured = {}
    db_path = tmp_path / "db.duckdb"
    db_path.write_text("", encoding="utf-8")

    async def fake_run_in_threadpool(func, *args):
        captured["func"] = func
        captured["args"] = args
        return layout_router.RepresentativesResponse(
            group_by=args[2],
            entities=[],
            total=0,
        )

    monkeypatch.setattr(layout_router, "get_working_directory", lambda: tmp_path)
    monkeypatch.setattr(layout_router, "get_database_path", lambda: db_path)
    monkeypatch.setattr(layout_router, "run_in_threadpool", fake_run_in_threadpool)

    response = asyncio.run(layout_router.get_representatives("taxons", limit=7))

    assert response.group_by == "taxons"
    assert response.total == 0
    assert captured == {
        "func": layout_router._get_representatives_sync,
        "args": (tmp_path, db_path, "taxons", 7),
    }
