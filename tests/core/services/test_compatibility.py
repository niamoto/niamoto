"""Unit tests for the pre-import impact check service."""

from __future__ import annotations

import logging

import pandas as pd
import yaml

from niamoto.common.database import Database
from niamoto.core.imports.registry import EntityKind, EntityRegistry
from niamoto.core.imports.source_registry import TransformSourceRegistry
from niamoto.core.services.compatibility import (
    CSVSchemaReader,
    CompatibilityService,
    ConfigRefCollector,
    EntityResolver,
    ImpactLevel,
    TargetKind,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_IMPORT_CONFIG = {
    "entities": {
        "datasets": {
            "occurrences": {
                "connector": {"type": "file", "path": "imports/occurrences.csv"},
                "schema": {
                    "id_field": "id",
                    "fields": [
                        {"name": "id", "type": "integer"},
                        {"name": "species", "type": "string"},
                        {"name": "dbh", "type": "float"},
                    ],
                },
                "links": [
                    {
                        "entity": "taxons",
                        "field": "id_taxonref",
                        "target_field": "taxons_id",
                    }
                ],
            },
        },
        "references": {
            "taxons": {
                "kind": "hierarchical",
                "connector": {
                    "type": "derived",
                    "source": "occurrences",
                    "extraction": {
                        "levels": [
                            {"name": "family", "column": "family"},
                            {"name": "genus", "column": "genus"},
                            {"name": "species", "column": "species"},
                        ],
                        "id_column": "id_taxonref",
                        "name_column": "taxaname",
                        "additional_columns": ["infra"],
                    },
                },
                "hierarchy": {
                    "strategy": "adjacency_list",
                    "levels": ["family", "genus", "species"],
                },
                "schema": {"id_field": "id", "fields": []},
            },
            "plots": {
                "connector": {
                    "type": "file",
                    "path": "imports/plots.csv",
                },
                "schema": {
                    "id_field": "id_plot",
                    "fields": [{"name": "geo_pt", "type": "geometry"}],
                },
            },
        },
    }
}

SAMPLE_TRANSFORM_CONFIG = [
    {
        "group_by": "taxons",
        "sources": [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": "taxons",
                "relation": {
                    "plugin": "nested_set",
                    "key": "id_taxonref",
                    "ref_key": "taxons_id",
                    "fields": {
                        "parent": "parent_id",
                        "left": "lft",
                        "right": "rght",
                    },
                },
            }
        ],
    },
    {
        "group_by": "plots",
        "sources": [
            {
                "name": "occurrences",
                "data": "occurrences",
                "grouping": "plots",
                "relation": {
                    "plugin": "direct_reference",
                    "key": "plot_name",
                    "ref_key": "plot",
                },
            },
            {
                "name": "plot_stats",
                "data": "imports/raw_plot_stats.csv",
                "grouping": "plots",
                "relation": {
                    "plugin": "stats_loader",
                    "key": "id",
                    "ref_field": "id_plot",
                    "match_field": "plot_id",
                },
            },
        ],
        "widgets_data": {
            "plot_area": {
                "plugin": "direct_attribute",
                "params": {"source": "plot_stats", "field": "area_ha"},
            },
            "plot_metrics": {
                "plugin": "field_aggregator",
                "params": {
                    "fields": [
                        {"source": "plot_stats", "field": "rainfall", "target": "x"},
                        {"source": "plots", "field": "plot", "target": "plot"},
                    ]
                },
            },
        },
    },
]


# ===================================================================
# TestConfigRefCollector
# ===================================================================


class TestConfigRefCollector:
    def setup_method(self):
        self.collector = ConfigRefCollector()

    def test_collects_dataset_schema_refs(self):
        refs = self.collector.collect("occurrences", SAMPLE_IMPORT_CONFIG, [])
        # id_field + 3 fields + 2 link columns
        assert "id" in refs
        assert "species" in refs
        assert "dbh" in refs
        assert "id_taxonref" in refs  # link field
        assert "taxons_id" in refs  # link target_field
        for col in ("id", "species", "dbh", "id_taxonref", "taxons_id"):
            assert all(lvl == ImpactLevel.BLOCKS_IMPORT for _, lvl in refs[col])

    def test_collects_reference_hierarchy_refs(self):
        refs = self.collector.collect("taxons", SAMPLE_IMPORT_CONFIG, [])
        # hierarchy levels are strings, mapped as column names
        assert "family" in refs
        assert "genus" in refs
        assert "species" in refs

    def test_collects_extraction_refs_for_reference(self):
        """Extraction columns are collected for the *reference* entity in import.yml."""
        refs = self.collector.collect("taxons", SAMPLE_IMPORT_CONFIG, [])
        assert "id_taxonref" in refs  # extraction.id_column
        assert "taxaname" in refs  # extraction.name_column
        assert "infra" in refs  # extraction.additional_columns

    def test_collects_derived_extraction_refs_for_source_dataset(self):
        """When checking a dataset, extraction columns from DERIVED references
        that depend on it must also be collected (P1 fix)."""
        refs = self.collector.collect("occurrences", SAMPLE_IMPORT_CONFIG, [])
        # taxons is DERIVED from occurrences → extraction levels reference
        # columns that exist in the occurrences CSV
        assert "family" in refs
        assert "genus" in refs
        assert "species" in refs
        assert "infra" in refs  # additional_columns
        assert "id_taxonref" in refs  # extraction.id_column
        assert "taxaname" in refs  # extraction.name_column
        for col in ("family", "genus", "species", "infra", "id_taxonref", "taxaname"):
            assert any(lvl == ImpactLevel.BLOCKS_IMPORT for _, lvl in refs[col])

    def test_collects_transform_relation_key_for_data_entity(self):
        refs = self.collector.collect(
            "occurrences", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        # relation.key in taxons group → id_taxonref → belongs to occurrences
        assert "id_taxonref" in refs
        transform_refs = [
            (p, lvl) for p, lvl in refs["id_taxonref"] if "transform" in p
        ]
        assert any(lvl == ImpactLevel.BREAKS_TRANSFORM for _, lvl in transform_refs)

        # relation.key in plots group → plot_name → belongs to occurrences
        assert "plot_name" in refs
        assert any(lvl == ImpactLevel.BREAKS_TRANSFORM for _, lvl in refs["plot_name"])

    def test_collects_transform_ref_key_for_grouping_entity(self):
        refs = self.collector.collect(
            "taxons", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        # relation.ref_key = taxons_id → belongs to taxons (grouping)
        assert "taxons_id" in refs
        transform_refs = [(p, lvl) for p, lvl in refs["taxons_id"] if "transform" in p]
        assert any(lvl == ImpactLevel.BREAKS_TRANSFORM for _, lvl in transform_refs)

    def test_collects_relation_fields_values_for_grouping_entity(self):
        refs = self.collector.collect(
            "taxons", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        # relation.fields values: parent_id, lft, rght → belong to taxons
        assert "parent_id" in refs
        assert "lft" in refs
        assert "rght" in refs
        for col in ("parent_id", "lft", "rght"):
            assert any(lvl == ImpactLevel.BREAKS_TRANSFORM for _, lvl in refs[col])

    def test_attributes_key_to_data_not_grouping(self):
        refs = self.collector.collect(
            "taxons", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        # relation.key = id_taxonref is for occurrences (data), NOT taxons
        # BUT id_taxonref is also in extraction.id_column for taxons
        # so we check that transform refs for id_taxonref are NOT present for taxons
        transform_id_refs = [
            (p, lvl)
            for p, lvl in refs.get("id_taxonref", [])
            if "transform" in p and "relation.key" in p
        ]
        assert len(transform_id_refs) == 0

    def test_attributes_ref_key_to_grouping_not_data(self):
        refs = self.collector.collect(
            "occurrences", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        # relation.ref_key = taxons_id belongs to taxons, NOT occurrences
        # So occurrences should NOT have transform refs for taxons_id
        if "taxons_id" in refs:
            transform_refs = [
                (p, lvl) for p, lvl in refs["taxons_id"] if "transform" in p
            ]
            assert len(transform_refs) == 0

    def test_collects_ref_field_for_grouping_entity(self):
        refs = self.collector.collect(
            "plots", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        # ref_field = id_plot from plot_stats source → belongs to plots
        assert "id_plot" in refs
        transform_refs = [(p, lvl) for p, lvl in refs["id_plot"] if "transform" in p]
        assert any(lvl == ImpactLevel.BREAKS_TRANSFORM for _, lvl in transform_refs)

    def test_collects_match_field_for_transform_source(self):
        refs = self.collector.collect(
            "plot_stats", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        assert "id" in refs
        assert "plot_id" in refs
        transform_refs = [(p, lvl) for p, lvl in refs["plot_id"] if "transform" in p]
        assert any("relation.match_field" in path for path, _ in transform_refs)

    def test_collects_direct_attribute_refs_for_transform_source(self):
        refs = self.collector.collect(
            "plot_stats", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        assert "area_ha" in refs
        assert any("params.field" in path for path, _ in refs["area_ha"])

    def test_collects_field_aggregator_refs_for_transform_source(self):
        refs = self.collector.collect(
            "plot_stats", SAMPLE_IMPORT_CONFIG, SAMPLE_TRANSFORM_CONFIG
        )
        assert "rainfall" in refs
        assert any("params.fields[0].field" in path for path, _ in refs["rainfall"])

    def test_collects_class_object_series_refs_for_transform_source(self):
        transform_cfg = [
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "plot_stats",
                        "data": "imports/raw_plot_stats.csv",
                        "grouping": "plots",
                        "relation": {"plugin": "stats_loader", "key": "id"},
                    }
                ],
                "widgets_data": {
                    "fragmentation_distribution": {
                        "plugin": "class_object_series_extractor",
                        "params": {
                            "source": "plot_stats",
                            "class_object": "forest_fragmentation",
                            "size_field": {"input": "class_name", "output": "sizes"},
                            "value_field": {
                                "input": "class_value",
                                "output": "values",
                            },
                        },
                    }
                },
            }
        ]

        refs = self.collector.collect("plot_stats", SAMPLE_IMPORT_CONFIG, transform_cfg)

        assert "class_object" in refs
        assert "class_name" in refs
        assert "class_value" in refs
        assert any("params.size_field.input" in path for path, _ in refs["class_name"])
        assert any(
            "params.value_field.input" in path for path, _ in refs["class_value"]
        )

    def test_collects_class_object_field_aggregator_refs_for_transform_source(self):
        transform_cfg = [
            {
                "group_by": "shapes",
                "sources": [
                    {
                        "name": "shape_stats",
                        "data": "imports/raw_shape_stats.csv",
                        "grouping": "shapes",
                        "relation": {"plugin": "stats_loader", "key": "id"},
                    }
                ],
                "widgets_data": {
                    "general_info": {
                        "plugin": "class_object_field_aggregator",
                        "params": {
                            "source": "shape_stats",
                            "fields": [
                                {"class_object": "land_area_ha", "target": "area"},
                            ],
                        },
                    }
                },
            }
        ]

        refs = self.collector.collect(
            "shape_stats", SAMPLE_IMPORT_CONFIG, transform_cfg
        )

        assert "class_object" in refs
        assert "class_value" in refs
        assert "class_name" not in refs

    def test_collects_class_object_axis_refs_for_transform_source(self):
        transform_cfg = [
            {
                "group_by": "shapes",
                "sources": [
                    {
                        "name": "shape_stats",
                        "data": "imports/raw_shape_stats.csv",
                        "grouping": "shapes",
                        "relation": {"plugin": "stats_loader", "key": "id"},
                    }
                ],
                "widgets_data": {
                    "forest_types_by_elevation": {
                        "plugin": "class_object_series_by_axis_extractor",
                        "params": {
                            "source": "shape_stats",
                            "axis": {"field": "class_name", "output_field": "bins"},
                            "types": {"forest": "forest_mature_elevation"},
                        },
                    }
                },
            }
        ]

        refs = self.collector.collect(
            "shape_stats", SAMPLE_IMPORT_CONFIG, transform_cfg
        )

        assert "class_object" in refs
        assert "class_name" in refs
        assert "class_value" in refs
        assert any("params.axis.field" in path for path, _ in refs["class_name"])

    def test_handles_missing_import_config(self):
        refs = self.collector.collect("occurrences", {}, [])
        assert refs == {}

    def test_handles_missing_transform_config(self):
        refs = self.collector.collect("occurrences", SAMPLE_IMPORT_CONFIG, [])
        # Should still have import refs, no crash
        assert "id" in refs

    def test_collects_simple_widget_refs_for_source_entity(self):
        transform_with_params = [
            {
                "group_by": "taxons",
                "sources": [
                    {
                        "name": "occ",
                        "data": "occurrences",
                        "grouping": "taxons",
                        "relation": {"plugin": "nested_set", "key": "id_taxonref"},
                    }
                ],
                "widgets_data": {
                    "dbh_hist": {
                        "plugin": "binned_distribution",
                        "params": {"source": "occurrences", "field": "dbh"},
                    },
                    "geo": {
                        "plugin": "geospatial_extractor",
                        "params": {"source": "occurrences", "field": "geo_pt"},
                    },
                },
            }
        ]
        refs = self.collector.collect(
            "occurrences", SAMPLE_IMPORT_CONFIG, transform_with_params
        )
        assert "dbh" in refs
        assert any("params.field" in path for path, _ in refs["dbh"])
        assert "geo_pt" in refs
        assert any("params.field" in path for path, _ in refs["geo_pt"])

    def test_collects_time_series_refs_for_source_entity(self):
        transform_cfg = [
            {
                "group_by": "taxons",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "taxons",
                        "relation": {"plugin": "nested_set", "key": "id_taxonref"},
                    }
                ],
                "widgets_data": {
                    "phenology": {
                        "plugin": "time_series_analysis",
                        "params": {
                            "source": "occurrences",
                            "fields": {"flower": "flower", "fruit": "fruit"},
                            "time_field": "month_obs",
                        },
                    }
                },
            }
        ]

        refs = self.collector.collect(
            "occurrences", SAMPLE_IMPORT_CONFIG, transform_cfg
        )

        assert "month_obs" in refs
        assert "flower" in refs
        assert "fruit" in refs
        assert any("params.time_field" in path for path, _ in refs["month_obs"])
        assert any("params.fields.flower" in path for path, _ in refs["flower"])
        assert any("params.fields.fruit" in path for path, _ in refs["fruit"])

    def test_collects_widget_refs_for_grouping_entity_without_source_entry(self):
        transform_cfg = [
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "plots",
                        "relation": {
                            "plugin": "direct_reference",
                            "key": "plot_name",
                            "ref_key": "plot",
                        },
                    }
                ],
                "widgets_data": {
                    "summary": {
                        "plugin": "statistical_summary",
                        "params": {"source": "plots", "field": "biomass"},
                    },
                    "nav": {
                        "plugin": "hierarchical_nav_widget",
                        "params": {
                            "referential_data": "plots",
                            "id_field": "id_plot",
                            "name_field": "plot_label",
                            "parent_id_field": "parent_id",
                        },
                    },
                },
            }
        ]

        refs = self.collector.collect("plots", SAMPLE_IMPORT_CONFIG, transform_cfg)

        assert "biomass" in refs
        assert any("params.field" in path for path, _ in refs["biomass"])
        assert "id_plot" in refs
        assert "plot_label" in refs
        assert "parent_id" in refs
        assert any("params.id_field" in path for path, _ in refs["id_plot"])

    def test_collects_top_ranking_hierarchy_and_join_refs(self):
        transform_cfg = [
            {
                "group_by": "taxons",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "taxons",
                        "relation": {"plugin": "nested_set", "key": "id_taxonref"},
                    }
                ],
                "widgets_data": {
                    "top_taxa": {
                        "plugin": "top_ranking",
                        "params": {
                            "source": "occurrences",
                            "field": "id_taxonref",
                            "mode": "hierarchical",
                            "hierarchy_table": "taxons",
                            "hierarchy_columns": {
                                "id": "taxons_id",
                                "name": "full_name",
                                "rank": "rank_name",
                                "parent_id": "parent_id",
                                "left": "lft",
                                "right": "rght",
                            },
                        },
                    },
                    "joined_taxa": {
                        "plugin": "top_ranking",
                        "params": {
                            "source": "occurrences",
                            "field": "occurrence_id",
                            "mode": "join",
                            "join_table": "taxons",
                            "join_columns": {
                                "source_id": "occurrence_id",
                                "hierarchy_id": "taxons_id",
                            },
                        },
                    },
                },
            }
        ]

        occ_refs = self.collector.collect(
            "occurrences", SAMPLE_IMPORT_CONFIG, transform_cfg
        )
        assert "id_taxonref" in occ_refs
        assert "occurrence_id" in occ_refs
        assert any("params.field" in path for path, _ in occ_refs["id_taxonref"])

        taxon_refs = self.collector.collect(
            "taxons", SAMPLE_IMPORT_CONFIG, transform_cfg
        )
        for column in (
            "taxons_id",
            "full_name",
            "rank_name",
            "parent_id",
            "lft",
            "rght",
        ):
            assert column in taxon_refs
        assert any(
            "params.hierarchy_columns.id" in path for path, _ in taxon_refs["taxons_id"]
        )

    def test_collects_geospatial_secondary_fields(self):
        transform_cfg = [
            {
                "group_by": "taxons",
                "sources": [
                    {
                        "name": "occurrences",
                        "data": "occurrences",
                        "grouping": "taxons",
                        "relation": {"plugin": "nested_set", "key": "id_taxonref"},
                    }
                ],
                "widgets_data": {
                    "map": {
                        "plugin": "geospatial_extractor",
                        "params": {
                            "source": "occurrences",
                            "field": "geo_pt",
                            "properties": ["species", "dbh"],
                            "children_properties": ["family"],
                            "hierarchy_config": {
                                "type_field": "plot_type",
                                "parent_field": "parent_id",
                                "left_field": "lft",
                                "right_field": "rght",
                            },
                        },
                    }
                },
            }
        ]

        refs = self.collector.collect(
            "occurrences", SAMPLE_IMPORT_CONFIG, transform_cfg
        )

        for column in (
            "geo_pt",
            "species",
            "dbh",
            "family",
            "plot_type",
            "parent_id",
            "lft",
            "rght",
        ):
            assert column in refs
        assert any("params.properties[0]" in path for path, _ in refs["species"])
        assert any(
            "params.hierarchy_config.type_field" in path
            for path, _ in refs["plot_type"]
        )

    def test_collects_entity_map_refs_for_grouping_entity(self):
        transform_cfg = [
            {
                "group_by": "plots",
                "sources": [],
                "widgets_data": {
                    "map": {
                        "plugin": "entity_map_extractor",
                        "params": {
                            "entity_table": "entity_plots",
                            "geometry_field": "geo_pt",
                            "name_field": "id_plot",
                            "id_field": "id_plot",
                        },
                    }
                },
            }
        ]

        refs = self.collector.collect("plots", SAMPLE_IMPORT_CONFIG, transform_cfg)

        assert "geo_pt" in refs
        assert "id_plot" in refs
        assert any("params.geometry_field" in path for path, _ in refs["geo_pt"])


# ===================================================================
# TestCSVSchemaReader
# ===================================================================


class TestCSVSchemaReader:
    def test_reads_simple_csv(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("id,name,value\n1,a,1.5\n2,b,2.5\n")
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is None
        assert len(fields) == 3
        names = {f["name"] for f in fields}
        assert names == {"id", "name", "value"}
        types = {f["name"]: f["type"] for f in fields}
        assert types["id"] == "integer"
        assert types["name"] == "string"
        assert types["value"] == "float"

    def test_handles_semicolon_separator(self, tmp_path):
        csv = tmp_path / "euro.csv"
        csv.write_text("id;nom;val\n1;test;3.14\n")
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is None
        assert {f["name"] for f in fields} == {"id", "nom", "val"}

    def test_handles_latin1_encoding(self, tmp_path):
        csv = tmp_path / "latin.csv"
        csv.write_bytes(b"id;nom\n1;\xe9l\xe8ve\n")
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is None
        assert len(fields) == 2

    def test_all_null_sample_column_is_unknown(self, tmp_path):
        csv = tmp_path / "nulls.csv"
        csv.write_text("id,optional\n1,\n2,\n3,\n")
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is None
        types = {f["name"]: f["type"] for f in fields}
        assert types["optional"] == "unknown"

    def test_returns_error_for_empty_file(self, tmp_path):
        csv = tmp_path / "empty.csv"
        csv.write_text("")
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is not None

    def test_returns_error_for_nonexistent_file(self, tmp_path):
        csv = tmp_path / "nonexistent.csv"
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is not None

    def test_header_only_returns_string_types(self, tmp_path):
        csv = tmp_path / "header_only.csv"
        csv.write_text("id,name,value\n")
        fields, err = CSVSchemaReader.read_schema(csv)
        assert err is None
        assert len(fields) == 3
        # With no sampled values at all, the reader keeps the type as unknown.
        for f in fields:
            assert f["type"] == "unknown"


# ===================================================================
# TestEntityResolver
# ===================================================================


class TestEntityResolver:
    def test_matches_dataset_entity(self):
        result = EntityResolver.resolve("occurrences.csv", SAMPLE_IMPORT_CONFIG)
        assert result == "occurrences"

    def test_matches_reference_entity(self):
        result = EntityResolver.resolve("plots.csv", SAMPLE_IMPORT_CONFIG)
        assert result == "plots"

    def test_returns_none_for_unknown_file(self):
        result = EntityResolver.resolve("unknown.csv", SAMPLE_IMPORT_CONFIG)
        assert result is None

    def test_returns_none_for_empty_config(self):
        result = EntityResolver.resolve("test.csv", {})
        assert result is None

    def test_skips_derived_entities(self):
        # taxons is DERIVED — has no path, shouldn't match anything
        result = EntityResolver.resolve("taxons.csv", SAMPLE_IMPORT_CONFIG)
        assert result is None

    def test_returns_none_and_warns_on_duplicate_basename(self, caplog):
        """When multiple entities share the same filename, return None."""
        config = {
            "entities": {
                "datasets": {
                    "occ_v1": {"connector": {"type": "file", "path": "v1/data.csv"}},
                    "occ_v2": {"connector": {"type": "file", "path": "v2/data.csv"}},
                },
                "references": {},
            }
        }
        with caplog.at_level(logging.WARNING):
            result = EntityResolver.resolve("data.csv", config)
        assert result is None
        assert "Ambiguous" in caplog.text

    def test_resolves_transform_only_csv_source(self):
        """CSV sources defined only in transform.yml (not import.yml) should match."""
        transform = [
            {
                "group_by": "plots",
                "sources": [
                    {
                        "name": "plot_stats",
                        "data": "imports/raw_plot_stats.csv",
                        "grouping": "plots",
                        "relation": {"plugin": "stats_loader", "key": "id"},
                    }
                ],
            }
        ]
        result = EntityResolver.resolve(
            "raw_plot_stats.csv", SAMPLE_IMPORT_CONFIG, transform
        )
        assert result == "plot_stats"

    def test_resolves_auxiliary_source_from_import_config(self):
        config = {
            "entities": {"datasets": {}, "references": {}},
            "auxiliary_sources": [
                {
                    "name": "shape_stats",
                    "data": "imports/raw_shape_stats.csv",
                    "grouping": "shapes",
                    "relation": {"plugin": "stats_loader", "key": "id"},
                }
            ],
        }
        result = EntityResolver.resolve("raw_shape_stats.csv", config, [])
        assert result == "shape_stats"

    def test_does_not_match_vector_entity_path(self):
        """VECTOR entities have paths but should be skipped by the resolver."""
        config = {
            "entities": {
                "datasets": {},
                "references": {
                    "geo": {"connector": {"type": "vector", "path": "imports/geo.gpkg"}}
                },
            }
        }
        # VECTOR is not in the skip list of the resolver — it has a path.
        # But check_compatibility will skip it via _get_skip_reason.
        result = EntityResolver.resolve("geo.gpkg", config)
        # The resolver WILL match it — the skip happens in check_compatibility
        assert result == "geo"


# ===================================================================
# TestCompatibilityService
# ===================================================================


class TestCompatibilityService:
    """Test the orchestrator with mocked file reads."""

    def _make_service(self, tmp_path, import_cfg=None, transform_cfg=None):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        imports_dir = tmp_path / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)

        if import_cfg is not None:
            (config_dir / "import.yml").write_text(
                yaml.dump(import_cfg, default_flow_style=False)
            )
        if transform_cfg is not None:
            (config_dir / "transform.yml").write_text(
                yaml.dump(transform_cfg, default_flow_style=False)
            )
        return CompatibilityService(tmp_path)

    def test_no_issues_when_all_columns_present(self, tmp_path):
        csv = tmp_path / "imports" / "occurrences.csv"
        service = self._make_service(
            tmp_path,
            import_cfg={
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {
                                "type": "file",
                                "path": "imports/occurrences.csv",
                            },
                            "schema": {
                                "id_field": "id",
                                "fields": [{"name": "species", "type": "string"}],
                            },
                        }
                    },
                    "references": {},
                }
            },
        )
        pd.DataFrame({"id": [1, 2], "species": ["a", "b"]}).to_csv(csv, index=False)
        report = service.check_compatibility("occurrences", "imports/occurrences.csv")
        assert not report.has_blockers
        assert not report.has_warnings
        assert report.error is None

    def test_detects_missing_column_blocks_import(self, tmp_path):
        csv = tmp_path / "imports" / "occurrences.csv"
        service = self._make_service(
            tmp_path,
            import_cfg={
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {
                                "type": "file",
                                "path": "imports/occurrences.csv",
                            },
                            "schema": {
                                "id_field": "id",
                                "fields": [{"name": "species", "type": "string"}],
                            },
                        }
                    },
                    "references": {},
                }
            },
        )
        # CSV missing "species" column
        pd.DataFrame({"id": [1, 2]}).to_csv(csv, index=False)
        report = service.check_compatibility("occurrences", "imports/occurrences.csv")
        assert report.has_blockers
        missing = [i for i in report.impacts if i.level == ImpactLevel.BLOCKS_IMPORT]
        assert any(i.column == "species" for i in missing)

    def test_detects_missing_column_breaks_transform(self, tmp_path):
        csv = tmp_path / "imports" / "occurrences.csv"
        service = self._make_service(
            tmp_path,
            import_cfg={
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {
                                "type": "file",
                                "path": "imports/occurrences.csv",
                            },
                            "schema": {"id_field": "id", "fields": []},
                        }
                    },
                    "references": {},
                }
            },
            transform_cfg=[
                {
                    "group_by": "taxons",
                    "sources": [
                        {
                            "name": "occ",
                            "data": "occurrences",
                            "grouping": "taxons",
                            "relation": {
                                "plugin": "nested_set",
                                "key": "id_taxonref",
                            },
                        }
                    ],
                }
            ],
        )
        # CSV missing id_taxonref
        pd.DataFrame({"id": [1]}).to_csv(csv, index=False)
        report = service.check_compatibility("occurrences", "imports/occurrences.csv")
        breaking = [
            i for i in report.impacts if i.level == ImpactLevel.BREAKS_TRANSFORM
        ]
        assert any(i.column == "id_taxonref" for i in breaking)

    def test_detects_new_columns_as_opportunity(self, tmp_path):
        csv = tmp_path / "imports" / "occurrences.csv"
        service = self._make_service(
            tmp_path,
            import_cfg={
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {
                                "type": "file",
                                "path": "imports/occurrences.csv",
                            },
                            "schema": {"id_field": "id", "fields": []},
                        }
                    },
                    "references": {},
                }
            },
        )
        pd.DataFrame({"id": [1], "brand_new_col": ["x"]}).to_csv(csv, index=False)
        report = service.check_compatibility("occurrences", "imports/occurrences.csv")
        opportunities = [
            i for i in report.impacts if i.level == ImpactLevel.OPPORTUNITY
        ]
        assert any(i.column == "brand_new_col" for i in opportunities)

    def test_ignores_unknown_sample_type_warning(self, tmp_path):
        service = self._make_service(tmp_path)
        report = service._compare(
            entity_name="occurrences",
            file_path="imports/occurrences.csv",
            new_schema={"plot_name": "unknown"},
            old_schema={"plot_name": "string"},
            config_refs={
                "plot_name": [
                    (
                        "transform.yml > group plots > source occurrences > relation.key",
                        ImpactLevel.BREAKS_TRANSFORM,
                    )
                ]
            },
            target_kind=TargetKind.IMPORT_ENTITY,
        )
        assert report.matched_columns[0].new_type == "unknown"
        assert not report.has_warnings

    def test_returns_error_for_unreadable_file(self, tmp_path):
        service = self._make_service(
            tmp_path,
            import_cfg={
                "entities": {
                    "datasets": {
                        "occurrences": {
                            "connector": {
                                "type": "file",
                                "path": "imports/occurrences.csv",
                            },
                            "schema": {"id_field": "id", "fields": []},
                        }
                    },
                    "references": {},
                }
            },
        )
        # File does not exist
        report = service.check_compatibility("occurrences", "imports/occurrences.csv")
        assert report.error is not None

    def test_loads_registry_schema_from_configured_duckdb_path(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        db_dir = tmp_path / "db"
        db_dir.mkdir(parents=True, exist_ok=True)

        (config_dir / "config.yml").write_text(
            yaml.dump({"database": {"path": "db/niamoto.duckdb"}})
        )

        db_path = db_dir / "niamoto.duckdb"
        db = Database(str(db_path), read_only=False)
        registry = EntityRegistry(db)
        registry.register_entity(
            name="occurrences",
            kind=EntityKind.DATASET,
            table_name="dataset_occurrences",
            config={
                "schema": {
                    "id_field": "id",
                    "fields": [
                        {"name": "id", "type": "integer"},
                        {"name": "species", "type": "string"},
                    ],
                }
            },
        )
        db.close_db_session()
        db.engine.dispose()

        service = CompatibilityService(tmp_path)
        schema = service._load_registry_schema("occurrences")
        assert schema == {"id": "integer", "species": "string"}

    def test_returns_empty_when_no_config(self, tmp_path):
        (tmp_path / "imports").mkdir(parents=True)
        csv = tmp_path / "imports" / "test.csv"
        pd.DataFrame({"a": [1]}).to_csv(csv, index=False)
        service = CompatibilityService(tmp_path)
        report = service.check_compatibility("test", "imports/test.csv")
        # No config → no refs → no blockers
        assert not report.has_blockers

    def test_rejects_path_outside_project(self, tmp_path):
        service = self._make_service(
            tmp_path,
            import_cfg={
                "entities": {
                    "datasets": {
                        "x": {
                            "connector": {"type": "file", "path": "imports/x.csv"},
                            "schema": {"id_field": "id", "fields": []},
                        }
                    },
                    "references": {},
                }
            },
        )
        report = service.check_compatibility("x", "../../../tmp/evil.csv")
        assert report.error is not None
        assert "outside" in report.error.lower()

    def test_check_all_skips_derived(self, tmp_path):
        service = self._make_service(tmp_path, import_cfg=SAMPLE_IMPORT_CONFIG)
        # Create CSV for file-based entities so they don't error
        imports = tmp_path / "imports"
        imports.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "id": [1],
                "species": ["a"],
                "dbh": [1.0],
                "id_taxonref": [1],
                "plot_name": ["p1"],
            }
        ).to_csv(imports / "occurrences.csv", index=False)
        pd.DataFrame({"id_plot": [1], "geo_pt": ["POINT(0 0)"]}).to_csv(
            imports / "plots.csv", index=False
        )
        reports = service.check_all()
        taxon_report = next(r for r in reports if r.entity_name == "taxons")
        assert taxon_report.skipped_reason is not None
        assert "Derived" in taxon_report.skipped_reason

    def test_check_all_skips_multi_feature(self, tmp_path):
        cfg = {
            "entities": {
                "datasets": {
                    "occ": {
                        "connector": {"type": "file", "path": "imports/occ.csv"},
                        "schema": {"id_field": "id", "fields": []},
                    }
                },
                "references": {
                    "shapes": {
                        "connector": {
                            "type": "file_multi_feature",
                            "sources": [
                                {
                                    "name": "Provinces",
                                    "path": "imports/prov.gpkg",
                                    "name_field": "nom",
                                }
                            ],
                        },
                        "schema": {"fields": []},
                    }
                },
            }
        }
        service = self._make_service(tmp_path, import_cfg=cfg)
        imports = tmp_path / "imports"
        imports.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"id": [1]}).to_csv(imports / "occ.csv", index=False)
        reports = service.check_all()
        shapes_report = next(r for r in reports if r.entity_name == "shapes")
        assert shapes_report.skipped_reason is not None
        assert "V1" in shapes_report.skipped_reason

    def test_check_compatibility_skips_vector_entity(self, tmp_path):
        """check_compatibility must return skip for VECTOR entities (P2-B fix)."""
        cfg = {
            "entities": {
                "datasets": {},
                "references": {
                    "geo": {
                        "connector": {"type": "vector", "path": "imports/geo.gpkg"},
                        "schema": {"fields": []},
                    }
                },
            }
        }
        service = self._make_service(tmp_path, import_cfg=cfg)
        (tmp_path / "imports").mkdir(parents=True, exist_ok=True)
        (tmp_path / "imports" / "geo.gpkg").write_bytes(b"fake")
        report = service.check_compatibility("geo", "imports/geo.gpkg")
        assert report.skipped_reason is not None
        assert "V1" in report.skipped_reason

    def test_check_all_includes_transform_sources(self, tmp_path):
        service = self._make_service(
            tmp_path,
            import_cfg={"entities": {"datasets": {}, "references": {}}},
            transform_cfg=[
                {
                    "group_by": "plots",
                    "sources": [
                        {
                            "name": "plot_stats",
                            "data": "imports/raw_plot_stats.csv",
                            "grouping": "plots",
                            "relation": {"plugin": "stats_loader", "key": "id"},
                        }
                    ],
                }
            ],
        )
        csv = tmp_path / "imports" / "raw_plot_stats.csv"
        pd.DataFrame({"id": [1]}).to_csv(csv, index=False)

        reports = service.check_all()
        assert any(report.entity_name == "plot_stats" for report in reports)

    def test_transform_source_missing_required_field_breaks_transform(self, tmp_path):
        service = self._make_service(
            tmp_path,
            import_cfg={"entities": {"datasets": {}, "references": {}}},
            transform_cfg=[
                {
                    "group_by": "plots",
                    "sources": [
                        {
                            "name": "plot_stats",
                            "data": "imports/raw_plot_stats.csv",
                            "grouping": "plots",
                            "relation": {
                                "plugin": "stats_loader",
                                "key": "id",
                                "match_field": "plot_id",
                            },
                        }
                    ],
                    "widgets_data": {
                        "plot_area": {
                            "plugin": "direct_attribute",
                            "params": {"source": "plot_stats", "field": "area_ha"},
                        }
                    },
                }
            ],
        )
        csv = tmp_path / "imports" / "raw_plot_stats.csv"
        pd.DataFrame({"id": [1]}).to_csv(csv, index=False)

        report = service.check_compatibility("plot_stats", "imports/raw_plot_stats.csv")
        breaking = [
            i for i in report.impacts if i.level == ImpactLevel.BREAKS_TRANSFORM
        ]
        assert {item.column for item in breaking} == {"area_ha", "plot_id"}

    def test_transform_source_without_baseline_suppresses_opportunities(self, tmp_path):
        service = self._make_service(
            tmp_path,
            import_cfg={"entities": {"datasets": {}, "references": {}}},
            transform_cfg=[
                {
                    "group_by": "plots",
                    "sources": [
                        {
                            "name": "plot_stats",
                            "data": "imports/raw_plot_stats.csv",
                            "grouping": "plots",
                            "relation": {"plugin": "stats_loader", "key": "id"},
                        }
                    ],
                }
            ],
        )
        csv = tmp_path / "imports" / "raw_plot_stats.csv"
        pd.DataFrame({"id": [1], "new_metric": [42]}).to_csv(csv, index=False)

        report = service.check_compatibility("plot_stats", "imports/raw_plot_stats.csv")
        assert not any(i.level == ImpactLevel.OPPORTUNITY for i in report.impacts)
        assert report.info_message is not None
        assert "First check" in report.info_message

    def test_transform_source_class_object_series_requires_class_name(self, tmp_path):
        service = self._make_service(
            tmp_path,
            import_cfg={"entities": {"datasets": {}, "references": {}}},
            transform_cfg=[
                {
                    "group_by": "plots",
                    "sources": [
                        {
                            "name": "plot_stats",
                            "data": "imports/raw_plot_stats.csv",
                            "grouping": "plots",
                            "relation": {"plugin": "stats_loader", "key": "id"},
                        }
                    ],
                    "widgets_data": {
                        "fragmentation_distribution": {
                            "plugin": "class_object_series_extractor",
                            "params": {
                                "source": "plot_stats",
                                "class_object": "forest_fragmentation",
                                "size_field": {
                                    "input": "class_name",
                                    "output": "sizes",
                                },
                                "value_field": {
                                    "input": "class_value",
                                    "output": "values",
                                },
                            },
                        }
                    },
                }
            ],
        )
        csv = tmp_path / "imports" / "raw_plot_stats.csv"
        pd.DataFrame({"id": [1], "class_object": ["x"], "class_value": [0.5]}).to_csv(
            csv, index=False
        )

        report = service.check_compatibility("plot_stats", "imports/raw_plot_stats.csv")

        breaking = [
            i for i in report.impacts if i.level == ImpactLevel.BREAKS_TRANSFORM
        ]
        assert {item.column for item in breaking} == {"class_name"}

    def test_transform_source_class_object_field_aggregator_requires_class_object(
        self, tmp_path
    ):
        service = self._make_service(
            tmp_path,
            import_cfg={"entities": {"datasets": {}, "references": {}}},
            transform_cfg=[
                {
                    "group_by": "shapes",
                    "sources": [
                        {
                            "name": "shape_stats",
                            "data": "imports/raw_shape_stats.csv",
                            "grouping": "shapes",
                            "relation": {"plugin": "stats_loader", "key": "id"},
                        }
                    ],
                    "widgets_data": {
                        "general_info": {
                            "plugin": "class_object_field_aggregator",
                            "params": {
                                "source": "shape_stats",
                                "fields": [
                                    {
                                        "class_object": "land_area_ha",
                                        "target": "land_area_ha",
                                    }
                                ],
                            },
                        }
                    },
                }
            ],
        )
        csv = tmp_path / "imports" / "raw_shape_stats.csv"
        pd.DataFrame({"id": [1], "class_value": [0.5]}).to_csv(csv, index=False)

        report = service.check_compatibility(
            "shape_stats", "imports/raw_shape_stats.csv"
        )

        breaking = [
            i for i in report.impacts if i.level == ImpactLevel.BREAKS_TRANSFORM
        ]
        assert {item.column for item in breaking} == {"class_object"}

    def test_missing_transform_source_registry_table_is_quiet(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        db_dir = tmp_path / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.yml").write_text(
            yaml.dump({"database": {"path": "db/niamoto.duckdb"}})
        )

        db_path = db_dir / "niamoto.duckdb"
        db = Database(str(db_path), read_only=False)
        db.close_db_session()
        db.engine.dispose()

        service = CompatibilityService(tmp_path)
        schema = service._load_transform_source_schema("plot_stats")
        assert schema == {}

    def test_loads_transform_source_schema_from_registry(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        db_dir = tmp_path / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.yml").write_text(
            yaml.dump({"database": {"path": "db/niamoto.duckdb"}})
        )

        db_path = db_dir / "niamoto.duckdb"
        db = Database(str(db_path), read_only=False)
        registry = TransformSourceRegistry(db)
        registry.register_source(
            name="plot_stats",
            path="imports/raw_plot_stats.csv",
            grouping="plots",
            config={
                "schema": {
                    "fields": [
                        {"name": "id", "type": "integer"},
                        {"name": "plot_id", "type": "string"},
                    ]
                }
            },
        )
        db.close_db_session()
        db.engine.dispose()

        service = CompatibilityService(tmp_path)
        schema = service._load_transform_source_schema("plot_stats")
        assert schema == {"id": "integer", "plot_id": "string"}
