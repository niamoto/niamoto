"""
This module contains the StatisticsCalculator class, which is an abstract base class for calculating statistics.
"""
import json
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Dict, Any, Hashable, Tuple, Union

import pandas as pd
from rich.console import Console
from shapely import Point
from shapely.wkb import loads as load_wkb
from shapely.wkt import loads as load_wkt

from niamoto.common.config import Config
from niamoto.common.database import Database
from ...models import TaxonRef
from ...utils.logging_utils import setup_logging


class StatisticsCalculator(ABC):
    """
    An abstract base class for calculating statistics.

    Attributes:
        db (Database): The database connection.
        occurrences (list[dict[Hashable, Any]]): The occurrences.
        group_by (str): The group by field.
        group_config (dict[str, Any]): The group configuration.
    """

    def __init__(
        self,
        db: Database,
        occurrences: list[dict[Hashable, Any]],
        group_config: dict,
        log_component: str = "statistics",
    ):
        """
        Initializes the StatisticsCalculator.

        Args:
            db (Database): The database connection.
            occurrences (list[dict[Hashable, Any]]): The occurrences.
            group_config (dict): Configuration for the group from stats.yml
            log_component (str): Name of the logging component
        """
        self.db = db
        self.occurrences = occurrences
        self.group_config = group_config
        self.group_by = group_config.get("group_by")
        self.widgets_data = group_config.get("widgets_data", {})

        self.config = Config()
        sources_config = self.config.sources
        occurrences_config = sources_config.get("occurrences", {})
        self.occurrence_identifier = occurrences_config.get("identifier", "id_taxonref")

        # Setup logging
        self.logger = setup_logging(component_name=log_component)
        self.console = Console()

    @abstractmethod
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
        pass

    def initialize_stats_table(self) -> None:
        """
        Initialize the statistics table.
        """
        # Construct the name of the statistics table by appending "_stats" to the group name
        table_name = f"{self.group_by}_stats"

        # Call the create_stats_table method with the constructed table name
        # and initialize parameter set to True. This will create a new table in the database
        # with the given name. If a table with the same name already exists, it will be dropped
        # and a new one will be created.
        self.create_stats_table(table_name, initialize=True)

    def create_or_update_stats_entry(
        self, group_id: int, stats: Dict[str, Any]
    ) -> None:
        """
        Create or update a statistics entry.

        Args:
            group_id (int): The group id.
            stats (Dict[str, Any]): The statistics for each widget.
        """
        table_name = f"{self.group_by}_stats"
        # Create table if it doesn't exist
        if not self.db.has_table(table_name):
            self.create_stats_table(table_name)

        # Check if an entry exists for this group
        query = f"""
            SELECT COUNT(*) FROM {table_name} WHERE {self.group_by}_id = {group_id}
        """
        result = self.db.execute_select(query)

        if result is not None:
            count = result.scalar()
            if count is not None and count > 0:
                # Update existing entry
                set_clauses = []
                for widget_name, widget_data in stats.items():
                    json_data = json.dumps(widget_data).replace("'", "''")
                    set_clauses.append(f"{widget_name} = '{json_data}'")

                if set_clauses:
                    update_query = f"""
                        UPDATE {table_name}
                        SET {', '.join(set_clauses)}
                        WHERE {self.group_by}_id = {group_id}
                    """
                    self.db.execute_sql(update_query)
            else:
                # Insert new entry
                columns = [f"{self.group_by}_id"] + list(stats.keys())
                escaped_values = [str(group_id)]
                for value in stats.values():
                    json_data = json.dumps(value).replace("'", "''")
                    escaped_values.append(f"'{json_data}'")

                insert_query = f"""
                                INSERT INTO {table_name} ({', '.join(columns)})
                                VALUES ({', '.join(escaped_values)})
                            """
                self.db.execute_sql(insert_query)

    def create_stats_table(self, table_name: str, initialize: bool = False) -> None:
        """
        Create a statistics table with JSON columns for each widget.

        Args:
            table_name (str): The table name.
            initialize (bool): Whether to initialize the table. Defaults to False.
        """
        # Drop table if initialize is True
        if initialize:
            drop_query = f"DROP TABLE IF EXISTS {table_name}"
            self.db.execute_sql(drop_query)

        # Create table with primary key and JSON columns for each widget
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {self.group_by}_id INTEGER PRIMARY KEY"""

        # Add a JSON column for each widget in widgets_data
        for widget_name in self.widgets_data.keys():
            create_table_query += f",\n        {widget_name} JSON"

        create_table_query += "\n    )"

        try:
            self.db.execute_sql(create_table_query)
        except Exception as e:
            self.logger.error(f"Error creating table {table_name}: {e}")
            raise

    @staticmethod
    def calculate_bins(values: List[float], bins: List[float]) -> dict[str, float]:
        """
        Categorizes the field data into specified bins and calculates the frequencies for each category.
        The frequencies are then converted to percentages and returned as a dictionary.

        Args:
            values (List[float]): The list of field values.
            bins (List[int]): The list of bins to categorize the data.

        Returns:
            dict[Any, Any]: A dictionary containing the frequencies of the field data categories as percentages.
            The keys are the left endpoints of the intervals and the values are the percentages.
        """
        # Convert the list of values to a pandas Series
        data = pd.Series(values)

        # Distribute the data into categories
        binned_data = pd.cut(data.dropna(), bins=bins, right=False)

        # Calculate the frequencies for each category
        data_counts = binned_data.value_counts(sort=False, normalize=True)

        # Convert to percentages
        data_percentages = data_counts.apply(
            lambda x: round(x * 100, 2) if not pd.isna(x) else 0.0
        )

        # Convert to dictionary
        return {
            str(interval.left): percentage
            for interval, percentage in data_percentages.items()
            if isinstance(interval, pd.Interval)
        }

    @staticmethod
    def extract_coordinates(
        filtered_data: Any, source_field: str
    ) -> List[Dict[str, Any]]:
        """
        Extract unique geographic coordinates and their occurrence counts from the filtered data.

        Args:
            source_field (str): The source field containing the geographic coordinates.
            filtered_data (pd.DataFrame): The DataFrame containing the filtered data.

        Returns:
            List[Dict[str, int]]: A list of dictionaries containing unique coordinates and their occurrence counts.
        """
        coordinate_counts: defaultdict[Tuple[float, ...], int] = defaultdict(int)

        for point in filtered_data[source_field]:
            if pd.notna(point):  # Check that the point is not NaN
                if isinstance(point, Point):
                    # If the point is a shapely Point object
                    coordinates = (point.x, point.y)
                else:
                    try:
                        # Attempt to parse the point as WKB hex string
                        geom = load_wkb(bytes.fromhex(point))
                    except (ValueError, TypeError):
                        try:
                            # Attempt to parse as WKT
                            geom = load_wkt(point)
                        except (ValueError, TypeError):
                            # Fall back to assuming the point is a string in the format 'POINT (x y)'
                            try:
                                coordinates = tuple(
                                    map(
                                        float,
                                        str(point)
                                        .replace("POINT (", "")
                                        .replace(")", "")
                                        .split(),
                                    )
                                )
                            except ValueError:
                                continue  # Skip the point if it can't be parsed
                        else:
                            if isinstance(geom, Point):
                                coordinates = (geom.x, geom.y)
                            else:
                                continue  # Skip if it's not a Point geometry
                    else:
                        if isinstance(geom, Point):
                            coordinates = (geom.x, geom.y)
                        else:
                            continue  # Skip if it's not a Point geometry
                coordinate_counts[coordinates] += 1

        return [
            {"coordinates": list(coords), "count": count}
            for coords, count in coordinate_counts.items()
        ]

    def calculate_top_items(
        self, occurrences: list[dict[Hashable, Any]], transform: dict
    ) -> Union[dict[Any, Any], dict[str, Union[list[str], list[int]]]]:
        """
        Calculate the top most frequent items in the occurrences.

        Args:
            occurrences: List of occurrences to analyze
            transform: The transformation configuration
        """
        taxon_ids = {
            occ.get(self.occurrence_identifier)
            for occ in occurrences
            if occ.get(self.occurrence_identifier)
        }

        target_ranks = transform.get("target_ranks", [])
        top_count = transform.get("count", 10)

        if not taxon_ids:
            return {}

        # Query all taxons in a single query
        taxons = (
            self.db.session.query(TaxonRef).filter(TaxonRef.id.in_(taxon_ids)).all()
        )
        taxon_dict = {taxon.id: taxon for taxon in taxons}

        # Query parent taxons to ensure we have the complete hierarchy
        parent_ids = {
            taxon.parent_id for taxon in taxons if taxon.parent_id is not None
        }
        while parent_ids:
            parent_taxons = (
                self.db.session.query(TaxonRef)
                .filter(TaxonRef.id.in_(parent_ids))
                .all()
            )
            for parent_taxon in parent_taxons:
                taxon_dict[parent_taxon.id] = parent_taxon
            parent_ids = {
                taxon.parent_id
                for taxon in parent_taxons
                if taxon.parent_id is not None and taxon.parent_id not in taxon_dict
            }

        item_counts: dict[str, int] = {}

        for occ in occurrences:
            taxon_id = occ.get(self.occurrence_identifier)
            if taxon_id and taxon_id in taxon_dict:
                taxon = taxon_dict[taxon_id]
                item_name = self.find_item_name(taxon, taxon_dict, target_ranks)
                if item_name:
                    item_counts[item_name] = item_counts.get(item_name, 0) + 1

        # Sort the items by count in descending order
        sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)

        # Take the top 'top_count' items
        top_items = sorted_items[:top_count]

        # Separate the names and counts into two lists
        tops = [item[0] for item in top_items]
        counts = [item[1] for item in top_items]

        # Return the result in the desired format
        return {"tops": tops, "counts": counts}

    @staticmethod
    def find_item_name(
        taxon: TaxonRef, taxon_dict: Dict[int, TaxonRef], target_ranks: list[str]
    ) -> Any:
        """
        Find the item name based on target ranks by traversing up the hierarchy.

        Args:
            taxon ('niamoto.core.models.models.TaxonRef'): The taxon to start the search from.
            taxon_dict (Dict[int, 'niamoto.core.models.models.TaxonRef']): The dictionary of all taxons.
            target_ranks (list[str]): The list of target ranks to consider.

        Returns:
            str: The item name if found, otherwise None.
        """
        while taxon and taxon.rank_name.lower() not in target_ranks:
            taxon = taxon_dict.get(taxon.parent_id)
        return (
            taxon.full_name
            if taxon and taxon.rank_name.lower() in target_ranks
            else None
        )
