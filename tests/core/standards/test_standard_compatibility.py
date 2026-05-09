"""Tests for standard profile grain compatibility."""

from __future__ import annotations

from niamoto.core.standards.compatibility import StandardCompatibilityService
from niamoto.core.standards.models import StandardProfileConfig


def _import_config() -> dict:
    return {
        "entities": {
            "references": {
                "taxons": {
                    "kind": "hierarchical",
                    "schema": {"fields": [{"name": "species", "type": "string"}]},
                },
                "plots": {
                    "kind": "spatial",
                    "schema": {"fields": [{"name": "plot_name", "type": "string"}]},
                },
            },
            "datasets": {
                "occurrences": {
                    "schema": {
                        "fields": [
                            {"name": "occurrence_id", "type": "string"},
                            {"name": "taxon_id", "type": "integer"},
                        ]
                    },
                    "links": [
                        {
                            "entity": "taxons",
                            "field": "taxon_id",
                            "target_field": "id",
                        }
                    ],
                }
            },
        }
    }


def test_darwin_core_occurrence_from_taxon_context_uses_occurrence_relation():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_taxon_context",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "collection", "name": "taxons"},
        }
    )
    service = StandardCompatibilityService(import_config=_import_config())

    report = service.evaluate(profile)

    assert report.status == "compatible"
    assert report.target_grain == "occurrence"
    assert report.source_grain == "taxon"
    assert report.confidence >= 0.8
    assert report.blockers == []
    assert report.evidence[0].kind == "occurrence_relation"
    assert report.evidence[0].details["occurrence_dataset"] == "occurrences"


def test_darwin_core_occurrence_source_has_exact_grain_confidence():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
        }
    )
    service = StandardCompatibilityService(import_config=_import_config())

    report = service.evaluate(profile)

    assert report.status == "compatible"
    assert report.source_grain == "occurrence"
    assert report.confidence == 1.0
    assert report.evidence[0].kind == "source_grain"
    assert report.evidence[0].confidence == 1.0


def test_humboldt_event_from_plot_collection_is_plausible_with_warnings():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "plot_inventory",
            "standard": "humboldt_event",
            "target_grain": "event",
            "source": {"type": "collection", "name": "plots"},
        }
    )
    service = StandardCompatibilityService(import_config=_import_config())

    report = service.evaluate(profile)

    assert report.status == "plausible"
    assert report.source_grain == "site"
    assert report.blockers == []
    assert report.warnings == [
        "Site-grain collection can start a Humboldt/Event profile, but Event or inventory evidence is still required."
    ]


def test_occurrence_named_collection_uses_backing_source_relation():
    import_config = _import_config()
    import_config["metadata"] = {
        "collections": {
            "occurrence_summary": {
                "source": {"type": "reference", "name": "taxons"},
                "grain": "reference",
                "roles": ["standard"],
            }
        }
    }
    profile = StandardProfileConfig.model_validate(
        {
            "name": "bad_occurrence",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "collection", "name": "occurrence_summary"},
        }
    )
    service = StandardCompatibilityService(import_config=import_config)

    report = service.evaluate(profile)

    assert report.status == "compatible"
    assert report.evidence[0].details["relation_entity"] == "taxons"


def test_occurrence_named_collection_without_backing_relation_is_blocked():
    import_config = _import_config()
    import_config["metadata"] = {
        "collections": {
            "occurrence_summary": {
                "source": {"type": "reference", "name": "plots"},
                "grain": "reference",
                "roles": ["standard"],
            }
        }
    }
    profile = StandardProfileConfig.model_validate(
        {
            "name": "bad_occurrence",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "collection", "name": "occurrence_summary"},
        }
    )
    service = StandardCompatibilityService(import_config=import_config)

    report = service.evaluate(profile)

    assert report.status == "blocked"
    assert report.confidence < 0.5
    assert report.blockers == [
        "Darwin Core Occurrence requires occurrence-grain data or an explicit relation to occurrence data."
    ]
