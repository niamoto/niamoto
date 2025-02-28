"""
A module for importing occurrence data from a CSV file into the database.
"""

from pathlib import Path
from typing import List, Tuple
import pandas as pd
import sqlalchemy
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)
from sqlalchemy.exc import SQLAlchemyError

from niamoto.common.database import Database
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    OccurrenceImportError,
    FileReadError,
    DataValidationError,
    DatabaseError,
    CSVError,
)


class OccurrenceImporter:
    """
    A class used to import occurrence data from a CSV file into the database.

    Attributes:
        db (Database): The database connection.
    """

    def __init__(self, db: Database):
        self.db = db
        self.db_path = self.db.db_path

    @error_handler(log=True, raise_error=True)
    def analyze_data(self, csvfile: str) -> List[Tuple[str, str]]:
        """
        Analyze column data types in CSV.

        Args:
            csvfile: Path to CSV file

        Returns:
            List of column name and type tuples

        Raises:
            CSVError: If analysis fails
        """
        try:
            # Read sample for type inference
            df = pd.read_csv(csvfile, nrows=1000)

            # Map pandas types to SQLite
            type_mapping = {
                "int64": "INTEGER",
                "float64": "REAL",
                "object": "TEXT",
                "bool": "INTEGER",
                "datetime64": "TIMESTAMP",
            }

            # Get and map types
            types_info = []
            for column in df.columns:
                pandas_type = str(df[column].dtype)
                sql_type = type_mapping.get(pandas_type, "TEXT")
                types_info.append((column, sql_type))

            return types_info

        except Exception as e:
            raise CSVError(
                csvfile, "Failed to analyze CSV structure", details={"error": str(e)}
            )

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
                columns_sql = f"id INTEGER PRIMARY KEY, {columns_sql}"
            columns_sql += ", taxon_ref_id INTEGER REFERENCES taxon_ref(id)"

            # Drop the existing occurrences table if it exists
            drop_table_sql = "DROP TABLE IF EXISTS occurrences;"
            self.db.execute_sql(drop_table_sql)

            # Create the 'occurrences' table with a foreign key to 'taxon_ref'
            create_table_sql = f"CREATE TABLE occurrences ({columns_sql});"
            self.db.execute_sql(create_table_sql)

            # Import the data with a spinner
            with Console().status(
                "[italic green]Importing occurrences...", spinner="dots"
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
                self.db.execute_sql(import_csv_sql)

            # Count the number of imported occurrences
            count_sql = "SELECT COUNT(*) FROM occurrences;"
            result = self.db.execute_sql(count_sql).fetchone()
            if result is not None:
                imported_count = result[0]
            else:
                imported_count = 0

            return f"Total occurrences imported: {imported_count}"

        except Exception as e:
            raise e

    @error_handler(log=True, raise_error=True)
    def import_valid_occurrences(
        self,
        csvfile: str,
        taxon_id_column: str,
        location_column: str,
        only_existing_taxons: bool = True,
    ) -> str:
        """
        Import valid occurrences from CSV.

        Args:
            csvfile: Path to CSV file
            taxon_id_column: Name of taxon ID column
            location_column: Name of location column
            only_existing_taxons: Only import existing taxons

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data validation fails
            OccurrenceImportError: If import fails
            DatabaseError: If database operations fail
        """
        try:
            # Validate file exists
            file_path = str(Path(csvfile).resolve())
            if not Path(file_path).exists():
                raise FileReadError(file_path, "Occurrence file not found")

            # Analyze and validate CSV structure
            column_schema = self.analyze_data(file_path)
            schema_cols = {col_name for col_name, _ in column_schema}

            # Validate required columns
            if taxon_id_column not in schema_cols:
                raise DataValidationError(
                    "Missing required column",
                    [{"field": taxon_id_column, "error": "Column not found in CSV"}],
                )
            if location_column not in schema_cols:
                raise DataValidationError(
                    "Missing required column",
                    [{"field": location_column, "error": "Column not found in CSV"}],
                )

            # Check for ID column
            id_column_exists = "id" in schema_cols

            try:
                # Create table structure
                self._create_table_structure(column_schema, id_column_exists)
            except SQLAlchemyError as e:
                raise DatabaseError(
                    "Failed to create occurrences table", details={"error": str(e)}
                )

            # Import data
            imported_count = self._import_data(
                file_path, taxon_id_column, id_column_exists, only_existing_taxons
            )

            return f"{imported_count} valid occurrences imported from {file_path}"

        except Exception as e:
            if isinstance(e, (FileReadError, DataValidationError, DatabaseError)):
                raise
            raise OccurrenceImportError(
                "Failed to import occurrences",
                details={"file": csvfile, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def _create_table_structure(
        self, column_schema: List[Tuple[str, str]], id_column_exists: bool
    ) -> None:
        """
        Create occurrences table structure.

        Args:
            column_schema: Column definitions
            id_column_exists: Whether ID column exists

        Raises:
            DatabaseError: If table creation fails
        """
        try:
            # Generate columns SQL
            columns_sql = ", ".join(
                f"{col_name} {col_type}" for col_name, col_type in column_schema
            )
            if not id_column_exists:
                columns_sql = f"id INTEGER PRIMARY KEY, {columns_sql}"
            columns_sql += ", taxon_ref_id INTEGER REFERENCES taxon_ref(id)"

            # Create table
            self.db.execute_sql("DROP TABLE IF EXISTS occurrences;")
            self.db.execute_sql(f"CREATE TABLE occurrences ({columns_sql});")

        except SQLAlchemyError as e:
            raise DatabaseError(
                "Failed to create table structure", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def _import_data(
        self,
        file_path: str,
        taxon_id_column: str,
        id_column_exists: bool,
        only_existing_taxons: bool,
    ) -> int:
        """
        Import data from CSV.

        Args:
            file_path: Path to CSV file
            taxon_id_column: Taxon ID column name
            id_column_exists: Whether ID column exists
            only_existing_taxons: Filter for existing taxons

        Returns:
            Number of imported records

        Raises:
            FileReadError: If file cannot be read
            DatabaseError: If import fails
        """
        try:
            # Read data
            df = pd.read_csv(file_path, low_memory=False)
            engine = sqlalchemy.create_engine(f"sqlite:///{self.db_path}")

            # Filter for existing taxons if requested
            if only_existing_taxons:
                valid_taxon_ids = set(
                    pd.read_sql("SELECT id FROM taxon_ref", engine)["id"]
                )
                df = df[df[taxon_id_column].isin(valid_taxon_ids)]

            # Add ID if needed
            if not id_column_exists:
                df["id"] = range(1, len(df) + 1)

            # Add taxon reference
            df["taxon_ref_id"] = df[taxon_id_column]

            # Import in chunks
            chunk_size = 1000
            num_chunks = len(df) // chunk_size + (len(df) % chunk_size > 0)

            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            )

            with progress:
                task = progress.add_task(
                    "[green]Importing occurrences...", total=num_chunks
                )

                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i : i + chunk_size]
                    chunk.to_sql("occurrences", engine, if_exists="append", index=False)
                    progress.update(task, advance=1)

            # Get final count
            result = self.db.execute_sql(
                "SELECT COUNT(*) FROM occurrences;", fetch=True
            )
            return result[0] if result else 0

        except Exception as e:
            if isinstance(e, SQLAlchemyError):
                raise DatabaseError(
                    "Database error during import", details={"error": str(e)}
                )
            raise FileReadError(file_path, f"Failed to read or process file: {str(e)}")

    @error_handler(log=True, raise_error=True)
    def import_occurrence_plot_links(self, csvfile: str) -> str:
        """
        Import occurrence-plot links.

        Args:
            csvfile: Path to CSV file

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            CSVError: If CSV structure is invalid
            OccurrenceImportError: If import fails
            DatabaseError: If database operations fail
        """
        try:
            # Validate file
            file_path = str(Path(csvfile).resolve())
            if not Path(file_path).exists():
                raise FileReadError(file_path, "File not found")

            # Read CSV data
            df = pd.read_csv(file_path)

            # Convertir les colonnes en entiers
            df["id_plot"] = df["id_plot"].astype("Int64")
            df["id_occurrence"] = df["id_occurrence"].astype("Int64")

            # Get plot_ref data for mapping id_locality to id
            plot_ref_query = """
                SELECT id, id_locality
                FROM plot_ref
            """
            plot_ref_df = pd.read_sql(plot_ref_query, f"sqlite:///{self.db_path}")
            plot_ref_df["id"] = plot_ref_df["id"].astype("Int64")
            plot_ref_df["id_locality"] = plot_ref_df["id_locality"].astype("Int64")

            # Merge avec plot_ref pour obtenir le bon id
            df_plots = pd.DataFrame(
                {
                    "id_locality": df[
                        "id_plot"
                    ]  # id_plot dans le CSV est en fait id_locality
                }
            )
            df_plots = df_plots.merge(plot_ref_df, on="id_locality", how="left")

            # Get occurrences data for mapping id_source to id
            occurrences_query = """
                SELECT id, id_source
                FROM occurrences
                WHERE source = 'occ_ncpippn'
            """
            occurrences_df = pd.read_sql(occurrences_query, f"sqlite:///{self.db_path}")
            occurrences_df["id"] = occurrences_df["id"].astype("Int64")
            occurrences_df["id_source"] = occurrences_df["id_source"].astype("Int64")

            # Sauvegarder les colonnes originales dont nous avons besoin
            original_columns = {
                "plot_short_name": df["plot_short_name"],
                "plot_full_name": df["plot_full_name"],
                "occurrence_id_taxon": df["occurrence_id_taxon"],
                "occurrence_taxon_full_name": df["occurrence_taxon_full_name"],
            }

            # Merge avec occurrences
            df_occurrences = pd.DataFrame(
                {
                    "id_source": df[
                        "id_occurrence"
                    ]  # L'id_occurrence du CSV est en fait id_source
                }
            )
            df_occurrences = df_occurrences.merge(
                occurrences_df, on="id_source", how="left"
            )

            # Afficher un exemple d'ID manquant
            missing_mask = df_occurrences["id"].isna()

            # Filtrer les lignes sans occurrence
            valid_mask = ~missing_mask
            df = df[valid_mask]
            df_occurrences = df_occurrences[valid_mask]

            occurrence_ids = df_occurrences["id"]  # Les nouveaux IDs d'occurrence

            # Créer le DataFrame final avec les bons IDs et les colonnes originales
            new_df = pd.DataFrame()
            new_df["id_occurrence"] = occurrence_ids
            new_df["id_plot"] = df_plots["id"]  # Utiliser l'id de plot_ref
            new_df["plot_short_name"] = original_columns["plot_short_name"]
            new_df["plot_full_name"] = original_columns["plot_full_name"]
            new_df["occurrence_id_taxon"] = original_columns["occurrence_id_taxon"]
            new_df["occurrence_taxon_full_name"] = original_columns[
                "occurrence_taxon_full_name"
            ]

            # Remplacer df par new_df
            df = new_df

            # Create table
            self.db.execute_sql("DROP TABLE IF EXISTS occurrences_plots;")

            # Get column types from DataFrame
            dtype_mapping = {
                "int64": "INTEGER",
                "float64": "REAL",
                "object": "TEXT",
                "bool": "INTEGER",
            }

            # Créer la définition des colonnes SQL
            columns_def = []
            for col_name in df.columns:
                dtype = str(df.dtypes[col_name])
                sql_type = dtype_mapping.get(
                    dtype, "TEXT"
                )  # TEXT par défaut si type inconnu
                columns_def.append(f"{col_name} {sql_type}")

            columns_sql = ", ".join(columns_def)
            self.db.execute_sql(f"CREATE TABLE occurrences_plots ({columns_sql});")

            # Import data
            engine = sqlalchemy.create_engine(f"sqlite:///{self.db_path}")

            # Process in chunks
            chunk_size = 1000
            num_chunks = len(df) // chunk_size + (len(df) % chunk_size > 0)

            with Progress() as progress:
                task = progress.add_task("[green]Importing links...", total=num_chunks)

                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i : i + chunk_size]
                    chunk.to_sql(
                        "occurrences_plots", engine, if_exists="append", index=False
                    )
                    progress.update(task, advance=1)

            return f"Successfully imported {len(df)} occurrence-plot links"

        except Exception as e:
            raise OccurrenceImportError(
                message="Failed to import occurrence-plot links",
                details={"error": str(e)},
            )
