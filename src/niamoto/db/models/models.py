"""
This module defines the database models for the Niamoto application.
It uses SQLAlchemy as the ORM and geoalchemy2 for spatial features.
"""
# pylint: disable=too-few-public-methods


from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Text, Sequence
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Taxon(Base):
    """Represents a taxon in the database."""

    __tablename__ = "taxon"

    """
    Sequence and Column for an auto-incrementing primary key in DuckDB.

    Attributes:
        id_seq (Sequence): A sequence object named 'taxon_id_seq' used to generate unique identifiers for each record.
        id (Column): An Integer column that serves as the primary key. It auto-increments using values from 'id_seq'.
    """
    id_seq = Sequence("taxon_id_seq")
    id = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
    parent_id = Column(Integer, ForeignKey("taxon.id"), nullable=True)
    full_name = Column(String(255))
    rank_name = Column(String(50))
    id_source = Column(Integer)
    id_taxonref = Column(Integer)
    id_family = Column(Integer)
    id_genus = Column(Integer)
    id_species = Column(Integer)
    id_infra = Column(Integer)
    occ_count = Column(Integer)
    occ_um_count = Column(Integer)
    freq_max = Column(Float)
    freq10_max = Column(Float)
    freq_plot1ha_max = Column(Float)
    dbh_avg = Column(Float)
    dbh_max = Column(Float)
    dbh_median = Column(Float)
    height_max = Column(Float)
    wood_density_avg = Column(Float)
    wood_density_min = Column(Float)
    wood_density_max = Column(Float)
    bark_thickness_avg = Column(Float)
    bark_thickness_min = Column(Float)
    bark_thickness_max = Column(Float)
    leaf_sla_avg = Column(Float)
    leaf_sla_min = Column(Float)
    leaf_sla_max = Column(Float)
    leaf_area_avg = Column(Float)
    leaf_area_min = Column(Float)
    leaf_area_max = Column(Float)
    leaf_thickness_avg = Column(Float)
    leaf_thickness_min = Column(Float)
    leaf_thickness_max = Column(Float)
    leaf_ldmc_avg = Column(Float)
    leaf_ldmc_min = Column(Float)
    leaf_ldmc_max = Column(Float)
    ncpippn_count = Column(Integer)
    # geo_pts_pn = Column(Geometry(geometry_type="MULTIPOINT", srid=4326))
    geo_pts_pn = Column(JSON)

    # Create relationship for self-referential foreign key
    parent = relationship("Taxon", remote_side=[id], back_populates="children")
    children = relationship("Taxon", back_populates="parent")

    frequencies = Column(JSON)


class Plot(Base):
    """Represents a plot in the database."""

    __tablename__ = "plot"

    """
    Sequence and Column for an auto-incrementing primary key in DuckDB.

    Attributes:
        id_seq (Sequence): A sequence object named 'taxon_id_seq' used to generate unique identifiers for each record.
        id (Column): An Integer column that serves as the primary key. It auto-increments using values from 'id_seq'.
    """
    id_seq = Sequence("plot_id_seq")
    id = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
    plot_name = Column(String, nullable=False)
    plot_type = Column(String)
    plot_area = Column(Float)
    plot_orientation = Column(Float)
    plot_slope = Column(Float)
    plot_altitude = Column(Float)
    vegetation_type = Column(String)
    description = Column(String)
    access = Column(String)
    date = Column(Date)
    photopoint = Column(String)
    photopoint_description = Column(String)
    # geom = Column(Geometry(geometry_type="POLYGON", srid=4326))

    frequencies = Column(JSON)


class Shape(Base):
    """Represents a shape in the database."""

    __tablename__ = "shape"

    """
    Sequence and Column for an auto-incrementing primary key in DuckDB.

    Attributes:
        id_seq (Sequence): A sequence object named 'taxon_id_seq' used to generate unique identifiers for each record.
        id (Column): An Integer column that serves as the primary key. It auto-increments using values from 'id_seq'.
    """
    id_seq = Sequence("shape_id_seq")
    id = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
    name = Column(String, nullable=False)
    # geo = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    area = Column(Float)
    perimeter = Column(Float)

    frequencies = Column(JSON)


class MappingConfig(Base):
    __tablename__ = "mapping"

    """
    Sequence and Column for an auto-incrementing primary key in DuckDB.

    Attributes:
        id_seq (Sequence): A sequence object named 'taxon_id_seq' used to generate unique identifiers for each record.
        id (Column): An Integer column that serves as the primary key. It auto-increments using values from 'id_seq'.
    """
    id_seq = Sequence("config_id_seq")
    id = Column(Integer, id_seq, server_default=id_seq.next_value(), primary_key=True)
    target_table_name = Column(String(255), nullable=False)
    target_field = Column(String(255), nullable=False)
    source_field = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)
    transformation = Column(String(50), nullable=False)
    description = Column(Text)

    def __repr__(self) -> str:
        return (
            f"<MappingConfig(target_table_name={self.target_table_name}, "
            f"source_field={self.source_field}, target_field={self.target_field}, "
            f"field_type={self.field_type}, transformation={self.transformation})>"
        )
