from pathlib import Path

import duckdb
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.app import create_app


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
