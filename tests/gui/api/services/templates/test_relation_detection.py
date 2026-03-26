from pathlib import Path

import duckdb

from niamoto.gui.api.services.templates.relation_detection import (
    find_stats_sources_for_reference,
    find_best_stats_source_for_reference,
    is_high_confidence_auto_attach,
    read_csv_columns,
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


def test_find_best_stats_source_for_reference_without_raw_prefix(tmp_path: Path):
    work_dir = tmp_path
    db_dir = work_dir / "db"
    imports_dir = work_dir / "imports"
    db_dir.mkdir()
    imports_dir.mkdir()

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE entity_plots (
            id INTEGER,
            id_plot VARCHAR,
            plot VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO entity_plots VALUES
        (1, 'P-01', 'Plot A'),
        (2, 'P-02', 'Plot B')
        """
    )
    conn.close()

    (imports_dir / "monitoring_plot_metrics.csv").write_text(
        "\n".join(
            [
                "id;plot_id;class_object;class_name;class_value",
                "1;P-01;dbh;0-10;4",
                "2;P-02;dbh;10-20;7",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    best = find_best_stats_source_for_reference(work_dir, "plots")

    assert best is not None
    assert best["name"] == "monitoring_plot_metrics"
    assert best["data"] == "imports/monitoring_plot_metrics.csv"
    assert best["ref_field"] == "id_plot"
    assert best["match_field"] == "plot_id"


def test_find_stats_sources_for_reference_requires_class_object_shape(tmp_path: Path):
    work_dir = tmp_path
    db_dir = work_dir / "db"
    imports_dir = work_dir / "imports"
    db_dir.mkdir()
    imports_dir.mkdir()

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE entity_plots (
            id INTEGER,
            id_plot VARCHAR,
            plot VARCHAR
        )
        """
    )
    conn.execute(
        """
        INSERT INTO entity_plots VALUES
        (1, 'P-01', 'Plot A'),
        (2, 'P-02', 'Plot B')
        """
    )
    conn.close()

    (imports_dir / "raw_plot_stats.csv").write_text(
        "\n".join(
            [
                "id;plot_id;class_object;class_name;class_value",
                "1;P-01;dbh;0-10;4",
                "2;P-02;dbh;10-20;7",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (imports_dir / "raw_plot_lookup_stats.csv").write_text(
        "\n".join(
            [
                "id;plot_id;value",
                "1;P-01;4",
                "2;P-02;7",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    matches = find_stats_sources_for_reference(work_dir, "plots")

    assert len(matches) == 1
    assert matches[0]["name"] == "plot_stats"


def test_read_csv_columns_normalizes_quoted_headers(tmp_path: Path):
    csv_path = tmp_path / "quoted.csv"
    csv_path.write_text(
        '"id";"class_object";"class_name";"class_value";"plot_id"\n'
        '1;"dbh";"0-10";4;"P-01"\n',
        encoding="utf-8",
    )

    assert read_csv_columns(csv_path) == [
        "id",
        "class_object",
        "class_name",
        "class_value",
        "plot_id",
    ]


def test_high_confidence_auto_attach_rejects_generic_reference_id():
    assert not is_high_confidence_auto_attach("id", "plot_id", 1.0, min_score=0.75)
    assert is_high_confidence_auto_attach("id_plot", "plot_id", 1.0, min_score=0.75)
