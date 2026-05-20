import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router


def _write_import_config(work_dir, references=None):
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump({"entities": {"references": references or {}}}),
        encoding="utf-8",
    )


def _write_transform_config(work_dir, groups):
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(groups, sort_keys=False),
        encoding="utf-8",
    )


def _write_export_config(work_dir, groups):
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {"exports": [{"name": "web", "groups": groups}]},
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_update_transform_widget_updates_existing_group(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_import_config(work_dir)
    _write_transform_config(
        work_dir,
        [{"group_by": "taxons", "widgets_data": {"old": {"plugin": "summary"}}}],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).put(
        "/api/config/transform/taxons/widgets/richness",
        json={"plugin": "field_aggregator", "params": {"field": "count"}},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": "richness",
        "plugin": "field_aggregator",
        "params": {"field": "count"},
    }
    transform_config = yaml.safe_load(
        (work_dir / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    assert transform_config[0]["widgets_data"]["richness"] == {
        "plugin": "field_aggregator",
        "params": {"field": "count"},
    }


def test_update_transform_widget_creates_known_reference_group(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_import_config(work_dir, references={"plots": {"kind": "generic"}})
    _write_transform_config(work_dir, [])
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).put(
        "/api/config/transform/plots/widgets/plot_info",
        json={"plugin": "field_aggregator", "params": {"field": "name"}},
    )

    assert response.status_code == 200, response.text
    transform_config = yaml.safe_load(
        (work_dir / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    assert transform_config == [
        {
            "group_by": "plots",
            "sources": [],
            "widgets_data": {
                "plot_info": {
                    "plugin": "field_aggregator",
                    "params": {"field": "name"},
                }
            },
        }
    ]


def test_update_transform_widget_rejects_unknown_group(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_import_config(work_dir, references={"plots": {"kind": "generic"}})
    _write_transform_config(work_dir, [])
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).put(
        "/api/config/transform/taxons/widgets/richness",
        json={"plugin": "field_aggregator", "params": {}},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Group 'taxons' not found and is not a known reference in import.yml"
    )


def test_update_transform_widget_rejects_invalid_transform_config(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    _write_import_config(work_dir, references={"plots": {"kind": "generic"}})
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "transform.yml").write_text("not-a-list: true\n", encoding="utf-8")
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).put(
        "/api/config/transform/plots/widgets/richness",
        json={"plugin": "field_aggregator", "params": {}},
    )

    assert response.status_code == 400
    assert "Invalid transform configuration" in response.json()["detail"]


def test_delete_transform_widget_removes_widget(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_transform_config(
        work_dir,
        [{"group_by": "taxons", "widgets_data": {"richness": {"plugin": "summary"}}}],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/transform/taxons/widgets/richness"
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"success": True}
    transform_config = yaml.safe_load(
        (work_dir / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    assert transform_config[0]["widgets_data"] == {}


def test_delete_transform_widget_rejects_non_object_widgets(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_transform_config(work_dir, [{"group_by": "taxons", "widgets_data": []}])
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/transform/taxons/widgets/richness"
    )

    assert response.status_code == 400
    assert "Invalid transform configuration" in response.json()["detail"]
    assert "widgets_data" in response.json()["detail"]


def test_get_transform_widget_returns_not_found_for_null_widgets(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_transform_config(work_dir, [{"group_by": "taxons", "widgets_data": None}])
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).get(
        "/api/config/transform/taxons/widgets/richness"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Widget 'richness' not found in group 'taxons'"


def test_get_transform_widget_normalizes_stubbed_null_widgets(monkeypatch):
    monkeypatch.setattr(
        config_router,
        "_load_transform_config",
        lambda: [{"group_by": "plots", "widgets_data": None}],
    )

    response = TestClient(create_app()).get("/api/config/transform/plots/widgets/foo")

    assert response.status_code == 404
    assert response.json()["detail"] == "Widget 'foo' not found in group 'plots'"


def test_get_transform_widget_rejects_non_object_widgets(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_transform_config(work_dir, [{"group_by": "taxons", "widgets_data": []}])
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).get(
        "/api/config/transform/taxons/widgets/richness"
    )

    assert response.status_code == 400
    assert "widgets_data" in response.json()["detail"]
    assert "valid dictionary" in response.json()["detail"]


def test_delete_transform_widget_returns_not_found_for_missing_group(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    _write_transform_config(work_dir, [{"group_by": "plots", "widgets_data": {}}])
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/transform/taxons/widgets/richness"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Group 'taxons' not found"


def test_delete_transform_widget_returns_not_found_for_missing_widget(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    _write_transform_config(
        work_dir,
        [{"group_by": "taxons", "widgets_data": {"height": {"plugin": "summary"}}}],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/transform/taxons/widgets/richness"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Widget 'richness' not found in group 'taxons'"


def test_delete_export_widget_removes_data_source(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    _write_export_config(
        work_dir,
        [
            {
                "group_by": "taxons",
                "widgets": [
                    {"plugin": "info_grid", "data_source": "richness"},
                    {"plugin": "bar_plot", "data_source": "height"},
                ],
            }
        ],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/export/taxons/widgets/richness"
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"success": True}
    export_config = yaml.safe_load(
        (work_dir / "config" / "export.yml").read_text(encoding="utf-8")
    )
    assert [
        w["data_source"] for w in export_config["exports"][0]["groups"][0]["widgets"]
    ] == ["height"]


def test_delete_export_widget_removes_synthetic_hierarchical_nav_widget(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    _write_export_config(
        work_dir,
        [
            {
                "group_by": "taxons",
                "widgets": [
                    {"plugin": "hierarchical_nav_widget", "params": {}},
                    {"plugin": "info_grid", "data_source": "richness"},
                ],
            }
        ],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/export/taxons/widgets/taxons_hierarchical_nav_widget"
    )

    assert response.status_code == 200, response.text
    export_config = yaml.safe_load(
        (work_dir / "config" / "export.yml").read_text(encoding="utf-8")
    )
    widgets = export_config["exports"][0]["groups"][0]["widgets"]
    assert widgets == [{"plugin": "info_grid", "data_source": "richness"}]


def test_delete_export_widget_searches_params_groups_when_root_groups_exist(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web",
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [
                                    {
                                        "plugin": "info_grid",
                                        "data_source": "taxon_summary",
                                    }
                                ],
                            }
                        ],
                        "params": {
                            "groups": [
                                {
                                    "group_by": "plots",
                                    "widgets": [
                                        {
                                            "plugin": "interactive_map",
                                            "data_source": "plot_map",
                                        },
                                        {
                                            "plugin": "info_grid",
                                            "data_source": "plot_summary",
                                        },
                                    ],
                                }
                            ]
                        },
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/export/plots/widgets/plot_map"
    )

    assert response.status_code == 200, response.text
    export_config = yaml.safe_load(
        (work_dir / "config" / "export.yml").read_text(encoding="utf-8")
    )
    root_widgets = export_config["exports"][0]["groups"][0]["widgets"]
    params_widgets = export_config["exports"][0]["params"]["groups"][0]["widgets"]
    assert [widget["data_source"] for widget in root_widgets] == ["taxon_summary"]
    assert [widget["data_source"] for widget in params_widgets] == ["plot_summary"]


def test_delete_export_widget_returns_not_found_for_missing_group(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    _write_export_config(
        work_dir,
        [{"group_by": "plots", "widgets": [{"plugin": "info_grid"}]}],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/export/taxons/widgets/richness"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Group 'taxons' not found in export config"


def test_delete_export_widget_returns_not_found_for_missing_widget(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    _write_export_config(
        work_dir,
        [
            {
                "group_by": "taxons",
                "widgets": [{"plugin": "info_grid", "data_source": "height"}],
            }
        ],
    )
    monkeypatch.setattr(config_router, "get_working_directory", lambda: work_dir)

    response = TestClient(create_app()).delete(
        "/api/config/export/taxons/widgets/richness"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Widget 'richness' not found in group 'taxons'"
