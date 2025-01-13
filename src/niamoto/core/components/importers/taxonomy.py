"""
This module contains the TaxonomyImporter class used to import taxonomy data from a CSV file into the database.
"""
from typing import Tuple, Optional, Any

import pandas as pd
from rich.progress import track
from sqlalchemy import func

from niamoto.common.database import Database
from niamoto.core.models import TaxonRef
from niamoto.core.utils.logging_utils import setup_logging


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
        self.logger = setup_logging(component_name="taxonomy_import")

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
                    self._create_or_update_taxon(row, session, ranks)

                session.commit()
                self._update_nested_set_values(session)

    def _create_or_update_taxon(
        self, row: Any, session: Any, ranks: Tuple[str, ...]
    ) -> Optional[TaxonRef]:
        """
        Create or update a taxon.

        Args:
            row (Any): The row to create or update the taxon from.
            session (Any): The session to use.
            ranks (Tuple[str, ...]): The taxonomy ranks.

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
            taxon.authors = row["authors"] if pd.notna(row["authors"]) else None
            taxon.rank_name = row["rank_name"]

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
        except Exception as e:
            self.logger.info(f"Duplicate key for id_taxon: {taxon_id} - {e}")
            session.rollback()
            return None

    @staticmethod
    def _convert_to_correct_type(value: Any) -> Any:
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

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
            """
            Traverse the taxonomy tree to update left and right values for nested set representation.

            This recursive function traverses the taxonomy tree starting from a given taxon, updating
            the 'lft' and 'rght' values of each taxon to represent the tree in a nested set model. This
            model facilitates efficient tree queries.

            Args:
                taxon_id (int): The ID of the current taxon being traversed.
                _left (int): The current left value to be assigned to the taxon.
                level (int): The current depth level in the taxonomy tree.

            Returns:
                int: The next right value to be used in the traversal.

            The traversal uses a depth-first search approach, incrementing the left value for each taxon,
            then recursively calling itself for each child, and finally setting the right value. This
            method allows for the entire tree structure to be represented linearly in two dimensions.
            """
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
