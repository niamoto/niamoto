"""
Taxonomy statistics calculator module.
"""
import time
from calendar import month_abbr
from typing import List, Dict, Any, Hashable, Optional

import numpy as np
import pandas as pd
from rich.progress import track
from sqlalchemy import select

from niamoto.common.database import Database
from .statistics_calculator import StatisticsCalculator
from niamoto.core.models import TaxonRef


class TaxonomyStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for taxonomies.

    Inherits from:
        StatisticsCalculator
    """

    def __init__(
        self,
        db: Database,
        occurrences: list[dict[Hashable, Any]],
        group_config: dict,
    ):
        """
        Initialize TaxonomyStatsCalculator.

        Args:
            db (Database): The database connection
            occurrences (list[dict[Hashable, Any]]): The occurrences data
            group_config (dict): Configuration for taxonomy stats from stats.yml
        """
        super().__init__(
            db=db,
            occurrences=occurrences,
            group_config=group_config,
            log_component="taxonomy_stats",
        )

    def calculate_taxonomy_stats(self) -> None:
        """
        Calculate statistics for all taxonomies.
        """
        start_time = time.time()

        try:
            taxons = self._retrieve_all_taxons()

            self.initialize_stats_table()

            for taxon in track(taxons, description="Processing Taxons..."):
                self.process_taxon(taxon)

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
        finally:
            total_time = time.time() - start_time
            self.console.print(
                f"⏱ Total processing time: {total_time:.2f} seconds",
                style="italic blue",
            )

    def process_taxon(self, taxon: TaxonRef) -> None:
        """Process a taxon."""
        try:
            taxon_id = self._extract_taxon_id(taxon)

            if taxon_id is None:
                self.logger.debug("Skipping taxon - no ID found")
                return

            taxon_occurrences = self.get_taxon_occurrences(taxon)

            if not taxon_occurrences:
                self.logger.debug("Skipping taxon - no occurrences found")
                return

            stats = self.calculate_stats(taxon_id, taxon_occurrences)

            self.create_or_update_stats_entry(taxon_id, stats)

        except Exception as e:
            self.logger.error(f"Failed to process taxon {taxon.id}: {e}")
            # Ajoutons la stacktrace complète
            self.logger.exception("Full error details:")

    def calculate_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for each widget defined in the configuration.

        Args:
            group_id: ID of the taxonomic group
            group_occurrences: List of occurrences for this group

        Returns:
            Dictionary with widget names as keys and their calculated statistics as values
        """
        stats = {}
        df_occurrences = pd.DataFrame(group_occurrences)

        # Process each widget
        for widget_name, widget_config in self.widgets_data.items():
            transformations = widget_config.get("transformations", [])
            for transform in transformations:
                transform_name = transform.get("name")

                # 1. General info widget
                if transform_name == "collect_fields":
                    stats[widget_name] = self._process_collect_fields(
                        transform.get("items", []), df_occurrences, group_id
                    )

                # 2. Distribution map widget
                elif transform_name == "coordinates":
                    source_field = transform.get("source_field")
                    if source_field in df_occurrences.columns:
                        stats[widget_name] = self._process_coordinates(
                            df_occurrences, source_field
                        )

                # 3. Top species widget
                elif transform_name == "top":
                    stats[widget_name] = self.calculate_top_items(
                        group_occurrences, transform
                    )

                # 4. Distribution substrat widget
                elif transform_name == "count_bool":
                    source_field = transform.get("source_field")
                    if source_field in df_occurrences.columns:
                        counts = df_occurrences[source_field].value_counts()
                        stats[widget_name] = {
                            "um": int(counts.get(True, 0)),
                            "num": int(counts.get(False, 0)),
                        }

                # 5. Phenology distribution widget
                elif transform_name == "temporal_phenology":
                    stats[widget_name] = self._process_temporal_phenology(
                        df_occurrences,
                        transform.get("source_fields", {}),
                        transform.get("time_field"),
                    )

                # 6. Distribution widgets (dbh, elevation, rainfall, holdridge, strata)
                elif transform_name in ["dbh_bins", "histogram"]:
                    source_field = transform.get("source_field")
                    if source_field in df_occurrences.columns:
                        stats[widget_name] = self._process_histogram(
                            df_occurrences[source_field],
                            transform.get("bins", []),
                            transform.get("labels", []),
                        )

                # 7. Gauge widgets (max_value)
                elif transform_name == "max_value":
                    source_field = transform.get("source_field")
                    if source_field in df_occurrences.columns:
                        stats[widget_name] = self._process_max_value(
                            df_occurrences[source_field], transform
                        )

                # 8. Stats widgets (min, mean, max)
                elif transform_name == "stats_min_mean_max":
                    source_field = transform.get("source_field")
                    if source_field in df_occurrences.columns:
                        stats[widget_name] = self._process_min_mean_max(
                            df_occurrences[source_field], transform
                        )

        return stats

    def _process_collect_fields(
        self, items: list, df: pd.DataFrame, taxon_id: int
    ) -> Dict[str, Any]:
        """
        Process collect_fields transformation.

        Args:
            items (list): List of fields to collect
            df (pd.DataFrame): DataFrame of occurrences
            taxon_id (int): The ID of the current taxon

        Returns:
            Dict[str, Any]: Collected field values
        """
        result = {}

        for item in items:
            source = item.get("source")
            field = item.get("field")
            value = None

            if source == "taxonomy":
                # Get value from taxonomy table
                value = self._get_taxonomy_field(field, taxon_id)
            elif source == "occurrences":
                # Calculate from occurrences
                transform = item.get("transformation")
                if transform == "count":
                    value = len(df)

            key = item.get("key", field)
            result[key] = value if value is not None else ""

        return result

    def _get_taxonomy_field(self, field: str, taxon_id: int) -> Any:
        """
        Get a field value from the taxonomy table for a specific taxon.
        """
        try:
            # Construisons et exécutons une requête explicite avec SQLAlchemy
            taxon = (
                self.db.session.query(TaxonRef).filter(TaxonRef.id == taxon_id).first()
            )

            if taxon is None:
                print(f"No taxon found for id {taxon_id}")
                return ""

            # On accède à l'attribut via getattr
            value = getattr(taxon, field, None)

            return str(value) if value is not None else ""

        except Exception as e:
            print(f"Error getting taxonomy field {field} for taxon {taxon_id}: {e}")
            return ""

    def _process_coordinates(self, df: pd.DataFrame, field: str) -> Dict[str, Any]:
        """Process coordinates transformation."""
        if field and field in df.columns:
            coordinates = self.extract_coordinates(df, field)
            return {"type": "MultiPoint", "coordinates": coordinates}
        return {}

    @staticmethod
    def _process_min_mean_max(series: pd.Series, transform: dict) -> Dict[str, Any]:
        """
        Process min/mean/max statistics for a series.

        Args:
            series: The data series to process
            transform: The transformation configuration containing units and max_value
        """
        result = {
            "min": float(series.min()) if not pd.isna(series.min()) else None,
            "mean": float(series.mean()) if not pd.isna(series.mean()) else None,
            "max": float(series.max()) if not pd.isna(series.max()) else None,
            "units": transform.get("units", ""),
        }

        if "max_value" in transform:
            result["max_value"] = transform["max_value"]

        return result

    @staticmethod
    def _process_max_value(series: pd.Series, transform: dict) -> Dict[str, Any]:
        """
        Process max value with appropriate units from config.

        Args:
            series: The data series to process
            transform: The transformation configuration containing units and max_value
        """
        max_val = series.max()

        if pd.isna(max_val):
            return {"value": None, "max": None, "units": transform.get("units", "")}

        max_val = float(max_val)
        return {
            "value": max_val,
            "max": transform.get("max_value", max_val * 1.2),
            "units": transform.get("units", ""),
        }

    @staticmethod
    def _process_histogram(
        series: pd.Series, bins: List[float], labels: List[str] = None
    ) -> Dict[str, Any]:
        """Process histogram data."""
        hist, bin_edges = np.histogram(series.dropna(), bins=bins)
        result = {
            "bins": bins[:-1],
            "counts": hist.tolist(),
        }
        if labels:
            result["labels"] = labels
        return result

    @staticmethod
    def _process_temporal_phenology(
        df: pd.DataFrame, source_fields: Dict[str, str], time_field: str
    ) -> Dict[str, Any]:
        """Process temporal phenology data."""
        if not all(
            field in df.columns for field in [time_field] + list(source_fields.values())
        ):
            return {}

        df[time_field] = pd.to_numeric(df[time_field], errors="coerce")

        monthly_data = {name: [0] * 12 for name in source_fields.keys()}

        for month in range(1, 13):
            month_data = df[df[time_field] == month]
            if not month_data.empty:
                for phenology_name, field_name in source_fields.items():
                    if field_name in month_data:
                        value = (month_data[field_name].sum() / len(month_data)) * 100
                        monthly_data[phenology_name][month - 1] = round(value, 2)

        return {
            "month_data": monthly_data,
            "labels": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
        }

    @staticmethod
    def calculate_temporal_phenology(
        occurrences: list[dict[Hashable, Any]], field_config: dict
    ) -> Dict[str, Any]:
        """
            Calculate temporal phenology.
        Args:
            occurrences(list[dict[Hashable, Any]]): The occurrences data.
            field_config(dict): The field configuration.

        Returns:
            Dict[str, Any]: The temporal phenology data.

        """
        df = pd.DataFrame(occurrences)
        time_config = field_config["time_grouping"]
        time_field = time_config["field"]
        grouping_type = time_config["type"]

        # Get the field names from the configuration
        source_fields = field_config["source_fields"]

        # Verify all required fields are present
        required_fields = [time_field] + list(source_fields.values())
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(
                    f"'{field}' column is missing from the occurrences data"
                )

        df[time_field] = pd.to_numeric(df[time_field], errors="coerce")

        if grouping_type == "month":
            groups = range(1, 13)  # 1 to 12 for months
            labels = month_abbr[1:]  # Jan, Feb, Mar, etc.
        else:
            raise ValueError(f"Unsupported grouping type: {grouping_type}")

        phenology_data = {field_name: [] for field_name in source_fields.keys()}

        for month in groups:
            month_data = df[df[time_field] == month]
            total_obs = len(month_data)

            if total_obs > 0:
                for field_name, field_column in source_fields.items():
                    field_percent = month_data[field_column].sum() / total_obs * 100
                    phenology_data[field_name].append(round(field_percent, 2))
            else:
                for field_name in source_fields.keys():
                    phenology_data[field_name].append(0)

        return {"data": phenology_data, "labels": labels}

    def get_taxon_occurrences(self, taxon: TaxonRef) -> list[dict[Hashable, Any]]:
        """
        Get taxon occurrences.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to get occurrences for.

        Returns:
            list[dict[Hashable, Any]]: The taxon occurrences.
        """
        taxon_ids = self.get_taxon_and_descendant_ids(taxon)
        return [
            occ
            for occ in self.occurrences
            if occ[self.occurrence_identifier] in taxon_ids
        ]

    def get_taxon_and_descendant_ids(self, taxon: TaxonRef) -> List[int]:
        """
        Get taxon and descendant ids.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to get ids for.

        Returns:
            List[int]: The taxon and descendant ids.
        """
        taxon_ids = (
            self.db.session.query(TaxonRef.id)
            .filter(TaxonRef.lft >= taxon.lft, TaxonRef.rght <= taxon.rght)
            .all()
        )
        return [taxon_id[0] for taxon_id in taxon_ids]

    def _retrieve_all_taxons(self) -> List[TaxonRef]:
        """
        Retrieve all taxons from the database.

        Returns:
            List[TaxonRef]: A list of taxon references.
        """
        return self.db.session.query(TaxonRef).all()

    def _extract_taxon_id(self, taxon: TaxonRef) -> Optional[int]:
        """
        Extract the taxon ID value.

        Args:
            taxon (TaxonRef): The taxon from which to extract the ID.

        Returns:
            int (Optional[int]): The taxon ID.
        """
        return self.db.session.execute(select(taxon.id)).scalar()
