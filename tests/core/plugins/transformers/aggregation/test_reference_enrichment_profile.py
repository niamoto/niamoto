"""Tests for the reference_enrichment_profile transformer plugin."""

import json
from unittest.mock import Mock

import pandas as pd

from niamoto.core.plugins.transformers.aggregation.reference_enrichment_profile import (
    ReferenceEnrichmentProfile,
)


def test_reference_enrichment_profile_transforms_json_extra_data_and_infers_formats():
    plugin = ReferenceEnrichmentProfile(Mock())
    data = pd.DataFrame(
        {
            "extra_data": [
                json.dumps(
                    {
                        "api_enrichment": {
                            "sources": {
                                "gbif": {
                                    "label": "GBIF",
                                    "status": "completed",
                                    "data": {
                                        "match": {
                                            "canonical_name": "Araucaria columnaris",
                                            "status": "ACCEPTED",
                                        },
                                        "links": {
                                            "species": "https://www.gbif.org/species/2685484"
                                        },
                                    },
                                },
                                "endemia": {
                                    "label": "Endemia",
                                    "status": "completed",
                                    "data": {
                                        "endemic": True,
                                    },
                                },
                            }
                        }
                    }
                )
            ]
        }
    )
    config = {
        "plugin": "reference_enrichment_profile",
        "params": {
            "source": "taxons",
            "summary_items": [
                {
                    "label": "Canonical name",
                    "source_id": "gbif",
                    "path": "match.canonical_name",
                },
                {
                    "label": "Status",
                    "source_id": "gbif",
                    "path": "match.status",
                },
            ],
            "sections": [
                {
                    "id": "links",
                    "title": "Links",
                    "source_id": "gbif",
                    "collapsed": True,
                    "items": [
                        {
                            "label": "GBIF page",
                            "path": "links.species",
                        }
                    ],
                },
                {
                    "id": "details",
                    "title": "Details",
                    "source_id": "endemia",
                    "items": [
                        {
                            "label": "Endemic",
                            "path": "endemic",
                        }
                    ],
                },
                {
                    "id": "missing",
                    "title": "Missing",
                    "source_id": "gbif",
                    "items": [
                        {
                            "label": "Unknown",
                            "path": "does.not.exist",
                        }
                    ],
                },
            ],
        },
    }

    result = plugin.transform(data, config)

    assert [item["label"] for item in result["summary"]] == [
        "Canonical name",
        "Status",
    ]
    assert result["summary"][0]["format"] == "text"
    assert result["summary"][1]["format"] == "badge"

    assert [section["id"] for section in result["sections"]] == ["links", "details"]
    assert result["sections"][0]["source_label"] == "GBIF"
    assert result["sections"][0]["items"][0]["format"] == "link"
    assert result["sections"][1]["items"][0]["value"] is True
    assert result["sections"][1]["items"][0]["format"] == "badge"

    assert result["sources"] == [
        {"id": "endemia", "label": "Endemia"},
        {"id": "gbif", "label": "GBIF"},
    ]
    assert result["meta"]["visible_sections"] == 2
    assert result["meta"]["source_count"] == 2
