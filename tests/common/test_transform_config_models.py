from __future__ import annotations

import pytest
from pydantic import ValidationError

from niamoto.common.transform_config_models import validate_transform_config


def test_validate_transform_config_normalizes_valid_group() -> None:
    data = [
        {
            "group_by": "taxons",
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "taxons",
                    "relation": {
                        "plugin": "join_table",
                        "key": "taxon_id",
                    },
                }
            ],
            "widgets_data": {
                "richness": {
                    "plugin": "summary_stats",
                    "field": "count",
                    "params": {"label": "Richness"},
                }
            },
        }
    ]

    normalized = validate_transform_config(data)

    assert normalized == data


def test_validate_transform_config_keeps_extra_fields() -> None:
    data = [
        {
            "group_by": "plots",
            "sources": [
                {
                    "name": "occurrences",
                    "data": "occurrences",
                    "grouping": "plots",
                    "relation": {
                        "plugin": "join_table",
                        "key": "plot_id",
                        "custom_hint": "kept",
                    },
                    "custom_source_flag": True,
                }
            ],
            "widgets_data": {},
            "custom_group_field": "kept",
        }
    ]

    normalized = validate_transform_config(data)

    assert normalized[0]["custom_group_field"] == "kept"
    assert normalized[0]["sources"][0]["custom_source_flag"] is True
    assert normalized[0]["sources"][0]["relation"]["custom_hint"] == "kept"


def test_validate_transform_config_raises_for_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        validate_transform_config([{"group_by": "taxons", "sources": "invalid"}])
