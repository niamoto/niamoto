"""Tests pour les modèles du moteur de preview."""

from niamoto.gui.api.services.preview_engine.models import (
    PreviewRequest,
    PreviewResult,
)


class TestPreviewRequest:
    """Tests du dataclass PreviewRequest."""

    def test_defaults(self):
        req = PreviewRequest()
        assert req.template_id is None
        assert req.group_by is None
        assert req.source is None
        assert req.entity_id is None
        assert req.mode == "full"
        assert req.inline is None

    def test_with_template_id(self):
        req = PreviewRequest(
            template_id="elevation_binned_distribution_bar_plot",
            group_by="taxons",
            mode="thumbnail",
        )
        assert req.template_id == "elevation_binned_distribution_bar_plot"
        assert req.group_by == "taxons"
        assert req.mode == "thumbnail"

    def test_with_inline(self):
        inline = {
            "transformer_plugin": "binned_distribution",
            "transformer_params": {"field": "elevation"},
            "widget_plugin": "bar_plot",
            "widget_params": None,
            "widget_title": "Test",
        }
        req = PreviewRequest(group_by="taxons", inline=inline)
        assert req.inline is not None
        assert req.inline["transformer_plugin"] == "binned_distribution"

    def test_frozen(self):
        """Les requêtes sont immutables."""
        req = PreviewRequest(template_id="test")
        try:
            req.template_id = "other"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


class TestPreviewResult:
    """Tests du dataclass PreviewResult."""

    def test_creation(self):
        result = PreviewResult(
            html="<html></html>",
            etag="abc123",
            preview_key="test:full",
        )
        assert result.html == "<html></html>"
        assert result.etag == "abc123"
        assert result.preview_key == "test:full"
        assert result.warnings == ()

    def test_with_warnings(self):
        result = PreviewResult(
            html="<html></html>",
            etag="abc123",
            preview_key="test:full",
            warnings=("Warning 1", "Warning 2"),
        )
        assert len(result.warnings) == 2

    def test_frozen(self):
        result = PreviewResult(
            html="<html></html>",
            etag="abc123",
            preview_key="test:full",
        )
        try:
            result.html = "other"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass


class TestPreviewMode:
    """Tests du type PreviewMode."""

    def test_valid_modes(self):
        req_full = PreviewRequest(mode="full")
        assert req_full.mode == "full"

        req_thumb = PreviewRequest(mode="thumbnail")
        assert req_thumb.mode == "thumbnail"
