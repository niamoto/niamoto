import pandas as pd
import pytest
import yaml

from niamoto.gui.api.services.templates.utils import entity_finder


class _DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _query):
        return None


class _DummyEngine:
    def connect(self):
        return _DummyConnection()


class _DummyDatabase:
    def __init__(self, existing_tables=None, engine=None):
        self.engine = engine or object()
        self._existing_tables = set(existing_tables or [])

    def has_table(self, table_name: str) -> bool:
        return table_name in self._existing_tables


def test_detect_geometry_column_prefers_known_candidates():
    assert entity_finder._detect_geometry_column(["id", "label", "wkb_geometry"]) == (
        "wkb_geometry"
    )
    assert entity_finder._detect_geometry_column(["id", "GEO_PT", "name"]) == "GEO_PT"
    assert entity_finder._detect_geometry_column(["id", "label"]) is None


def test_find_representative_entity_uses_relation_key_for_flat_reference(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "GROUP BY plot_id" in query_text:
            return pd.DataFrame([{"plot_id": 17, "cnt": 8}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_representative_entity(
        _DummyDatabase(),
        {
            "reference_name": "plots",
            "source_dataset": "occurrences",
            "levels": [],
            "relation": {"key": "plot_id"},
        },
    )

    assert result == {
        "level": "plots",
        "column": "plot_id",
        "value": 17,
        "count": 8,
        "table_name": "occurrences",
    }


def test_find_representative_entity_reads_relation_key_from_transform_config(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "plots",
                    "sources": [{"relation": {"key": "plots_id"}}],
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(entity_finder, "get_working_directory", lambda: tmp_path)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "GROUP BY plots_id" in query_text:
            return pd.DataFrame([{"plots_id": "P-019", "cnt": 5}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_representative_entity(
        _DummyDatabase(),
        {
            "reference_name": "plots",
            "source_dataset": "occurrences",
            "levels": [],
        },
    )

    assert result == {
        "level": "plots",
        "column": "plots_id",
        "value": "P-019",
        "count": 5,
        "table_name": "occurrences",
    }


def test_find_representative_entity_falls_back_to_reference_table(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: "entity_plots"
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "GROUP BY plot_id" in query_text:
            return pd.DataFrame(columns=["plot_id", "cnt"])
        if "SELECT * FROM entity_plots LIMIT 0" in query_text:
            return pd.DataFrame(columns=["id_plot", "label"])
        if "SELECT * FROM entity_plots LIMIT 1" in query_text:
            return pd.DataFrame([{"id_plot": 10, "label": "Parcelle 10"}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_representative_entity(
        _DummyDatabase(existing_tables={"entity_plots"}),
        {
            "reference_name": "plots",
            "source_dataset": "occurrences",
            "levels": [],
            "relation": {"key": "plot_id"},
            "id_field": "id_plot",
        },
    )

    assert result == {
        "level": "plots",
        "column": "id_plot",
        "value": 10,
        "count": 0,
        "table_name": "entity_plots",
        "entity_name": "Parcelle 10",
    }


def test_find_representative_entity_returns_spatial_geometry(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: "entity_shapes"
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "SELECT * FROM entity_shapes LIMIT 0" in query_text:
            return pd.DataFrame(
                columns=["id_shape", "name", "wkb_geometry", "shape_type"]
            )
        if "COUNT(*) as cnt" in query_text and "FROM entity_shapes" in query_text:
            return pd.DataFrame([{"cnt": 8}])
        if "ORDER BY ST_Area" in query_text:
            return pd.DataFrame(
                [
                    {
                        "id_shape": 7,
                        "name": "Province Sud",
                        "_geom_wkt": "POLYGON ((0 0,1 0,1 1,0 1,0 0))",
                        "shape_type": "province",
                    }
                ]
            )
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_representative_entity(
        _DummyDatabase(
            existing_tables={"entity_shapes"},
            engine=_DummyEngine(),
        ),
        {
            "reference_name": "shapes",
            "source_dataset": "occurrences",
            "levels": [],
            "kind": "spatial",
            "id_field": "id_shape",
        },
    )

    assert result == {
        "level": "shapes",
        "column": "id_shape",
        "value": 7,
        "count": 0,
        "table_name": "entity_shapes",
        "entity_name": "Province Sud",
        "geometry": "POLYGON ((0 0,1 0,1 1,0 1,0 0))",
        "spatial_query": True,
        "kind": "spatial",
        "shape_type": "province",
    }


def test_find_representative_entity_uses_first_hierarchy_level(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "GROUP BY family_name" in query_text:
            return pd.DataFrame([{"family_name": "Myrtaceae", "cnt": 42}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_representative_entity(
        _DummyDatabase(),
        {
            "reference_name": "taxons",
            "source_dataset": "occurrences",
            "levels": ["family", "genus"],
            "level_columns": {"family": "family_name"},
            "kind": "hierarchical",
        },
    )

    assert result == {
        "level": "family",
        "column": "family_name",
        "value": "Myrtaceae",
        "count": 42,
        "table_name": "occurrences",
    }


def test_find_representative_entity_falls_back_to_hierarchy_relation_key(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "GROUP BY family" in query_text:
            raise RuntimeError("first-level lookup failed")
        if "GROUP BY id_taxonref" in query_text:
            return pd.DataFrame([{"id_taxonref": 99, "cnt": 12}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_representative_entity(
        _DummyDatabase(),
        {
            "reference_name": "taxons",
            "source_dataset": "occurrences",
            "levels": ["family"],
            "kind": "hierarchical",
            "relation": {"key": "id_taxonref"},
        },
    )

    assert result == {
        "level": "taxons",
        "column": "id_taxonref",
        "value": 99,
        "count": 12,
        "table_name": "occurrences",
    }


def test_find_entity_by_id_falls_back_to_representative_without_reference_table(
    monkeypatch,
):
    fallback = {
        "level": "plots",
        "column": "plot_id",
        "value": 17,
        "count": 8,
        "table_name": "occurrences",
    }

    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: None
    )
    monkeypatch.setattr(
        entity_finder, "find_representative_entity", lambda _db, _info: fallback
    )

    result = entity_finder.find_entity_by_id(
        _DummyDatabase(),
        {"reference_name": "plots", "source_dataset": "occurrences"},
        "17",
    )

    assert result == fallback


def test_find_entity_by_id_uses_detected_id_field_and_relation_count(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: "entity_plots"
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(entity_finder, "get_working_directory", lambda: None)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "SELECT * FROM entity_plots LIMIT 0" in query_text:
            return pd.DataFrame(columns=["id_plot", "full_name", "plots_id"])
        if "SELECT *" in query_text and "FROM entity_plots" in query_text:
            return pd.DataFrame(
                [{"id_plot": "17", "full_name": "Forêt Nord", "plots_id": "P-017"}]
            )
        if "COUNT(*) as cnt" in query_text and "FROM occurrences" in query_text:
            return pd.DataFrame([{"cnt": 6}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_entity_by_id(
        _DummyDatabase(existing_tables={"entity_plots"}),
        {
            "reference_name": "plots",
            "source_dataset": "occurrences",
            "relation": {"key": "plot_id", "ref_field": "plots_id"},
        },
        "17",
    )

    assert result == {
        "level": "plots",
        "column": "plot_id",
        "value": "P-017",
        "count": 6,
        "table_name": "occurrences",
        "entity_name": "Forêt Nord",
    }


def test_find_entity_by_id_uses_hierarchy_level_when_rank_matches(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "taxons": {
                            "kind": "hierarchical",
                            "schema": {"id_field": "id_taxon"},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: "entity_taxons"
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(entity_finder, "get_working_directory", lambda: tmp_path)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "SELECT * FROM entity_taxons LIMIT 0" in query_text:
            return pd.DataFrame(
                columns=["id_taxon", "full_name", "rank_name", "rank_value"]
            )
        if (
            "FROM entity_taxons" in query_text
            and "WHERE id_taxon = :entity_id" in query_text
        ):
            return pd.DataFrame(
                [
                    {
                        "id_taxon": "17",
                        "full_name": "Myrtaceae",
                        "rank_name": "family",
                        "rank_value": "Myrtaceae",
                    }
                ]
            )
        if "COUNT(*) as cnt FROM occurrences WHERE family = :val" in query_text:
            return pd.DataFrame([{"cnt": 33}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_entity_by_id(
        _DummyDatabase(existing_tables={"entity_taxons"}),
        {
            "reference_name": "taxons",
            "source_dataset": "occurrences",
            "levels": ["family", "genus"],
            "level_columns": {"family": "family"},
        },
        "17",
    )

    assert result == {
        "level": "family",
        "column": "family",
        "value": "Myrtaceae",
        "count": 33,
        "table_name": "occurrences",
        "entity_name": "Myrtaceae",
    }


def test_find_entity_by_id_reads_relation_key_from_transform_config(
    monkeypatch, tmp_path
):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "plots",
                    "sources": [{"relation": {"key": "plot_id"}}],
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: "entity_plots"
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(entity_finder, "get_working_directory", lambda: tmp_path)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "SELECT * FROM entity_plots LIMIT 0" in query_text:
            return pd.DataFrame(columns=["id_plot", "full_name", "plots_id"])
        if (
            "FROM entity_plots" in query_text
            and "WHERE id_plot = :entity_id" in query_text
        ):
            return pd.DataFrame(
                [{"id_plot": "17", "full_name": "Forêt Nord", "plots_id": "P-017"}]
            )
        if "COUNT(*) as cnt" in query_text and "FROM occurrences" in query_text:
            return pd.DataFrame([{"cnt": 9}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_entity_by_id(
        _DummyDatabase(existing_tables={"entity_plots"}),
        {
            "reference_name": "plots",
            "source_dataset": "occurrences",
        },
        "17",
    )

    assert result == {
        "level": "plots",
        "column": "plot_id",
        "value": "P-017",
        "count": 9,
        "table_name": "occurrences",
        "entity_name": "Forêt Nord",
    }


def test_find_entity_by_id_returns_spatial_entity_with_geometry(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "references": {
                        "shapes": {
                            "kind": "spatial",
                            "schema": {"id_field": "id_shape"},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(
        entity_finder, "_resolve_reference_table", lambda _db, _name: "entity_shapes"
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(entity_finder, "get_working_directory", lambda: tmp_path)

    def fake_read_sql(query, _engine, params=None):
        query_text = str(query)
        if "SELECT * FROM entity_shapes LIMIT 0" in query_text:
            return pd.DataFrame(columns=["id_shape", "name", "geom", "shape_type"])
        if (
            "FROM entity_shapes" in query_text
            and "WHERE id_shape = :entity_id" in query_text
        ):
            return pd.DataFrame(
                [
                    {
                        "id_shape": "7",
                        "name": "Province Sud",
                        "geom": "010100",
                        "shape_type": "province",
                    }
                ]
            )
        if "SELECT COALESCE(" in query_text and "AS wkt" in query_text:
            return pd.DataFrame([{"wkt": "POLYGON((0 0,1 0,1 1,0 1,0 0))"}])
        raise AssertionError(f"Unexpected SQL: {query_text}")

    monkeypatch.setattr(entity_finder.pd, "read_sql", fake_read_sql)

    result = entity_finder.find_entity_by_id(
        _DummyDatabase(
            existing_tables={"entity_shapes"},
            engine=_DummyEngine(),
        ),
        {
            "reference_name": "shapes",
            "source_dataset": "occurrences",
        },
        "7",
    )

    assert result["level"] == "shapes"
    assert result["column"] == "id_shape"
    assert result["value"] == "7"
    assert result["count"] == 0
    assert result["table_name"] == "entity_shapes"
    assert result["entity_name"] == "Province Sud"
    assert result["source_type"] == "entity"
    assert result["shape_type"] == "province"
    assert result["geometry"] == "POLYGON((0 0,1 0,1 1,0 1,0 0))"
    assert result["spatial_query"] is True
    assert result["kind"] == "spatial"
    assert result["entity_data"]["name"] == "Province Sud"


def test_find_representative_entity_raises_when_hierarchy_has_no_data(monkeypatch):
    monkeypatch.setattr(
        entity_finder,
        "_resolve_source_dataset_table",
        lambda _db, _dataset: "occurrences",
    )
    monkeypatch.setattr(entity_finder, "_quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(
        entity_finder.pd,
        "read_sql",
        lambda query, _engine, params=None: pd.DataFrame(),
    )

    with pytest.raises(entity_finder.HTTPException, match="No data found"):
        entity_finder.find_representative_entity(
            _DummyDatabase(),
            {
                "reference_name": "taxons",
                "source_dataset": "occurrences",
                "levels": ["family"],
                "kind": "hierarchical",
            },
        )
