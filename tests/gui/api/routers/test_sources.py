import asyncio
from copy import deepcopy
from pathlib import Path
import threading
import time

import duckdb
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
from niamoto.gui.api.routers import config as config_router
from niamoto.gui.api.routers import sources as sources_router


def test_upload_rejects_files_over_size_limit(
    monkeypatch,
    gui_duckdb_client: TestClient,
    gui_duckdb_context: Path,
):
    monkeypatch.setattr(sources_router, "MAX_UPLOAD_SIZE_BYTES", 10)
    monkeypatch.setattr(sources_router, "UPLOAD_CHUNK_SIZE_BYTES", 4)

    response = gui_duckdb_client.post(
        "/api/sources/taxons/upload",
        params={"source_name": "large_stats"},
        files={
            "file": ("large.csv", b"class_object,class_name,class_value\n", "text/csv")
        },
    )

    assert response.status_code == 413
    assert not (gui_duckdb_context / "imports" / "raw_large_stats.csv").exists()


def test_upload_rejects_existing_source_file(
    gui_duckdb_client: TestClient,
    gui_duckdb_context: Path,
):
    imports_dir = gui_duckdb_context / "imports"
    imports_dir.mkdir(exist_ok=True)
    existing_file = imports_dir / "raw_existing_stats.csv"
    existing_file.write_text("existing\n", encoding="utf-8")

    response = gui_duckdb_client.post(
        "/api/sources/taxons/upload",
        params={"source_name": "existing_stats"},
        files={
            "file": (
                "replacement.csv",
                b"class_object,class_name,class_value\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 409
    assert existing_file.read_text(encoding="utf-8") == "existing\n"


def test_save_source_uses_selected_entity_column_and_reference_key(
    gui_duckdb_context: Path,
):
    work_dir = gui_duckdb_context

    import_path = work_dir / "config" / "import.yml"
    with open(import_path, "r", encoding="utf-8") as f:
        import_config = yaml.safe_load(f) or {}

    import_config["entities"]["references"]["taxons"]["relation"] = {
        "dataset": "occurrences",
        "foreign_key": "taxon_id",
        "reference_key": "taxons_id",
    }

    with open(import_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(import_config, f, sort_keys=False)

    db_path = work_dir / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("ALTER TABLE entity_taxons ADD COLUMN taxons_id INTEGER")
        conn.execute("UPDATE entity_taxons SET taxons_id = id")
    finally:
        conn.close()

    imports_dir = work_dir / "imports"
    imports_dir.mkdir(exist_ok=True)
    (imports_dir / "raw_taxa_stats.csv").write_text(
        "\n".join(
            [
                "entity_id;taxon_id;class_object;class_name;class_value",
                "101;101;nbe_source_dataset;network;12",
                "202;202;nbe_source_dataset;network;5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/sources/taxons/save",
        json={
            "source_name": "taxa_stats",
            "file_path": "imports/raw_taxa_stats.csv",
            "entity_id_column": "taxon_id",
        },
    )

    assert response.status_code == 200

    transform_path = work_dir / "config" / "transform.yml"
    with open(transform_path, "r", encoding="utf-8") as f:
        transform_config = yaml.safe_load(f) or []

    taxons_group = next(
        group for group in transform_config if group.get("group_by") == "taxons"
    )
    source = next(
        configured
        for configured in taxons_group.get("sources", [])
        if configured.get("name") == "taxa_stats"
    )
    assert source["relation"]["ref_field"] == "taxons_id"
    assert source["relation"]["match_field"] == "taxon_id"


def test_save_source_rejects_paths_outside_imports(
    gui_duckdb_client: TestClient,
    gui_duckdb_context: Path,
):
    work_dir = gui_duckdb_context
    outside_csv = work_dir.parent / "outside.csv"
    outside_csv.write_text(
        "taxon_id;class_object;class_name;class_value\n"
        "101;nbe_source_dataset;network;12\n",
        encoding="utf-8",
    )
    transform_path = work_dir / "config" / "transform.yml"
    before = (
        transform_path.read_text(encoding="utf-8") if transform_path.exists() else None
    )

    response = gui_duckdb_client.post(
        "/api/sources/taxons/save",
        json={
            "source_name": "escaped_stats",
            "file_path": str(outside_csv),
            "entity_id_column": "taxon_id",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Source path must stay inside the imports directory"
    )
    after = (
        transform_path.read_text(encoding="utf-8") if transform_path.exists() else None
    )
    assert after == before


def test_save_source_persists_canonical_imports_relative_path(
    gui_duckdb_client: TestClient,
    gui_duckdb_context: Path,
):
    work_dir = gui_duckdb_context
    imports_dir = work_dir / "imports"
    imports_dir.mkdir(exist_ok=True)
    source_path = imports_dir / "raw_taxa_stats.csv"
    source_path.write_text(
        "\n".join(
            [
                "taxon_id;class_object;class_name;class_value",
                "101;nbe_source_dataset;network;12",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    response = gui_duckdb_client.post(
        "/api/sources/taxons/save",
        json={
            "source_name": "taxa_stats_absolute",
            "file_path": str(source_path),
            "entity_id_column": "taxon_id",
        },
    )

    assert response.status_code == 200, response.text
    transform_config = yaml.safe_load(
        (work_dir / "config" / "transform.yml").read_text(encoding="utf-8")
    )
    taxons_group = next(
        group for group in transform_config if group.get("group_by") == "taxons"
    )
    source = next(
        configured
        for configured in taxons_group.get("sources", [])
        if configured.get("name") == "taxa_stats_absolute"
    )
    assert source["data"] == "imports/raw_taxa_stats.csv"


def test_source_save_shares_transform_write_lock_with_widget_updates(
    monkeypatch, tmp_path
):
    work_dir = tmp_path / "project"
    imports_dir = work_dir / "imports"
    imports_dir.mkdir(parents=True)
    source_csv = imports_dir / "raw_taxa_stats.csv"
    source_csv.write_text(
        "taxon_id;class_object;class_name;class_value\n"
        "101;nbe_source_dataset;network;12\n",
        encoding="utf-8",
    )

    current_groups = [{"group_by": "taxons", "sources": [], "widgets_data": {}}]
    config_lock = threading.Lock()
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    def load_groups():
        with config_lock:
            return deepcopy(current_groups)

    def save_groups(groups):
        nonlocal current_groups
        if groups[0].get("sources") and not groups[0].get("widgets_data"):
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        with config_lock:
            current_groups = deepcopy(groups)

    def load_sources_config(_work_dir):
        groups = {
            group["group_by"]: {
                key: value for key, value in group.items() if key != "group_by"
            }
            for group in load_groups()
        }
        return {"groups": groups}

    def save_sources_config(_work_dir, config):
        groups = []
        for group_name, group_config in config["groups"].items():
            group = {"group_by": group_name}
            group.update(group_config)
            groups.append(group)
        save_groups(groups)

    monkeypatch.setattr(sources_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(config_router, "_is_known_reference", lambda _group_by: True)
    monkeypatch.setattr(config_router, "_load_transform_config", load_groups)
    monkeypatch.setattr(config_router, "_save_transform_config", save_groups)
    monkeypatch.setattr(sources_router, "_load_transform_config", load_sources_config)
    monkeypatch.setattr(sources_router, "_save_transform_config", save_sources_config)
    monkeypatch.setattr(
        sources_router,
        "detect_relation_fields",
        lambda *_args, **_kwargs: ("id", "taxon_id", 1.0),
    )

    def save_source():
        try:
            asyncio.run(
                sources_router.save_source_config(
                    "taxons",
                    sources_router.SaveSourceRequest(
                        source_name="taxa_stats",
                        file_path="imports/raw_taxa_stats.csv",
                        entity_id_column="taxon_id",
                    ),
                )
            )
        except BaseException as exc:
            errors.append(exc)

    def update_widget():
        try:
            asyncio.run(
                config_router.update_transform_widget(
                    "taxons",
                    "summary_widget",
                    config_router.TransformWidgetUpdate(
                        plugin="field_aggregator",
                        params={"field": "class_value"},
                    ),
                )
            )
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=save_source)
    second = threading.Thread(target=update_widget)

    first.start()
    assert first_save_entered.wait(timeout=2)
    second.start()
    time.sleep(0.05)
    release_first_save.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert current_groups[0]["sources"][0]["name"] == "taxa_stats"
    assert "summary_widget" in current_groups[0]["widgets_data"]


def test_save_source_config_serializes_concurrent_source_writes(monkeypatch, tmp_path):
    work_dir = tmp_path / "project"
    imports_dir = work_dir / "imports"
    imports_dir.mkdir(parents=True)
    for source_name in ("first_stats", "second_stats"):
        (imports_dir / f"raw_{source_name}.csv").write_text(
            "taxon_id;class_object;class_name;class_value\n"
            "101;nbe_source_dataset;network;12\n",
            encoding="utf-8",
        )

    current_config = {"groups": {"taxons": {"sources": [], "widgets_data": {}}}}
    config_lock = threading.Lock()
    first_save_entered = threading.Event()
    release_first_save = threading.Event()
    errors: list[BaseException] = []

    def load_transform_config(_work_dir):
        with config_lock:
            return deepcopy(current_config)

    def save_transform_config(_work_dir, config):
        nonlocal current_config
        sources = config["groups"]["taxons"]["sources"]
        if len(sources) == 1 and sources[0].get("name") == "first_stats":
            first_save_entered.set()
            release_first_save.wait(timeout=2)
        with config_lock:
            current_config = deepcopy(config)

    monkeypatch.setattr(sources_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(sources_router, "_load_transform_config", load_transform_config)
    monkeypatch.setattr(sources_router, "_save_transform_config", save_transform_config)
    monkeypatch.setattr(
        sources_router,
        "detect_relation_fields",
        lambda *_args, **_kwargs: ("id", "taxon_id", 1.0),
    )

    def save_source(source_name: str):
        try:
            asyncio.run(
                sources_router.save_source_config(
                    "taxons",
                    sources_router.SaveSourceRequest(
                        source_name=source_name,
                        file_path=f"imports/raw_{source_name}.csv",
                        entity_id_column="taxon_id",
                    ),
                )
            )
        except BaseException as exc:
            errors.append(exc)

    first = threading.Thread(target=save_source, args=("first_stats",))
    second = threading.Thread(target=save_source, args=("second_stats",))

    first.start()
    assert first_save_entered.wait(timeout=2)
    second.start()
    time.sleep(0.05)
    release_first_save.set()
    first.join(timeout=2)
    second.join(timeout=2)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert {
        source["name"] for source in current_config["groups"]["taxons"]["sources"]
    } == {"first_stats", "second_stats"}


def test_analyze_existing_source_rejects_paths_outside_imports(
    monkeypatch,
    gui_duckdb_client: TestClient,
    gui_duckdb_context: Path,
):
    work_dir = gui_duckdb_context
    transform_path = work_dir / "config" / "transform.yml"
    transform_path.write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "sources": [
                        {
                            "name": "escaped_stats",
                            "data": "../secret.csv",
                            "grouping": "taxons",
                            "relation": {
                                "plugin": "stats_loader",
                                "key": "id",
                                "ref_field": "id",
                                "match_field": "id",
                            },
                        }
                    ],
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (work_dir.parent / "secret.csv").write_text("id,value\n1,2\n", encoding="utf-8")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("ClassObjectAnalyzer should not read escaped paths")

    monkeypatch.setattr(sources_router, "ClassObjectAnalyzer", fail_if_called)

    response = gui_duckdb_client.get(
        "/api/sources/taxons/analyze/escaped_stats",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Source path must stay inside the imports directory"
    )
