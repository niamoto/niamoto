from unittest.mock import Mock

from niamoto.core.plugins.widgets.plotly_utils import render_plotly_figure
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
