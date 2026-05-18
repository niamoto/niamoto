from pathlib import Path

import duckdb
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app
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
