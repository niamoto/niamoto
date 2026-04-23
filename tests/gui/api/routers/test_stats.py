"""Unit tests for stats router helper functions."""

import asyncio
from typing import Any, Dict, List

import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.routers import stats as stats_router
from niamoto.gui.api.routers.stats import (
    _load_import_entities_config,
    _pick_first_existing,
    _resolve_physical_table_name,
    _build_entity_type_map,
    _find_geometry_column,
    _resolve_entity_table,
    _resolve_occurrence_table,
    _resolve_spatial_reference_tables,
    _resolve_taxonomy_table_name,
    classify_table_type,
    detect_coordinate_columns,
    find_table_by_pattern,
)


class _DummyInspector:
    """Minimal inspector stub for geometry helper tests."""

    def __init__(self, columns_by_table: Dict[str, List[Dict[str, Any]]]):
        self.columns_by_table = columns_by_table

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        return self.columns_by_table.get(table_name, [])


class _DummyDatabase:
    """Minimal DB stub matching the backend-safe get_columns helper."""

    def __init__(self, columns_by_table: Dict[str, List[Dict[str, Any]]]):
        self.columns_by_table = columns_by_table

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        return self.columns_by_table.get(table_name, [])


def test_classify_table_type_detects_layers_and_defaults_to_dataset():
    assert classify_table_type("raster_dem_tiles") == "layer"
    assert classify_table_type("vector_layer_metadata") == "layer"
    assert classify_table_type("observations_table") == "dataset"


def test_detect_coordinate_columns_detects_wkt_and_xy_candidates():
    detected = detect_coordinate_columns(
        ["sample_id", "Longitude", "Latitude", "geo_pt_geom"]
    )

    assert detected == {
        "wkt_col": "geo_pt_geom",
        "x_col": "Longitude",
        "y_col": "Latitude",
    }


def test_find_table_by_pattern_supports_exact_resolution_and_partial_match():
    table_names = ["dataset_observations", "entity_taxons", "plots_archive"]

    assert find_table_by_pattern(table_names, "taxons") == "entity_taxons"
    assert find_table_by_pattern(table_names, "archive") == "plots_archive"
    assert find_table_by_pattern(table_names, "missing") is None


def test_load_import_entities_config_reads_project_metadata(monkeypatch, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump(
            {
                "entities": {
                    "datasets": {"observations": {"connector": {"type": "csv"}}},
                    "references": {"plots": {"kind": "spatial"}},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(stats_router, "get_working_directory", lambda: tmp_path)

    datasets, references = _load_import_entities_config()

    assert datasets == {"observations": {"connector": {"type": "csv"}}}
    assert references == {"plots": {"kind": "spatial"}}


def test_load_import_entities_config_returns_empty_on_missing_or_invalid_config(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(stats_router, "get_working_directory", lambda: None)
    assert _load_import_entities_config() == ({}, {})

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "import.yml").write_text(
        yaml.safe_dump({"entities": {"datasets": [], "references": []}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(stats_router, "get_working_directory", lambda: tmp_path)

    assert _load_import_entities_config() == ({}, {})


def test_resolve_physical_table_name_and_pick_first_existing():
    table_names = ["dataset_occurrences", "entity_taxons"]
    columns_by_lower = {"id_plot": "ID_PLOT", "label": "Label"}

    assert _resolve_physical_table_name(table_names, "taxons") == "entity_taxons"
    assert (
        _resolve_physical_table_name(table_names, "occurrences")
        == "dataset_occurrences"
    )
    assert _resolve_physical_table_name(table_names, "missing") is None

    assert (
        _pick_first_existing(columns_by_lower, [None, "id_plot", "label"]) == "ID_PLOT"
    )
    assert _pick_first_existing(columns_by_lower, ["missing", "LABEL"]) == "Label"
    assert _pick_first_existing(columns_by_lower, ["missing"]) is None


def test_resolve_occurrence_table_prefers_configured_dataset():
    """When no 'occurrences' dataset exists, pick configured dataset instead of hardcoding."""
    table_names = ["dataset_observations", "entity_admin_areas"]
    datasets = {"observations": {"connector": {"type": "file"}}}

    resolved = _resolve_occurrence_table(table_names, "occurrences", datasets)

    assert resolved == "dataset_observations"


def test_resolve_occurrence_table_uses_explicit_entity():
    """An explicit logical dataset name should resolve to its physical table."""
    table_names = ["dataset_observations", "entity_admin_areas"]
    datasets = {"observations": {"connector": {"type": "file"}}}

    resolved = _resolve_occurrence_table(table_names, "observations", datasets)

    assert resolved == "dataset_observations"


def test_resolve_entity_table_prefers_config_metadata():
    """Entity table resolution should use datasets/references before fuzzy matching."""
    table_names = ["dataset_observations", "entity_admin_areas"]
    datasets = {"observations": {"connector": {"type": "file"}}}
    references = {"admin_areas": {"kind": "spatial"}}

    assert (
        _resolve_entity_table(table_names, "observations", datasets, references)
        == "dataset_observations"
    )
    assert (
        _resolve_entity_table(table_names, "admin_areas", datasets, references)
        == "entity_admin_areas"
    )


def test_build_entity_type_map_uses_import_entities():
    """Summary classification should be driven by import.yml entities."""
    table_names = ["dataset_observations", "entity_admin_areas", "misc_table"]
    datasets = {"observations": {"connector": {"type": "file"}}}
    references = {"admin_areas": {"kind": "spatial"}}

    type_map = _build_entity_type_map(table_names, datasets, references)

    assert type_map["dataset_observations"] == "dataset"
    assert type_map["entity_admin_areas"] == "reference"
    assert "misc_table" not in type_map


def test_find_geometry_column_prefers_native_geometry():
    """Native GEOMETRY/BYTEA columns should have priority over WKT-like columns."""
    columns_info = [
        {"name": "location", "type": "VARCHAR"},
        {"name": "wkb_geometry", "type": "BYTEA"},
    ]

    geo_col, is_native = _find_geometry_column(columns_info)

    assert geo_col == "wkb_geometry"
    assert is_native is True


def test_resolve_spatial_reference_tables_from_config_without_keywords():
    """Configured spatial references should resolve even with neutral table names."""
    table_names = ["entity_admin_areas", "dataset_observations"]
    references = {
        "admin_areas": {
            "kind": "spatial",
            "description": "Administrative areas",
            "schema": {"id_field": "area_id"},
        }
    }
    inspector = _DummyInspector(
        {
            "entity_admin_areas": [
                {"name": "area_id", "type": "INTEGER"},
                {"name": "label", "type": "VARCHAR"},
                {"name": "wkb_geometry", "type": "BYTEA"},
            ]
        }
    )
    db = _DummyDatabase(inspector.columns_by_table)

    resolved = _resolve_spatial_reference_tables(
        db, table_names, inspector, references, occurrence_table="dataset_observations"
    )

    assert len(resolved) == 1
    assert resolved[0]["table_name"] == "entity_admin_areas"
    assert resolved[0]["has_geometry"] is True
    assert resolved[0]["geo_column"] == "wkb_geometry"
    assert resolved[0]["id_column"] == "area_id"
    assert resolved[0]["name_column"] == "label"


def test_resolve_spatial_reference_tables_fallback_geometry_scan():
    """When config is missing, fallback should detect any geometry table."""
    table_names = ["zones_polygons", "dataset_observations"]
    inspector = _DummyInspector(
        {
            "zones_polygons": [
                {"name": "zone_code", "type": "VARCHAR"},
                {"name": "zone_name", "type": "VARCHAR"},
                {"name": "geometry", "type": "GEOMETRY"},
            ],
            "dataset_observations": [
                {"name": "id", "type": "INTEGER"},
                {"name": "geo_pt", "type": "VARCHAR"},
            ],
        }
    )
    db = _DummyDatabase(inspector.columns_by_table)

    resolved = _resolve_spatial_reference_tables(
        db,
        table_names,
        inspector,
        references={},
        occurrence_table="dataset_observations",
    )

    assert len(resolved) == 1
    assert resolved[0]["table_name"] == "zones_polygons"
    assert resolved[0]["has_geometry"] is True
    assert resolved[0]["geo_column"] == "geometry"


def test_resolve_spatial_reference_tables_accepts_file_multi_feature_connector():
    table_names = ["entity_shapes", "dataset_occurrences"]
    references = {
        "shapes": {
            "connector": {"type": "file_multi_feature"},
            "schema": {"id_field": "shape_id"},
        }
    }
    inspector = _DummyInspector(
        {
            "entity_shapes": [
                {"name": "shape_id", "type": "INTEGER"},
                {"name": "name", "type": "VARCHAR"},
                {"name": "type", "type": "VARCHAR"},
                {"name": "geometry", "type": "GEOMETRY"},
            ]
        }
    )
    db = _DummyDatabase(inspector.columns_by_table)

    resolved = _resolve_spatial_reference_tables(
        db, table_names, inspector, references, occurrence_table="dataset_occurrences"
    )

    assert resolved == [
        {
            "reference_name": "shapes",
            "table_name": "entity_shapes",
            "display_name": "Shapes",
            "has_geometry": True,
            "geo_column": "geometry",
            "is_native": True,
            "id_column": "shape_id",
            "name_column": "name",
            "type_column": "type",
        }
    ]


def test_resolve_spatial_reference_tables_fallback_skips_internal_tables():
    table_names = ["dataset_occurrences", "_internal_cache", "sqlite_sequence", "zones"]
    inspector = _DummyInspector(
        {
            "dataset_occurrences": [{"name": "geo_pt", "type": "VARCHAR"}],
            "zones": [
                {"name": "zone_id", "type": "INTEGER"},
                {"name": "title", "type": "VARCHAR"},
                {"name": "geom", "type": "VARCHAR"},
            ],
        }
    )
    db = _DummyDatabase(inspector.columns_by_table)

    resolved = _resolve_spatial_reference_tables(
        db,
        table_names,
        inspector,
        references={},
        occurrence_table="dataset_occurrences",
    )

    assert resolved == [
        {
            "reference_name": "zones",
            "table_name": "zones",
            "display_name": "Zones",
            "has_geometry": True,
            "geo_column": "geom",
            "is_native": False,
            "id_column": "zone_id",
            "name_column": "title",
            "type_column": None,
        }
    ]


def test_resolve_taxonomy_table_name_prefers_hierarchical_reference():
    """Taxonomy resolver should pick configured hierarchical reference."""
    table_names = ["entity_plants", "entity_admin_areas"]
    references = {
        "plants": {"kind": "hierarchical"},
        "admin_areas": {"kind": "spatial"},
    }

    resolved = _resolve_taxonomy_table_name(
        table_names, references, requested="taxonomy"
    )

    assert resolved == "entity_plants"


def test_import_summary_uses_duckdb_fixture_without_sqlalchemy_reflection_errors(
    gui_duckdb_client: TestClient,
):
    """Summary endpoint should introspect DuckDB tables without PostgreSQL reflection."""

    response = gui_duckdb_client.get("/api/stats/summary")

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["total_entities"] == 2
    assert payload["total_rows"] == 5

    entities = {entity["name"]: entity for entity in payload["entities"]}
    assert entities["dataset_occurrences"]["entity_type"] == "dataset"
    assert entities["dataset_occurrences"]["column_count"] == 4
    assert entities["dataset_occurrences"]["columns"] == [
        "id",
        "taxon_id",
        "count",
        "locality",
    ]
    assert entities["entity_taxons"]["entity_type"] == "reference"


def test_completeness_endpoint_uses_duckdb_fixture_without_reflection_errors(
    gui_duckdb_client: TestClient,
):
    response = gui_duckdb_client.get("/api/stats/completeness/dataset_occurrences")

    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["entity"] == "dataset_occurrences"
    assert payload["overall_completeness"] == 1.0
    columns = {column["column"]: column for column in payload["columns"]}
    assert columns["id"]["total_count"] == 3
    assert columns["id"]["null_count"] == 0
    assert columns["taxon_id"]["unique_count"] == 2
    assert columns["locality"]["completeness"] == 1.0


def test_completeness_endpoint_returns_404_for_unknown_entity(
    gui_duckdb_client: TestClient,
):
    response = gui_duckdb_client.get("/api/stats/completeness/missing_table")

    assert response.status_code == 404
    assert response.json()["detail"] == "Entity 'missing_table' not found"


def test_validation_rules_default_and_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(stats_router, "get_working_directory", lambda: tmp_path)

    defaults = asyncio.run(stats_router.get_validation_rules())
    assert len(defaults.rules) == 2
    assert defaults.rules[0].rule_type == "outlier"
    assert defaults.rules[1].target == "coordinates"

    updated = stats_router.ValidationRules(
        rules=[
            stats_router.ValidationRule(
                rule_type="required",
                target="dataset_occurrences.locality",
                method="manual",
                params={"allow_empty": False},
            )
        ]
    )

    result = asyncio.run(stats_router.update_validation_rules(updated))

    assert result == updated
    saved_path = tmp_path / "config" / "validation.yml"
    assert saved_path.exists()
    saved = yaml.safe_load(saved_path.read_text(encoding="utf-8"))
    assert saved == {
        "rules": [
            {
                "type": "required",
                "target": "dataset_occurrences.locality",
                "method": "manual",
                "params": {"allow_empty": False},
            }
        ]
    }

    reloaded = asyncio.run(stats_router.get_validation_rules())
    assert reloaded == updated
