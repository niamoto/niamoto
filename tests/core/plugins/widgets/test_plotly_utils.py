from unittest.mock import Mock

from niamoto.core.plugins.widgets.plotly_utils import (
    MUTED_CHART_COLORS,
    generate_muted_discrete_colors,
    generate_muted_gradient_colors,
    get_plotly_layout_defaults,
    render_plotly_figure,
)
from tests.common.base_test import NiamotoTestCase


class TestRenderPlotlyFigure(NiamotoTestCase):
    def test_preview_forces_hidden_legend(self):
        fig = Mock()
        fig.to_json.return_value = '{"data":[],"layout":{}}'

        html = render_plotly_figure(fig)

        self.assertIn("figure.layout.showlegend = false;", html)

    def test_preview_keeps_static_render_path(self):
        fig = Mock()
        fig.to_json.return_value = '{"data":[],"layout":{}}'

        html = render_plotly_figure(fig)

        self.assertIn("plotConfig.responsive = false;", html)
        self.assertIn("plotConfig.staticPlot = true;", html)


def test_layout_defaults_use_muted_colorway():
    defaults = get_plotly_layout_defaults()

    assert defaults["colorway"] == MUTED_CHART_COLORS


def test_generate_muted_discrete_colors_extends_palette_without_duplicates():
    colors = generate_muted_discrete_colors(len(MUTED_CHART_COLORS) + 3)

    assert colors[: len(MUTED_CHART_COLORS)] == MUTED_CHART_COLORS
    assert len(colors) == len(set(colors))
    assert all(color.startswith("#") and len(color) == 7 for color in colors)


def test_generate_muted_gradient_colors_softens_multi_color_gradient():
    colors = generate_muted_gradient_colors("#ff6b35", 4, "saturation")

    assert len(colors) == 4
    assert colors[0] != "#ff6b35"
    assert len(set(colors)) == 4
    assert all(color.startswith("#") and len(color) == 7 for color in colors)
