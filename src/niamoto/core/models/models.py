"""
This module defines the database models for the Niamoto application.
It uses SQLAlchemy as the ORM and geoalchemy2 for spatial features.
"""
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Sequence,
    Index,
)
from sqlalchemy.dialects.postgresql import BIGINT, JSON
from sqlalchemy.orm import DeclarativeBase, relationship


# pylint: disable=too-few-public-methods


class Base(DeclarativeBase):
    """
    Base class for all other database models.
    """

    pass


class TaxonRef(Base):
    """
    A class used to represent a taxon reference.

    Parameters:
        id (BIGINT): The primary key. :no-index:
        full_name (String): The full name of the taxon. :noindex:
        authors (String): The authors of the taxon. :noindex:
        rank_name (String): The rank name of the taxon. :noindex:
        lft (Integer): The left value for nested set model. :noindex:
        rght (Integer): The right value for nested set model. :noindex:
        level (Integer): The level value for nested set model. :noindex:
        parent_id (BIGINT): The parent taxon id. :noindex:
        children (List[TaxonRef]): The children of the taxon. :noindex:
        extra_data (JSON): Additional fields stored in JSON format. :noindex:
    """

    __tablename__ = "taxon_ref"

    id_seq: Sequence = Sequence("taxon_id_seq")
    id = Column(BIGINT, id_seq, server_default=id_seq.next_value(), primary_key=True)
    full_name = Column(String(255))
    authors = Column(String(255))
    rank_name = Column(String(50))
    lft = Column(Integer)
    rght = Column(Integer)
    level = Column(Integer)
    extra_data = Column(JSON, nullable=True)

    if TYPE_CHECKING:
        parent_id: Optional[int]
        children: List["TaxonRef"]
    else:
        parent_id = Column(BIGINT, ForeignKey("taxon_ref.id"), nullable=True)
        children = relationship("TaxonRef", backref="parent", remote_side=[id])

    __table_args__ = (
        Index("ix_taxon_ref_id", "id"),
        Index("ix_taxon_ref_rank_name", "rank_name"),
        Index("ix_taxon_ref_full_name", "full_name"),
    )

    def __repr__(self) -> str:
        return f"<TaxonRef(id={self.id}, id_taxon={self.id}, full_name={self.full_name}, rank_name={self.rank_name})>"


class PlotRef(Base):
    """
    A class used to represent a plot reference.

    Parameters:
        id (BIGINT): The primary key. :no-index:
        locality (String): The locality of the plot. :noindex:
        geometry (String): The geometry of the plot. :noindex:
    """

    __tablename__ = "plot_ref"

    id_seq: Sequence = Sequence("plot_id_seq")
    id = Column(BIGINT, id_seq, server_default=id_seq.next_value(), primary_key=True)
    id_locality = Column(BIGINT, nullable=False)
    locality = Column(String, nullable=False)
    geometry = Column(String)


class ShapeRef(Base):
    """
    A class used to represent a shape reference.

    Attributes:
        id (int): The primary key. :noindex:
        label (str): The label of the shape. :noindex:
        type (str): The type of the shape. :noindex:
        location (str): The geometry of the shape (MultiPolygon) as WKT. :noindex:
    """

    __tablename__ = "shape_ref"

    id_seq = Sequence("shape_id_seq")
    id = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
    label = Column(String(50), nullable=False)
    type = Column(String(50))
    location = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_shape_ref_id", "id"),
        Index("ix_shape_ref_label", "label"),
        Index("ix_shape_ref_type", "type"),
        Index(
            "ix_shape_ref_label_type", "label", "type", unique=True
        ),  # Unique constraint on label and type
    )

    def __repr__(self) -> str:
        return f"<ShapeRef(id={self.id}, label='{self.label}', type='{self.type}', location='{self.location[:30]}...')>"
