"""Tests for standard profile auto-configuration."""

from __future__ import annotations

import duckdb

from niamoto.core.standards.auto_config import StandardProfileAutoConfigService
from niamoto.core.standards.models import StandardProfileSource


def test_darwin_core_auto_config_proposes_enriched_occurrence_terms(tmp_path):
    db_path = tmp_path / "niamoto.duckdb"
    connection = duckdb.connect(str(db_path))
    try:
        connection.execute(
            """
            CREATE TABLE dataset_occurrences (
                id INTEGER,
                id_taxonref INTEGER,
                taxaname VARCHAR,
                family VARCHAR,
                genus VARCHAR,
                species VARCHAR,
                infra VARCHAR,
                month_obs INTEGER,
                plot_name VARCHAR,
                geo_pt VARCHAR,
                dbh DOUBLE,
                height DOUBLE,
                elevation INTEGER
            )
            """
        )
        connection.execute(
            """
            INSERT INTO dataset_occurrences VALUES (
                1,
                42,
                'Araucaria columnaris',
                'Araucariaceae',
                'Araucaria',
                'columnaris',
                NULL,
                4,
                'plot-1',
                'POINT (165.7683 -21.6461)',
                12.5,
                8.0,
                450
            )
            """
        )
    finally:
        connection.close()

    service = StandardProfileAutoConfigService(
        tmp_path,
        db_path=db_path,
        import_config={"entities": {"datasets": {"occurrences": {}}}},
    )

    result = service.propose(
        name="dwc_occurrences",
        standard="darwin_core_occurrence",
        source=StandardProfileSource(type="dataset", name="occurrences"),
    )

    mappings = result.profile.mappings
    assert mappings["occurrenceID"] == {"source": "id"}
    assert mappings["scientificName"] == {"source": "taxaname"}
    assert mappings["taxonID"] == {"source": "id_taxonref"}
    assert mappings["family"] == {"source": "family"}
    assert mappings["genus"] == {"source": "genus"}
    assert mappings["specificEpithet"] == {"source": "species"}
    assert mappings["infraspecificEpithet"] == {"source": "infra"}
    assert mappings["month"] == {"source": "month_obs"}
    assert mappings["locationID"] == {"source": "plot_name"}
    assert mappings["decimalLatitude"] == {
        "generator": "extract_geometry_coordinate",
        "params": {"source": "geo_pt", "coordinate": "latitude"},
    }
    assert mappings["decimalLongitude"] == {
        "generator": "extract_geometry_coordinate",
        "params": {"source": "geo_pt", "coordinate": "longitude"},
    }
    assert mappings["basisOfRecord"] == {
        "generator": "constant",
        "params": {"value": "HumanObservation"},
    }
    assert mappings["dynamicProperties"] == {
        "generator": "format_measurements",
        "params": {"fields": ["dbh", "height"]},
    }
    assert result.unresolved == ["eventDate"]
    assert result.columns_inspected == 13
    assert result.rows_sampled == 1
