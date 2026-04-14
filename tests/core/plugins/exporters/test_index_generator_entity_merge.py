from pathlib import Path
from types import SimpleNamespace

import duckdb
from jinja2 import DictLoader, Environment

from niamoto.common.database import Database
from niamoto.core.plugins.exporters.index_generator import IndexGeneratorPlugin
from niamoto.core.plugins.models import IndexGeneratorConfig


def test_generate_index_merges_reference_extra_data(tmp_path: Path) -> None:
    db_path = tmp_path / "niamoto.duckdb"
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
                (
                    101,
                    '{"name":{"value":null},"rank":{"value":"species"}}'
                ),
                (
                    202,
                    '{"name":{"value":"Second taxon"},"rank":{"value":"species"}}'
                )
            """
        )

        conn.execute(
            """
            CREATE TABLE entity_taxons (
                id BIGINT,
                taxons_id BIGINT,
                full_name VARCHAR,
                extra_data JSON
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (
                    1,
                    101,
                    'Araucaria columnaris',
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","data":{"endemic":true}}}}}'
                ),
                (
                    2,
                    202,
                    'Agathis ovata',
                    '{"api_enrichment":{"sources":{"api-endemia-nc":{"label":"Endemia NC","data":{"endemic":false}}}}}'
                )
            """
        )
    finally:
        conn.close()

    db = Database(str(db_path), read_only=True)
    try:
        plugin = IndexGeneratorPlugin(db)
        config = IndexGeneratorConfig(
            page_config={"title": "Taxons"},
            filters=[
                {
                    "field": "extra_data.api_enrichment.sources.api-endemia-nc.data.endemic",
                    "values": [True],
                    "operator": "in",
                }
            ],
            display_fields=[
                {
                    "name": "name",
                    "source": "general_info.name.value",
                    "fallback": "full_name",
                    "type": "text",
                    "searchable": True,
                },
                {
                    "name": "label",
                    "source": "extra_data.api_enrichment.sources.api-endemia-nc.label",
                    "type": "text",
                    "searchable": False,
                },
            ],
        )

        jinja_env = Environment(
            loader=DictLoader(
                {
                    "_group_index.html": (
                        "{{ items_data|length }}|"
                        "{{ items_data[0]['name'] }}|"
                        "{{ items_data[0]['label'] }}"
                    )
                }
            )
        )

        plugin.generate_index(
            group_by="taxons",
            config=config,
            output_dir=tmp_path,
            jinja_env=jinja_env,
            html_params=SimpleNamespace(
                site=None,
                navigation=None,
                footer_navigation=None,
            ),
            site_context={"title": "Niamoto"},
            navigation=[],
            footer_navigation=[],
        )
    finally:
        db.close_db_session()

    generated_index = tmp_path / "taxons" / "index.html"
    assert generated_index.exists()
    assert generated_index.read_text(encoding="utf-8") == (
        "1|Araucaria columnaris|Endemia NC"
    )


def test_generate_index_exposes_hierarchy_context_from_reference_table(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "niamoto.duckdb"
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
                (
                    101,
                    '{"name":{"value":"Abebaia dissecta"},"rank":{"value":"species"}}'
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
                lft BIGINT,
                rght BIGINT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO entity_taxons VALUES
                (1, 11, 'Sapotaceae', 'family', NULL, 1, 6),
                (2, 22, 'Abebaia', 'genus', 1, 2, 5),
                (3, 101, 'Abebaia dissecta', 'species', 2, 3, 4)
            """
        )
    finally:
        conn.close()

    db = Database(str(db_path), read_only=True)
    try:
        plugin = IndexGeneratorPlugin(db)
        config = IndexGeneratorConfig(
            page_config={"title": "Taxons"},
            display_fields=[
                {
                    "name": "name",
                    "source": "general_info.name.value",
                    "type": "text",
                    "searchable": True,
                },
                {
                    "name": "family",
                    "source": "hierarchy_context.family.name",
                    "type": "text",
                    "searchable": False,
                },
                {
                    "name": "genus",
                    "source": "hierarchy_context.genus.name",
                    "type": "text",
                    "searchable": False,
                },
            ],
        )

        jinja_env = Environment(
            loader=DictLoader(
                {
                    "_group_index.html": (
                        "{{ items_data|length }}|"
                        "{{ items_data[0]['name'] }}|"
                        "{{ items_data[0]['family'] }}|"
                        "{{ items_data[0]['genus'] }}"
                    )
                }
            )
        )

        plugin.generate_index(
            group_by="taxons",
            config=config,
            output_dir=tmp_path,
            jinja_env=jinja_env,
            html_params=SimpleNamespace(
                site=None,
                navigation=None,
                footer_navigation=None,
            ),
            site_context={"title": "Niamoto"},
            navigation=[],
            footer_navigation=[],
        )
    finally:
        db.close_db_session()

    generated_index = tmp_path / "taxons" / "index.html"
    assert generated_index.exists()
    assert generated_index.read_text(encoding="utf-8") == (
        "1|Abebaia dissecta|Sapotaceae|Abebaia"
    )
