import os

import pandas as pd
from typing import Tuple, Optional, Any
from rich.progress import track
from sqlalchemy import func
from niamoto.core.models import TaxonRef
from niamoto.common.database import Database
import logging


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
        # Ensure the logs directory exists
        log_directory = "logs"
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        # Configure logging to write to a file in the logs directory
        log_file_path = os.path.join(log_directory, "taxonomy_import.log")
        logging.basicConfig(
            filename=log_file_path,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def import_from_csv(self, file_path: str, ranks: Tuple[str, ...]) -> str:
        """
        Import taxonomy data from a CSV file.

        Args:
            file_path (str): The path to the CSV file to be imported.
            ranks (Tuple[str, ...]): The ranks to be imported.

        Returns:
            str: A message indicating the success of the import operation.
        """
        df = pd.read_csv(file_path)
        df = self._prepare_dataframe(df, ranks)
        self._process_dataframe(df, ranks)
        return f"Taxonomy data imported successfully from {file_path}"

    def _prepare_dataframe(
        self, df: pd.DataFrame, ranks: Tuple[str, ...]
    ) -> pd.DataFrame:
        """
        Prepare the dataframe for processing.

        Args:
            df (pd.DataFrame): The dataframe to be prepared.
            ranks (Tuple[str, ...]): The ranks to be prepared.

        Returns:
            pd.DataFrame: The prepared dataframe.
        """
        df["rank"] = df.apply(lambda row: self._get_rank(row, ranks), axis=1)
        df["parent_id"] = df.apply(lambda row: self._get_parent_id(row, ranks), axis=1)
        df.sort_values(by=["rank", "full_name"], inplace=True)
        return df

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

    def _process_dataframe(self, df: pd.DataFrame, ranks: Tuple[str, ...]) -> None:
        """
        Process the dataframe.

        Args:
            df (pd.DataFrame): The dataframe to be processed.
            ranks (Tuple[str, ...]): The ranks to be processed.
        """
        with self.db.session() as session:
            for rank in ranks:
                rank_taxons = df[df["rank"] == rank]

                for _, row in track(
                    rank_taxons.iterrows(),
                    total=rank_taxons.shape[0],
                    description=f"{rank}",
                ):
                    self._create_or_update_taxon(row, session)

                session.commit()
                self._update_nested_set_values(session)

    @staticmethod
    def _create_or_update_taxon(row: Any, session: Any) -> Optional[TaxonRef]:
        """
        Create or update a taxon.

        Args:
            row (Any): The row to create or update the taxon from.
            session (Any): The session to use.

        Returns:
            Optional[TaxonRef]: The created or updated taxon, or None if an error occurred.
        """
        taxon_id = int(row["id_taxon"])
        try:
            taxon: Optional[TaxonRef] = (
                session.query(TaxonRef).filter_by(id=taxon_id).one_or_none()
            )

            if taxon is None:
                taxon = TaxonRef(id=taxon_id)
                session.add(taxon)

            taxon.full_name = row["full_name"]
            taxon.authors = row["authors"]
            taxon.rank_name = row["rank"]

            parent_id = row["parent_id"]
            if not pd.isna(parent_id):
                taxon.parent_id = int(parent_id)

            session.flush()
            return taxon
        except Exception as e:
            logging.info(f"Duplicate key for id_taxon: {taxon_id} - {e}")
            session.rollback()
            return None

    @staticmethod
    def _update_nested_set_values(session: Any) -> None:
        """
        Update the nested set values.

        Args:
            session (Any): The session to use.
        """
        taxons = (
            session.query(TaxonRef)
            .order_by(TaxonRef.rank_name, TaxonRef.full_name)
            .all()
        )
        taxon_dict = {taxon.id: taxon for taxon in taxons}

        def traverse(taxon_id: int, _left: int, level: int) -> int:
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
