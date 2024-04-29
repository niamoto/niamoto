"""
This module provides a Database class for connecting to and interacting with a DuckDB database.

The Database class offers methods to establish a connection, get new sessions, 
add instances to the database, and close sessions.
"""
from typing import TypeVar, Any, Optional, List
import duckdb
from sqlalchemy import create_engine, exc, text, inspect
from sqlalchemy.orm import scoped_session, sessionmaker, Query, Session

T = TypeVar("T")


class Database:
    """
    A class that provides a connection to a database and offers methods
    to interact with it.

    Attributes:
    - engine: The database engine connection.
    - session: A scoped session for creating new database sessions.

    Methods:
    - get_new_session: Returns a new session.
    - add_instance_and_commit: Adds an instance to the session and commits it.
    - close_db_session: Closes the database session.
    """

    def __init__(
        self,
        db_path: str,
    ) -> None:
        """
        Initialize the Database class with given parameters.

        :param db_path: Path to the database file.
        """

        try:
            self.db_path = db_path
            self.connection_string = f"duckdb:///{db_path}"
            self.engine = create_engine(self.connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self.session = scoped_session(self.session_factory)
            self.active_transaction = False
        except exc.SQLAlchemyError as e:
            raise Exception(
                f"SQLAlchemy error during database initialization: {e}"
            ) from e

    def has_table(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        :param table_name: The name of the table to check.
        :return: True if the table exists, False otherwise.
        """
        inspector = inspect(self.engine)
        return table_name in inspector.get_table_names()

    def get_new_session(self) -> scoped_session[Session]:
        """
        Get a new session from the session factory.

        :return: A new session.
        """
        return self.session

    def add_instance_and_commit(self, instance: Any) -> None:
        """
        Add an instance to the session and commit.

        :param instance: The instance to be added.
        """
        try:
            self.session.add(instance)
            self.session.commit()
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            print(f"Error while adding and committing: {e}")

    @staticmethod
    def execute_query(query: Query[T]) -> Optional[List[Any]]:
        """
        Execute a given query and handle any database-related exceptions.

        :param query: A SQLAlchemy query object.
        :return: The result of the query if successful, None otherwise.
        """
        try:
            return query.all()
        except (duckdb.duckdb.IOException, exc.SQLAlchemyError) as e:  # type: ignore
            Database.__handle_db_errors(e)
            return None

    def execute_select(self, sql: str) -> Optional[Any]:
        """
        Execute a SELECT query using the database engine.

        :param sql: A string containing the SELECT query to be executed.
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql))
                return result
        except (duckdb.duckdb.IOException, exc.SQLAlchemyError) as e:  # type: ignore
            print(f"Exception occurred: {e}")
            self.__handle_db_errors(e)
            return None

    def execute_sql(self, sql: str) -> Optional[Any]:
        """
        Execute a raw SQL query using the database engine.

        :param sql: A string containing the SQL query to be executed.
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql))
                connection.commit()
                return result
        except (duckdb.duckdb.IOException, exc.SQLAlchemyError) as e:  # type: ignore
            print(f"Exception occurred: {e}")
            self.__handle_db_errors(e)
            return None

    def commit_session(self) -> None:
        """
        Commit the current session to the database.
        """
        try:
            self.session.commit()
        except (duckdb.duckdb.IOException, exc.SQLAlchemyError) as e:  # type: ignore
            self.session.rollback()
            Database.__handle_db_errors(e)

    def rollback_session(self) -> None:
        """
        Rollback the current session, discarding any uncommitted changes.
        """
        try:
            self.session.rollback()
        except duckdb.duckdb.IOException as e:  # type: ignore
            if "Resource temporarily unavailable" in str(e):
                raise Exception(
                    "Database is currently in use by another application. Please try again later."
                ) from e
            else:
                raise Exception(f"Unexpected IO error with the database: {e}") from e
        except exc.SQLAlchemyError as e:
            raise Exception(f"SQLAlchemy error during database operation: {e}") from e

    def close_db_session(self) -> None:
        """
        Close the database session.
        """
        self.session.remove()

    def begin_transaction(self) -> None:
        """
        Begin a new transaction.
        """
        if not self.active_transaction:
            self.session.begin()
            self.active_transaction = True
        else:
            raise Exception("A transaction is already active.")

    def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        """
        if self.active_transaction:
            try:
                self.session.commit()
                self.active_transaction = False
            except (duckdb.duckdb.IOException, exc.SQLAlchemyError) as e:  # type: ignore
                self.__handle_db_errors(e)
        else:
            raise Exception("No active transaction to commit.")

    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.
        """
        if self.active_transaction:
            try:
                self.session.rollback()
                self.active_transaction = False
            except (duckdb.duckdb.IOException, exc.SQLAlchemyError) as e:  # type: ignore
                self.__handle_db_errors(e)
        else:
            raise Exception("No active transaction to rollback.")

    @staticmethod
    def __handle_db_errors(error: Exception) -> None:
        """
        Private helper method to handle database-related errors.

        :param error: The exception object that was raised.
        :raises Exception: Raises an appropriate exception based on the error type.
        """
        if isinstance(error, duckdb.duckdb.IOException):  # type: ignore
            if "Resource temporarily unavailable" in str(error):
                raise Exception(
                    "Database is currently in use by another application. Please try again later."
                ) from error
            else:
                raise Exception(
                    f"Unexpected IO error with the database: {error}"
                ) from error
        elif isinstance(error, exc.SQLAlchemyError):
            raise Exception(
                f"SQLAlchemy error during database operation: {error}"
            ) from error
        else:
            raise Exception(
                f"Unexpected error during database operation: {error}"
            ) from error
