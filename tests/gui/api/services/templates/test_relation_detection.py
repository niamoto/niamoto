from pathlib import Path

import duckdb

from niamoto.gui.api.services.templates.relation_detection import (
    find_best_stats_source_for_reference,
)


def test_find_best_stats_source_for_reference_matches_arbitrary_names(tmp_path: Path):
    work_dir = tmp_path
    db_dir = work_dir / "db"
    imports_dir = work_dir / "imports"
    db_dir.mkdir()
    imports_dir.mkdir()

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE entity_sampling_units (
            id INTEGER,
            id_sampling_unit VARCHAR,
            name VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO entity_sampling_units VALUES
        (1, 'SU-01', 'Alpha'),
        (2, 'SU-02', 'Beta')
        """
    )
    conn.close()

    (imports_dir / "raw_monitoring_metrics_stats.csv").write_text(
        "\n".join(
            [
                "metric_id;sampling_unit_code;class_object;class_name;class_value",
                "1;SU-01;cover;forest;12",
                "2;SU-02;cover;forest;15",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    best = find_best_stats_source_for_reference(work_dir, "sampling_units")

    assert best is not None
    assert best["name"] == "monitoring_metrics_stats"
    assert best["data"] == "imports/raw_monitoring_metrics_stats.csv"
    assert best["grouping"] == "sampling_units"
    assert best["relation_plugin"] == "stats_loader"
    assert best["key"] == "id"
    assert best["ref_field"] == "id_sampling_unit"
    assert best["match_field"] == "sampling_unit_code"
