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


def _manual_collection_import_config() -> dict:
    return {
        "entities": {
            "datasets": {
                "occurrences": {
                    "schema": {
                        "fields": [
                            {"name": "occurrence_id", "type": "string"},
                            {"name": "scientific_name", "type": "string"},
                        ]
                    }
                }
            }
        },
        "metadata": {
            "collections": {
                "occurrences_publication": {
                    "source": {"type": "dataset", "name": "occurrences"},
                    "grain": "occurrence",
                    "roles": ["api", "standard"],
                    "visible": False,
                    "review_status": "accepted",
                }
            }
        },
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


def test_darwin_core_profile_preview_uses_representative_mapped_record(
    tmp_path, monkeypatch
):
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
            "outputs": [{"type": "api_json"}],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    def fake_load_records(source, *, limit=None):
        assert limit == 100
        return [
            {"id": 1, "scientific_name": None},
            {
                "id": 2,
                "scientific_name": "Araucaria columnaris",
                "geo_pt_geom": b"\x01\x01\x00\x00\x00\xef\x1b",
            },
        ]

    monkeypatch.setattr(service, "_load_records", fake_load_records)

    result = service.preview_profile(profile, output_type="api_json")

    assert result.output_type == "api_json"
    assert result.item_id == 2
    assert result.preview["metadata"]["profile_name"] == "dwc_occurrences"
    assert result.metadata["draft"] is True
    assert result.metadata["sample_basis"] == "representative_record"
    assert result.metadata["rows_sampled"] == 2
    assert result.metadata["source_record_id"] == 2
    assert result.metadata["retention_policy"] == {
        "type": "manual_cleanup",
        "location": "exports/.draft/profiles",
    }
    assert result.preview["records"] == [
        {"occurrenceID": 2, "scientificName": "Araucaria columnaris"}
    ]
    assert result.source == {
        "id": 2,
        "scientific_name": "Araucaria columnaris",
    }
    assert "geo_pt_geom" not in result.source
    assert "Araucaria columnaris" in result.model_dump_json()


def test_darwin_core_profile_generators_extract_coordinates_and_properties(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {
                "occurrenceID": {"source": "id"},
                "decimalLatitude": {
                    "generator": "extract_geometry_coordinate",
                    "params": {"source": "geo_pt", "coordinate": "latitude"},
                },
                "decimalLongitude": {
                    "generator": "extract_geometry_coordinate",
                    "params": {"source": "geo_pt", "coordinate": "longitude"},
                },
                "dynamicProperties": {
                    "generator": "format_measurements",
                    "params": {"fields": ["dbh", "height"]},
                },
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
        records=[
            {
                "id": 1,
                "geo_pt": "POINT (165.7683 -21.6461)",
                "dbh": 12.5,
                "height": 8,
            }
        ],
    )

    payload = json.loads(result.files[0].read_text(encoding="utf-8"))
    assert payload["records"] == [
        {
            "occurrenceID": 1,
            "decimalLatitude": -21.6461,
            "decimalLongitude": 165.7683,
            "dynamicProperties": '{"dbh": 12.5, "height": 8}',
        }
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


def test_darwin_core_taxon_context_rejects_context_mappings_until_joined(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_taxon_context",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "collection", "name": "taxons"},
            "mappings": {
                "occurrenceID": {"source": "occurrence_id"},
                "scientificName": {"source": "@taxon.full_name"},
            },
            "outputs": [{"type": "api_json"}],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_taxon_context_import_config()
    )

    with pytest.raises(ValueError, match="Context mapping for term 'scientificName'"):
        service.execute_profile(profile, output_type="api_json")


def test_manual_collection_output_loads_backing_source(tmp_path, monkeypatch):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_manual_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "collection", "name": "occurrences_publication"},
            "mappings": {
                "occurrenceID": {"source": "occurrence_id"},
                "scientificName": {"source": "scientific_name"},
            },
            "outputs": [{"type": "api_json"}],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_manual_collection_import_config()
    )
    loaded_sources: list[dict[str, str]] = []

    def fake_load_records(source):
        loaded_sources.append(source.model_dump(mode="json"))
        return [
            {
                "occurrence_id": "occ-1",
                "scientific_name": "Araucaria columnaris",
            }
        ]

    monkeypatch.setattr(service, "_load_records", fake_load_records)

    result = service.execute_profile(profile, output_type="api_json")

    assert loaded_sources == [{"type": "dataset", "name": "occurrences"}]
    payload = json.loads(result.files[0].read_text(encoding="utf-8"))
    assert payload["metadata"]["record_source"] == {
        "type": "dataset",
        "name": "occurrences",
    }
    assert payload["records"] == [
        {
            "occurrenceID": "occ-1",
            "scientificName": "Araucaria columnaris",
        }
    ]


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


def test_darwin_core_archive_draft_output_uses_isolated_location(tmp_path):
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
                        "output_dir": "exports/profiles/final_archive",
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
        draft=True,
    )

    archive_path = (
        tmp_path
        / "exports"
        / ".draft"
        / "profiles"
        / "dwc_occurrences"
        / "dwc_archive"
        / "profile-dwc.zip"
    )
    assert result.status == "success"
    assert result.output_path == str(archive_path)
    assert result.metadata["draft"] is True
    assert result.metadata["publication_output"] is False
    assert result.metadata["retention_policy"]["location"] == "exports/.draft/profiles"
    assert archive_path.exists()
    assert not (tmp_path / "exports" / "profiles" / "final_archive").exists()


def test_publication_output_with_critical_validation_errors_is_blocked(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {},
            "outputs": [{"type": "dwc_archive"}],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    with pytest.raises(ValueError, match="Publication outputs require"):
        service.execute_profile(
            profile,
            output_type="dwc_archive",
            records=[{"id": "occ-1"}],
        )


def test_darwin_core_archive_empty_records_returns_clear_error(tmp_path):
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
                    "params": {"output_dir": "exports/profiles/dwc_archive"},
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    with pytest.raises(ValueError, match="generated no archive files"):
        service.execute_profile(profile, output_type="dwc_archive", records=[])


@pytest.mark.parametrize(
    ("output_dir", "error"),
    [
        ("/tmp/niamoto-escape", "output_dir must be relative"),
        ("../outside", "output_dir must not contain parent"),
    ],
)
def test_profile_output_rejects_unsafe_output_dir(tmp_path, output_dir, error):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {"occurrenceID": {"source": "id"}},
            "outputs": [
                {
                    "type": "api_json",
                    "params": {"output_dir": output_dir},
                }
            ],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    with pytest.raises(ValueError, match=error):
        service.execute_profile(profile, output_type="api_json", records=[{"id": 1}])


def test_profile_output_rejects_unsafe_profile_name_in_paths(tmp_path):
    profile = StandardProfileConfig.model_validate(
        {
            "name": "../dwc_occurrences",
            "standard": "darwin_core_occurrence",
            "target_grain": "occurrence",
            "source": {"type": "dataset", "name": "occurrences"},
            "mappings": {"occurrenceID": {"source": "id"}},
            "outputs": [{"type": "api_json"}],
        }
    )
    service = StandardProfileOutputService(
        tmp_path, import_config=_occurrence_import_config()
    )

    with pytest.raises(ValueError, match="profile name must be a safe path segment"):
        service.execute_profile(profile, output_type="api_json", records=[{"id": 1}])


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
