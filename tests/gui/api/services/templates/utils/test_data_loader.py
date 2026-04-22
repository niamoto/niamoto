from pathlib import Path

import pandas as pd
import pytest
import yaml
from fastapi import HTTPException

from niamoto.gui.api.services.templates.utils import data_loader


class _ScalarValue:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class _DummyDatabase:
    def __init__(self, existing_tables=None):
        self.engine = object()
        self._existing_tables = set(existing_tables or [])

    def has_table(self, table_name: str) -> bool:
        return table_name in self._existing_tables


def test_load_sample_data_returns_entity_dataframe_without_sql():
    result = data_loader.load_sample_data(
        db=_DummyDatabase(),
        representative={
            "source_type": "entity",
            "entity_data": {"id_shape": 3, "name": "Parc Bleu"},
        },
        template_config={"field": "*"},
    )

    assert result.to_dict("records") == [{"id_shape": 3, "name": "Parc Bleu"}]


def test_load_sample_data_builds_filtered_query_with_random_limit(monkeypatch):
    captured: dict[str, object] = {}

    def fake_read_sql(query, _engine, params=None):
        captured["query"] = str(query)
        captured["params"] = params
        return pd.DataFrame([{"plot_id": 42}])

    monkeypatch.setattr(data_loader, "quote_identifier", lambda _db, name: name)
    monkeypatch.setattr(data_loader.pd, "read_sql", fake_read_sql)

    result = data_loader.load_sample_data(
        db=_DummyDatabase(existing_tables={"dataset_occurrences"}),
        representative={
            "table_name": "dataset_occurrences",
            "column": "plot_id",
            "value": _ScalarValue(42),
        },
        template_config={"field": "plot_id"},
        limit=5,
    )

    assert result.to_dict("records") == [{"plot_id": 42}]
    assert (
        "SELECT plot_id FROM dataset_occurrences WHERE plot_id = :match_value "
        "ORDER BY RANDOM() LIMIT 5"
    ) in str(captured["query"])
    assert captured["params"] == {"match_value": 42}


def test_load_sample_data_rejects_unknown_table():
    with pytest.raises(
        HTTPException, match="Unknown table: dataset_occurrences"
    ) as exc:
        data_loader.load_sample_data(
            db=_DummyDatabase(),
            representative={
                "table_name": "dataset_occurrences",
                "column": "plot_id",
                "value": 42,
            },
            template_config={"field": "*"},
        )

    assert exc.value.status_code == 400


def test_load_class_object_data_for_preview_prioritizes_reference_name(tmp_path):
    config_dir = tmp_path / "config"
    imports_dir = tmp_path / "imports"
    config_dir.mkdir(parents=True)
    imports_dir.mkdir()

    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            {
                "groups": {
                    "shapes": {
                        "sources": [
                            {"name": "shape_stats", "data": "imports/shapes.csv"}
                        ]
                    },
                    "plots": {
                        "sources": [{"name": "plot_stats", "data": "imports/plots.csv"}]
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    (imports_dir / "shapes.csv").write_text(
        "\n".join(
            [
                "class_object,class_name,class_value",
                "dbh,wrong-group,999",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (imports_dir / "plots.csv").write_text(
        "\n".join(
            [
                "id;class_object;class_name;class_value",
                "1;dbh;10;4",
                "2;dbh;10;6",
                "3;dbh;20;5",
                "4;dbh;20;invalid",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = data_loader.load_class_object_data_for_preview(
        Path(tmp_path), "dbh", "plots"
    )

    assert result == {
        "tops": ["10", "20"],
        "counts": [10.0, 5.0],
        "source": "plot_stats",
        "group_by": "plots",
        "class_object": "dbh",
    }


def test_load_class_object_csv_dataframe_prefers_named_source_and_richest_entity(
    tmp_path,
):
    config_dir = tmp_path / "config"
    imports_dir = tmp_path / "imports"
    config_dir.mkdir(parents=True)
    imports_dir.mkdir()

    (config_dir / "transform.yml").write_text(
        yaml.safe_dump(
            [
                {
                    "group_by": "plots",
                    "sources": [
                        {"name": "other_stats", "data": "imports/other.csv"},
                        {"name": "plot_stats", "data": "imports/plots.csv"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    (imports_dir / "other.csv").write_text(
        "class_object,class_name,class_value\nfallback,a,1\n",
        encoding="utf-8",
    )
    (imports_dir / "plots.csv").write_text(
        "\n".join(
            [
                "id,class_object,class_name,class_value",
                "1,dbh,10,3",
                "1,dbh,20,4",
                "2,dbh,10,5",
                "2,dbh,20,6",
                "2,dbh,30,7",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = data_loader.load_class_object_csv_dataframe(
        Path(tmp_path), "plots", source_name="plot_stats"
    )

    assert result is not None
    assert result["id"].tolist() == [2, 2, 2]
    assert result["class_object"].tolist() == ["dbh", "dbh", "dbh"]
    assert result["class_value"].tolist() == [5, 6, 7]
