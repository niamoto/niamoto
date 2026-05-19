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
