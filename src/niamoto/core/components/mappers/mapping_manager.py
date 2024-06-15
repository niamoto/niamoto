import os

import click
import duckdb
import yaml
from typing import List, Any, Optional, Dict, Collection
from duckdb import DuckDBPyConnection
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.table import Table

from niamoto.common.database import Database
from niamoto.core.utils.csv_utils import analyze_csv_data_types, is_duckdb_type_numeric


class MappingManager:
    """
    A class used to manage the mapping of data.

    Attributes:
        db (Database): The database connection.
    """

    def __init__(self, db: Database):
        """
        Initializes the MappingManager with the database connection.

        Args:
            db (Database): The database connection.
        """
        self.db = db

    def generate_mapping(
        self,
        csvfile: str,
        group_by: str,
        reference_table_name: Optional[str] = None,
        reference_data_path: Optional[str] = None,
    ) -> None:
        """
        Generate a mapping from a CSV file.

        Args:
            csvfile (str): The path to the CSV file.
            group_by (str): The group by field.
            reference_table_name (Optional[str], optional): The reference table name. Defaults to None.
            reference_data_path (Optional[str], optional): The reference data path. Defaults to None.
        """
        console = Console()
        try:
            con = duckdb.connect()
            con.execute(
                f"CREATE TEMPORARY TABLE temp_csv AS SELECT * FROM READ_CSV_AUTO('{csvfile}')"
            )
            column_schema = analyze_csv_data_types(csvfile)
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Field", style="dim")
            table.add_column("Type")
            for col_name, col_type in column_schema:
                table.add_row(col_name, col_type)
            console.print(table)
            field_names = [col_name for col_name, col_type in column_schema]
            field_completer = WordCompleter(field_names)
            identifier_field = prompt(
                "Please select the field to use as the identifier: ",
                completer=field_completer,
            )
            console.print(
                f"[bold green]Identifier field selected:[/bold green] {identifier_field}"
            )

            # Remove the identifier field from the list of fields
            field_names.remove(identifier_field)

            # Prompt the user to select the fields to map
            chosen_fields = prompt(
                "Please enter the fields you want to map (separated by commas): ",
                completer=field_completer,
            )

            # Split the chosen fields and add them to the mapping
            selected_fields = [field.strip() for field in chosen_fields.split(",")]
            mapping_data = {}
            for column_name in selected_fields:
                column_type = next(
                    (ct for cn, ct in column_schema if cn == column_name), None
                )
                transforms, bins = self.get_transforms_and_bins(
                    con, column_name, column_type
                )
                column_mapping_data = {
                    "source_field": column_name,
                    "field_type": column_type,
                    "label": column_name.upper(),
                    "description": column_name,
                    "transformations": transforms,
                    "bins": bins,
                }
                mapping_data[column_name] = column_mapping_data
            self.db.commit_session()
            console.print(f"Mapping table updated for {csvfile}", style="italic green")

            # Load the existing configuration data
            config_path = os.path.join(os.getcwd(), "config.yml")
            with open(config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file) or {}

            # Ensure 'aggregations' section exists
            if "aggregations" not in config_data:
                config_data["aggregations"] = []

            # Check if an entry with the same 'group_by' value already exists
            existing_entry = next(
                (
                    entry
                    for entry in config_data["aggregations"]
                    if entry["group_by"] == group_by
                ),
                None,
            )

            if existing_entry:
                # Update the existing entry with the new mapping data
                existing_entry["identifier"] = identifier_field
                existing_entry["reference_table_name"] = reference_table_name
                existing_entry["reference_data_path"] = reference_data_path
                existing_entry["fields"].update(mapping_data)
            else:
                # Create a new mapping entry
                new_mapping_entry = {
                    "group_by": group_by,
                    "identifier": identifier_field,
                    "source_table_name": "occurrences",
                    "reference_table_name": reference_table_name,
                    "reference_data_path": reference_data_path,
                    "fields": mapping_data,
                }
                config_data["aggregations"].append(new_mapping_entry)

            # Write the updated configuration data to the file
            with open(config_path, "w") as config_file:
                yaml.safe_dump(
                    config_data,
                    config_file,
                    default_flow_style=None,
                    sort_keys=False,
                )
            console.print(
                f"Mapping data written to {config_path}", style="italic green"
            )

        except Exception as e:
            console.print(f"Error while generating mapping: {e}", style="bold red")

        finally:
            self.db.close_db_session()

    @staticmethod
    def add_mapping(field: str) -> str:
        """
        Add a new field to the mapping.

        Args:
            field (str): The field to be added.

        Returns:
            str: A message indicating the field has been added.
        """
        return f"Adding new field {field} to the mapping"
        # Implement the logic to add a new field to the existing mapping

    def get_transforms_and_bins(
        self, con: DuckDBPyConnection, column_name: str, column_type: Any
    ) -> tuple[list[dict[str, str]], Collection[str]]:
        """
        Get the transforms and bins for a column.

        Args:
            con (DuckDBPyConnection): The connection to use.
            column_name (str): The column name.
            column_type (Any): The column type.

        Returns:
            tuple[list[dict[str, str]], Collection[str]]: The transforms and bins.
        """
        apply_transforms = self.custom_confirm(
            f"Apply transformations for [bold]{column_name}[/bold]?", default=True
        )
        transforms = (
            self.determine_transformations(column_type) if apply_transforms else []
        )
        calculate_bins = self.custom_confirm(
            f"Calculate bins for [bold]{column_name}[/bold]?", default=True
        )
        bins = (
            self.calculate_default_bins(con, column_name, column_type)
            if calculate_bins
            else []
        )
        return transforms, bins

    @staticmethod
    def custom_confirm(question: str, default: bool = False) -> bool:
        """
        Custom confirm prompt.

        Args:
            question (str): The question to ask.
            default (bool, optional): The default answer. Defaults to False.

        Returns:
            bool: The user's answer.
        """
        console = Console()
        while True:
            console.print(question, end=" ")
            response = click.prompt(
                "(Y/n)" if default else "(y/N)", default="", show_default=False
            ).lower()
            if not response:
                return default
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                console.print("Invalid input. Please enter 'y' or 'n'.")

    @staticmethod
    def determine_transformations(data_type: str) -> List[Dict[str, str]]:
        """
        Determine the transformations for a data type.

        Args:
            data_type (str): The data type.

        Returns:
            List[Dict[str, str]]: The transformations.
        """
        if is_duckdb_type_numeric(data_type):
            return [
                {"name": "mean"},
                {"name": "max"},
                {"name": "median"},
                {"name": "min"},
            ]
        return []

    @staticmethod
    def calculate_default_bins(
        con: DuckDBPyConnection,
        column_name: str,
        column_type: str,
        num_intervals: int = 6,
    ) -> Dict[str, Any]:
        """
        Calculate the default bins for a column.

        Args:
            con (DuckDBPyConnection): The connection to use.
            column_name (str): The column name.
            column_type (str): The column type.
            num_intervals (int, optional): The number of intervals. Defaults to 6.

        Returns:
            Dict[str, Any]: The default bins.
        """
        if is_duckdb_type_numeric(column_type):
            if column_type == "BOOLEAN":
                return {}

            min_query = f"SELECT MIN({column_name}) FROM temp_csv"
            max_query = f"SELECT MAX({column_name}) FROM temp_csv"

            min_result = con.execute(min_query).fetchone()
            if min_result is not None:
                min_value = min_result[0]
            else:
                min_value = 0  # or any default value

            max_result = con.execute(max_query).fetchone()
            if max_result is not None:
                max_value = max_result[0]
            else:
                max_value = 0

            interval_width = (max_value - min_value) / num_intervals

            intervals = [
                min_value + i * interval_width for i in range(num_intervals + 1)
            ]

            # Check if the bin values are tight
            unique_intervals = sorted(
                set(int(round(interval)) for interval in intervals)
            )

            if len(unique_intervals) <= 3:
                # If the bin values are tight, use 3 decimals
                intervals = [round(interval, 3) for interval in intervals]
            else:
                # Otherwise, round the bins to whole numbers
                intervals = [int(round(interval)) for interval in intervals]

            return {
                "values": intervals,
                "chart_type": "bar",
                "chart_options": {
                    "title": f"{column_name.capitalize()} Distribution",
                    "color": "blue",
                },
            }

        return {}

    def get_mapping(self) -> List[Dict[str, Any]]:
        """
        Get the mapping.

        Returns:
            List[Dict[str, Any]]: The mapping.
        """
        config_path = os.path.join(os.getcwd(), "config.yml")
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file) or {}
                return config_data.get("aggregations", [])
        else:
            return []

    def get_sources(self) -> Dict[str, Any]:
        """
        Get the sources from the configuration file.

        Returns:
            Dict[str, Any]: The sources.
        """
        config_path = os.path.join(os.getcwd(), "config.yml")
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file) or {}
                return config_data.get("sources", {})
        else:
            return {}

    def get_group_config(self, group_by: str) -> Dict[str, Any]:
        """
        Get the group config for a group.

        Args:
            group_by (str): The group by field.

        Returns:
            Dict[str, Any]: The group config.
        """
        mapping_data = self.get_mapping()
        group_config = next(
            (entry for entry in mapping_data if entry["group_by"] == group_by), None
        )
        return group_config if group_config is not None else {}

    def get_fields(self, group_by: str) -> Dict[str, Any]:
        """
        Get the fields for a group.

        Args:
            group_by (str): The group by field.

        Returns:
            Dict[str, Any]: The fields.
        """
        group_config: Optional[Dict[str, Any]] = self.get_group_config(group_by)
        if group_config:
            fields: Dict[str, Any] = group_config["fields"]
            return fields
        else:
            return {}
