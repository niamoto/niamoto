import pytest
from typing import Any
from sqlalchemy.exc import InvalidRequestError, OperationalError
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session
from niamoto.core.models import Base, TaxonRef
from niamoto.common.database import Database

# Assuming you're using an in-memory SQLite database for testing
TEST_DATABASE_URI = "sqlite:///:memory:"


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
    dummy_instance = TaxonRef(full_name="test")
    test_database.add_instance_and_commit(dummy_instance)
    result = session.query(TaxonRef).filter_by(full_name="test").first()
    assert result is not None
    assert result.full_name == "test"


def test_access_nonexistent_column(test_database: Any, session: scoped_session) -> None:
    """
    Attempt to access a column that does not exist.
    This should raise an OperationalError.
    """
    with pytest.raises(OperationalError):
        # Use raw SQL to bypass Python attribute checks
        session.execute(text("SELECT nonexistent_column FROM taxon_ref")).fetchall()


def test_use_incorrect_table_name_in_query(
    test_database: Any, session: scoped_session
) -> None:
    """
    Use an incorrect table name in a query.
    This should raise an OperationalError.
    """
    with pytest.raises(OperationalError):
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
    dummy_instance = TaxonRef(full_name="test_query")
    test_database.add_instance_and_commit(dummy_instance)

    # Use a raw SQL query string instead of a SQLAlchemy Query object
    result = test_database.execute_query(
        "SELECT * FROM taxon_ref WHERE full_name = 'test_query'"
    )

    assert result is not None
    assert len(result) == 1
    assert result[0][1] == "test_query"  # Assuming full_name is the second column


def test_commit_session(test_database: Any, session: scoped_session) -> None:
    """
    Test committing the session.
    """
    dummy_instance = TaxonRef(full_name="test_commit")
    session.add(dummy_instance)

    test_database.commit_session()

    result = session.query(TaxonRef).filter_by(full_name="test_commit").first()
    assert result is not None
    assert result.full_name == "test_commit"


def test_has_table(test_database: Any) -> None:
    """Test checking if a table exists."""
    # TaxonRef table should exist as it was created in the fixture
    assert test_database.has_table("taxon_ref") is True
    # Non-existent table should return False
    assert test_database.has_table("non_existent_table") is False


def test_execute_select(test_database: Any, session: scoped_session) -> None:
    """Test executing a SELECT query."""
    # Add test data
    dummy_instance = TaxonRef(full_name="test_select")
    test_database.add_instance_and_commit(dummy_instance)

    # Execute SELECT query
    result = test_database.execute_select(
        "SELECT full_name FROM taxon_ref WHERE full_name = 'test_select'"
    )
    assert result is not None
    row = result.fetchone()
    assert row is not None
    assert row[0] == "test_select"

    # Test with invalid SQL
    with pytest.raises(Exception):
        test_database.execute_select("SELECT * FROM non_existent_table")


def test_execute_sql(test_database: Any, session: scoped_session) -> None:
    """Test executing raw SQL queries."""
    # Test INSERT
    test_database.execute_sql("INSERT INTO taxon_ref (full_name) VALUES ('test_sql')")

    # Test SELECT with fetch=True
    result = test_database.execute_sql(
        "SELECT full_name FROM taxon_ref WHERE full_name = 'test_sql'", fetch=True
    )
    assert result is not None
    assert result[0] == "test_sql"

    # Test invalid SQL
    with pytest.raises(Exception):
        test_database.execute_sql("SELECT * FROM non_existent_table")


def test_rollback_session(test_database: Any, session: scoped_session) -> None:
    """Test rolling back a session."""
    # Add an instance but don't commit
    dummy_instance = TaxonRef(full_name="test_rollback")
    session.add(dummy_instance)

    # Rollback the session
    test_database.rollback_session()

    # Verify the instance was not committed
    result = session.query(TaxonRef).filter_by(full_name="test_rollback").first()
    assert result is None


def test_transaction_lifecycle(test_database: Any) -> None:
    """Test the complete transaction lifecycle."""
    # Begin transaction
    test_database.begin_transaction()
    assert test_database.active_transaction is True

    # Try to begin another transaction (should fail)
    with pytest.raises(Exception):
        test_database.begin_transaction()

    # Add some data
    dummy_instance = TaxonRef(full_name="test_transaction")
    test_database.session.add(dummy_instance)

    # Commit transaction
    test_database.commit_transaction()
    assert test_database.active_transaction is False

    # Verify data was committed
    result = (
        test_database.session.query(TaxonRef)
        .filter_by(full_name="test_transaction")
        .first()
    )
    assert result is not None
    assert result.full_name == "test_transaction"


def test_transaction_rollback(test_database: Any) -> None:
    """Test rolling back a transaction."""
    # Begin transaction
    test_database.begin_transaction()
    assert test_database.active_transaction is True

    # Add some data
    dummy_instance = TaxonRef(full_name="test_transaction_rollback")
    test_database.session.add(dummy_instance)

    # Rollback transaction
    test_database.rollback_transaction()
    assert test_database.active_transaction is False

    # Verify data was not committed
    result = (
        test_database.session.query(TaxonRef)
        .filter_by(full_name="test_transaction_rollback")
        .first()
    )
    assert result is None


def test_transaction_errors(test_database: Any) -> None:
    """Test transaction error cases."""
    # Try to commit without active transaction
    with pytest.raises(Exception):
        test_database.commit_transaction()

    # Try to rollback without active transaction
    with pytest.raises(Exception):
        test_database.rollback_transaction()

    # Begin transaction
    test_database.begin_transaction()

    # Try to begin another transaction
    with pytest.raises(Exception):
        test_database.begin_transaction()

    # Clean up
    test_database.rollback_transaction()
