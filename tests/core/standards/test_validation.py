"""Tests for standard profile validation reports."""

from __future__ import annotations

from niamoto.core.standards.models import StandardProfileConfig
from niamoto.core.standards.validation import StandardProfileValidationService


def _import_config() -> dict:
    return {
        "entities": {
            "references": {
                "plots": {"kind": "spatial"},
            },
            "datasets": {
                "occurrences": {
                    "schema": {
                        "fields": [
                            {"name": "occurrence_id", "type": "string"},
                            {"name": "scientific_name", "type": "string"},
                        ]
                    }
                }
            },
        }
    }


def test_missing_critical_mapping_blocks_conformant_status():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {},
        }
    )
    service = StandardProfileValidationService(import_config=_import_config())

    report = service.validate(profile)

    assert report.status == "invalid"
    assert report.summary["critical"] == 1
    assert report.checklist[0].code == "dwc_occurrence_id"
    assert report.checklist[0].status == "fail"
    assert report.issues[0].severity == "critical"


def test_malformed_mapping_returns_critical_issue_without_exception():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {"occurrenceID": ["not", "valid"]},
        }
    )
    service = StandardProfileValidationService(import_config=_import_config())

    report = service.validate(profile)

    assert report.status == "invalid"
    assert [issue.code for issue in report.issues] == ["mapping_invalid"]


def test_unsupported_standard_generator_returns_critical_issue():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {
                "occurrenceID": {"source": "occurrence_id"},
                "eventDate": {"generator": "format_event_date"},
            },
        }
    )
    service = StandardProfileValidationService(import_config=_import_config())

    report = service.validate(profile)

    assert report.status == "invalid"
    assert "mapping_unsupported_generator" in {issue.code for issue in report.issues}


def test_darwin_core_occurrence_with_required_mapping_can_be_conformant():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {"occurrenceID": {"source": "occurrence_id"}},
        }
    )
    service = StandardProfileValidationService(import_config=_import_config())

    report = service.validate(profile)

    assert report.status == "conformant"
    assert report.summary["critical"] == 0
    assert report.compatibility.status == "compatible"


def test_humboldt_event_plot_profile_stays_partial_with_recommended_gaps():
    profile = StandardProfileConfig.model_validate(
        {
            "name": "plot_inventory",
            "standard": "humboldt_event",
            "target_grain": "event",
            "source": {"type": "collection", "name": "plots"},
            "mappings": {"eventID": {"source": "plot_id"}},
        }
    )
    service = StandardProfileValidationService(import_config=_import_config())

    report = service.validate(profile)

    assert report.status == "partial"
    assert report.compatibility.status == "plausible"
    assert report.summary["recommended"] >= 1
    assert "humboldt_event_date" in {item.code for item in report.checklist}
