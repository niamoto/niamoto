import json
import os

import click
import duckdb
import yaml
from typing import List, Any, Optional, Tuple, Dict, Collection
from duckdb import DuckDBPyConnection
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.table import Table

from niamoto.common.database import Database
from niamoto.core.models import Mapping
from niamoto.core.utils.csv_utils import analyze_csv_data_types, is_duckdb_type_numeric


class MappingManager:
    def __init__(self, db: Database):
        self.db = db

    def generate_mapping(
        self,
        csvfile: str,
        group_by: str,
        reference_table_name: Optional[str] = None,
        reference_data_path: Optional[str] = None,
    ) -> None:
        console = Console()
        try:
            con = duckdb.connect()
            con.execute(
                f"CREATE TEMPORARY TABLE temp_csv AS SELECT * FROM READ_CSV_AUTO('{csvfile}')"
            )
            session = self.db.get_new_session()
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

            # Add the identifier field to the mapping
            self.add_mapping_entry(
                session,
                identifier_field,
                column_schema,
                group_by,
                reference_table_name,
                reference_data_path,
                is_identifier=True,
            )
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
                self.add_mapping_entry(
                    session,
                    column_name,
                    column_schema,
                    group_by,
                    reference_table_name,
                    reference_data_path,
                    transforms,
                    bins,
                )
                column_mapping_data = {
                    "target_field": column_name,
                    "field_type": column_type,
                    "label": column_name.upper(),
                    "description": column_name,
                    "transformations": transforms,
                    "bins": bins,
                    "is_identifier": False,
                }
                if column_name == identifier_field:
                    column_mapping_data["is_identifier"] = True
                mapping_data[column_name] = column_mapping_data
            self.db.commit_session()
            console.print(f"Mapping table updated for {csvfile}", style="italic green")

            # Write the mapping data to the mapping file
            mapping_path = os.path.join(os.getcwd(), "config", "mapping.yml")

            # Load the existing mapping data if the file exists
            if os.path.exists(mapping_path):
                with open(mapping_path, "r") as mapping_file:
                    existing_mapping_data = yaml.safe_load(mapping_file) or []
            else:
                existing_mapping_data = []

            # Check if an entry with the same 'group_by' value already exists
            existing_entry = next(
                (
                    entry
                    for entry in existing_mapping_data
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
                    "target_table_name": "occurrences",
                    "reference_table_name": reference_table_name,
                    "reference_data_path": reference_data_path,
                    "fields": mapping_data,
                }
                existing_mapping_data.append(new_mapping_entry)

            # Write the updated mapping data to the file
            with open(mapping_path, "w") as mapping_file:
                yaml.safe_dump(
                    existing_mapping_data,
                    mapping_file,
                    default_flow_style=None,
                    sort_keys=False,
                )
            console.print(
                f"Mapping data written to {mapping_path}", style="italic green"
            )

        except Exception as e:
            console.print(f"Error while generating mapping: {e}", style="bold red")

        finally:
            self.db.close_db_session()

    @staticmethod
    def add_mapping(field: str) -> str:
        return f"Adding new field {field} to the mapping"
        # Implement the logic to add a new field to the existing mapping

    @staticmethod
    def add_mapping_entry(
        session: Any,
        column_name: str,
        column_schema: List[Tuple[str, str]],
        group_by: str,
        reference_table_name: Optional[str],
        reference_data_path: Optional[str],
        transforms: Optional[List[Dict[str, str]]] = None,
        bins: Optional[Collection[str]] = None,
        is_identifier: bool = False,
    ) -> None:
        field_type = next((ct for cn, ct in column_schema if cn == column_name), None)
        mapping_entry = (
            session.query(Mapping)
            .filter_by(target_field=column_name, group_by=group_by)
            .first()
        )
        if mapping_entry:
            mapping_entry.field_type = field_type
            mapping_entry.reference_table_name = reference_table_name
            mapping_entry.reference_data_path = reference_data_path
            mapping_entry.is_identifier = is_identifier
            if transforms:
                mapping_entry.transformation = ",".join(
                    json.dumps(transform) for transform in transforms
                )
            if bins:
                mapping_entry.bins = ",".join(map(str, bins))
        else:
            new_entry = Mapping(
                target_table_name="occurrences",
                target_field=column_name,
                field_type=field_type,
                group_by=group_by,
                reference_table_name=reference_table_name,
                reference_data_path=reference_data_path,
                is_identifier=is_identifier,
                label=column_name.upper(),
                description=column_name,
                transformation=",".join(
                    json.dumps(transform) for transform in transforms
                )
                if transforms
                else None,
                bins=",".join(map(str, bins)) if bins else None,
            )
            session.add(new_entry)

    def get_transforms_and_bins(
        self, con: DuckDBPyConnection, column_name: str, column_type: Any
    ) -> tuple[list[dict[str, str]], Collection[str]]:
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

    @staticmethod
    def get_mapping() -> List[Dict[str, Any]]:
        mapping_path = os.path.join(os.getcwd(), "config", "mapping.yml")
        if os.path.exists(mapping_path):
            with open(mapping_path, "r") as mapping_file:
                mapping_data = yaml.safe_load(mapping_file) or []
        else:
            mapping_data = []
        return mapping_data

    def get_group_config(self, group_by: str) -> Dict[str, Any]:
        mapping_data = self.get_mapping()
        group_config = next(
            (entry for entry in mapping_data if entry["group_by"] == group_by), None
        )
        return group_config if group_config is not None else {}

    def get_fields(self, group_by: str) -> Dict[str, Any]:
        group_config: Optional[Dict[str, Any]] = self.get_group_config(group_by)
        if group_config:
            fields: Dict[str, Any] = group_config["fields"]
            return fields
        else:
            return {}
