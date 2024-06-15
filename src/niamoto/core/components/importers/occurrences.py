# components/importers/occurrences.py

import duckdb
import pandas as pd
import sqlalchemy
from typing import Any
from rich.console import Console
from rich.progress import Progress


class OccurrenceImporter:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)

    @staticmethod
    def analyze_data(csvfile: str) -> Any:
        """
        Analyzes the data types of columns in a CSV file.

        Args:
            csvfile (str): Path to the CSV file to be analyzed.

        Returns:
            List[Tuple[str, str]]: A list of tuples with column names and types.
        """
        con = duckdb.connect()
        con.execute(
            f"CREATE TEMPORARY TABLE temp_csv AS SELECT * FROM READ_CSV_AUTO('{csvfile}')"
        )
        types_info = con.execute("DESCRIBE temp_csv").fetchall()
        con.close()

        return [(col_info[0], col_info[1]) for col_info in types_info]

    def import_occurrences(self, csvfile: str, taxon_id_column: str) -> str:
        """
        Creates the 'occurrences' table based on the CSV file schema and imports the data.

        Args:
            csvfile (str): Path to the CSV file to be imported.
            taxon_id_column (str): Name of the column in the CSV that corresponds to the taxon ID.

        Returns:
            str: A message indicating the number of imported occurrences.
        """
        try:
            # Analyse the CSV file to get the schema
            column_schema = self.analyze_data(csvfile)

            # Ensure the taxon_id_column exists in the schema
            if taxon_id_column not in [
                col_name for col_name, col_type in column_schema
            ]:
                raise ValueError(f"Column {taxon_id_column} not found in CSV file.")

            # Check if 'id' column exists in the CSV schema
            id_column_exists = any(col_name == "id" for col_name, _ in column_schema)

            # Generate columns for SQL CREATE TABLE statement
            columns_sql = ", ".join(
                [f"{col_name} {col_type}" for col_name, col_type in column_schema]
            )
            if not id_column_exists:
                columns_sql = f"id BIGINT PRIMARY KEY, {columns_sql}"
            columns_sql += ", taxon_ref_id BIGINT REFERENCES taxon_ref(id)"

            # Drop the existing occurrences table if it exists
            drop_table_sql = "DROP TABLE IF EXISTS occurrences;"
            self.con.execute(drop_table_sql)

            # Create the 'occurrences' table with a foreign key to 'taxon_ref'
            create_table_sql = f"CREATE TABLE occurrences ({columns_sql});"
            self.con.execute(create_table_sql)

            # Import the data with a spinner
            with Console().status(
                "[bold green]Importing occurrences...", spinner="dots"
            ):
                column_names = ", ".join(
                    [
                        col_name
                        for col_name, col_type in column_schema
                        if col_name != taxon_id_column
                    ]
                )
                if not id_column_exists:
                    import_csv_sql = f"""
                        INSERT INTO occurrences (id, {column_names}, taxon_ref_id)
                        SELECT row_number() OVER () AS id, {column_names}, taxon_ref.id AS taxon_ref_id
                        FROM read_csv_auto('{csvfile}') AS csv
                        LEFT JOIN taxon_ref ON csv.{taxon_id_column} = taxon_ref.id
                        ON CONFLICT (id) DO NOTHING;
                        """
                else:
                    import_csv_sql = f"""
                        INSERT INTO occurrences ({column_names}, taxon_ref_id)
                        SELECT {column_names}, taxon_ref.id AS taxon_ref_id
                        FROM read_csv_auto('{csvfile}') AS csv
                        LEFT JOIN taxon_ref ON csv.{taxon_id_column} = taxon_ref.id
                        ON CONFLICT (id) DO NOTHING;
                        """
                self.con.execute(import_csv_sql)

            # Count the number of imported occurrences
            count_sql = "SELECT COUNT(*) FROM occurrences;"
            result = self.con.execute(count_sql).fetchone()
            if result is not None:
                imported_count = result[0]
            else:
                imported_count = 0

            return f"Total occurrences imported: {imported_count}"

        except Exception as e:
            raise e

    def import_valid_occurrences(
        self,
        csvfile: str,
        taxon_id_column: str,
        location_column: str,
        only_existing_taxons: bool = True,
    ) -> str:
        """
        Import occurrences from a CSV file. Optionally, only import occurrences with existing taxons.

        Args:
            csvfile (str): Path to the CSV file to be imported.
            taxon_id_column (str): Name of the column in the CSV that corresponds to the taxon ID.
            only_existing_taxons (bool): If True, only import occurrences for existing taxons.

        Returns:
            str: A message indicating the number of valid occurrences imported.

        Raises:
            ValueError: If the specified taxon ID column is not found in the CSV file.
        """
        try:
            # Analyse the CSV file to get the schema
            column_schema = self.analyze_data(csvfile)

            # Check if 'id' column exists in the CSV schema
            id_column_exists = any(col_name == "id" for col_name, _ in column_schema)

            # Verify that the taxon_id_column exists in the CSV schema
            if not any(col_name == taxon_id_column for col_name, _ in column_schema):
                raise ValueError(
                    f"The specified taxon ID column '{taxon_id_column}' is not found in the CSV file."
                )

            # Create the 'occurrences' table
            columns_sql = ", ".join(
                [f"{col_name} {col_type}" for col_name, col_type in column_schema]
            )
            if not id_column_exists:
                columns_sql = f"id BIGINT PRIMARY KEY, {columns_sql}"
            columns_sql += ", taxon_ref_id BIGINT REFERENCES taxon_ref(id)"

            # Drop the existing occurrences table if it exists
            drop_table_sql = "DROP TABLE IF EXISTS occurrences;"
            self.con.execute(drop_table_sql)

            # Create the 'occurrences' table with the foreign key constraint
            create_table_sql = (
                f"CREATE TABLE IF NOT EXISTS occurrences ({columns_sql});"
            )
            self.con.execute(create_table_sql)

            df = pd.read_csv(csvfile, low_memory=False)
            engine = sqlalchemy.create_engine(f"duckdb:///{self.db_path}")

            if only_existing_taxons:
                # Filter to include only rows with existing taxons
                valid_taxon_ids = pd.read_sql("SELECT id FROM taxon_ref", engine)
                valid_taxon_ids_set = set(valid_taxon_ids["id"])
                df = df[df[taxon_id_column].isin(valid_taxon_ids_set)]

            if not id_column_exists:
                # Add an 'id' column with unique values
                df["id"] = range(1, len(df) + 1)

            # Add a 'taxon_ref_id' column
            df["taxon_ref_id"] = df[taxon_id_column]

            # Define the size of each "chunk" for insertion
            chunk_size = 1000
            num_chunks = len(df) // chunk_size + (len(df) % chunk_size > 0)

            with Progress() as progress:
                task = progress.add_task(
                    "[green]Importing occurrences...", total=num_chunks
                )

                # Insert data by chunks
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i : i + chunk_size]
                    chunk.to_sql("occurrences", engine, if_exists="append", index=False)
                    progress.update(task, advance=1)

            # Count the number of valid imported occurrences
            count_sql = "SELECT COUNT(*) FROM occurrences;"
            result = self.con.execute(count_sql).fetchone()
            if result is not None:
                imported_count = result[0]
            else:
                imported_count = 0

            return f"Total valid occurrences imported: {imported_count}"

        except ValueError as ve:
            raise ve
        except Exception as e:
            raise e

    def import_occurrence_plot_links(self, csvfile: str) -> str:
        try:
            # Analyse the CSV file to get the schema
            column_schema = self.analyze_data(csvfile)

            # Drop the existing occurrences table if it exists
            drop_table_sql = "DROP TABLE IF EXISTS occurrences_plots;"
            self.con.execute(drop_table_sql)

            # Create the 'occurrences_plots' table
            columns_sql = ", ".join(
                [f"{col_name} {col_type}" for col_name, col_type in column_schema]
            )
            create_table_sql = (
                f"CREATE TABLE IF NOT EXISTS occurrences_plots ({columns_sql})"
            )
            self.con.execute(create_table_sql)

            df = pd.read_csv(csvfile)
            engine = sqlalchemy.create_engine(f"duckdb:///{self.db_path}")

            # Define the size of each "chunk" for insertion
            chunk_size = 1000
            num_chunks = len(df) // chunk_size + (len(df) % chunk_size > 0)

            with Progress() as progress:
                task = progress.add_task(
                    "[green]Importing occurrence-plot links...", total=num_chunks
                )

                # Insert data by chunks
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i : i + chunk_size]
                    chunk.to_sql(
                        "occurrences_plots", engine, if_exists="append", index=False
                    )
                    progress.update(task, advance=1)

            # Count the number of imported links
            count_sql = "SELECT COUNT(*) FROM occurrences_plots;"
            result = self.con.execute(count_sql).fetchone()
            if result is not None:
                imported_count = result[0]
            else:
                imported_count = 0

            return f"Total occurrence-plot links imported: {imported_count}"

        except Exception as e:
            raise e
