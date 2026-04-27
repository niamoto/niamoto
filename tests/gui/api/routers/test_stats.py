"""Unit tests for stats router helper functions."""

import asyncio
from typing import Any, Dict, List

import duckdb
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.routers import stats as stats_router
from niamoto.gui.api.routers.stats import (
    _load_import_entities_config,
    _pick_first_existing,
    _resolve_physical_table_name,
    _build_entity_type_map,
    _classify_geometry_kind,
    _find_geometry_column,
    _resolve_entity_table,
    _resolve_mappable_reference_metadata,
    _resolve_occurrence_table,
    _resolve_spatial_reference_tables,
    _resolve_taxonomy_table_name,
    _serialize_hierarchy_node,
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


def test_resolve_mappable_reference_metadata_uses_schema_geometry_field():
    table_names = ["entity_plots"]
    references = {
        "plots": {
            "kind": "generic",
            "schema": {
                "id_field": "plot_key",
                "name_field": "plot_label",
                "fields": [
                    {"name": "plot_key", "type": "integer"},
                    {"name": "plot_label", "type": "string"},
                    {"name": "custom_location", "type": "geometry"},
                ],
            },
        }
    }
    db = _DummyDatabase(
        {
            "entity_plots": [
                {"name": "plot_key", "type": "INTEGER"},
                {"name": "plot_label", "type": "VARCHAR"},
                {"name": "custom_location", "type": "VARCHAR"},
            ]
        }
    )

    metadata = _resolve_mappable_reference_metadata(
        db, table_names, references, "plots"
    )

    assert metadata is not None
    assert metadata["table_name"] == "entity_plots"
    assert metadata["geometry_column"] == "custom_location"
    assert metadata["id_column"] == "plot_key"
    assert metadata["name_column"] == "plot_label"


def test_resolve_mappable_reference_metadata_prefers_configured_geometry_field():
    table_names = ["entity_shapes"]
    references = {
        "shapes": {
            "kind": "spatial",
            "schema": {
                "id_field": "shape_id",
                "name_field": "label",
                "geometry_field": "polygon_wkt",
            },
        }
    }
    db = _DummyDatabase(
        {
            "entity_shapes": [
                {"name": "shape_id", "type": "VARCHAR"},
                {"name": "label", "type": "VARCHAR"},
                {"name": "geo_pt", "type": "VARCHAR"},
                {"name": "polygon_wkt", "type": "VARCHAR"},
            ]
        }
    )

    metadata = _resolve_mappable_reference_metadata(
        db, table_names, references, "shapes"
    )

    assert metadata is not None
    assert metadata["geometry_column"] == "polygon_wkt"
    assert metadata["configured_geometry_column"] == "polygon_wkt"
    assert metadata["is_native"] is False


def test_classify_geometry_kind_groups_common_geometry_types():
    assert _classify_geometry_kind(["POINT"]) == "point"
    assert _classify_geometry_kind(["POLYGON", "MULTIPOLYGON"]) == "polygon"
    assert _classify_geometry_kind(["POINT", "POLYGON"]) == "mixed"


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


def test_serialize_hierarchy_node_falls_back_for_non_numeric_level():
    node = _serialize_hierarchy_node(
        {
            "id_value": 7,
            "parent_value": 3,
            "label_value": "Araucaria columnaris",
            "rank_value": "species",
            "level_value": "species",
            "path_value": "Araucariaceae > Araucaria > Araucaria columnaris",
        },
        child_count=0,
        level_fallback=2,
    )

    assert node.level == 2
    assert node.label == "Araucaria columnaris"
    assert node.has_children is False


def test_serialize_hierarchy_node_keeps_unknown_non_numeric_level_null():
    node = _serialize_hierarchy_node(
        {
            "id_value": 7,
            "parent_value": None,
            "label_value": "Family label",
            "rank_value": "family",
            "level_value": "rank-label",
            "path_value": "Family label",
        },
        child_count=1,
    )

    assert node.level is None
    assert node.has_children is True


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


def test_hierarchy_inspection_loads_roots_children_and_search(
    gui_duckdb_client: TestClient, gui_duckdb_project
):
    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("DROP TABLE entity_taxons")
        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id INTEGER,
                parent_id INTEGER,
                level INTEGER,
                rank_name VARCHAR,
                rank_value VARCHAR,
                full_name VARCHAR,
                full_path VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (101, NULL, 0, 'family', 'Araucariaceae', 'Araucariaceae', 'Araucariaceae'),
                (102, 101, 1, 'genus', 'Araucaria', 'Araucaria', 'Araucariaceae > Araucaria'),
                (103, 102, 2, 'species', 'columnaris', 'Araucaria columnaris', 'Araucariaceae > Araucaria > Araucaria columnaris'),
                (104, 999, 2, 'species', 'missing', 'Missing parent species', 'Missing parent species')
            """
        )
    finally:
        conn.close()

    roots_response = gui_duckdb_client.get("/api/stats/hierarchy/taxons?limit=10")
    assert roots_response.status_code == 200, roots_response.text
    roots = roots_response.json()

    assert roots["reference_name"] == "taxons"
    assert roots["table_name"] == "entity_taxons"
    assert roots["is_hierarchical"] is True
    assert roots["metadata_available"] is True
    assert roots["total_nodes"] == 4
    assert roots["root_count"] == 1
    assert roots["orphan_count"] == 1
    assert roots["nodes"][0]["label"] == "Araucariaceae"
    assert roots["nodes"][0]["child_count"] == 1
    species_level = next(
        level for level in roots["levels"] if level["level"] == "species"
    )
    assert species_level["orphan_count"] == 1

    children_response = gui_duckdb_client.get(
        "/api/stats/hierarchy/taxons?mode=children&parent_id=101&limit=10"
    )
    assert children_response.status_code == 200, children_response.text
    children = children_response.json()
    assert children["mode"] == "children"
    assert children["parent_id"] == "101"
    assert [node["label"] for node in children["nodes"]] == ["Araucaria"]

    search_response = gui_duckdb_client.get(
        "/api/stats/hierarchy/taxons?mode=search&search=columnaris&limit=10"
    )
    assert search_response.status_code == 200, search_response.text
    search = search_response.json()
    assert search["mode"] == "search"
    assert search["nodes"][0]["label"] == "Araucaria columnaris"
    assert "Araucariaceae" in search["nodes"][0]["path"]

    first_page_response = gui_duckdb_client.get(
        "/api/stats/hierarchy/taxons?mode=search&search=Araucaria&limit=1"
    )
    assert first_page_response.status_code == 200, first_page_response.text
    first_page = first_page_response.json()
    assert first_page["result_count"] == 3
    assert first_page["has_more"] is True
    assert first_page["next_offset"] == 1

    second_page_response = gui_duckdb_client.get(
        "/api/stats/hierarchy/taxons?mode=search&search=Araucaria&limit=1&offset=1"
    )
    assert second_page_response.status_code == 200, second_page_response.text
    second_page = second_page_response.json()
    assert second_page["offset"] == 1
    assert second_page["nodes"][0]["label"] == "Araucaria"


def test_hierarchy_inspection_uses_configured_hierarchy_columns(
    gui_duckdb_client: TestClient, gui_duckdb_project
):
    import_path = gui_duckdb_project / "config" / "import.yml"
    config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    config["entities"]["references"]["custom_taxons"] = {
        "kind": "hierarchical",
        "schema": {
            "id_field": "taxon_key",
            "name_field": "display_label",
        },
        "hierarchy": {
            "parent_field": "parent_key",
            "rank_field": "rank_label",
        },
    }
    import_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE entity_custom_taxons (
                taxon_key INTEGER,
                parent_key INTEGER,
                rank_label VARCHAR,
                display_label VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_custom_taxons VALUES
                (1, NULL, 'family', 'Configured Family'),
                (2, 1, 'genus', 'Configured Genus')
            """
        )
    finally:
        conn.close()

    response = gui_duckdb_client.get("/api/stats/hierarchy/custom_taxons")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["metadata_available"] is True
    assert payload["nodes"][0]["label"] == "Configured Family"
    assert payload["nodes"][0]["child_count"] == 1
    assert {level["level"] for level in payload["levels"]} == {"family", "genus"}


def test_hierarchy_inspection_handles_non_hierarchical_reference(
    gui_duckdb_client: TestClient, gui_duckdb_project
):
    import_path = gui_duckdb_project / "config" / "import.yml"
    config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    config["entities"]["references"]["plots"] = {"kind": "generic"}
    import_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE entity_plots (id INTEGER, name VARCHAR)")
        conn.execute("INSERT INTO entity_plots VALUES (1, 'Plot A')")
    finally:
        conn.close()

    response = gui_duckdb_client.get("/api/stats/hierarchy/plots")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["is_hierarchical"] is False
    assert payload["metadata_available"] is False
    assert payload["nodes"] == []


def test_hierarchy_inspection_returns_404_for_unknown_reference(
    gui_duckdb_client: TestClient,
):
    response = gui_duckdb_client.get("/api/stats/hierarchy/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Reference 'missing' not found"


def test_spatial_map_inspection_maps_generic_reference_with_geometry_schema(
    gui_duckdb_client: TestClient, gui_duckdb_project
):
    import_path = gui_duckdb_project / "config" / "import.yml"
    config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    config["entities"]["references"]["plots"] = {
        "kind": "generic",
        "schema": {
            "id_field": "id_plot",
            "name_field": "plot",
            "fields": [
                {"name": "id_plot", "type": "integer"},
                {"name": "plot", "type": "string"},
                {"name": "geo_pt", "type": "geometry"},
            ],
        },
    }
    import_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE entity_plots (
                id_plot INTEGER,
                plot VARCHAR,
                geo_pt VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_plots VALUES
                (1, 'Plot A', 'POINT (164.2 -20.4)'),
                (2, 'Plot B', 'POINT (166.9 -22.2)')
            """
        )
    finally:
        conn.close()

    response = gui_duckdb_client.get("/api/stats/spatial-map/plots?limit=1")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["is_mappable"] is True
    assert payload["geometry_column"] == "geo_pt"
    assert payload["geometry_storage"] == "wkt"
    assert payload["geometry_kind"] == "point"
    assert payload["total_features"] == 2
    assert payload["with_geometry"] == 2
    assert payload["has_more"] is True
    assert payload["next_offset"] == 1
    assert payload["bounding_box"] == {
        "min_x": 164.2,
        "min_y": -22.2,
        "max_x": 166.9,
        "max_y": -20.4,
    }
    features = payload["feature_collection"]["features"]
    assert len(features) == 1
    assert features[0]["geometry"]["type"] == "Point"
    assert features[0]["properties"]["label"] == "Plot A"


def test_spatial_map_inspection_maps_spatial_polygons_and_spatial_stats_bbox(
    gui_duckdb_client: TestClient, gui_duckdb_project
):
    import_path = gui_duckdb_project / "config" / "import.yml"
    config = yaml.safe_load(import_path.read_text(encoding="utf-8"))
    config["entities"]["references"]["shapes"] = {
        "kind": "spatial",
        "schema": {
            "id_field": "shape_id",
            "name_field": "name",
            "fields": [
                {"name": "shape_id", "type": "string"},
                {"name": "name", "type": "string"},
                {"name": "location", "type": "geometry"},
            ],
        },
    }
    import_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    db_path = gui_duckdb_project / "db" / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE entity_shapes (
                shape_id VARCHAR,
                name VARCHAR,
                type VARCHAR,
                location VARCHAR
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_shapes VALUES
                ('north', 'North', 'province',
                 'POLYGON ((164 -22, 165 -22, 165 -21, 164 -21, 164 -22))'),
                ('south', 'South', 'protected_area',
                 'POLYGON ((166 -21, 167 -21, 167 -20, 166 -20, 166 -21))'),
                ('group', 'Group', 'group', NULL)
            """
        )
    finally:
        conn.close()

    response = gui_duckdb_client.get("/api/stats/spatial-map/shapes?limit=10")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["is_mappable"] is True
    assert payload["geometry_kind"] == "polygon"
    assert payload["type_column"] == "type"
    assert payload["layer_column"] == "type"
    assert payload["with_geometry"] == 2
    assert payload["without_geometry"] == 1
    assert {layer["value"] for layer in payload["layers"]} == {
        "province",
        "protected_area",
        "group",
    }
    assert {layer["value"]: layer["with_geometry"] for layer in payload["layers"]} == {
        "province": 1,
        "protected_area": 1,
        "group": 0,
    }
    assert payload["bounding_box"] == {
        "min_x": 164.0,
        "min_y": -22.0,
        "max_x": 167.0,
        "max_y": -20.0,
    }
    assert payload["feature_collection"]["features"][0]["geometry"]["type"] == "Polygon"

    layer_response = gui_duckdb_client.get(
        "/api/stats/spatial-map/shapes?layer=province&limit=10"
    )
    assert layer_response.status_code == 200, layer_response.text
    layer_payload = layer_response.json()
    assert layer_payload["selected_layer"] == "province"
    assert layer_payload["total_features"] == 1
    assert layer_payload["with_geometry"] == 1
    assert (
        layer_payload["feature_collection"]["features"][0]["properties"]["label"]
        == "North"
    )
    assert layer_payload["bounding_box"] == {
        "min_x": 164.0,
        "min_y": -22.0,
        "max_x": 165.0,
        "max_y": -21.0,
    }

    render_response = gui_duckdb_client.get(
        "/api/stats/spatial-map/shapes/render?layer=province&limit=10"
    )
    assert render_response.status_code == 200, render_response.text
    assert "Plotly.newPlot" in render_response.text
    assert "plotly-niamoto-maps" in render_response.text
    assert "#2E7D32" in render_response.text

    all_layers_render_response = gui_duckdb_client.get(
        "/api/stats/spatial-map/shapes/render?limit=10"
    )
    assert all_layers_render_response.status_code == 200
    assert "Select a layer" in all_layers_render_response.text
    assert "Plotly.newPlot" not in all_layers_render_response.text
    assert "plotly-niamoto-maps" not in all_layers_render_response.text

    stats_response = gui_duckdb_client.get("/api/stats/spatial?entity=shapes")
    assert stats_response.status_code == 200, stats_response.text
    stats_payload = stats_response.json()
    assert stats_payload["with_coordinates"] == 2
    assert stats_payload["bounding_box"] == payload["bounding_box"]


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
