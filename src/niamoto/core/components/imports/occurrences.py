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
            ) from e

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
            imported_count = result[0] if result else 0

            # Validate and update taxon links
            validation_result = self.validate_taxon_links()

            return f"Total occurrences imported: {imported_count}\n{validation_result}"

        except Exception as e:
            raise e

    @error_handler(log=True, raise_error=True)
    def import_valid_occurrences(
        self,
        csvfile: str,
        taxon_id_column: str,
        location_column: str,
        only_existing_taxons: bool = False,
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
                ) from e

            # Import data
            imported_count = self._import_data(
                file_path, taxon_id_column, id_column_exists, only_existing_taxons
            )

            return f"{imported_count} occurrences imported from {file_path}\n"

        except Exception as e:
            if isinstance(e, (FileReadError, DataValidationError, DatabaseError)):
                raise
            raise OccurrenceImportError(
                "Failed to import occurrences",
                details={"file": csvfile, "error": str(e)},
            ) from e

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
            ) from e

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
            df["taxon_ref_id"] = None

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

            # Get final count before validation
            result = self.db.execute_sql(
                "SELECT COUNT(*) FROM occurrences;", fetch=True
            )
            imported_count = result[0] if result else 0

            # Get final count after validation
            result = self.db.execute_sql(
                "SELECT COUNT(*) FROM occurrences;", fetch=True
            )
            imported_count = result[0] if result else 0

            # Validate and update taxon links
            self.validate_taxon_links(taxon_id_column)

            return imported_count

        except Exception as e:
            if isinstance(e, SQLAlchemyError):
                raise DatabaseError(
                    "Database error during import", details={"error": str(e)}
                ) from e
            raise FileReadError(
                file_path, f"Failed to read or process file: {str(e)}"
            ) from e

    @error_handler(log=True, raise_error=True)
    def validate_taxon_links(self, taxon_id_column: str) -> str:
        """
        Validate and update taxon links for occurrences.

        Returns:
            str: A status message with linking statistics
        """
        from rich.console import Console

        console = Console()
        try:
            # Get counts and check if linking is needed
            total_count = self._get_occurrence_count()
            already_linked = self._get_linked_occurrence_count()

            if already_linked == total_count:
                return f"Occurrence-Taxon links status: All {total_count} occurrences already linked"

            # Process links
            linked_stats = self._process_taxon_links(taxon_id_column)

            # Get final counts
            linked_count = self._get_linked_occurrence_count()
            unlinked_count = total_count - linked_count

            self._format_link_status(
                total_count=total_count,
                linked_count=linked_count,
                linked_by_taxon_id=linked_stats["linked_count"],
                unlinked_count=unlinked_count,
                unlinked_examples=linked_stats["unlinked_examples"]
                if unlinked_count > 0
                else "",
                console=console,
            )

        except Exception as e:
            raise OccurrenceImportError(
                message="Error validating taxon links",
                details={"error": str(e)},
            ) from e

    def _get_occurrence_count(self) -> int:
        """Get total number of occurrences."""
        return self.db.execute_sql("SELECT COUNT(*) FROM occurrences;", fetch=True)[0]

    def _get_linked_occurrence_count(self) -> int:
        """Get number of occurrences linked to taxons."""
        return self.db.execute_sql(
            "SELECT COUNT(*) FROM occurrences WHERE taxon_ref_id IS NOT NULL;",
            fetch=True,
        )[0]

    def _process_taxon_links(self, taxon_id_column: str) -> dict:
        """
        Process all taxon links in one go and return statistics.

        Args:
            taxon_id_column: Name of the column containing the taxon ID

        Returns:
            dict: Statistics about the linking process
        """
        engine = sqlalchemy.create_engine(f"sqlite:///{self.db_path}")

        # Get taxon data
        taxon_df = pd.read_sql("SELECT id, taxon_id FROM taxon_ref", engine)

        # Build query with dynamic column name
        unlinked_query = f"""
        SELECT id, {taxon_id_column}
        FROM occurrences
        WHERE taxon_ref_id IS NULL
        """

        # Get unlinked occurrences
        occurrences_df = pd.read_sql(
            unlinked_query,
            engine,
        )

        if occurrences_df.empty:
            return {"by_taxon_id": 0, "unlinked_examples": ""}

        # Create mapping dictionary
        taxon_id_to_taxon = {}
        for _, row in taxon_df.iterrows():
            if pd.notna(row["taxon_id"]):
                external_id = row["taxon_id"]
                if isinstance(external_id, float) and external_id.is_integer():
                    external_id = int(external_id)
                taxon_id_to_taxon[str(external_id)] = row["id"]

        # Link occurrences
        updates = []
        linked_count = 0

        for _, row in occurrences_df.iterrows():
            occ_id = row["id"]
            external_taxon_id = (
                row[taxon_id_column] if pd.notna(row[taxon_id_column]) else None
            )
            external_taxon_id_str = (
                str(external_taxon_id) if external_taxon_id is not None else None
            )

            # Try to link by taxon ID
            if external_taxon_id_str and external_taxon_id_str in taxon_id_to_taxon:
                updates.append(
                    {
                        "occ_id": occ_id,
                        "taxon_id": taxon_id_to_taxon[external_taxon_id_str],
                    }
                )
                linked_count += 1

        # Apply updates in batches
        self._apply_batch_updates(updates)

        # Get sample of remaining unlinked occurrences
        unlinked_examples = (
            self._get_unlinked_examples(taxon_id_column) if updates else ""
        )

        return {
            "linked_count": linked_count,
            "unlinked_examples": unlinked_examples,
        }

    def _apply_batch_updates(self, updates):
        """Apply updates in efficient batches using CASE statements."""
        if not updates:
            return

        batch_size = 1000
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]

            # Build CASE statement
            case_stmt = " ".join(
                f"WHEN {update['occ_id']} THEN {update['taxon_id']}" for update in batch
            )

            ids = ", ".join(str(update["occ_id"]) for update in batch)

            query = f"""
            UPDATE occurrences
            SET taxon_ref_id = CASE id {case_stmt} END
            WHERE id IN ({ids})
            """

            self.db.execute_sql(query)

    def _get_unlinked_examples(self, taxon_id_column: str, limit=5):
        """
        Get a small sample of unlinked occurrences for debugging.

        Args:
            taxon_id_column: Name of the column containing the taxon ID
            limit: Maximum number of examples to return

        Returns:
            str: Formatted string of unlinked occurrence examples
        """
        engine = sqlalchemy.create_engine(f"sqlite:///{self.db_path}")

        # Dynamic query using the configured column name
        query = f"""
        SELECT id, {taxon_id_column}
        FROM occurrences
        WHERE taxon_ref_id IS NULL
        LIMIT {limit}
        """

        sample_df = pd.read_sql(query, engine)

        if sample_df.empty:
            return ""

        return "\n".join(
            f"  - ID: {row['id']}, "
            f"Original Taxon ID: {row[taxon_id_column] if pd.notna(row[taxon_id_column]) else 'N/A'}"
            for _, row in sample_df.iterrows()
        )

    def _format_link_status(
        self,
        total_count: int,
        linked_count: int,
        linked_by_taxon_id: int,
        unlinked_count: int,
        unlinked_examples: str = "",
        console=None,
    ):
        """
        Format and print the link status as a rich Table.

        Args:
            total_count: Total number of occurrences
            linked_count: Total number of successfully linked occurrences
            linked_by_taxon_id: Number of occurrences linked by taxon ID
            unlinked_count: Number of occurrences that could not be linked
            unlinked_examples: Sample of unlinked occurrences for debugging
            console: Optional Rich console to use for printing
        """
        from rich.table import Table
        from rich.console import Console
        from rich.panel import Panel

        # Créer une console si non fournie
        if console is None:
            console = Console()

        table = Table(title="Occurrence-Taxon Links Status")

        # Add columns
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Percentage", style="yellow")

        # Add rows
        table.add_row("Total occurrences", str(total_count), "100%")

        if total_count > 0:
            linked_percent = f"{linked_count / total_count * 100:.1f}%"
            table.add_row("Successfully linked", str(linked_count), linked_percent)

            if linked_by_taxon_id > 0:
                by_id_percent = f"{linked_by_taxon_id / total_count * 100:.1f}%"
                table.add_row(
                    "- Linked by taxon ID", str(linked_by_taxon_id), by_id_percent
                )

            if unlinked_count > 0:
                unlinked_percent = f"{unlinked_count / total_count * 100:.1f}%"
                table.add_row(
                    "Failed to link", str(unlinked_count), unlinked_percent, style="red"
                )

        # Print the table
        console.print(table)

        # Print examples if there are any
        if unlinked_examples:
            console.print(
                Panel(
                    unlinked_examples,
                    title="Sample of Unlinked Occurrences",
                    border_style="red",
                )
            )
