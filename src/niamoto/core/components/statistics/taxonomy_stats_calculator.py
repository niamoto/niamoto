"""
Taxonomy statistics calculator module.
"""
import time
from calendar import month_abbr
from typing import List, Dict, Any, Hashable, Union, Optional

import pandas as pd
from rich.progress import track
from sqlalchemy import select

from niamoto.common.database import Database
from .statistics_calculator import StatisticsCalculator
from niamoto.core.models import TaxonRef
from ...services.mapper import MapperService


class TaxonomyStatsCalculator(StatisticsCalculator):
    """
    A class used to calculate statistics for taxonomies.

    Inherits from:
        StatisticsCalculator
    """

    def __init__(
        self,
        db: Database,
        mapper_service: MapperService,
        occurrences: list[dict[Hashable, Any]],
        group_by: str,
    ):
        super().__init__(
            db, mapper_service, occurrences, group_by, log_component="taxonomy_stats"
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
        """
        Process a taxon.

        Args:
            taxon (niamoto.core.models.models.TaxonRef): The taxon to process.
        """
        try:
            taxon_id = self._extract_taxon_id(taxon)
            if taxon_id is None:
                return

            taxon_occurrences = self.get_taxon_occurrences(taxon)
            if not taxon_occurrences:
                return

            stats = self.calculate_stats(taxon_id, taxon_occurrences)

            self.create_or_update_stats_entry(taxon_id, stats)

        except Exception as e:
            self.logger.error(f"Failed to process taxon {taxon.id}: {e}")

    def calculate_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a group.

        Args:
            group_id (int): The group id.
            group_occurrences (list[dict[Hashable, Any]]): The group occurrences.

        Returns:
            Dict[str, Any]: The statistics.
        """
        stats: Dict[str, Union[int, Dict[str, Any], pd.Series[Any], float]] = {}

        # Convert occurrences to pandas DataFrame
        df_occurrences = pd.DataFrame(group_occurrences)

        # Iterate over fields in the mapping
        for field, field_config in self.fields.items():
            source_field = field_config.get("source_field")
            transformations = field_config.get("transformations", [])

            if source_field is None:
                if transformations:
                    for transformation in transformations:
                        transform_name = transformation.get("name")
                        column_name = f"{field}_{transform_name}"
                        if transform_name == "count":
                            stats[column_name] = len(group_occurrences)
                            break
                        elif transform_name == "top":
                            stats[column_name] = self.calculate_top_items(
                                group_occurrences, field_config
                            )
                        elif transform_name == "temporal_phenology":
                            stats[column_name] = self.calculate_temporal_phenology(
                                group_occurrences, field_config
                            )

            elif source_field in df_occurrences.columns:
                # Binary field (ex: um_occurrences)
                if field_config.get("field_type") == "BOOLEAN":
                    if source_field in df_occurrences.columns:
                        value_counts = df_occurrences[source_field].value_counts()
                        stats[f"{field}_true"] = value_counts.get(True, 0)
                        stats[f"{field}_false"] = value_counts.get(False, 0)

                # Geolocation field (ex: occurrence_location)
                elif field_config.get("field_type") == "GEOGRAPHY":
                    if source_field in df_occurrences.columns:
                        if transformations:
                            for transformation in transformations:
                                transform_name = transformation.get("name")
                                column_name = f"{field}_{transform_name}"
                                coordinates = self.extract_coordinates(
                                    df_occurrences, source_field
                                )
                                stats[f"{column_name}"] = {
                                    "type": "MultiPoint",
                                    "coordinates": coordinates,
                                }

                else:
                    # Other fields
                    field_values = df_occurrences[source_field]
                    field_values = field_values[
                        (field_values != 0) & (field_values.notnull())
                    ]

                    # Calculate transformations
                    transformations = field_config.get("transformations", [])
                    for transformation in transformations:
                        transform_name = transformation.get("name")
                        if hasattr(pd.Series, transform_name) and len(field_values) > 0:
                            transform_func = getattr(pd.Series, transform_name)
                            transform_result = transform_func(field_values)
                            if isinstance(transform_result, pd.Series):
                                stats[
                                    f"{field}_{transform_name}"
                                ] = transform_result.round(2)
                            else:
                                stats[f"{field}_{transform_name}"] = round(
                                    transform_result, 2
                                )

                    # Calculate bins
                    bins_config = field_config.get("bins")
                    if bins_config:
                        bins = bins_config["values"]
                        self.logger.debug(f"Bins for field {field}: {bins}")
                        if bins and len(field_values) > 0:
                            try:
                                bin_percentages = self.calculate_bins(
                                    field_values.tolist(), bins
                                )
                                stats[f"{field}_bins"] = bin_percentages
                            except ValueError as e:
                                self.logger.error(
                                    f"Error calculating bins for field {field}: {e}"
                                )

        return stats

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
        return [occ for occ in self.occurrences if occ[self.identifier] in taxon_ids]

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
