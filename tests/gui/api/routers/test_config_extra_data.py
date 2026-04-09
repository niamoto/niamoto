"""Tests for extra_data schema extraction from config router helpers."""

from __future__ import annotations

import pandas as pd

from niamoto.gui.api.routers.config import _extract_extra_data_fields


def test_extract_extra_data_fields_handles_namespaced_enrichment_sources():
    """Nested multi-source enrichment payloads should be exposed as dotted fields."""

    df = pd.DataFrame(
        {
            "extra_data": [
                {
                    "api_enrichment": {
                        "sources": {
                            "endemia": {
                                "data": {
                                    "api_id": 42,
                                    "rank_name": "species",
                                },
                                "status": "completed",
                            },
                            "gbif": {
                                "data": {
                                    "usage_key": 987654,
                                },
                            },
                        }
                    },
                    "reviewed_by": "botanist",
                }
            ]
        }
    )

    schema = _extract_extra_data_fields(df)

    assert "extra_data.api_enrichment.sources.endemia.data.api_id" in schema
    assert "extra_data.api_enrichment.sources.endemia.data.rank_name" in schema
    assert "extra_data.api_enrichment.sources.endemia.status" in schema
    assert "extra_data.api_enrichment.sources.gbif.data.usage_key" in schema
    assert "extra_data.reviewed_by" in schema


def test_extract_extra_data_fields_keeps_legacy_flat_enrichment_paths():
    """Legacy single-source payloads should still be detected."""

    df = pd.DataFrame(
        {
            "extra_data": [
                {
                    "api_enrichment": {
                        "api_id": 21,
                        "rank_name": "species",
                    },
                    "enriched_at": "2026-04-09T11:00:00",
                }
            ]
        }
    )

    schema = _extract_extra_data_fields(df)

    assert "extra_data.api_enrichment.api_id" in schema
    assert "extra_data.api_enrichment.rank_name" in schema
    assert "extra_data.enriched_at" in schema
