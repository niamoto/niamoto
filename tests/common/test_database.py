import pytest
from typing import Any
from sqlalchemy.exc import InvalidRequestError, ProgrammingError
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session
from niamoto.core.models import Base, Taxon
from niamoto.common.database import Database

# Assuming you're using an in-memory DuckDB database for testing
TEST_DATABASE_URI = "duckdb:///:memory:"


@pytest.fixture
def test_database() -> Any:
    """
    Fixture to create a test database instance.
    It initializes a Database object with a test database name.
    """
    # Here you create a new instance of the Database class configured for testing
    db = Database(db_path=":memory:")
    # Here you create all the tables using the metadata
    Base.metadata.create_all(db.engine)
    yield db
    db.close_db_session()


@pytest.fixture
def session(test_database) -> scoped_session:
    """
    Creates a new database session for a test.
    """
    session = test_database.get_new_session()
    yield session
    session.rollback()
    session.close()


def test_database_initialization(test_database: Any) -> None:
    """
    Test if the database is initialized correctly.
    Ensures that the engine and session properties are set up properly.
    """
    assert test_database.engine is not None
    assert test_database.session is not None


def test_get_new_session(test_database: Any) -> None:
    """
    Test getting a new session.
    Validates that a new session can be retrieved and is operational.
    """
    session = test_database.get_new_session()
    assert session is not None
    # Perform additional tests to check if the session is valid
    assert session.is_active


def test_add_instance_and_commit(test_database: Any, session: scoped_session) -> None:
    """
    Test adding and committing an instance.
    Adds a dummy model instance to the database and commits it.
    Then it retrieves the instance to ensure it was properly added.
    """
    dummy_instance = Taxon(full_name="test")
    test_database.add_instance_and_commit(dummy_instance)
    result = session.query(Taxon).filter_by(full_name="test").first()
    assert result is not None
    assert result.full_name == "test"


def test_access_nonexistent_column(test_database: Any, session: scoped_session) -> None:
    """
    Attempt to access a column that does not exist.
    This should raise a ProgrammingError.
    """
    with pytest.raises(ProgrammingError):
        # Use raw SQL to bypass Python attribute checks
        session.execute(text("SELECT nonexistent_column FROM taxon")).fetchall()


def test_use_incorrect_table_name_in_query(
    test_database: Any, session: scoped_session
) -> None:
    """
    Use an incorrect table name in a query.
    This should raise a ProgrammingError.
    """
    with pytest.raises(ProgrammingError):
        # Directly using SQL expression to simulate incorrect table name
        result = session.execute(text("SELECT * FROM non_existent_table"))
        result.fetchall()


def test_start_new_transaction_without_ending_previous(
    test_database: Any, session: scoped_session
) -> None:
    """
    Start a new transaction without committing or rolling back the previous one.
    This should raise an InvalidRequestError.
    """
    session.begin()
    # Start a new transaction
    with pytest.raises(InvalidRequestError):
        session.begin()
        # Attempt to start another without ending the first


def test_close_db_session(test_database: Any, session) -> None:
    """
    Test closing the database session.
    Checks if closing the session makes it unusable as expected, indicating that it is indeed closed.
    """
    session = test_database.get_new_session()
    test_database.close_db_session()

    # Try to use the session after it has been closed
    with pytest.raises(Exception):
        session.execute("SELECT 1")


def test_execute_query(test_database: Any, session: scoped_session) -> None:
    """
    Test executing a query through the execute_query method.
    """
    dummy_instance = Taxon(full_name="test_query")
    test_database.add_instance_and_commit(dummy_instance)

    query = session.query(Taxon).filter_by(full_name="test_query")

    result = test_database.execute_query(query)
    assert result is not None
    assert len(result) == 1
    assert result[0].full_name == "test_query"


def test_commit_session(test_database: Any, session: scoped_session) -> None:
    """
    Test committing the session.
    """
    dummy_instance = Taxon(full_name="test_commit")
    session.add(dummy_instance)

    test_database.commit_session()

    result = session.query(Taxon).filter_by(full_name="test_commit").first()
    assert result is not None
    assert result.full_name == "test_commit"
