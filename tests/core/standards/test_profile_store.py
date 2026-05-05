"""Tests for standard profile persistence in export.yml."""

from __future__ import annotations

import pytest

from niamoto.core.standards.profile_store import StandardProfileStore


KNOWN_SOURCES = [
    {"type": "collection", "name": "taxons"},
    {"type": "dataset", "name": "occurrences"},
    {"type": "collection", "name": "plots"},
]


def test_create_darwin_core_profile_persists_separately_from_exports():
    export_config = {
        "exports": [
            {
                "name": "json_api",
                "exporter": "json_api_exporter",
                "params": {
                    "output_dir": "exports/api",
                    "detail_output_pattern": "{group}/{id}.json",
                },
                "groups": [],
            }
        ]
    }
    store = StandardProfileStore(export_config, known_sources=KNOWN_SOURCES)

    profile = store.create_profile(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "context": {"type": "collection", "name": "taxons"},
            "mappings": {"occurrenceID": {"source": "occurrence_id"}},
            "outputs": [{"type": "api_json"}],
        }
    )

    assert profile.name == "dwc_occurrences"
    assert export_config["exports"][0]["name"] == "json_api"
    assert export_config["standard_profiles"] == [
        {
            "name": "dwc_occurrences",
            "enabled": True,
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "context": {"type": "collection", "name": "taxons"},
            "mappings": {"occurrenceID": {"source": "occurrence_id"}},
            "outputs": [{"type": "api_json", "enabled": True, "params": {}}],
            "validation_status": "draft",
            "metadata": {},
        }
    ]


def test_create_humboldt_event_profile_can_start_as_draft_with_warnings():
    export_config = {"exports": []}
    store = StandardProfileStore(export_config, known_sources=KNOWN_SOURCES)

    profile = store.create_profile(
        {
            "name": "plot_inventory",
            "standard": "humboldt_event",
            "target_grain": "event",
            "source": {"type": "collection", "name": "plots"},
            "validation_status": "partial",
            "metadata": {"warnings": ["Missing sampling protocol"]},
        }
    )

    assert profile.standard == "humboldt_event"
    assert profile.validation_status == "partial"
    assert export_config["standard_profiles"][0]["metadata"] == {
        "warnings": ["Missing sampling protocol"]
    }


def test_store_rejects_duplicate_profile_names_without_mutating_config():
    export_config = {
        "exports": [],
        "standard_profiles": [
            {
                "name": "dwc_occurrences",
                "standard": "darwin_core_occurrence",
                "target_grain": "occurrence",
                "source": {"type": "dataset", "name": "occurrences"},
            }
        ],
    }
    store = StandardProfileStore(export_config, known_sources=KNOWN_SOURCES)

    with pytest.raises(ValueError, match="already exists"):
        store.create_profile(
            {
                "name": "dwc_occurrences",
                "standard": "darwin_core_occurrence",
                "target_grain": "occurrence",
                "source": {"type": "dataset", "name": "occurrences"},
            }
        )

    assert len(export_config["standard_profiles"]) == 1


def test_store_rejects_unknown_profile_source_without_mutating_config():
    export_config = {"exports": []}
    store = StandardProfileStore(export_config, known_sources=KNOWN_SOURCES)

    with pytest.raises(ValueError, match="Unknown dataset source 'missing'"):
        store.create_profile(
            {
                "name": "bad_profile",
                "standard": "darwin_core_occurrence",
                "target_grain": "occurrence",
                "source": {"type": "dataset", "name": "missing"},
            }
        )

    assert "standard_profiles" not in export_config


def test_legacy_dwc_occurrence_json_export_is_reported_as_hint_only():
    export_config = {
        "exports": [
            {
                "name": "dwc_occurrence_json",
                "exporter": "json_api_exporter",
                "params": {
                    "output_dir": "exports/dwc",
                    "detail_output_pattern": "{group}/{id}.json",
                },
                "groups": [
                    {
                        "group_by": "taxons",
                        "transformer_plugin": "niamoto_to_dwc_occurrence",
                        "transformer_params": {
                            "occurrence_list_source": "occurrences",
                            "mapping": {},
                        },
                    }
                ],
            }
        ]
    }
    store = StandardProfileStore(export_config)

    assert store.list_legacy_hints() == [
        {
            "export_name": "dwc_occurrence_json",
            "standard": "darwin_core_occurrence",
            "message": "Legacy JSON API target can be reviewed as a Darwin Core Occurrence profile.",
            "source": {"type": "collection", "name": "taxons"},
        }
    ]
    assert "standard_profiles" not in export_config
