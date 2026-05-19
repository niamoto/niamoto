"""Tests for collection catalog metadata and inference."""

from __future__ import annotations

from niamoto.core.collections.catalog import CollectionCatalogService


def _import_config() -> dict:
    return {
        "entities": {
            "references": {
                "taxons": {
                    "kind": "hierarchical",
                    "description": "Taxonomic hierarchy",
                    "schema": {
                        "id": "id",
                        "name_field": "full_name",
                        "fields": [
                            {"name": "id", "type": "integer"},
                            {"name": "full_name", "type": "string"},
                        ],
                    },
                },
                "plots": {
                    "kind": "spatial",
                    "schema": {
                        "id": "id",
                        "name_field": "plot_name",
                        "fields": [{"name": "plot_name", "type": "string"}],
                    },
                },
            },
            "datasets": {
                "occurrences": {
                    "description": "Occurrence records",
                    "schema": {
                        "id": "id",
                        "fields": [
                            {"name": "id", "type": "integer"},
                            {"name": "taxon_id", "type": "integer"},
                        ],
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


def test_references_are_exposed_as_reviewable_collection_candidates():
    service = CollectionCatalogService(import_config=_import_config())

    catalog = service.list_collections()
    collections = {item.name: item for item in catalog.collections}

    assert set(collections) == {"taxons", "plots"}
    assert collections["taxons"].source_type == "reference"
    assert collections["taxons"].review_status == "pending"
    assert collections["taxons"].roles == ["site", "api"]
    assert collections["taxons"].visible is True
    assert collections["taxons"].grain == "taxon"
    assert collections["taxons"].evidence[0].kind == "import_reference"


def test_metadata_overlay_overrides_label_roles_visibility_and_review_state():
    import_config = _import_config()
    import_config["metadata"] = {
        "collections": {
            "taxons": {
                "label": "Taxonomic review",
                "roles": ["technical", "standard"],
                "visible": False,
                "review_status": "accepted",
                "grain": "taxon",
            }
        }
    }
    service = CollectionCatalogService(import_config=import_config)

    taxons = service.get_collection("taxons")

    assert taxons.label == "Taxonomic review"
    assert taxons.roles == ["technical", "standard"]
    assert taxons.visible is False
    assert taxons.review_status == "accepted"
    assert taxons.source_type == "reference"


def test_manual_dataset_collection_is_persisted_without_requiring_page_visibility():
    import_config = _import_config()
    service = CollectionCatalogService(import_config=import_config)

    collection = service.create_collection(
        name="occurrence_records",
        source_type="dataset",
        source_name="occurrences",
        grain="occurrence",
        roles=["api", "standard"],
        visible=False,
        label="Occurrence records",
    )

    assert collection.name == "occurrence_records"
    assert collection.source_type == "dataset"
    assert collection.source_name == "occurrences"
    assert collection.roles == ["api", "standard"]
    assert collection.visible is False
    saved = import_config["metadata"]["collections"]["occurrence_records"]
    assert saved["source"] == {"type": "dataset", "name": "occurrences"}
    assert saved["grain"] == "occurrence"
    assert saved["review_status"] == "accepted"


def test_transform_only_groups_are_exposed_as_technical_candidates():
    service = CollectionCatalogService(
        import_config=_import_config(),
        transform_config=[
            {"group_by": "taxons", "sources": []},
            {"group_by": "plot_stats", "sources": [{"name": "raw_plot_stats"}]},
        ],
    )

    collections = {item.name: item for item in service.list_collections().collections}

    assert collections["plot_stats"].source_type == "transform_group"
    assert collections["plot_stats"].roles == ["technical"]
    assert collections["plot_stats"].visible is False
    assert collections["plot_stats"].review_status == "pending"


def test_list_sources_includes_references_datasets_and_transform_groups():
    service = CollectionCatalogService(
        import_config=_import_config(),
        transform_config=[
            {"group_by": "taxons"},
            {"group_by": "plot_stats"},
            {"group_by": "plot_stats"},
        ],
    )

    sources = {(source.type, source.name) for source in service.list_sources()}

    assert sources == {
        ("reference", "taxons"),
        ("reference", "plots"),
        ("dataset", "occurrences"),
        ("transform_group", "taxons"),
        ("transform_group", "plot_stats"),
    }


def test_update_collection_validates_roles_and_review_status():
    service = CollectionCatalogService(import_config=_import_config())

    updated = service.update_collection(
        "taxons",
        roles=["api", "api", "standard"],
        review_status="accepted",
        label="Accepted taxons",
    )

    assert updated.roles == ["api", "standard"]
    assert updated.review_status == "accepted"
    assert updated.label == "Accepted taxons"

    try:
        service.update_collection("taxons", roles=["invalid"])
    except ValueError as exc:
        assert "Invalid collection roles" in str(exc)
    else:
        raise AssertionError("Expected invalid role to be rejected")

    try:
        service.update_collection("taxons", review_status="invalid")
    except ValueError as exc:
        assert "review_status must be one of" in str(exc)
    else:
        raise AssertionError("Expected invalid review_status to be rejected")


def test_get_collection_rejects_missing_name():
    service = CollectionCatalogService(import_config=_import_config())

    try:
        service.get_collection("missing")
    except KeyError as exc:
        assert "Collection 'missing' not found" in str(exc)
    else:
        raise AssertionError("Expected missing collection to be rejected")


def test_unknown_manual_source_is_rejected_without_mutating_metadata():
    import_config = _import_config()
    service = CollectionCatalogService(import_config=import_config)

    try:
        service.create_collection(
            name="missing_source_collection",
            source_type="dataset",
            source_name="missing",
            grain="occurrence",
            roles=["api"],
        )
    except ValueError as exc:
        assert "Unknown dataset source 'missing'" in str(exc)
    else:
        raise AssertionError("Expected missing source to be rejected")

    assert import_config.get("metadata") is None
