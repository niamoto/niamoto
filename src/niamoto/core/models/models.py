"""
This module defines the database models for the Niamoto application.
It uses SQLAlchemy as the ORM and geoalchemy2 for spatial features.
"""
from typing import List, Optional, TYPE_CHECKING

# pylint: disable=too-few-public-methods


from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Sequence,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSON, BIGINT
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """
    Base class for all other database models.
    """

    pass


class TaxonRef(Base):
    """
    A class used to represent a taxon reference.

    Attributes:
        id (BIGINT): The primary key. :no-index:
        full_name (String): The full name of the taxon.
        authors (String): The authors of the taxon.
        rank_name (String): The rank name of the taxon.
        lft (Integer): The left value for nested set model.
        rght (Integer): The right value for nested set model.
        level (Integer): The level value for nested set model.
        parent_id (BIGINT): The parent taxon id.
        children (List[TaxonRef]): The children of the taxon.
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

    if TYPE_CHECKING:
        parent_id: Optional[int]
        children: List["TaxonRef"]
    else:
        parent_id = Column(BIGINT, ForeignKey("taxon_ref.id"), nullable=True)
        children = relationship("TaxonRef", backref="parent", remote_side=[id])

    def __repr__(self) -> str:
        return f"<TaxonRef(id={self.id}, id_taxon={self.id}, full_name={self.full_name}, rank_name={self.rank_name})>"


class PlotRef(Base):
    """
    A class used to represent a plot reference.

    Attributes:
        id (BIGINT): The primary key.
        id_locality (BIGINT): The locality id.
        locality (String): The locality of the plot.
        substrat (String): The substrat of the plot.
        geometry (String): The geometry of the plot.
    """

    __tablename__ = "plot_ref"

    id_seq: Sequence = Sequence("plot_id_seq")
    id = Column(BIGINT, id_seq, server_default=id_seq.next_value(), primary_key=True)
    id_locality = Column(BIGINT, nullable=False)
    locality = Column(String, nullable=False)
    substrat = Column(String)
    geometry = Column(String)


class Mapping(Base):
    """
    A class used to represent a mapping.

    Attributes:
        id (Integer): The primary key.
        target_table_name (String): The target table name.
        target_field (String): The target field.
        field_type (String): The field type.
        group_by (String): The group by field.
        reference_table_name (String): The reference table name.
        reference_data_path (String): The reference data path.
        is_identifier (Boolean): Whether the field is an identifier.
        label (String): The label of the field.
        description (String): The description of the field.
        transformation (Text): The transformation of the field.
        bins (Text): The bins of the field.
        widgets (JSON): The widgets of the field.
    """

    __tablename__ = "mapping"

    id_seq: Sequence = Sequence("mapping_id_seq")
    id = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
    target_table_name = Column(String(255))
    target_field = Column(String(255))
    field_type = Column(String(50))
    group_by = Column(String(50))
    reference_table_name = Column(String(255), nullable=True)
    reference_data_path = Column(String(255), nullable=True)
    is_identifier = Column(Boolean, nullable=False)
    label = Column(String(255))
    description = Column(String(255))
    transformation = Column(Text)
    bins = Column(Text)
    widgets = Column(JSON)

    def __repr__(self) -> str:
        return (
            f"<Mapping(id={self.id}, target_table_name={self.target_table_name}, "
            f"target_field={self.target_field}, field_type={self.field_type}, "
            f"is_identifier={self.is_identifier}, label={self.label}, "
            f"description={self.description}, transformation={self.transformation}, "
            f"bins={self.bins}, widgets={self.widgets})>"
        )
