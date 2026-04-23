"""Tests for enrichment display catalog heuristics."""

from niamoto.core.enrichment_display import (
    build_default_panel_config,
    build_enrichment_catalog,
)


def test_endemia_catalog_skips_root_source_media_for_mixed_payload() -> None:
    catalog = build_enrichment_catalog(
        [
            {
                "api_enrichment": {
                    "sources": {
                        "api-endemia-nc": {
                            "label": "Endemia NC",
                            "status": "completed",
                            "data": {
                                "id_endemia": 9314,
                                "endemic": False,
                                "protected": False,
                                "endemia_url": "https://endemia.nc/flore/fiche9314",
                                "image_small_thumb": "https://img.example/small.jpg",
                                "image_big_thumb": "https://img.example/big.jpg",
                            },
                        }
                    }
                }
            }
        ]
    )

    endemia = next(item for item in catalog if item["id"] == "api-endemia-nc")
    field_paths = {field["path"] for field in endemia["fields"]}

    assert "." not in field_paths
    assert "image_small_thumb" in field_paths
    assert "image_big_thumb" in field_paths


def test_endemia_default_panel_prefers_explicit_image_field() -> None:
    catalog = build_enrichment_catalog(
        [
            {
                "api_enrichment": {
                    "sources": {
                        "api-endemia-nc": {
                            "label": "Endemia NC",
                            "data": {
                                "endemic": False,
                                "image_small_thumb": "https://img.example/small.jpg",
                                "image_big_thumb": "https://img.example/big.jpg",
                            },
                        }
                    }
                }
            }
        ]
    )

    panel = build_default_panel_config(
        next(item for item in catalog if item["id"] == "api-endemia-nc")
    )
    media_section = next(
        section for section in panel["sections"] if section["id"] == "media"
    )

    assert [item["path"] for item in media_section["items"]] == ["image_big_thumb"]


def test_catalog_keeps_root_media_for_image_list_payload() -> None:
    catalog = build_enrichment_catalog(
        [
            {
                "api_enrichment": {
                    "sources": {
                        "custom-gallery": {
                            "label": "Custom gallery",
                            "data": [
                                "https://img.example/a.jpg",
                                "https://img.example/b.jpg",
                            ],
                        }
                    }
                }
            }
        ]
    )

    gallery = next(item for item in catalog if item["id"] == "custom-gallery")
    root_field = next(field for field in gallery["fields"] if field["path"] == ".")

    assert root_field["format"] == "image"


def test_generic_panel_prefers_collection_and_best_image_variant() -> None:
    catalog = build_enrichment_catalog(
        [
            {
                "api_enrichment": {
                    "sources": {
                        "custom-media": {
                            "label": "Custom media",
                            "data": {
                                "images": [
                                    "https://img.example/a.jpg",
                                    "https://img.example/b.jpg",
                                ],
                                "image_small_thumb": "https://img.example/small.jpg",
                                "image_big_thumb": "https://img.example/big.jpg",
                            },
                        }
                    }
                }
            }
        ]
    )

    panel = build_default_panel_config(
        next(item for item in catalog if item["id"] == "custom-media")
    )
    media_section = next(
        section for section in panel["sections"] if section["id"] == "media"
    )

    assert [item["path"] for item in media_section["items"]] == [
        "images",
        "image_big_thumb",
    ]
