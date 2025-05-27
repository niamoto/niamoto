"""
This module defines the database models for the Niamoto application.
It uses SQLAlchemy as the ORM.
"""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Index,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """
    Base class for all other database models.
    """

    pass


class TaxonRef(Base):
    """
    A class used to represent a taxon reference.

    Parameters:
        id (Integer): The primary key. :no-index:
        full_name (String): The full name of the taxon. :noindex:
        authors (String): The authors of the taxon. :noindex:
        rank_name (String): The rank name of the taxon. :noindex:
        lft (Integer): The left value for nested set model. :noindex:
        rght (Integer): The right value for nested set model. :noindex:
        level (Integer): The level value for nested set model. :noindex:
        parent_id (Integer): The parent taxon id. :noindex:
        children (List[TaxonRef]): The children of the taxon. :noindex:
        taxon_id (Integer): The external identifier of the taxon. :noindex:
        extra_data (String): Additional fields stored in JSON format. :noindex:
    """

    __tablename__ = "taxon_ref"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255))
    authors = Column(String(255))
    rank_name = Column(String(50))
    lft = Column(Integer)
    rght = Column(Integer)
    level = Column(Integer)
    taxon_id = Column(Integer, nullable=True)
    extra_data = Column(JSON, nullable=True)  # Store JSON as text in SQLite

    if TYPE_CHECKING:
        parent_id: Optional[int]
        children: List["TaxonRef"]
    else:
        parent_id = Column(Integer, ForeignKey("taxon_ref.id"), nullable=True)
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
    A class used to represent a plot reference with hierarchical support.

    Parameters:
        id (Integer): The primary key. :no-index:
        locality (String): The locality of the plot. :noindex:
        geometry (String): The geometry of the plot. :noindex:
        lft (Integer): The left value for nested set model. :noindex:
        rght (Integer): The right value for nested set model. :noindex:
        level (Integer): The level value for nested set model. :noindex:
        parent_id (Integer): The parent plot id. :noindex:
        plot_type (String): The type of plot (plot, locality, country). :noindex:
        extra_data (JSON): Additional fields stored in JSON format. :noindex:
    """

    __tablename__ = "plot_ref"

    id = Column(Integer, primary_key=True)  # Manual ID setting still possible
    id_locality = Column(Integer, nullable=False)
    locality = Column(String, nullable=False)
    geometry = Column(String)
    lft = Column(Integer, nullable=True)
    rght = Column(Integer, nullable=True)
    level = Column(Integer, nullable=True)
    plot_type = Column(String(50), nullable=True)  # 'plot', 'locality', 'country'
    extra_data = Column(JSON, nullable=True)  # Store JSON as text in SQLite

    if TYPE_CHECKING:
        parent_id: Optional[int]
        children: List["PlotRef"]
    else:
        parent_id = Column(Integer, ForeignKey("plot_ref.id"), nullable=True)
        children = relationship("PlotRef", backref="parent", remote_side=[id])

    __table_args__ = (
        Index("ix_plot_ref_id", "id"),
        Index("ix_plot_ref_locality", "locality"),
        Index("ix_plot_ref_plot_type", "plot_type"),
        Index("ix_plot_ref_parent_id", "parent_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<PlotRef(id={self.id}, locality={self.locality}, type={self.plot_type})>"
        )


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

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(50), nullable=False)
    type = Column(String(50))
    type_label = Column(String(50))
    location = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_shape_ref_id", "id"),
        Index("ix_shape_ref_label", "label"),
        Index("ix_shape_ref_type", "type"),
        Index("ix_shape_ref_type_label", "type_label"),
        Index("ix_shape_ref_label_type", "label", "type", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ShapeRef(id={self.id}, label='{self.label}', type='{self.type}', location='{self.location[:30]}...')>"
