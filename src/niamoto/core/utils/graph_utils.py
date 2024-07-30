from typing import Dict, Any

import matplotlib.pyplot as plt
from matplotlib.patches import Circle


class GraphGenerator:
    """
    A class to generate various types of graphs based on given data and configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the GraphGenerator with the configuration.

        Args:
            config (Dict[str, Any]): Configuration for generating graphs.
        """
        self.config = config

    def generate_graph(
        self, data: Dict[str, Any], transformation: Dict[str, Any]
    ) -> None:
        """
        Generate a graph based on the provided data and transformation options.

        Args:
            data (Dict[str, Any]): The data to be plotted.
            transformation (Dict[str, Any]): Transformation options from the configuration.
        """
        chart_type = transformation["chart_type"]
        chart_options = transformation["chart_options"]

        if chart_type == "histogram":
            self.plot_histogram(data, chart_options)
        elif chart_type == "line":
            self.plot_line_chart(data, chart_options)
        elif chart_type == "donut":
            self.plot_donut_chart(data, chart_options)
        elif chart_type == "stacked_bar":
            self.plot_stacked_bar_chart(data, chart_options)
        elif chart_type == "gauge":
            self.plot_gauge_chart(data, chart_options)
        # Add other chart types here as needed

    def plot_histogram(self, data: Dict[str, Any], options: Dict[str, Any]) -> None:
        altitudes = data["altitudes"]
        forest = data["forest"]
        non_forest = data["non_forest"]

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(altitudes, forest, label="Forest", color="#548235", height=90)
        ax.barh(
            altitudes,
            non_forest,
            left=forest,
            label="Non-forest",
            color="#ecdcad",
            height=90,
        )
        ax.set_ylabel(options.get("x_label", "Altitude (m)"))
        ax.set_xlabel(options.get("y_label", "Area (ha)"))
        ax.set_title(options.get("title", "Altitudinal Distribution (Histogram)"))
        ax.legend(loc="lower right")
        ax.invert_yaxis()
        ax.set_xlim(0, max(max(forest), max(non_forest)) * 1.1)
        plt.tight_layout()
        plt.show()

    def plot_line_chart(self, data: Dict[str, Any], options: Dict[str, Any]) -> None:
        x_values = data["x_values"]
        y_values = data["y_values"]

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.plot(
            x_values, y_values, label=options.get("label", "Line Plot"), color="#548235"
        )
        ax.set_xlabel(options.get("x_label", "X-axis"))
        ax.set_ylabel(options.get("y_label", "Y-axis"))
        ax.set_title(options.get("title", "Line Chart"))
        ax.legend(loc="best")
        plt.tight_layout()
        plt.show()

    def plot_donut_chart(self, data: Dict[str, Any], options: Dict[str, Any]) -> None:
        sizes = data["sizes"]
        labels = options.get("categories", [])

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.add_artist(Circle((0, 0), 0.70, color="white"))
        ax.set_title(options.get("title", "Donut Chart"))
        plt.tight_layout()
        plt.show()

    def plot_stacked_bar_chart(
        self, data: Dict[str, Any], options: Dict[str, Any]
    ) -> None:
        categories = options.get("categories", [])
        values = data["values"]

        fig, ax = plt.subplots(figsize=(10, 8))
        bottom_values = [0] * len(categories)
        for value_set in values:
            ax.bar(categories, value_set, bottom=bottom_values)
            bottom_values = [sum(x) for x in zip(bottom_values, value_set)]

        ax.set_xlabel(options.get("x_label", "Category"))
        ax.set_ylabel(options.get("y_label", "Frequency (%)"))
        ax.set_title(options.get("title", "Stacked Bar Chart"))
        ax.legend(loc="best")
        plt.tight_layout()
        plt.show()

    def plot_gauge_chart(self, data: Dict[str, Any], options: Dict[str, Any]) -> None:
        # Gauge chart implementation can be complex and might need additional libraries like plotly
        pass
