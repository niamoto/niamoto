"""Tests for standard profile output generation."""

from __future__ import annotations

import json
import zipfile

import pytest

from niamoto.core.standards.models import StandardProfileConfig
from niamoto.core.standards.output_service import StandardProfileOutputService


def _occurrence_import_config() -> dict:
    return {
        "entities": {
            "datasets": {
                "occurrences": {
                    "schema": {
                        "fields": [
                            {"name": "id", "type": "integer"},
                            {"name": "scientific_name", "type": "string"},
                        ]
                    }
                }
            }
        }
    }


def _taxon_context_import_config() -> dict:
    return {
        "entities": {
            "references": {
                "taxons": {
                    "kind": "hierarchical",
                    "schema": {"fields": [{"name": "species", "type": "string"}]},
                }
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


def test_darwin_core_profile_api_json_writes_profile_owned_records(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {
                "occurrenceID": {"source": "id"},
                "scientificName": {"source": "scientific_name"},
            },
            "outputs": [
                {
                    "type": "api_json",
                    "params": {"output_dir": "exports/profiles/dwc"},
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    result = service.execute_profile(
        profile,
        output_type="api_json",
        records=[{"id": 1, "scientific_name": "Araucaria columnaris"}],
    )

    assert result.status == "success"
    assert result.validation_status == "conformant"
    output_path = tmp_path / "exports" / "profiles" / "dwc" / "dwc_occurrences.json"
    assert result.output_path == str(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["profile_name"] == "dwc_occurrences"
    assert payload["metadata"]["validation_status"] == "conformant"
    assert payload["records"] == [
        {"occurrenceID": 1, "scientificName": "Araucaria columnaris"}
    ]


def test_darwin_core_taxon_context_output_loads_related_occurrences(
    tmp_path, monkeypatch
):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_taxon_context",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "collection", "name": "taxons"},
            "mappings": {
                "occurrenceID": {"source": "occurrence_id"},
                "taxonID": {"source": "taxon_id"},
            },
            "outputs": [
                {
                    "type": "api_json",
                    "params": {"output_dir": "exports/profiles/dwc"},
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_taxon_context_import_config()
    )
    loaded_sources: list[dict[str, str]] = []

    def fake_load_records(source):
        loaded_sources.append(source.model_dump(mode="json"))
        return [{"occurrence_id": "occ-1", "taxon_id": 42}]

    monkeypatch.setattr(service, "_load_records", fake_load_records)

    result = service.execute_profile(profile, output_type="api_json")

    assert loaded_sources == [{"type": "dataset", "name": "occurrences"}]
    assert result.source_grain == "occurrence"
    payload = json.loads(result.files[0].read_text(encoding="utf-8"))
    assert payload["metadata"]["source"] == {
        "type": "collection",
        "name": "taxons",
    }
    assert payload["metadata"]["record_source"] == {
        "type": "dataset",
        "name": "occurrences",
    }
    assert payload["records"] == [{"occurrenceID": "occ-1", "taxonID": 42}]


def test_darwin_core_archive_output_creates_archive(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {"occurrenceID": {"source": "id"}},
            "outputs": [
                {
                    "type": "dwc_archive",
                    "params": {
                        "output_dir": "exports/profiles/dwc_archive",
                        "archive_name": "profile-dwc.zip",
                    },
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    result = service.execute_profile(
        profile,
        output_type="dwc_archive",
        records=[{"id": "occ-1"}],
    )

    archive_path = tmp_path / "exports" / "profiles" / "dwc_archive" / "profile-dwc.zip"
    assert result.status == "success"
    assert result.output_path == str(archive_path)
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path, "r") as archive:
        assert {"occurrence.csv", "meta.xml", "eml.xml"}.issubset(
            set(archive.namelist())
        )


def test_invalid_profile_output_never_reports_conformant(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {},
            "outputs": [
                {
                    "type": "api_json",
                    "params": {"output_dir": "exports/profiles/dwc"},
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    result = service.execute_profile(
        profile, output_type="api_json", records=[{"id": 1}]
    )

    assert result.status == "success"
    assert result.validation_status == "invalid"
    payload = json.loads(result.files[0].read_text(encoding="utf-8"))
    assert payload["metadata"]["validation_status"] == "invalid"
    assert payload["metadata"]["conformant"] is False


def test_disabled_output_request_returns_clear_error(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {"occurrenceID": {"source": "id"}},
            "outputs": [{"type": "api_json", "enabled": False}],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    with pytest.raises(ValueError, match="Output 'api_json' is disabled"):
        service.execute_profile(profile, output_type="api_json", records=[{"id": 1}])


def test_humboldt_event_profile_writes_partial_standard_files(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "plot_inventory",
            "standard": "humboldt_event",
            "target_grain": "event",
            "source": {"type": "collection", "name": "plots"},
            "mappings": {"eventID": {"source": "plot_id"}},
            "outputs": [
                {
                    "type": "standard_files",
                    "params": {"output_dir": "exports/profiles/humboldt"},
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path,
        import_config={"entities": {"references": {"plots": {"kind": "spatial"}}}},
    )

    result = service.execute_profile(
        profile,
        output_type="standard_files",
        records=[{"plot_id": "plot-1", "plot_name": "Plot 1"}],
    )

    event_path = tmp_path / "exports" / "profiles" / "humboldt" / "event.csv"
    assert result.status == "success"
    assert result.validation_status == "partial"
    assert event_path.exists()
    assert "eventID" in event_path.read_text(encoding="utf-8")
