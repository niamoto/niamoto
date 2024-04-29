import pandas as pd
from typing import Tuple, Optional, Any
from rich.progress import track
from sqlalchemy import func
from niamoto.core.models import TaxonRef
from niamoto.common.database import Database


class TaxonomyImporter:
    def __init__(self, db: Database):
        self.db = db

    def import_from_csv(self, file_path: str, ranks: Tuple[str, ...]) -> str:
        df = pd.read_csv(file_path)
        df = self._prepare_dataframe(df, ranks)
        self._process_dataframe(df, ranks)
        return f"Taxonomy data imported successfully from {file_path}"

    def _prepare_dataframe(
        self, df: pd.DataFrame, ranks: Tuple[str, ...]
    ) -> pd.DataFrame:
        df["rank"] = df.apply(lambda row: self._get_rank(row, ranks), axis=1)
        df["parent_id"] = df.apply(lambda row: self._get_parent_id(row, ranks), axis=1)
        df.sort_values(by=["rank", "full_name"], inplace=True)
        return df

    @staticmethod
    def _get_rank(row: Any, ranks: Tuple[str, ...]) -> Optional[str]:
        for rank in reversed(ranks):
            if pd.notna(row[rank]) and row["id_taxon"] == row[rank]:
                return rank
        return None

    @staticmethod
    def _get_parent_id(row: Any, ranks: Tuple[str, ...]) -> Optional[int]:
        for rank in reversed(ranks):
            if pd.notna(row[rank]) and row["id_taxon"] != row[rank]:
                parent_id = row[rank]
                if not pd.isna(parent_id):
                    return int(parent_id)
        return None

    def _process_dataframe(self, df: pd.DataFrame, ranks: Tuple[str, ...]) -> None:
        with self.db.session() as session:
            for rank in ranks:
                rank_taxons = df[df["rank"] == rank]

                for _, row in track(
                    rank_taxons.iterrows(),
                    total=rank_taxons.shape[0],
                    description=f"Importing {rank}",
                ):
                    self._create_or_update_taxon(row, session)

                session.commit()
                self._update_nested_set_values(session)

    @staticmethod
    def _create_or_update_taxon(row: Any, session: Any) -> TaxonRef:
        taxon_id = int(row["id_taxon"])
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

        return taxon

    @staticmethod
    def _update_nested_set_values(session: Any) -> None:
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
