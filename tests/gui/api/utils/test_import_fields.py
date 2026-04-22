"""Tests for import-field metadata helpers."""

from __future__ import annotations

from niamoto.gui.api.utils import import_fields


def test_taxonomy_import_type_exposes_dynamic_rank_metadata():
    payload = import_fields.get_required_fields_for_import_type("taxonomy")

    assert payload["supports_dynamic_ranks"] is True
    assert payload["default_ranks"] == ["family", "genus", "species", "infra"]
    assert payload["fields"] == [
        {
            "key": "taxon_id",
            "label": "Taxon ID",
            "description": "Unique identifier for each taxon",
            "required": True,
        },
        {
            "key": "authors",
            "label": "Authors",
            "description": "Taxonomic authority",
            "required": False,
        },
    ]


def test_occurrences_fields_follow_import_method_signature(monkeypatch):
    monkeypatch.setattr(
        import_fields,
        "get_import_method_info",
        lambda method_name: {
            "taxon_id_column": {"required": True},
            "location_column": {"required": False},
        },
    )

    payload = import_fields.get_required_fields_for_import_type("occurrences")

    assert payload["fields"] == [
        {
            "key": "taxon_id",
            "label": "Taxon ID",
            "description": "Reference to taxonomy",
            "required": True,
        },
        {
            "key": "location",
            "label": "Location",
            "description": "Occurrence coordinates (WKT format)",
            "required": False,
        },
        {
            "key": "plot_name",
            "label": "Plot Name",
            "description": "Link to plot",
            "required": False,
        },
    ]
    assert payload["method_params"] == {
        "taxon_id_column": {"required": True},
        "location_column": {"required": False},
    }


def test_unknown_import_type_returns_empty_payload():
    assert import_fields.get_required_fields_for_import_type("unknown") == {
        "fields": [],
        "method_params": {},
    }


def test_get_all_import_types_info_aggregates_each_type(monkeypatch):
    calls = []

    def fake_get_required_fields(import_type):
        calls.append(import_type)
        return {"kind": import_type}

    monkeypatch.setattr(
        import_fields,
        "get_required_fields_for_import_type",
        fake_get_required_fields,
    )

    payload = import_fields.get_all_import_types_info()

    assert calls == ["taxonomy", "plots", "occurrences", "shapes"]
    assert payload == {
        "taxonomy": {"kind": "taxonomy"},
        "plots": {"kind": "plots"},
        "occurrences": {"kind": "occurrences"},
        "shapes": {"kind": "shapes"},
    }
