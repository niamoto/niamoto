"""Tests for the enrichment_panel widget."""

from unittest.mock import Mock

from niamoto.core.plugins.widgets.enrichment_panel import (
    EnrichmentPanelParams,
    EnrichmentPanelWidget,
)
from tests.common.base_test import NiamotoTestCase


class TestEnrichmentPanelWidget(NiamotoTestCase):
    """Test cases for EnrichmentPanelWidget."""

    def setUp(self):
        super().setUp()
        self.mock_db = Mock()
        self.widget = EnrichmentPanelWidget(self.mock_db)

    def test_render_structured_profile(self):
        params = EnrichmentPanelParams(summary_columns=2, show_source_badges=True)
        data = {
            "summary": [
                {
                    "label": "Canonical name",
                    "value": "Araucaria columnaris",
                    "format": "text",
                    "source_label": "GBIF",
                },
                {
                    "label": "Occurrences",
                    "value": 42,
                    "format": "number",
                    "source_label": "GBIF",
                },
            ],
            "sections": [
                {
                    "id": "links",
                    "title": "Links",
                    "source_label": "GBIF",
                    "collapsed": True,
                    "items": [
                        {
                            "label": "GBIF page",
                            "value": "https://www.gbif.org/species/2685484",
                            "format": "link",
                            "source_label": "GBIF",
                        }
                    ],
                },
                {
                    "id": "media",
                    "title": "Media",
                    "source_label": "Endemia",
                    "collapsed": False,
                    "items": [
                        {
                            "label": "Images",
                            "value": {
                                "thumbnail": "https://example.org/thumb.jpg",
                                "url": "https://example.org/full.jpg",
                            },
                            "format": "image",
                            "source_label": "Endemia",
                        }
                    ],
                },
                {
                    "id": "details",
                    "title": "Details",
                    "collapsed": False,
                    "items": [
                        {
                            "label": "Endemic",
                            "value": True,
                            "format": "badge",
                            "source_label": "Endemia",
                        },
                        {
                            "label": "Countries",
                            "value": ["NC", "VU"],
                            "format": "list",
                            "source_label": "GBIF",
                        },
                    ],
                },
            ],
            "sources": [
                {"id": "gbif", "label": "GBIF"},
                {"id": "endemia", "label": "Endemia"},
            ],
        }

        result = self.widget.render(data, params)

        self.assertIn("Araucaria columnaris", result)
        self.assertIn("42", result)
        self.assertIn("href=", result)
        self.assertIn("https://www.gbif.org/species/2685484", result)
        self.assertIn("<img", result)
        self.assertIn("Yes", result)
        self.assertIn("Countries", result)
        self.assertIn("NC", result)
        self.assertIn("GBIF", result)
        self.assertIn("Endemia", result)
        self.assertIn("<details", result)

    def test_render_empty_state(self):
        params = EnrichmentPanelParams(empty_message="Aucune donnée")

        result = self.widget.render({"summary": [], "sections": []}, params)

        self.assertIn("Aucune donnée", result)
