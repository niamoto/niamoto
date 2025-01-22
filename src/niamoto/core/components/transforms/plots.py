"""
Plot transforms calculator module.
"""
from typing import List, Dict, Any, Hashable

import geopandas as gpd  # type: ignore
import numpy as np
import pandas as pd
from sqlalchemy import Table, MetaData, Column, Integer

from niamoto.common.config import Config
from niamoto.common.database import Database
from niamoto.common.exceptions import (
    DatabaseError,
    FileError,
    DataImportError,
    ValidationError,
    ProcessError,
)
from niamoto.common.utils.error_handler import error_handler
from niamoto.core.models import PlotRef
from .base_transformer import BaseTransformer


class PlotTransformer(BaseTransformer):
    """
    A class used to calculate transforms for plots.
    """

    def __init__(
        self, db: Database, occurrences: list[dict[Hashable, Any]], group_config: dict
    ):
        super().__init__(
            db=db,
            occurrences=occurrences,
            group_config=group_config,
            log_component="transform",
        )
        self.config = Config()
        plots_config = self.config.imports.get("plots", {})
        plots_path = plots_config.get("path")
        if not plots_path:
            raise ValidationError(
                "plots_path", "No path configured for plots source in import.yml"
            )

        self.plots_data = self.load_plots_data(plots_path)
        self.identifier = group_config.get("identifier", "id_source")

    @error_handler(log=True, raise_error=True)
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
            raise FileError(plots_path, f"Error loading plots data: {str(e)}")

    @error_handler(log=True, raise_error=True)
    def calculate_plot_stats(self) -> None:
        """
        Calculate transforms for all plots.
        """
        try:
            # Retrieve plots and initialize the transforms table
            plots = self._retrieve_all_plots()
            self.initialize_group_table()

            # Use the generic progress method
            self._run_with_progress(plots, "Processing plots...", self.process_plot)

        except Exception as e:
            raise ProcessError("Failed to calculate plot transforms") from e

    @error_handler(log=True, raise_error=True)
    def process_plot(self, plot: PlotRef) -> None:
        """Process a plot."""

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
        stats = self.transform_group(plot_identifier, plot_occurrences)

        # Create/update stats entry using plot_id
        self.create_or_update_group_entry(plot_id, stats)

    @staticmethod
    def _extract_plot_id(plot: PlotRef) -> int:
        """Extract the plot ID value."""
        return plot.id

    @error_handler(log=True, raise_error=True)
    def transform_group(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """Calculate transforms for each widget."""
        try:
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
        except Exception as e:
            raise ProcessError(f"Failed to calculate stats for group {group_id}") from e

    @error_handler(log=True, raise_error=True)
    def _process_collect_fields(
        self, items: list, df: pd.DataFrame, plot_id: int
    ) -> Dict[str, Any]:
        """Process collect_fields transformation."""
        try:
            result = {}
            for item in items:
                source = item.get("source")
                field = item.get("field")
                value = None

                if source == "plot_ref":
                    value = self._get_plot_field(field, plot_id)
                elif source == "plots":
                    plot_data = self.plots_data[
                        self.plots_data["id_locality"] == plot_id
                    ]
                    if not plot_data.empty and field in plot_data.columns:
                        value = plot_data[field].iloc[0]

                        # Convert numpy types to python standard types
                        if pd.notna(value):
                            if isinstance(value, (np.integer, np.int32, np.int64)):
                                value = int(value)
                            elif isinstance(value, (np.float32, np.float64)):
                                value = float(value)

                            if item.get("labels"):
                                labels = item.get("labels", {})
                                if isinstance(
                                    labels, dict
                                ):  # For the case of substrate type mappings
                                    value = labels.get(str(value), str(value))
                                else:  # For the case of lists of type Holdridge
                                    try:
                                        value = labels[int(value) - 1]
                                    except (IndexError, ValueError):
                                        value = str(value)
                            elif item.get("units"):
                                value = f"{value} {item.get('units')}"

                elif source == "occurrences":
                    transform = item.get("transformation")
                    if transform == "count":
                        value = int(len(df))

                key = item.get("key", field)
                result[key] = value if pd.notna(value) else ""

            return result
        except Exception as e:
            raise ProcessError(
                f"Failed to process collect fields for plot {plot_id}"
            ) from e

    @error_handler(log=True, raise_error=True)
    def _get_plot_field(self, field: str, plot_id: int) -> Any:
        """
        Get a field value from the plot_ref table.

        Args:
            field: Field name to get
            plot_id: Plot identifier (id)
        """
        try:
            plot = self.db.session.query(PlotRef).filter(PlotRef.id == plot_id).first()
            return getattr(plot, field, None)
        except Exception as e:
            raise DatabaseError(
                f"Error getting plot field {field} for plot {plot_id}"
            ) from e

    @error_handler(log=True, raise_error=True)
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
            raise DataImportError(
                f"Error getting plot data field {field} for plot {plot_id}"
            ) from e
        return None

    @error_handler(log=True, raise_error=True)
    def get_plot_occurrences(self, plot_id: int) -> list[dict[Hashable, Any]]:
        """Get plot occurrences using pivot table."""
        try:
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
                occ
                for occ in self.occurrences
                if occ[self.identifier] in occurrence_ids
            ]
        except Exception as e:
            raise DatabaseError(
                f"Failed to get plot occurrences for plot {plot_id}"
            ) from e

    @error_handler(log=True, raise_error=True)
    def _retrieve_all_plots(self) -> List[PlotRef]:
        """Retrieve all plots from the database."""
        try:
            return self.db.session.query(PlotRef).all()
        except Exception as e:
            raise DatabaseError("Failed to retrieve all plots") from e

    @error_handler(log=True, raise_error=True)
    def _process_geometry(self, plot_id: int) -> Dict[str, Any]:
        """Process geometry transformation."""
        try:
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
        except Exception as e:
            raise DatabaseError(f"Failed to process geometry for plot {plot_id}") from e

    @error_handler(log=True, raise_error=True)
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
            raise ProcessError(
                f"Failed to process identity value for plot {plot_id}, field {field}"
            ) from e
