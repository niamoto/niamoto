import pandas as pd

from ml.scripts.data import build_gold_set
from ml.scripts.data.concept_taxonomy import coarsen, coarsen_role


def test_extract_from_source_returns_labeled_column_contract(tmp_path):
    csv_path = tmp_path / "source.csv"
    pd.DataFrame(
        {
            "species": ["Araucaria columnaris", "Niaouli test"],
            "height": [12.5, 8.0],
            "ignored": ["a", "b"],
        }
    ).to_csv(csv_path, index=False)

    records = build_gold_set.extract_from_source(
        {
            "name": "fixture_source",
            "path": csv_path,
            "language": "fr",
            "labels": {
                "species": ("taxonomy.species", "taxonomy"),
                "height": ("measurement.height", "measurement"),
            },
        }
    )

    assert [record["column_name"] for record in records] == ["species", "height"]
    assert {record["source_dataset"] for record in records} == {"fixture_source"}
    assert {record["language"] for record in records} == {"fr"}
    assert {record["quality"] for record in records} == {"gold"}
    assert {record["is_anonymous"] for record in records} == {False}
    assert records[0]["values_sample"] == ["Araucaria columnaris", "Niaouli test"]
    assert records[1]["values_stats"]["dtype"] == "float64"
    assert records[1]["values_stats"]["mean"] == 10.25


def test_build_gold_set_adds_coarse_fields_and_skips_reserved_sources(
    monkeypatch,
    tmp_path,
):
    csv_path = tmp_path / "source.csv"
    pd.DataFrame({"dbh": [10, 20]}).to_csv(csv_path, index=False)
    monkeypatch.setattr(
        build_gold_set,
        "SOURCES",
        [
            {
                "name": "training_source",
                "path": csv_path,
                "language": "en",
                "labels": {"dbh": ("measurement.circumference", "measurement")},
            },
            {
                "name": "fia_or_tree",
                "path": csv_path,
                "language": "en",
                "labels": {"dbh": ("measurement.diameter", "measurement")},
            },
        ],
    )
    monkeypatch.setattr(
        build_gold_set,
        "generate_synthetic_columns",
        lambda: [
            {
                "column_name": "succession",
                "values_sample": ["primary"],
                "values_stats": {"numeric": False},
                "concept": "category.succession",
                "role": "category",
                "source_dataset": "synthetic_fixture",
                "language": "en",
                "is_anonymous": False,
                "quality": "synthetic",
            }
        ],
    )

    records = build_gold_set.build_gold_set()

    by_column = {record["column_name"]: record for record in records}
    assert set(by_column) == {"dbh", "succession"}
    assert by_column["dbh"]["concept_coarse"] == "measurement.diameter"
    assert by_column["dbh"]["role_coarse"] == "measurement"
    assert by_column["succession"]["concept_coarse"] == "category.ecology"
    assert by_column["succession"]["role_coarse"] == "category"


def test_concept_taxonomy_coarsens_known_concepts_and_keeps_unknowns():
    assert coarsen("category.succession") == "category.ecology"
    assert coarsen("taxonomy.species") == "taxonomy.species"
    assert coarsen_role("measurement.diameter") == "measurement"
    assert coarsen_role("freeform") == "freeform"
