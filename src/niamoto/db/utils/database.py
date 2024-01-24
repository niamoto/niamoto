"""
This module provides a Database class for connecting to and interacting with a DuckDB database.

The Database class offers methods to establish a connection, get new sessions, 
add instances to the database, and close sessions.
"""
from typing import TypeVar, Any, Optional, List
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import scoped_session, sessionmaker, Query
import duckdb

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
            self.engine = create_engine(f"duckdb:///{db_path}")
            self.session = scoped_session(sessionmaker(bind=self.engine))
        except exc.SQLAlchemyError as e:
            raise Exception(
                f"SQLAlchemy error during database initialization: {e}"
            ) from e

    def get_new_session(self) -> scoped_session[Any]:
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

    def execute_query(self, query: Query[T]) -> Optional[List[Any]]:
        """
        Execute a given query and handle any database-related exceptions.

        :param query: A SQLAlchemy query object.
        :return: The result of the query if successful, None otherwise.
        """
        try:
            return query.all()
        except duckdb.duckdb.IOException as e:  # type: ignore
            if "Resource temporarily unavailable" in str(e):
                raise Exception(
                    "Database is currently in use by another application. Please try again later."
                ) from e
            else:
                raise Exception(f"Unexpected IO error with the database: {e}") from e
        except exc.SQLAlchemyError as e:
            raise Exception(f"SQLAlchemy error during database operation: {e}") from e

    def commit_session(self) -> None:
        """
        Commit the current session to the database.
        """
        try:
            self.session.commit()
        except duckdb.duckdb.IOException as e:  # type: ignore
            if "Resource temporarily unavailable" in str(e):
                raise Exception(
                    "Database is currently in use by another application. Please try again later."
                ) from e
            else:
                raise Exception(f"Unexpected IO error with the database: {e}") from e
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"SQLAlchemy error during database operation: {e}") from e

    def close_db_session(self) -> None:
        """
        Close the database session.
        """
        self.session.remove()
