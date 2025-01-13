"""
Plot statistics calculator module.
"""
import time
from typing import List, Dict, Any, Hashable

import geopandas as gpd  # type: ignore
import numpy as np
import pandas as pd
from rich.progress import track
from sqlalchemy import Table, MetaData, Column, Integer

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.core.models import PlotRef
from .statistics_calculator import StatisticsCalculator


class PlotStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for plots.
    """

    def __init__(
        self, db: Database, occurrences: list[dict[Hashable, Any]], group_config: dict
    ):
        super().__init__(
            db=db,
            occurrences=occurrences,
            group_config=group_config,
            log_component="plot_stats",
        )
        self.config = Config()
        plots_config = self.config.sources.get("plots", {})
        plots_path = plots_config.get("path")
        if not plots_path:
            raise ValueError("No path configured for plots source in sources.yml")

        self.plots_data = self.load_plots_data(plots_path)
        self.identifier = group_config.get("identifier", "id_source")

    def load_plots_data(self, plots_path: str) -> pd.DataFrame:
        """
        Load plot data from GeoPackage file.

        Args:
            plots_path: Path to the GeoPackage file

        Returns:
            DataFrame containing plots data
        """
        try:
            gdf = gpd.read_file(plots_path)
            assert isinstance(gdf, pd.DataFrame), "gdf must be a pandas DataFrame"
            return gdf
        except Exception as e:
            self.logger.error(f"Error loading plots data from {plots_path}: {e}")
            raise

    def calculate_plot_stats(self) -> None:
        """Calculate statistics for all plots."""
        start_time = time.time()

        try:
            plots = self._retrieve_all_plots()
            self.initialize_stats_table()

            for plot in track(plots, description="Processing Plots..."):
                self.process_plot(plot)

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            total_time = time.time() - start_time
            self.console.print(
                f"⏱ Total processing time: {total_time:.2f} seconds",
                style="italic blue",
            )

    def process_plot(self, plot: PlotRef) -> None:
        """Process a plot."""
        try:
            # Extract the plot ID
            plot_id = self._extract_plot_id(plot)

            if plot_id is None:
                return

            # Get plot identifier from plot object
            plot_identifier = getattr(plot, "id_locality", None)

            if plot_identifier is None:
                return

            # Get plot occurrences
            plot_occurrences = self.get_plot_occurrences(plot_identifier)

            if not plot_occurrences:
                return

            # Calculate stats using plot_identifier
            stats = self.calculate_stats(plot_identifier, plot_occurrences)

            # Create/update stats entry using plot_id
            self.create_or_update_stats_entry(plot_id, stats)

        except Exception as e:
            print(f"Error processing plot {plot.id}: {e}")  # Debug
            self.logger.error(f"Failed to process plot {plot.id}: {e}")
            self.logger.exception("Full error details:")

    @staticmethod
    def _extract_plot_id(plot: PlotRef) -> int:
        """Extract the plot ID value."""
        return plot.id

    def calculate_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """Calculate statistics for each widget."""
        stats = {}
        df_occurrences = pd.DataFrame(group_occurrences)

        for widget_name, widget_config in self.widgets_data.items():
            for transform in widget_config.get("transformations", []):
                transform_name = transform.get("name")

                # 1. General info widget
                if transform_name == "collect_fields":
                    stats[widget_name] = self._process_collect_fields(
                        transform.get("items", []), df_occurrences, group_id
                    )

                # 2. Map panel widget
                elif transform_name == "get_geometry":
                    stats[widget_name] = self._process_geometry(group_id)

                # 3. Top families and species widgets
                elif transform_name == "top":
                    stats[widget_name] = self.calculate_top_items(
                        group_occurrences, transform
                    )

                # 4. Distribution widgets (dbh, strata)
                elif transform_name in ["dbh_bins", "histogram"]:
                    source_field = transform.get("source_field")
                    if source_field and source_field in df_occurrences.columns:
                        stats[widget_name] = self._process_histogram(
                            df_occurrences[source_field],
                            transform.get("bins", []),
                            transform.get("labels", []),
                        )

                # 5. Gauge widgets (mean value)
                elif transform_name == "mean_value":
                    source_field = transform.get("source_field")
                    if source_field and source_field in df_occurrences.columns:
                        stats[widget_name] = self._process_mean_value(
                            df_occurrences[source_field], transform
                        )

                # 6. Identity value widgets (values from plots)
                elif transform_name == "identity_value":
                    source_field = transform.get("source_field")
                    if source_field:
                        stats[widget_name] = self._process_identity_value(
                            group_id, source_field, transform
                        )

        return stats

    def _process_collect_fields(
        self, items: list, df: pd.DataFrame, plot_id: int
    ) -> Dict[str, Any]:
        """Process collect_fields transformation."""
        result = {}

        for item in items:
            source = item.get("source")
            field = item.get("field")
            value = None

            if source == "plot_ref":
                value = self._get_plot_field(field, plot_id)
            elif source == "plots":
                plot_data = self.plots_data[self.plots_data["id_locality"] == plot_id]
                if not plot_data.empty and field in plot_data.columns:
                    value = plot_data[field].iloc[0]

                    # Conversion des types numpy en types Python standard
                    if pd.notna(value):
                        if isinstance(value, (np.integer, np.int32, np.int64)):
                            value = int(value)
                        elif isinstance(value, (np.float32, np.float64)):
                            value = float(value)

                        if item.get("labels"):
                            labels = item.get("labels", {})
                            if isinstance(
                                labels, dict
                            ):  # Pour le cas des mappings type substrat
                                value = labels.get(str(value), str(value))
                            else:  # Pour le cas des listes type holdridge
                                try:
                                    value = labels[int(value) - 1]
                                except (IndexError, ValueError):
                                    value = str(value)
                        elif item.get("units"):
                            value = f"{value} {item.get('units')}"

            elif source == "occurrences":
                transform = item.get("transformation")
                if transform == "count":
                    value = int(len(df))  # Conversion explicite en int standard

            key = item.get("key", field)
            result[key] = value if pd.notna(value) else ""

        return result

    def _process_identity_value(
        self, plot_id: int, field: str, transform: dict
    ) -> Dict[str, Any]:
        """
        Process identity value from plots GeoPackage data.

        Args:
            plot_id: Plot identifier
            field: Field name to get from plots data
            transform: Transformation config containing units and max_value
        """
        try:
            # Récupérer la donnée depuis le GeoPackage
            plot_data = self.plots_data[self.plots_data["id_locality"] == plot_id]
            if plot_data.empty or field not in plot_data.columns:
                return {"value": None, "max": None, "units": transform.get("units", "")}

            value = plot_data[field].iloc[0]
            if pd.isna(value):
                return {"value": None, "max": None, "units": transform.get("units", "")}

            value = float(value)
            return {
                "value": value,
                "max": transform.get("max_value", value * 1.2),
                "units": transform.get("units", ""),
            }

        except Exception as e:
            self.logger.error(
                f"Error processing identity value for plot {plot_id}, field {field}: {e}"
            )
            return {"value": None, "max": None, "units": transform.get("units", "")}

    def _get_plot_field(self, field: str, plot_id: int) -> Any:
        """
        Get a field value from the plot_ref table.

        Args:
            field: Field name to get
            plot_id: Plot identifier (id)
        """
        plot = self.db.session.query(PlotRef).filter(PlotRef.id == plot_id).first()
        return getattr(plot, field, None)

    def _get_plot_data_field(self, field: str, plot_id: int) -> Any:
        """
        Get a field value from the plots GeoPackage data.

        Args:
            field: Field name to get
            plot_id: Plot identifier

        Returns:
            Field value or None if not found
        """
        try:
            plot_data = self.plots_data[self.plots_data["id"] == plot_id]
            if not plot_data.empty and field in plot_data.columns:
                return plot_data[field].iloc[0]
        except Exception as e:
            self.logger.error(
                f"Error getting plot data field {field} for plot {plot_id}: {e}"
            )
            return None
        return None

    def _process_histogram(
        self, series: pd.Series, bins: List[float], labels: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process histogram data.

        Args:
            series: Data series to process
            bins: List of bin boundaries
            labels: Optional list of labels for bins

        Returns:
            Dictionary containing histogram data
        """
        hist, bin_edges = np.histogram(series.dropna(), bins=bins)
        result = {"bins": bins[:-1], "counts": hist.tolist()}
        if labels:
            result["labels"] = labels
        return result

    def get_plot_occurrences(self, plot_id: int) -> list[dict[Hashable, Any]]:
        """Get plot occurrences using pivot table."""
        occurrences_plots = Table(
            self.group_config["pivot_table_name"],
            MetaData(),
            Column("id_occurrence", Integer, primary_key=True),
            Column("id_plot", Integer, primary_key=True),
        )

        # Base query
        query = self.db.session.query(occurrences_plots.c.id_occurrence).filter(
            occurrences_plots.c.id_plot == plot_id
        )

        # Apply filter if present in config
        # if "filter" in self.group_config:
        #     field = self.group_config["filter"].get("field")
        #     value = self.group_config["filter"].get("value")
        #     if field and value:
        #         query = query.filter(
        #             getattr(occurrences_plots.c, field) == value
        #         )

        occurrence_ids = [id[0] for id in query.all()]
        return [
            occ for occ in self.occurrences if occ[self.identifier] in occurrence_ids
        ]

    def _retrieve_all_plots(self) -> List[PlotRef]:
        """Retrieve all plots from the database."""
        return self.db.session.query(PlotRef).all()

    def _process_geometry(self, plot_id: int) -> Dict[str, Any]:
        """Process geometry transformation."""
        plot = (
            self.db.session.query(PlotRef)
            .filter(PlotRef.id_locality == plot_id)
            .first()
        )
        if plot and plot.geometry:
            return {
                "type": "Feature",
                "geometry": plot.geometry,
                "properties": {"id": plot.id, "name": plot.locality},
            }
        return {}

    @staticmethod
    def _process_mean_value(series: pd.Series, transform: dict) -> Dict[str, Any]:
        """
        Process mean value with units from config.

        Args:
            series: Data series to process
            transform: Transformation config containing units and max_value
        """
        mean_val = series.mean()
        if pd.isna(mean_val):
            return {"value": None, "max": None, "units": transform.get("units", "")}

        mean_val = float(mean_val)
        return {
            "value": mean_val,
            "max": transform.get("max_value", mean_val * 1.2),
            "units": transform.get("units", ""),
        }

    def _process_identity_value(
        self, plot_id: int, field: str, transform: dict
    ) -> Dict[str, Any]:
        """
        Process identity value from plots GeoPackage data.

        Args:
            plot_id: Plot identifier
            field: Field name to get from plots data
            transform: Transformation config containing units and max_value
        """
        try:
            # Récupérer la donnée depuis le GeoPackage
            plot_data = self.plots_data[self.plots_data["id_locality"] == plot_id]
            if plot_data.empty or field not in plot_data.columns:
                return {"value": None, "max": None, "units": transform.get("units", "")}

            value = plot_data[field].iloc[0]
            if pd.isna(value):
                return {"value": None, "max": None, "units": transform.get("units", "")}

            value = float(value)
            return {
                "value": value,
                "max": transform.get("max_value", value * 1.2),
                "units": transform.get("units", ""),
            }

        except Exception as e:
            self.logger.error(
                f"Error processing identity value for plot {plot_id}, field {field}: {e}"
            )
            return {"value": None, "max": None, "units": transform.get("units", "")}
