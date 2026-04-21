"""Tests for extra_data schema extraction from config router helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import duckdb
import json
import pandas as pd
import yaml
from fastapi.testclient import TestClient

from niamoto.gui.api.routers import config as config_router
from niamoto.gui.api.routers.config import (
    _analyze_dataframe_fields,
    _extract_extra_data_fields,
)
from niamoto.gui.api.app import create_app


def test_extract_extra_data_fields_handles_namespaced_enrichment_sources():
    """Nested multi-source enrichment payloads should be exposed as dotted fields."""

    df = pd.DataFrame(
        {
            "extra_data": [
                {
                    "api_enrichment": {
                        "sources": {
                            "endemia": {
                                "data": {
                                    "api_id": 42,
                                    "rank_name": "species",
                                },
                                "status": "completed",
                            },
                            "gbif": {
                                "data": {
                                    "usage_key": 987654,
                                },
                            },
                        }
                    },
                    "reviewed_by": "botanist",
                }
            ]
        }
    )

    schema = _extract_extra_data_fields(df)

    assert "extra_data.api_enrichment.sources.endemia.data.api_id" in schema
    assert "extra_data.api_enrichment.sources.endemia.data.rank_name" in schema
    assert "extra_data.api_enrichment.sources.endemia.status" in schema
    assert "extra_data.api_enrichment.sources.gbif.data.usage_key" in schema
    assert "extra_data.reviewed_by" in schema


def test_extract_extra_data_fields_keeps_legacy_flat_enrichment_paths():
    """Legacy single-source payloads should still be detected."""

    df = pd.DataFrame(
        {
            "extra_data": [
                {
                    "api_enrichment": {
                        "api_id": 21,
                        "rank_name": "species",
                    },
                    "enriched_at": "2026-04-09T11:00:00",
                }
            ]
        }
    )

    schema = _extract_extra_data_fields(df)

    assert "extra_data.api_enrichment.api_id" in schema
    assert "extra_data.api_enrichment.rank_name" in schema
    assert "extra_data.enriched_at" in schema


def test_analyze_dataframe_fields_expands_dict_paths_even_when_first_value_is_not_a_dict():
    df = pd.DataFrame(
        {
            "mixed_json": [
                '["ignored"]',
                '{"nested":{"label":"Abebaia"}}',
                '{"nested":{"label":"Pycnandra"}}',
            ]
        }
    )

    schema = _analyze_dataframe_fields(df)

    assert "mixed_json.nested.label" in schema
    assert schema["mixed_json.nested.label"]["sample_values"] == [
        "Abebaia",
        "Pycnandra",
    ]


def test_update_index_generator_accepts_localized_strings(tmp_path: Path):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "export.yml").write_text(
        yaml.safe_dump(
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "enabled": True,
                        "exporter": "html_page_exporter",
                        "params": {},
                        "groups": [
                            {
                                "group_by": "taxons",
                                "widgets": [],
                                "index_generator": {
                                    "enabled": True,
                                    "template": "_group_index.html",
                                    "page_config": {"title": "Taxons"},
                                    "filters": [],
                                    "display_fields": [],
                                    "views": [{"type": "grid", "default": True}],
                                },
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = {
        "enabled": True,
        "template": "_group_index.html",
        "page_config": {
            "title": {"fr": "Liste des taxons", "en": "Taxa list"},
            "description": {"fr": "Description FR", "en": "Description EN"},
            "items_per_page": 24,
        },
        "filters": [],
        "display_fields": [
            {
                "name": "family",
                "source": "hierarchy_context.family.name",
                "type": "text",
                "label": {"fr": "Famille", "en": "Family"},
                "searchable": False,
                "display": "normal",
            },
            {
                "name": "endemic",
                "source": "extra_data.api_enrichment.sources.provider.data.endemic",
                "type": "boolean",
                "label": {"fr": "Endémique", "en": "Endemic"},
                "true_label": {"fr": "Oui", "en": "Yes"},
                "false_label": {"fr": "Non", "en": "No"},
                "display": "normal",
            },
            {
                "name": "endemia",
                "source": "extra_data.api_enrichment.sources.provider.data.endemia_url",
                "type": "text",
                "display": "link",
                "link_label": {"fr": "Endemia", "en": "Endemia"},
                "link_title": {
                    "fr": "Voir sur Endemia",
                    "en": "View on Endemia",
                },
            },
        ],
        "views": [{"type": "grid", "default": True}],
    }

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.put("/api/config/export/taxons/index-generator", json=payload)

    assert response.status_code == 200, response.text
    assert response.json()["page_config"]["title"]["en"] == "Taxa list"
    assert response.json()["display_fields"][1]["true_label"]["fr"] == "Oui"
    assert response.json()["display_fields"][2]["link_title"]["en"] == "View on Endemia"

    saved = yaml.safe_load((config_dir / "export.yml").read_text(encoding="utf-8"))
    saved_group = saved["exports"][0]["groups"][0]["index_generator"]
    assert saved_group["page_config"]["title"]["fr"] == "Liste des taxons"
    assert saved_group["display_fields"][0]["label"]["en"] == "Family"
    assert saved_group["display_fields"][2]["link_label"]["fr"] == "Endemia"


def test_index_suggestions_merge_transformed_fields_with_reference_extra_data(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "transformers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES
                (1, '{"rank":{"value":"family"},"name":{"value":"Araucariaceae"}}'),
                (2, '{"rank":{"value":"genus"},"name":{"value":"Araucaria"}}'),
                (3, '{"rank":{"value":"species"},"name":{"value":"Araucaria columnaris"}}'),
                (4, '{"rank":{"value":"subspecies"},"name":{"value":"Araucaria humboldtensis"}}')
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                level BIGINT,
                parent_id BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (
                    10,
                    1,
                    'Araucariaceae',
                    1,
                    NULL,
                    1,
                    8,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","data":{"endemic":false,"image_small_thumb":"https://img.example/small-1.jpg","image_big_thumb":"https://img.example/big-1.jpg"}}}}}'
                ),
                (
                    20,
                    2,
                    'Araucaria',
                    2,
                    10,
                    2,
                    7,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","data":{"endemic":false,"image_small_thumb":"https://img.example/small-2.jpg","image_big_thumb":"https://img.example/big-2.jpg"}}}}}'
                ),
                (
                    30,
                    3,
                    'Araucaria columnaris',
                    3,
                    20,
                    3,
                    4,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","data":{"endemic":true,"image_small_thumb":"https://img.example/small-3.jpg","image_big_thumb":"https://img.example/big-3.jpg"}}}}}'
                ),
                (
                    40,
                    4,
                    'Araucaria humboldtensis',
                    3,
                    20,
                    5,
                    6,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","data":{"endemic":true,"image_small_thumb":"https://img.example/small-4.jpg","image_big_thumb":"https://img.example/big-4.jpg"}}}}}'
                )
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    display_field_sources = {field["source"] for field in payload["display_fields"]}
    assert "general_info.rank.value" in display_field_sources
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.label"
        not in display_field_sources
    )
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.data.image_small_thumb"
        not in display_field_sources
    )
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.data.image_big_thumb"
        not in display_field_sources
    )

    image_field = next(
        field
        for field in payload["display_fields"]
        if field["display"] == "image_preview"
    )
    assert (
        image_field["source"] == "extra_data.api_enrichment.sources.api-endemia-nc.data"
    )
    assert image_field["image_fields"] == {
        "thumbnail": "image_small_thumb",
        "full": "image_big_thumb",
        "url": "image_big_thumb",
    }

    rank_filter = next(
        flt for flt in payload["filters"] if flt["source"] == "general_info.rank.value"
    )
    assert "species" in rank_filter["values"]
    assert "subspecies" in rank_filter["values"]
    assert "family" not in rank_filter["values"]
    assert "genus" not in rank_filter["values"]


def test_index_suggestions_use_terminal_taxa_and_skip_metadata_fields(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "transformers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                level BIGINT,
                parent_id BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )

        taxon_rows = []
        entity_rows = []

        for idx in range(1, 101):
            rank = "family" if idx <= 50 else "genus"
            parent_family = f"Family {idx}" if rank == "genus" else None
            parent_genus = None
            general_info = {
                "rank": {"value": rank},
                "name": {"value": f"Taxon {idx}"},
            }
            if parent_family:
                general_info["parent_family"] = {"value": parent_family}
            if parent_genus:
                general_info["parent_genus"] = {"value": parent_genus}

            taxon_rows.append((idx, json.dumps(general_info)))
            entity_rows.append(
                (
                    idx,
                    idx,
                    f"Taxon {idx}",
                    1 if rank == "family" else 2,
                    None,
                    idx * 2,
                    idx * 2 + 1,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","enriched_at":"2026-04-14T10:00:00","updated_at":"2026-04-14T11:00:00","data":{"endemic":false}}}}}',
                )
            )

        for idx in range(101, 121):
            rank = "species" if idx <= 110 else "infra"
            general_info = {
                "rank": {"value": rank},
                "name": {"value": f"Taxon {idx}"},
            }
            taxon_rows.append((idx, json.dumps(general_info)))
            entity_rows.append(
                (
                    idx,
                    idx,
                    f"Taxon {idx}",
                    3,
                    idx - 1,
                    idx * 2,
                    idx * 2 + 1,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","enriched_at":"2026-04-14T10:00:00","updated_at":"2026-04-14T11:00:00","data":{"endemic":true}}}}}',
                )
            )

        conn.executemany("INSERT INTO taxons VALUES (?, ?)", taxon_rows)
        conn.executemany(
            "INSERT INTO entity_taxons VALUES (?, ?, ?, ?, ?, ?, ?, ?)", entity_rows
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    display_field_sources = {field["source"] for field in payload["display_fields"]}

    rank_filter = next(
        flt for flt in payload["filters"] if flt["source"] == "general_info.rank.value"
    )
    assert rank_filter["values"] == ["species", "infra"]

    assert "general_info.parent_family.value" not in display_field_sources
    assert "general_info.parent_genus.value" not in display_field_sources
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.enriched_at"
        not in display_field_sources
    )
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.updated_at"
        not in display_field_sources
    )


def test_index_suggestions_skip_low_value_widget_outputs_on_transformed_tables(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "widgets_data": {
                        "general_info": {
                            "plugin": "field_aggregator",
                            "params": {
                                "fields": [
                                    {
                                        "source": "taxons",
                                        "field": "full_name",
                                        "target": "name",
                                    },
                                    {
                                        "source": "taxons",
                                        "field": "rank_name",
                                        "target": "rank",
                                    },
                                    {
                                        "source": "occurrences",
                                        "field": "id",
                                        "target": "occurrences_count",
                                        "transformation": "count",
                                    },
                                ]
                            },
                        },
                        "distribution_map": {
                            "plugin": "geospatial_extractor",
                            "params": {},
                        },
                        "distribution_substrat": {
                            "plugin": "binary_counter",
                            "params": {},
                        },
                        "dbh_max": {
                            "plugin": "statistical_summary",
                            "params": {
                                "field": "dbh",
                                "stats": ["max"],
                            },
                        },
                        "wood_density": {
                            "plugin": "statistical_summary",
                            "params": {
                                "field": "wood_density",
                                "stats": ["mean"],
                            },
                        },
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON,
                distribution_map JSON,
                distribution_substrat JSON,
                dbh_max JSON,
                wood_density JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES
                (
                    1,
                    '{"name":{"value":"Araucaria columnaris"},"rank":{"value":"species"},"occurrences_count":{"value":43}}',
                    '{"type":"FeatureCollection"}',
                    '{"um":10,"num":5,"um_percent":66.6,"num_percent":33.4}',
                    '{"max":42,"units":"cm","max_value":500}',
                    '{"mean":0.71}'
                ),
                (
                    2,
                    '{"name":{"value":"Niaouli alba"},"rank":{"value":"infra"},"occurrences_count":{"value":12}}',
                    '{"type":"FeatureCollection"}',
                    '{"um":8,"num":4,"um_percent":66.6,"num_percent":33.4}',
                    '{"max":31,"units":"cm","max_value":500}',
                    '{"mean":0.63}'
                )
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                rank_name VARCHAR,
                level BIGINT,
                parent_id BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (
                    1,
                    1,
                    'Araucaria columnaris',
                    'species',
                    3,
                    NULL,
                    1,
                    2,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","status":"completed","data":{"endemic":true,"image_small_thumb":"https://img.example/small-1.jpg","image_big_thumb":"https://img.example/big-1.jpg"}}}}}'
                ),
                (
                    2,
                    2,
                    'Niaouli alba',
                    'infra',
                    3,
                    NULL,
                    3,
                    4,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","status":"completed","data":{"endemic":false,"image_small_thumb":"https://img.example/small-2.jpg","image_big_thumb":"https://img.example/big-2.jpg"}}}}}'
                )
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    display_field_sources = {field["source"] for field in payload["display_fields"]}
    name_field = next(
        field
        for field in payload["display_fields"]
        if field["source"] == "general_info.name.value"
    )

    assert "general_info.name.value" in display_field_sources
    assert "general_info.rank.value" in display_field_sources
    assert "general_info.occurrences_count.value" in display_field_sources
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.data" in display_field_sources
    )
    assert name_field["fallback"] == "full_name"

    assert "distribution_map.type" not in display_field_sources
    assert "distribution_substrat.um" not in display_field_sources
    assert "distribution_substrat.num" not in display_field_sources
    assert "dbh_max.units" not in display_field_sources
    assert "dbh_max.max" not in display_field_sources
    assert "wood_density.mean" not in display_field_sources
    assert "taxons_id" not in display_field_sources
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.label"
        not in display_field_sources
    )
    assert (
        "extra_data.api_enrichment.sources.api-endemia-nc.status"
        not in display_field_sources
    )


def test_index_suggestions_promote_external_links_and_inline_badges(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "transformers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES
                (1, '{"rank":{"value":"species"},"name":{"value":"Araucaria columnaris"}}'),
                (2, '{"rank":{"value":"infra"},"name":{"value":"Niaouli alba"}}')
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                level BIGINT,
                parent_id BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (
                    1,
                    1,
                    'Araucaria columnaris',
                    3,
                    NULL,
                    1,
                    2,
                    '{"api_enrichment":{"sources":{"gbif":{"data":{"url":"https://gbif.org/species/1","native":true,"monitored":false}},"api-endemia-nc":{"data":{"endemic":true}}}}}'
                ),
                (
                    2,
                    2,
                    'Niaouli alba',
                    3,
                    NULL,
                    3,
                    4,
                    '{"api_enrichment":{"sources":{"gbif":{"data":{"url":"https://gbif.org/species/2","native":false,"monitored":true}},"api-endemia-nc":{"data":{"endemic":false}}}}}'
                )
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    gbif_link = next(
        field
        for field in payload["display_fields"]
        if field["source"] == "extra_data.api_enrichment.sources.gbif.data.url"
    )
    assert gbif_link["display"] == "link"
    assert gbif_link["link_label"] == "GBIF"
    assert gbif_link["link_title"] == "Voir sur GBIF"
    assert gbif_link["link_target"] == "_blank"

    endemic_badge = next(
        field
        for field in payload["display_fields"]
        if field["source"]
        == "extra_data.api_enrichment.sources.api-endemia-nc.data.endemic"
    )
    assert endemic_badge["format"] == "badge"
    assert endemic_badge["inline_badge"] is True

    monitored_field = next(
        field
        for field in payload["display_fields"]
        if field["source"] == "extra_data.api_enrichment.sources.gbif.data.monitored"
    )
    assert monitored_field["format"] == "badge"
    assert monitored_field["inline_badge"] is False


def test_index_suggestions_promote_provider_specific_url_suffixes_to_links(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "transformers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES
                (1, '{"rank":{"value":"species"},"name":{"value":"Araucaria columnaris"}}'),
                (2, '{"rank":{"value":"infra"},"name":{"value":"Niaouli alba"}}')
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                level BIGINT,
                parent_id BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (
                    1,
                    1,
                    'Araucaria columnaris',
                    3,
                    NULL,
                    1,
                    2,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"data":{"endemia_url":"https://endemia.nc/flore/fiche1"}}}}}'
                ),
                (
                    2,
                    2,
                    'Niaouli alba',
                    3,
                    NULL,
                    3,
                    4,
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"data":{"endemia_url":"https://endemia.nc/flore/fiche2"}}}}}'
                )
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    endemia_link = next(
        field
        for field in payload["display_fields"]
        if field["source"]
        == "extra_data.api_enrichment.sources.api-endemia-nc.data.endemia_url"
    )
    assert endemia_link["name"] == "endemia"
    assert endemia_link["label"] == "Endemia"
    assert endemia_link["display"] == "link"
    assert endemia_link["link_label"] == "Endemia"
    assert endemia_link["link_title"] == "Voir sur Endemia"
    assert endemia_link["link_target"] == "_blank"


def test_index_suggestions_fallback_to_reference_fields_without_transformed_table(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "widgets_data": {},
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                rank_name VARCHAR,
                parent_id BIGINT,
                level BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (1, 11, 'Sapotaceae', 'family', NULL, 1, 1, 6, '{}'),
                (2, 22, 'Abebaia', 'genus', 1, 2, 2, 5, '{}'),
                (3, 101, 'Abebaia dissecta', 'species', 2, 3, 3, 4, '{"api_enrichment":{"sources":{"api-endemia-nc":{"data":{"endemic":true}}}}}'),
                (4, 44, 'Pycnandra', 'genus', 1, 2, 7, 12, '{}'),
                (5, 202, 'Pycnandra minor', 'infra', 4, 3, 8, 11, '{"api_enrichment":{"sources":{"api-endemia-nc":{"data":{"endemic":false}}}}}')
            """
        )
    finally:
        conn.close()

    with (
        patch(
            "niamoto.gui.api.routers.config.get_working_directory",
            return_value=project_dir,
        ),
        patch(
            "niamoto.gui.api.routers.config._load_table_records",
            wraps=config_router._load_table_records,
        ) as load_table_records,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    display_field_sources = {field["source"] for field in payload["display_fields"]}

    assert "full_name" in display_field_sources
    assert "rank_name" in display_field_sources
    assert "hierarchy_context.family.name" in display_field_sources
    assert "hierarchy_context.genus.name" in display_field_sources
    assert "level" not in display_field_sources
    assert "lft" not in display_field_sources
    assert "rght" not in display_field_sources

    rank_filter = next(
        flt for flt in payload["filters"] if flt["source"] == "rank_name"
    )
    assert rank_filter["values"] == ["species", "infra"]

    entity_taxons_calls = [
        call
        for call in load_table_records.call_args_list
        if call.args[1] == "entity_taxons"
    ]
    assert entity_taxons_calls

    loaded_column_sets = [set(call.kwargs["columns"]) for call in entity_taxons_calls]
    assert {"rank_name", "taxons_id", "id"} in loaded_column_sets
    assert {
        "id",
        "taxons_id",
        "full_name",
        "rank_name",
        "parent_id",
        "lft",
        "rght",
    } in loaded_column_sets
    assert all("extra_data" not in columns for columns in loaded_column_sets)
    assert all("level" not in columns for columns in loaded_column_sets)


def test_index_suggestions_infer_future_paths_before_first_transform_run(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "widgets_data": {
                        "general_info": {
                            "plugin": "field_aggregator",
                            "params": {
                                "fields": [
                                    {
                                        "source": "taxons",
                                        "field": "full_name",
                                        "target": "name",
                                    },
                                    {
                                        "source": "taxons",
                                        "field": "rank_name",
                                        "target": "rank",
                                    },
                                ]
                            },
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                rank_name VARCHAR,
                parent_id BIGINT,
                level BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (1, 11, 'Sapotaceae', 'family', NULL, 1, 1, 6, '{}'),
                (2, 22, 'Abebaia', 'genus', 1, 2, 2, 5, '{}'),
                (3, 101, 'Abebaia dissecta', 'species', 2, 3, 3, 4, '{}'),
                (4, 44, 'Pycnandra', 'genus', 1, 2, 7, 12, '{}'),
                (5, 202, 'Pycnandra minor', 'infra', 4, 3, 8, 11, '{}')
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    display_field_sources = {field["source"] for field in payload["display_fields"]}

    assert "general_info.name.value" in display_field_sources
    assert "general_info.rank.value" in display_field_sources
    assert "full_name" not in display_field_sources
    assert "rank_name" not in display_field_sources
    assert "hierarchy_context.family.name" in display_field_sources
    assert "hierarchy_context.genus.name" in display_field_sources

    rank_filter = next(
        flt for flt in payload["filters"] if flt["source"] == "general_info.rank.value"
    )
    assert rank_filter["values"] == ["species", "infra"]


def test_index_suggestions_recover_hierarchy_ancestors_from_reference_table(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "transformers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO taxons VALUES
                (101, '{"rank":{"value":"species"},"name":{"value":"Abebaia dissecta"}}'),
                (202, '{"rank":{"value":"infra"},"name":{"value":"Pycnandra minor"}}')
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                rank_name VARCHAR,
                parent_id BIGINT,
                level BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (1, 11, 'Sapotaceae', 'family', NULL, 1, 1, 6, '{}'),
                (2, 22, 'Abebaia', 'genus', 1, 2, 2, 5, '{}'),
                (3, 101, 'Abebaia dissecta', 'species', 2, 3, 3, 4, '{}'),
                (4, 44, 'Sapotaceae', 'family', NULL, 1, 7, 14, '{}'),
                (5, 55, 'Pycnandra', 'genus', 4, 2, 8, 13, '{}'),
                (6, 66, 'Pycnandra comptonii', 'species', 5, 3, 9, 12, '{}'),
                (7, 202, 'Pycnandra minor', 'infra', 6, 4, 10, 11, '{}')
            """
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    family_field = next(
        field
        for field in payload["display_fields"]
        if field["source"] == "hierarchy_context.family.name"
    )
    genus_field = next(
        field
        for field in payload["display_fields"]
        if field["source"] == "hierarchy_context.genus.name"
    )

    assert family_field["label"] == "Family"
    assert genus_field["label"] == "Genus"
    assert family_field["type"] == "text"
    assert genus_field["type"] == "select"


def test_index_suggestions_keep_hierarchy_ancestors_with_high_cardinality(
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    config_dir = project_dir / "config"
    db_dir = project_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "config.yml").write_text(
        yaml.safe_dump({"database": {"path": "db/niamoto.duckdb"}}),
        encoding="utf-8",
    )
    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "taxons",
                    "source": "taxons",
                    "transformers": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    db_path = db_dir / "niamoto.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE taxons (
                taxons_id BIGINT,
                general_info JSON
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                rank_name VARCHAR,
                parent_id BIGINT,
                level BIGINT,
                lft BIGINT,
                rght BIGINT,
                extra_data JSON
            )
            """
        )

        taxon_rows = []
        entity_rows = []
        next_entity_id = 1
        next_taxons_ref = 1000

        for idx in range(1, 61):
            family_id = next_entity_id
            next_entity_id += 1
            genus_id = next_entity_id
            next_entity_id += 1
            species_id = next_entity_id
            next_entity_id += 1

            family_taxons_id = next_taxons_ref
            genus_taxons_id = next_taxons_ref + 1
            species_taxons_id = next_taxons_ref + 2
            next_taxons_ref += 3

            family_name = f"Family {idx}"
            genus_name = f"Genus {idx}"
            species_name = f"Species {idx}"

            taxon_rows.append(
                (
                    species_taxons_id,
                    json.dumps(
                        {
                            "rank": {"value": "species"},
                            "name": {"value": species_name},
                        }
                    ),
                )
            )

            entity_rows.extend(
                [
                    (
                        family_id,
                        family_taxons_id,
                        family_name,
                        "family",
                        None,
                        1,
                        idx * 10,
                        idx * 10 + 5,
                        "{}",
                    ),
                    (
                        genus_id,
                        genus_taxons_id,
                        genus_name,
                        "genus",
                        family_id,
                        2,
                        idx * 10 + 1,
                        idx * 10 + 4,
                        "{}",
                    ),
                    (
                        species_id,
                        species_taxons_id,
                        species_name,
                        "species",
                        genus_id,
                        3,
                        idx * 10 + 2,
                        idx * 10 + 3,
                        "{}",
                    ),
                ]
            )

        conn.executemany("INSERT INTO taxons VALUES (?, ?)", taxon_rows)
        conn.executemany(
            "INSERT INTO entity_taxons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            entity_rows,
        )
    finally:
        conn.close()

    with patch(
        "niamoto.gui.api.routers.config.get_working_directory",
        return_value=project_dir,
    ):
        client = TestClient(create_app())
        response = client.get("/api/config/export/taxons/index-generator/suggestions")

    assert response.status_code == 200, response.text

    payload = response.json()
    display_field_sources = {field["source"] for field in payload["display_fields"]}

    assert "hierarchy_context.family.name" in display_field_sources
    assert "hierarchy_context.genus.name" in display_field_sources
