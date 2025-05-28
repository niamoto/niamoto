# Import all widget plugins to ensure they are registered
from .bar_plot import BarPlotWidget
from .diverging_bar_plot import DivergingBarPlotWidget
from .donut_chart import DonutChartWidget
from .hierarchical_nav_widget import HierarchicalNavWidget
from .info_grid import InfoGridWidget
from .interactive_map import InteractiveMapWidget
from .line_plot import LinePlotWidget
from .radial_gauge import RadialGaugeWidget
from .raw_data_widget import RawDataWidget
from .scatter_plot import ScatterPlotWidget
from .stacked_area_plot import StackedAreaPlotWidget
from .summary_stats import SummaryStatsWidget
from .sunburst_chart import SunburstChartWidget
from .table_view import TableViewWidget

__all__ = [
    "BarPlotWidget",
    "DivergingBarPlotWidget",
    "DonutChartWidget",
    "HierarchicalNavWidget",
    "InfoGridWidget",
    "InteractiveMapWidget",
    "LinePlotWidget",
    "RadialGaugeWidget",
    "RawDataWidget",
    "ScatterPlotWidget",
    "StackedAreaPlotWidget",
    "SummaryStatsWidget",
    "SunburstChartWidget",
    "TableViewWidget",
]
