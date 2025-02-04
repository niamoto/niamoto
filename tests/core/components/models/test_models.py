"""
This test module contains unit tests for the Taxon model.
It tests the basic CRUD operations (Create, Read, Update, Delete)
on the TaxonRef model using a SQLite in-memory database.
"""

import pytest
from typing import Any
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.engine import Engine
from niamoto.core.models import Base, TaxonRef

TEST_DATABASE_URI = "sqlite:///:memory:"  # SQLite in-memory database for testing


@pytest.fixture(scope="session")  # type: ignore
def engine() -> Engine:
    """
    Creates a SQLAlchemy engine that will be used for test sessions.
    """
    engine = create_engine(TEST_DATABASE_URI, echo=True)

    return engine


@pytest.fixture(scope="session")  # type: ignore
def tables(engine: Engine) -> Any:
    """
    Creates all tables for the test database, and drops them at the end of the session.
    """
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture  # type: ignore
def db_session(engine: Any, tables: Any) -> Any:
    """
    Returns an SQLAlchemy session, and after the test tears down everything properly.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    scoped_session_factory = scoped_session(session_factory)

    session = scoped_session_factory()

    yield session

    scoped_session_factory.remove()
    transaction.rollback()
    connection.close()


# Test cases for the TaxonRef model start here
def test_create_taxon(db_session: Any) -> None:
    """
    Tests that a Taxon instance can be successfully created and saved to the database.
    """
    new_taxon = TaxonRef(full_name="Quercus robur", rank_name="Species")
    db_session.add(new_taxon)
    db_session.commit()

    # Check that the instance has been saved in the database
    saved_taxon = (
        db_session.query(TaxonRef).filter_by(full_name="Quercus robur").first()
    )
    assert saved_taxon is not None
    assert saved_taxon.rank_name == "Species"


def test_update_taxon(db_session: Any) -> None:
    """
    Tests that a Taxon instance can be updated in the database.
    """
    taxon = TaxonRef(full_name="Quercus robur", rank_name="Species")
    db_session.add(taxon)
    db_session.commit()

    # Update the instance
    saved_taxon = (
        db_session.query(TaxonRef).filter_by(full_name="Quercus robur").first()
    )
    saved_taxon.rank_name = "Genus"
    db_session.commit()

    # Verify the instance has been updated
    updated_taxon = (
        db_session.query(TaxonRef).filter_by(full_name="Quercus robur").first()
    )
    assert updated_taxon.rank_name == "Genus"


def test_delete_taxon(db_session: Any) -> None:
    """
    Tests that a Taxon instance can be deleted from the database.
    """
    taxon = TaxonRef(full_name="Quercus robur", rank_name="Species")
    db_session.add(taxon)
    db_session.commit()

    # Delete the instance
    saved_taxon = (
        db_session.query(TaxonRef).filter_by(full_name="Quercus robur").first()
    )
    db_session.delete(saved_taxon)
    db_session.commit()

    # Verify the instance has been deleted
    deleted_taxon = (
        db_session.query(TaxonRef).filter_by(full_name="Quercus robur").first()
    )
    assert deleted_taxon is None
