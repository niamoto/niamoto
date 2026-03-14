"""Unit tests for stats router helper functions."""

from typing import Any, Dict, List

from niamoto.gui.api.routers.stats import (
    _build_entity_type_map,
    _find_geometry_column,
    _resolve_entity_table,
    _resolve_occurrence_table,
    _resolve_spatial_reference_tables,
    _resolve_taxonomy_table_name,
)


class _DummyInspector:
    """Minimal inspector stub for geometry helper tests."""

    def __init__(self, columns_by_table: Dict[str, List[Dict[str, Any]]]):
        self.columns_by_table = columns_by_table

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        return self.columns_by_table.get(table_name, [])


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

    resolved = _resolve_spatial_reference_tables(
        table_names, inspector, references, occurrence_table="dataset_observations"
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

    resolved = _resolve_spatial_reference_tables(
        table_names, inspector, references={}, occurrence_table="dataset_observations"
    )

    assert len(resolved) == 1
    assert resolved[0]["table_name"] == "zones_polygons"
    assert resolved[0]["has_geometry"] is True
    assert resolved[0]["geo_column"] == "geometry"


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
