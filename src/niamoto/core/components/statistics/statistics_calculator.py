import json
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Dict, Any, Hashable, Tuple, Union

import duckdb
import pandas as pd

from niamoto.common.database import Database
from niamoto.core.services.mapper import MapperService


class StatisticsCalculator(ABC):
    """
    An abstract base class for calculating statistics.

    Attributes:
        db (Database): The database connection.
        con (duckdb.DuckDBPyConnection): The DuckDB connection.
        mapper_service (MapperService): The mapper service.
        occurrences (list[dict[Hashable, Any]]): The occurrences.
        group_by (str): The group by field.
        group_config (dict[str, Any]): The group configuration.
        identifier (str): The identifier.
        reference_table_name (str): The reference table name.
        reference_data_path (str): The reference data path.
        fields (dict[str, Any]): The fields.
    """

    def __init__(
        self,
        db: Database,
        mapper_service: MapperService,
        occurrences: list[dict[Hashable, Any]],
        group_by: str,
    ):
        """
        Initializes the StatisticsCalculator with the database connection, mapper service, occurrences, and group by field.

        Args:
            db (Database): The database connection.
            mapper_service (MapperService): The mapper service.
            occurrences (list[dict[Hashable, Any]]): The occurrences.
            group_by (str): The group by field.
        """
        self.db = db
        self.con = duckdb.connect(self.db.db_path)
        self.mapper_service = mapper_service
        self.occurrences = occurrences
        self.group_by = group_by
        self.group_config = self.mapper_service.get_group_config(group_by)
        self.identifier = self.group_config.get("identifier")
        self.reference_table_name = self.group_config.get("reference_table_name")
        self.reference_data_path = self.group_config.get("reference_data_path")
        self.fields = self.mapper_service.get_fields(group_by)

    @abstractmethod
    def calculate_specific_stats(
        self, group_id: int, group_occurrences: list[dict[Hashable, Any]]
    ) -> Dict[str, Any]:
        """
        Abstract method to calculate specific statistics for a group.

        Args:
            group_id (int): The group id.
            group_occurrences (list[dict[Hashable, Any]]): The group occurrences.

        Returns:
            Dict[str, Any]: The specific statistics.
        """
        pass

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
            target_field = field_config.get("target_field")

            if target_field is None:
                # Special field without target_field (ex: total_occurrences)
                if field_config.get("transformations"):
                    for transformation in field_config.get("transformations", []):
                        if transformation.get("name") == "count":
                            stats[field] = len(group_occurrences)
                            break

            elif target_field in df_occurrences.columns:
                # Binary field (ex: um_occurrences)
                if field_config.get("field_type") == "BOOLEAN":
                    if target_field in df_occurrences.columns:
                        value_counts = df_occurrences[target_field].value_counts()
                        stats[f"{field}_true"] = value_counts.get(True, 0)
                        stats[f"{field}_false"] = value_counts.get(False, 0)

                # Geolocation field (ex: occurrence_location)
                elif field_config.get("field_type") == "GEOGRAPHY":
                    if target_field in df_occurrences.columns:
                        coordinates = self.extract_coordinates(df_occurrences)
                        stats[f"{field}"] = {
                            "type": "MultiPoint",
                            "coordinates": coordinates,
                        }

                else:
                    # Other fields
                    field_values = df_occurrences[target_field]
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
                        if bins and len(field_values) > 0:
                            bin_percentages = self.calculate_bins(
                                field_values.tolist(), bins
                            )
                            stats[f"{field}_bins"] = bin_percentages

        # Add group-specific stats
        specific_stats = self.calculate_specific_stats(group_id, group_occurrences)
        stats.update(specific_stats)

        return stats

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
            stats (Dict[str, Any]): The statistics.
        """
        table_name = f"{self.group_by}_stats"
        # Check if the table exists, otherwise create it
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
                # Update the existing entry
                update_query = f"""
                        UPDATE {table_name}
                        SET {', '.join(f"{key} = '{json.dumps(value)}'" if isinstance(value, dict) else f"{key} = '{value}'" for key, value in stats.items())}
                        WHERE {self.group_by}_id = {group_id}
                    """
                self.db.execute_sql(update_query)
            else:
                # Insert a new entry
                insert_query = f"""
                        INSERT INTO {table_name} ({self.group_by}_id, {', '.join(stats.keys())})
                        VALUES ({group_id}, {', '.join(f"'{json.dumps(value)}'" if isinstance(value, dict) else f"'{value}'" for value in stats.values())})
                    """
                self.db.execute_sql(insert_query)

    def create_stats_table(self, table_name: str, initialize: bool = False) -> None:
        """
        Create a statistics table.

        Args:
            table_name (str): The table name.
            initialize (bool, optional): Whether to initialize the table. Defaults to False.
        """
        if initialize:
            drop_query = f"DROP TABLE IF EXISTS {table_name}"
            self.con.execute(drop_query)

        fields_sql = [f"{self.group_by}_id INTEGER PRIMARY KEY"]

        for field, config in self.fields.items():
            target_field = config.get("target_field")

            if target_field is None:
                # Special field without target_field (ex: total_occurrences)
                field_name = field
                fields_sql.append(f"{field_name} {config.get('field_type', 'INTEGER')}")

            else:
                # Binary field (ex: um_occurrences)
                if config.get("field_type") == "BOOLEAN":
                    fields_sql.append(f"{field}_true INTEGER")
                    fields_sql.append(f"{field}_false INTEGER")

                # Geolocation field (ex: occurrence_location)
                elif config.get("field_type") == "GEOGRAPHY":
                    fields_sql.append(f"{field} TEXT")

                else:
                    # Other fields
                    for transformation in config.get("transformations", []):
                        transform_name = transformation.get("name")
                        field_name = f"{field}_{transform_name}"
                        fields_sql.append(
                            f"{field_name} {config.get('field_type', 'DOUBLE')}"
                        )

                    # Generate a column for the bins, if specified
                    if "bins" in config:
                        bins_field_name = f"{field}_bins"
                        fields_sql.append(f"{bins_field_name} TEXT")

        # Creating the table with all necessary columns
        create_query = f"CREATE TABLE {table_name} ({', '.join(fields_sql)})"
        self.con.execute(create_query)

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
    def extract_coordinates(filtered_data: Any) -> List[Dict[str, Any]]:
        """
        Extract unique geographic coordinates and their occurrence counts from the filtered data.

        Args:
            filtered_data (pd.DataFrame): The DataFrame containing the filtered data.

        Returns:
            List[Dict[str, int]]: A list of dictionaries containing unique coordinates and their occurrence counts.
        """
        coordinate_counts: defaultdict[Tuple[float, ...], int] = defaultdict(int)

        for point in filtered_data["geo_pt"]:
            if pd.notna(point):  # Check that the point is not NaN
                coordinates = tuple(
                    map(
                        float,
                        str(point).replace("POINT (", "").replace(")", "").split(),
                    )
                )
                coordinate_counts[coordinates] += 1

        return [
            {"coordinates": list(coords), "count": count}
            for coords, count in coordinate_counts.items()
        ]
