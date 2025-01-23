"""
This module contains the TaxonomyImporter class used to import taxonomy data from a CSV file into the database.
"""

from pathlib import Path
from typing import Tuple, Optional, Any

import pandas as pd
from rich.progress import track
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from niamoto.common.database import Database
from niamoto.core.models import TaxonRef
from niamoto.core.utils.logging_utils import setup_logging
from niamoto.common.utils import error_handler
from niamoto.common.exceptions import (
    TaxonomyImportError,
    FileReadError,
    DataValidationError,
    DatabaseError,
)


class TaxonomyImporter:
    """
    A class used to import taxonomy data from a CSV file into the database.

    Attributes:
        db (Database): The database connection.
    """

    def __init__(self, db: Database):
        """
        Initializes the TaxonomyImporter with the database connection.

        Args:
            db (Database): The database connection.
        """
        self.db = db
        self.logger = setup_logging(component_name="import")

    @error_handler(log=True, raise_error=True)
    def import_from_csv(self, file_path: str, ranks: Tuple[str, ...]) -> str:
        """
        Import taxonomy data from CSV.

        Args:
            file_path: Path to CSV file
            ranks: Taxonomy ranks to import

        Returns:
            Success message with import count

        Raises:
            FileReadError: If file cannot be read
            DataValidationError: If data is invalid
            TaxonomyImportError: If import fails
        """
        try:
            # Validate file exists
            file_path = str(Path(file_path).resolve())
            if not Path(file_path).exists():
                raise FileReadError(file_path, "Taxonomy file not found")

            # Read and validate CSV
            try:
                df = pd.read_csv(file_path)
            except Exception as e:
                raise FileReadError(file_path, f"Failed to read CSV file: {str(e)}")

            # Validate required columns
            required_cols = {"id_taxon", "full_name", "authors", "rank_name"}
            missing_cols = required_cols - set(df.columns)
            if missing_cols:
                raise DataValidationError(
                    "Missing required columns",
                    [{"field": col, "error": "Column missing"} for col in missing_cols],
                )

            # Prepare and process data
            df = self._prepare_dataframe(df, ranks)
            imported_count = self._process_dataframe(df, ranks)

            return f"{imported_count} taxons imported from {file_path}."

        except Exception as e:
            if isinstance(e, (FileReadError, DataValidationError)):
                raise
            raise TaxonomyImportError(
                f"Failed to import taxonomy data: {str(e)}",
                details={"file": file_path, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def _prepare_dataframe(
        self, df: pd.DataFrame, ranks: Tuple[str, ...]
    ) -> pd.DataFrame:
        """
        Prepare dataframe for processing.

        Args:
            df: Input dataframe
            ranks: Taxonomy ranks

        Returns:
            Prepared dataframe

        Raises:
            DataValidationError: If preparation fails
        """
        try:
            df["rank"] = df.apply(lambda row: self._get_rank(row, ranks), axis=1)
            df["parent_id"] = df.apply(
                lambda row: self._get_parent_id(row, ranks), axis=1
            )
            df.sort_values(by=["rank", "full_name"], inplace=True)
            return df
        except Exception as e:
            raise DataValidationError(
                "Failed to prepare taxonomy data", [{"error": str(e)}]
            )

    @staticmethod
    def _get_rank(row: Any, ranks: Tuple[str, ...]) -> Optional[str]:
        """
        Get the rank of a row.

        Args:
            row (Any): The row to get the rank from.
            ranks (Tuple[str, ...]): The ranks to get.

        Returns:
            Optional[str]: The rank of the row.
        """
        for rank in reversed(ranks):
            if pd.notna(row[rank]) and row["id_taxon"] == row[rank]:
                return rank
        return None

    @staticmethod
    def _get_parent_id(row: Any, ranks: Tuple[str, ...]) -> Optional[int]:
        """
        Get the parent id of a row.

        Args:
            row (Any): The row to get the parent id from.
            ranks (Tuple[str, ...]): The ranks to get.

        Returns:
            Optional[int]: The parent id of the row.
        """
        for rank in reversed(ranks):
            if pd.notna(row[rank]) and row["id_taxon"] != row[rank]:
                parent_id = row[rank]
                if not pd.isna(parent_id):
                    return int(parent_id)
        return None

    @error_handler(log=True, raise_error=True)
    def _process_dataframe(self, df: pd.DataFrame, ranks: Tuple[str, ...]) -> int:
        """
        Process dataframe and import data.

        Args:
            df: Dataframe to process
            ranks: Taxonomy ranks

        Returns:
            Number of imported records

        Raises:
            TaxonomyImportError: If processing fails
            DatabaseError: If database operations fail
        """
        imported_count = 0

        try:
            with self.db.session() as session:
                for rank in ranks:
                    rank_taxons = df[df["rank"] == rank]

                    for _, row in track(
                        rank_taxons.iterrows(),
                        total=rank_taxons.shape[0],
                        description=f"[green]Importing {rank}",
                    ):
                        try:
                            taxon = self._create_or_update_taxon(row, session, ranks)
                            if taxon is not None:
                                imported_count += 1
                        except SQLAlchemyError as e:
                            raise DatabaseError(
                                f"Database error while processing taxon: {str(e)}",
                            )

                    session.commit()
                    self._update_nested_set_values(session)

            return imported_count

        except Exception as e:
            if isinstance(e, DatabaseError):
                raise
            raise TaxonomyImportError(
                "Failed to process taxonomy data", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def _create_or_update_taxon(
        self, row: Any, session: Any, ranks: Tuple[str, ...]
    ) -> Optional[TaxonRef]:
        """
        Create or update a taxon record.

        Args:
            row: Data row
            session: Database session
            ranks: Taxonomy ranks

        Returns:
            Created or updated taxon

        Raises:
            DatabaseError: If database operation fails
        """
        taxon_id = int(row["id_taxon"])
        try:
            # Get or create taxon
            taxon: Optional[TaxonRef] = (
                session.query(TaxonRef).filter_by(id=taxon_id).one_or_none()
            )

            if taxon is None:
                taxon = TaxonRef(id=taxon_id)
                session.add(taxon)

            # Update fields
            taxon.full_name = row["full_name"]
            taxon.authors = row["authors"] if pd.notna(row["authors"]) else None
            taxon.rank_name = row["rank_name"]

            # Set parent ID
            parent_id = row["parent_id"]
            if not pd.isna(parent_id):
                taxon.parent_id = int(parent_id)

            # Store extra data
            standard_fields = ["id_taxon", "full_name", "authors", "rank", "parent_id"]
            all_ignored_fields = set(standard_fields).union(ranks)
            extra_data = {
                key: None if pd.isna(value) else self._convert_to_correct_type(value)
                for key, value in row.items()
                if key not in all_ignored_fields
            }
            taxon.extra_data = extra_data

            session.flush()
            return taxon

        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                f"Failed to create/update taxon {taxon_id}", details={"error": str(e)}
            )

    @staticmethod
    def _convert_to_correct_type(value: Any) -> Any:
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    @error_handler(log=True, raise_error=True)
    def _update_nested_set_values(self, session: Any) -> None:
        """
        Update nested set values for the taxonomy tree.

        Args:
            session: Database session

        Raises:
            DatabaseError: If update fails
        """
        try:
            # Get all taxons
            taxons = (
                session.query(TaxonRef)
                .order_by(TaxonRef.rank_name, TaxonRef.full_name)
                .all()
            )
            taxon_dict = {taxon.id: taxon for taxon in taxons}

            def traverse(taxon_id: int, _left: int, level: int) -> int:
                """Traverse tree and update nested set values."""
                taxon = taxon_dict[taxon_id]
                taxon.lft = _left
                taxon.level = level

                right = _left + 1
                child_ids = (
                    session.query(TaxonRef.id)
                    .filter(TaxonRef.parent_id == taxon_id)
                    .order_by(TaxonRef.rank_name, TaxonRef.full_name)
                    .all()
                )
                for (child_id,) in child_ids:
                    right = traverse(child_id, right, level + 1)

                taxon.rght = right
                return right + 1

            # Process root nodes
            left = 1
            root_taxons = (
                session.query(TaxonRef)
                .filter(func.coalesce(TaxonRef.parent_id, 0) == 0)
                .order_by(TaxonRef.rank_name, TaxonRef.full_name)
                .all()
            )
            for taxon in root_taxons:
                left = traverse(taxon.id, left, 0)

            session.commit()

        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(
                "Failed to update nested set values", details={"error": str(e)}
            )
