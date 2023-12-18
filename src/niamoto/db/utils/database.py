"""
This module provides a Database class for connecting to and interacting with a SQLite database.

The Database class offers methods to establish a connection, get new sessions, 
add instances to the database, and close sessions.
"""
from typing import Any, Optional
import traceback
from sqlalchemy import create_engine, event, exc
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool


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
        pool_size: Optional[int] = 5,
        max_overflow: Optional[int] = 10,
        pool_recycle: Optional[int] = 3600,
    ) -> None:
        """
        Initialize the Database class with given parameters.

        :param db_name: Name of the database.
        :param pool_size: Number of connections to keep in the connection pool.
        :param max_overflow: Maximum number of connections to create beyond the pool_size.
        :param pool_recycle: Time, in seconds, to recycle connections.
        """

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Added to test the connection before using it
        )

        @event.listens_for(self.engine, "connect")
        def enable_spatialite_extension(dbapi_connection: Any, _: Any) -> None:
            """
            Enable the spatialite extension for the given dbapi_connection.

            :param dbapi_connection: The connection to enable the spatialite extension on.
            """
            # pylint: disable=broad-except
            try:
                dbapi_connection.enable_load_extension(True)
                # load_extension = "SELECT load_extension('/opt/homebrew/lib/mod_spatialite.dylib')"
                # dbapi_connection.execute(load_extension)
                """ dbapi_connection.load_extension(
                    "/opt/homebrew/lib/mod_spatialite.dylib"
                ) """
                # dbapi_connection.execute("SELECT InitSpatialMetadata(1)")
            except Exception:
                # Here we print the full stack trace instead of just the exception message
                traceback.print_exc()

        self.session = scoped_session(sessionmaker(bind=self.engine))

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

    def close_db_session(self) -> None:
        """
        Close the database session.
        """
        self.session.remove()
