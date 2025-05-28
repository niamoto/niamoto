"""
This module provides a Database class for connecting to and interacting with a database.

The Database class offers methods to establish a connection, get new sessions,
add instances to the database, and close sessions.
"""

from typing import TypeVar, Any, Optional, List, Dict
from sqlalchemy import create_engine, exc, text, inspect
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from niamoto.common.exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseWriteError,
    TransactionError,
)
from niamoto.common.utils import error_handler

import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Database:
    """
    A class that provides a connection to a database and offers methods
    to interact with it.
    """

    @error_handler(log=True, raise_error=True)
    def __init__(
        self,
        db_path: str,
    ) -> None:
        """
        Initialize the Database class with given parameters.

        Args:
            db_path (str): Path to the database file.
        """

        try:
            self.db_path = db_path
            self.connection_string = f"sqlite:///{db_path}"
            self.engine = create_engine(self.connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            self.session = scoped_session(self.session_factory)
            self.active_transaction = False
        except exc.SQLAlchemyError as e:
            raise DatabaseConnectionError(
                message="Failed to initialize database connection",
                details={"path": db_path, "error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def has_table(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        inspector = inspect(self.engine)
        return table_name in inspector.get_table_names()

    @error_handler(log=True, raise_error=True)
    def get_new_session(self) -> scoped_session[Session]:
        """
        Get a new session from the session factory.

        Returns:
            scoped_session[Session]: A new session.
        """
        try:
            return self.session
        except Exception as e:
            raise DatabaseConnectionError(
                message="Failed to create new session", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def add_instance_and_commit(self, instance: Any) -> None:
        """
        Add an instance to the session and commit.

        Args:
            instance (Any): The instance to be added.
        """
        try:
            self.session.add(instance)
            self.session.commit()
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseWriteError(
                table_name=instance.__tablename__,
                message="Failed to add and commit instance",
                details={"error": str(e)},
            )

    @error_handler(log=True, raise_error=True)
    def execute_select(self, sql: str) -> Optional[Any]:
        """
        Execute a SELECT query using the database engine.

        Args:
            sql (str): A string containing the SELECT query to be executed.

        Returns:
            Optional[Any]: The result of the query if successful, None otherwise.
        """
        try:
            with self.engine.connect() as connection:
                return connection.execute(text(sql))
        except exc.SQLAlchemyError as e:
            raise DatabaseQueryError(
                query=sql, message="SELECT query failed", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def execute_sql(
        self, sql: str, params: Dict[str, Any] = None, fetch: bool = False
    ) -> Optional[Any]:
        """
        Execute a raw SQL query using the database engine.

        Args:
            sql (str): A string containing the SQL query to be executed.
            params (Dict[str, Any], optional): Parameters to bind to the query.
            fetch (bool): Whether to fetch one row from the result set if the query returns data.

        Returns:
            Optional[Any]: The result of the query if `fetch` is True and a result is available, or None otherwise.
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql), params or {})
                if fetch:
                    return result.fetchone() if fetch else result.fetchall()
                connection.commit()
                return result
        except exc.SQLAlchemyError as e:
            raise DatabaseQueryError(
                query=sql,
                message="SQL execution failed",
                details={"fetch": fetch, "params": params, "error": str(e)},
            )

    def commit_session(self) -> None:
        """
        Commit the current session to the database.
        """
        try:
            self.session.commit()
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseWriteError(
                table_name="session",
                message="Failed to commit session",
                details={"error": str(e)},
            )

    def rollback_session(self) -> None:
        """
        Rollback the current session, discarding any uncommitted changes.
        """
        try:
            self.session.rollback()
        except exc.SQLAlchemyError as e:
            raise DatabaseError(
                message="Failed to rollback session", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def close_db_session(self) -> None:
        """
        Close the database session.
        """
        try:
            self.session.remove()
        except exc.SQLAlchemyError as e:
            raise DatabaseError(
                message="Failed to close database session", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def begin_transaction(self) -> None:
        """
        Begin a new transaction.
        """
        if self.active_transaction:
            raise TransactionError(
                message="Cannot begin transaction",
                details={"reason": "A transaction is already active"},
            )
        try:
            self.session.begin()
            self.active_transaction = True
        except exc.SQLAlchemyError as e:
            raise DatabaseError(
                message="Failed to begin transaction", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        """
        if not self.active_transaction:
            raise TransactionError(
                message="Cannot commit transaction",
                details={"reason": "No active transaction"},
            )
        try:
            self.session.commit()
            self.active_transaction = False
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(
                message="Failed to commit transaction", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.
        """
        if not self.active_transaction:
            raise TransactionError(
                message="Cannot rollback transaction",
                details={"reason": "No active transaction"},
            )
        try:
            self.session.rollback()
            self.active_transaction = False
        except exc.SQLAlchemyError as e:
            raise DatabaseError(
                message="Failed to rollback transaction", details={"error": str(e)}
            )

    def get_table_columns(self, table_name: str) -> List[str]:
        """Retrieves the list of column names for a given table."""
        query = f"PRAGMA table_info({table_name});"
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                columns_info = result.fetchall()
                # The column name is the second element (index 1) in each row returned by PRAGMA table_info
                column_names = [row[1] for row in columns_info]
                if not column_names:
                    logger.warning(
                        f"Could not retrieve columns for table '{table_name}', it might not exist or has no columns."
                    )
                return column_names
        except exc.SQLAlchemyError as e:
            logger.error(
                f"Database error getting columns for table '{table_name}': {e}"
            )
            # Depending on desired strictness, could return empty list or re-raise
            return []
        except Exception as e:  # Catch potential issues like table name injection, though PRAGMA is safer
            logger.error(
                f"Unexpected error getting columns for table '{table_name}': {e}"
            )
            return []

    def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Executes a raw SQL query and returns all results as a list of dictionaries."""
        session = self.get_new_session()
        try:
            result = session.execute(text(query), params)
            # Use mappings().all() to get results as list of dicts
            rows = result.mappings().all()
            logger.debug(
                f"Executed fetch_all query '{query}' with params {params}. Found {len(rows)} rows."
            )
            return rows
        except exc.SQLAlchemyError as e:
            logger.error(
                f"Database error executing fetch_all query '{query}' with params {params}: {e}"
            )
            session.rollback()  # Rollback in case of error
            # Depending on desired behavior, could raise an exception or return empty list
            raise DatabaseError(
                message="Failed to execute fetch_all query",
                details={"query": query, "params": params, "error": str(e)},
            )
        except Exception as e:
            logger.error(
                f"Unexpected error executing fetch_all query '{query}' with params {params}: {e}",
                exc_info=True,
            )
            session.rollback()
            raise DatabaseError(
                message="Unexpected error during fetch_all query",
                details={"query": query, "params": params, "error": str(e)},
            )
        finally:
            session.close()
            logger.debug("Session closed after fetch_all.")

    def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Executes a raw SQL query and returns the first result as a dictionary, or None if no result."""
        session = self.get_new_session()
        try:
            result = session.execute(text(query), params)
            # Use mappings().first() to get the first result as a dict (or None)
            row = result.mappings().first()
            if row:
                logger.debug(
                    f"Executed fetch_one query '{query}' with params {params}. Found row."
                )
            else:
                logger.debug(
                    f"Executed fetch_one query '{query}' with params {params}. No row found."
                )
            return row
        except exc.SQLAlchemyError as e:
            logger.error(
                f"Database error executing fetch_one query '{query}' with params {params}: {e}"
            )
            session.rollback()
            raise DatabaseError(
                message="Failed to execute fetch_one query",
                details={"query": query, "params": params, "error": str(e)},
            )
        except Exception as e:
            logger.error(
                f"Unexpected error executing fetch_one query '{query}' with params {params}: {e}",
                exc_info=True,
            )
            session.rollback()
            raise DatabaseError(
                message="Unexpected error during fetch_one query",
                details={"query": query, "params": params, "error": str(e)},
            )
        finally:
            session.close()
            logger.debug("Session closed after fetch_one.")

    def execute_query(self, query: str, params: dict = None) -> Any:
        """Executes a given SQL query using the current session."""
        session = self.get_new_session()
        try:
            result = session.execute(text(query), params)
            return result.fetchall()
        except exc.SQLAlchemyError as e:
            session.rollback()
            raise DatabaseQueryError(
                query=query,
                message="Query execution failed",
                details={"error": str(e)},
            )
        finally:
            session.close()
