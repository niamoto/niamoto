"""
This module provides a Database class for connecting to and interacting with a database.

The Database class offers methods to establish a connection, get new sessions,
add instances to the database, and close sessions.
"""

from typing import TypeVar, Any, Optional, List, Dict
import warnings
from sqlalchemy import create_engine, exc, text, inspect
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from niamoto.common.exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseLockError,
    DatabaseWriteError,
    TransactionError,
)
from niamoto.common.utils import error_handler

import logging

logger = logging.getLogger(__name__)

# Suppress DuckDB reflection warnings - we handle reflection checks manually
# We skip index operations for DuckDB where needed, so this warning is expected
warnings.filterwarnings(
    "ignore",
    message="duckdb-engine doesn't yet support reflection on indices",
)
# Also catch by module
warnings.filterwarnings(
    "ignore",
    module="duckdb_engine",
)

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
        optimize: bool = True,
        engine: Optional[Engine] = None,
        read_only: bool = False,
    ) -> None:
        """
        Initialize the Database class with given parameters.

        Args:
            db_path (str): Path to the database file.
            optimize (bool): Whether to apply engine-specific optimizations.
            engine (Optional[Engine]): Optional pre-configured SQLAlchemy engine.
            read_only (bool): If True, open database in read-only mode (DuckDB only).
                This allows viewing the database when another process has a write lock.
        """

        try:
            self.db_path = db_path
            self.active_transaction = False
            self.read_only = read_only

            if engine is not None:
                self.engine = engine
                self.connection_string = str(getattr(engine, "url", "duckdb"))
                logger.debug("Database initialized with external engine instance")
            else:
                # Detect backend from path and create SQLAlchemy engine
                if db_path.startswith("sqlite://"):
                    self.connection_string = db_path
                    self.engine = create_engine(self.connection_string, echo=False)
                elif db_path in {":memory:", "memory", "sqlite:///:memory:"}:
                    self.connection_string = "sqlite:///:memory:"
                    self.engine = create_engine(self.connection_string, echo=False)
                elif db_path.endswith(".db") or db_path.endswith(".sqlite"):
                    self.connection_string = f"sqlite:///{db_path}"
                    self.engine = create_engine(self.connection_string, echo=False)
                else:
                    # For DuckDB, use connect_args to set access_mode
                    # Always use NullPool for DuckDB to avoid lock issues
                    self.connection_string = f"duckdb:///{db_path}"
                    engine_kwargs: Dict[str, Any] = {
                        "echo": False,
                        "poolclass": NullPool,
                    }
                    if read_only:
                        # Pass access_mode as connect_args for DuckDB
                        engine_kwargs["connect_args"] = {"read_only": True}
                        logger.info(f"Opening DuckDB in read-only mode: {db_path}")
                    self.engine = create_engine(self.connection_string, **engine_kwargs)

            connection_str = str(self.connection_string)
            self.is_duckdb = connection_str.startswith("duckdb")
            self.is_sqlite = connection_str.startswith("sqlite")

            self.session_factory = sessionmaker(bind=self.engine)
            self.session = scoped_session(self.session_factory)

            # Apply engine-specific optimizations
            if optimize and self.is_sqlite:
                self._apply_sqlite_optimizations()
                self._create_missing_indexes()
            if optimize and self.is_duckdb and not read_only:
                self._initialize_duckdb()

        except exc.SQLAlchemyError as e:
            error_msg = str(e)
            # Detect DuckDB lock error and provide a clearer message
            if (
                "Could not set lock on file" in error_msg
                and "Conflicting lock is held" in error_msg
            ):
                # Extract the application name from error message
                import re

                app_match = re.search(r"in ([^\(]+) \(PID", error_msg)
                app_name = (
                    app_match.group(1).strip() if app_match else "another application"
                )

                raise DatabaseLockError(
                    message=f"Database is locked by {app_name}. Close it or use read-only mode: Database(db_path, read_only=True)",
                    query="",
                    details={"path": db_path},
                )

            raise DatabaseConnectionError(
                message="Failed to initialize database connection",
                details={"path": db_path, "error": str(e)},
            )

    def _apply_sqlite_optimizations(self) -> None:
        """
        Apply SQLite PRAGMA optimizations for better performance.

        These optimizations can improve performance by 2-5x for typical workloads:
        - WAL mode: Allows concurrent reads and writes
        - Synchronous NORMAL: Faster writes while maintaining data integrity
        - Cache size: Increases memory cache to reduce disk I/O
        - Temp store: Keeps temporary tables in memory
        - Memory map: Uses memory-mapped I/O for better performance
        """
        optimizations = [
            "PRAGMA journal_mode = WAL",  # Write-Ahead Logging for concurrency
            "PRAGMA synchronous = NORMAL",  # Faster writes, still safe
            "PRAGMA cache_size = -64000",  # 64MB cache (negative = KB)
            "PRAGMA temp_store = MEMORY",  # Temporary tables in memory
            "PRAGMA mmap_size = 30000000000",  # 30GB memory-mapped I/O
            "PRAGMA page_size = 4096",  # Optimal page size for most systems
            "PRAGMA optimize",  # Run query optimizer
        ]

        try:
            with self.engine.connect() as connection:
                for pragma in optimizations:
                    connection.execute(text(pragma))
                    logger.debug(f"Applied optimization: {pragma}")
                connection.commit()
                logger.info("SQLite optimizations applied successfully")
        except exc.SQLAlchemyError as e:
            logger.warning(f"Failed to apply some SQLite optimizations: {e}")
            # Don't fail initialization if optimizations fail

    def _initialize_duckdb(self) -> None:
        """Load DuckDB extensions required by Niamoto (best effort)."""

        try:
            with self.engine.connect() as connection:
                for command in ("INSTALL spatial", "LOAD spatial"):
                    try:
                        connection.execute(text(command))
                    except exc.SQLAlchemyError as extension_error:
                        logger.debug(
                            "DuckDB extension command failed: %s (%s)",
                            command,
                            extension_error,
                        )
                connection.commit()
        except exc.SQLAlchemyError as e:
            # Check if it's a lock error - don't log it as warning in that case
            if "Could not set lock on file" in str(e):
                logger.debug("DuckDB initialization skipped (database locked)")
            else:
                logger.warning(f"DuckDB initialization warning: {e}")

    def _create_missing_indexes(self) -> None:
        """
        Automatically create indexes on foreign key columns that don't have them.

        SQLite doesn't automatically create indexes on foreign keys,
        which can significantly slow down joins and lookups.
        """
        if self.is_duckdb:
            logger.debug("Skipping automatic index creation for DuckDB (not supported)")
            return
        try:
            with self.engine.connect() as connection:
                # Get all tables
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()

                for table in tables:
                    # Get foreign keys for this table
                    foreign_keys = inspector.get_foreign_keys(table)

                    for fk in foreign_keys:
                        constrained_columns = fk["constrained_columns"]

                        for column in constrained_columns:
                            index_name = f"idx_{table}_{column}"

                            # Check if index already exists
                            existing_indexes = inspector.get_indexes(table)
                            index_exists = any(
                                column in idx.get("column_names", [])
                                for idx in existing_indexes
                            )

                            if not index_exists:
                                # Create index
                                sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
                                connection.execute(text(sql))
                                logger.info(f"Created index: {index_name}")

                connection.commit()
                logger.info("Missing indexes created successfully")

        except exc.SQLAlchemyError as e:
            logger.warning(f"Failed to create some indexes: {e}")
            # Don't fail if index creation fails

    def create_indexes_for_table(
        self, table_name: str, index_columns: List[str] = None
    ) -> None:
        """
        Create indexes on a dynamically created table.

        This method is designed for tables created during import/transform phases
        where table names are defined by user configuration.

        Args:
            table_name: Name of the dynamically created table
            index_columns: List of columns to index. If None, will auto-detect:
                - Columns ending with _id (likely foreign keys)
                - Common query columns (id, type, name, etc.)

        Example:
            # After creating 'occurrences' table from CSV
            db.create_indexes_for_table('occurrences')

            # After transform creates 'taxon_stats' table
            db.create_indexes_for_table('taxon_stats', ['taxon_id', 'year'])
        """
        if self.is_duckdb:
            logger.debug(
                "Skipping create_indexes_for_table('%s') for DuckDB (index reflection unsupported)",
                table_name,
            )
            return

        try:
            with self.engine.connect() as connection:
                inspector = inspect(self.engine)

                # Verify table exists
                if table_name not in inspector.get_table_names():
                    logger.debug(
                        f"Table '{table_name}' does not exist, skipping index creation"
                    )
                    return

                # Get all columns in the table
                columns_info = inspector.get_columns(table_name)
                all_columns = {col["name"] for col in columns_info}

                # Auto-detect columns to index if not specified
                if index_columns is None:
                    index_columns = []

                    # Pattern 1: Foreign key-like columns
                    fk_patterns = ["_id", "_fk"]
                    for col in all_columns:
                        if any(col.endswith(pattern) for pattern in fk_patterns):
                            index_columns.append(col)

                    # Pattern 2: Common filter/join columns
                    common_columns = [
                        "id",
                        "type",
                        "name",
                        "code",
                        "category",
                        "group_by",
                        "source",
                        "target",
                        "year",
                        "date",
                        "locality",
                        "region",
                        "status",
                        "rank_name",
                    ]
                    for col in common_columns:
                        if col in all_columns and col not in index_columns:
                            index_columns.append(col)

                # Filter to only existing columns
                index_columns = [col for col in index_columns if col in all_columns]

                if not index_columns:
                    logger.debug(f"No columns to index for table '{table_name}'")
                    return

                # Get existing indexes to avoid duplicates
                existing_indexes = inspector.get_indexes(table_name)
                indexed_columns = set()
                for idx in existing_indexes:
                    indexed_columns.update(idx.get("column_names", []))

                # Create individual indexes
                created_indexes = []
                # Use safe index naming (handle special characters in table/column names)
                safe_table_name = table_name.replace("-", "_").replace(" ", "_")

                for column in index_columns:
                    if column not in indexed_columns:
                        safe_column_name = column.replace("-", "_").replace(" ", "_")
                        index_name = f"idx_{safe_table_name}_{safe_column_name}"[
                            :63
                        ]  # SQLite limit

                        sql = f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}"("{column}")'
                        connection.execute(text(sql))
                        created_indexes.append(index_name)
                        logger.debug(f"Created index: {index_name}")

                # Create composite indexes for common patterns
                if len(index_columns) >= 2:
                    # If we have both an ID and a type/category column, create composite index
                    id_cols = [c for c in index_columns if "id" in c.lower()]
                    type_cols = [
                        c
                        for c in index_columns
                        if c in ["type", "category", "group_by"]
                    ]

                    if id_cols and type_cols:
                        for id_col in id_cols[:1]:  # Just the first ID column
                            for type_col in type_cols[:1]:  # Just the first type column
                                composite_name = (
                                    f"idx_{safe_table_name}_{id_col}_{type_col}"[:63]
                                )
                                sql = f'CREATE INDEX IF NOT EXISTS "{composite_name}" ON "{table_name}"("{id_col}", "{type_col}")'
                                connection.execute(text(sql))
                                created_indexes.append(composite_name)
                                logger.debug(
                                    f"Created composite index: {composite_name}"
                                )

                connection.commit()

                if created_indexes:
                    logger.info(
                        f"Created {len(created_indexes)} index(es) for table '{table_name}'"
                    )
                else:
                    logger.debug(
                        f"No new indexes needed for table '{table_name}' (already indexed)"
                    )

        except exc.SQLAlchemyError as e:
            logger.warning(f"Failed to create indexes for table '{table_name}': {e}")
            # Don't fail - indexes are optimization, not critical

    def optimize_all_tables(self) -> None:
        """
        Optimize all tables in the database by creating missing indexes.
        Useful after import/transform operations that create new tables.
        """
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()

            logger.info(f"Optimizing {len(tables)} tables...")

            for table in tables:
                self.create_indexes_for_table(table)

            # Run ANALYZE to update statistics
            with self.engine.connect() as connection:
                connection.execute(text("ANALYZE"))
                connection.commit()

            logger.info("Database optimization completed")

        except exc.SQLAlchemyError as e:
            logger.warning(f"Failed to optimize some tables: {e}")

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

        Note:
            For DuckDB, this method disposes of the connection pool before executing queries
            to ensure we see the latest committed data. This is necessary because DuckDB
            uses in-process connections that may cache database state.
        """
        try:
            # For DuckDB, dispose of the pool to get fresh connections
            # This ensures we see the latest data after imports/transforms
            if self.is_duckdb:
                self.engine.dispose()

            with self.engine.connect() as connection:
                return connection.execute(text(sql))
        except exc.SQLAlchemyError as e:
            raise DatabaseQueryError(
                query=sql, message="SELECT query failed", details={"error": str(e)}
            )

    @error_handler(log=True, raise_error=True)
    def execute_sql(
        self,
        sql: str,
        params: Dict[str, Any] = None,
        fetch: bool = False,
        *,
        fetch_all: bool = False,
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

                if fetch_all and fetch:
                    raise DatabaseQueryError(
                        query=sql,
                        message="Invalid fetch parameters",
                        details={"fetch": fetch, "fetch_all": fetch_all},
                    )

                if fetch_all:
                    rows = result.fetchall()
                    connection.commit()
                    return rows

                if fetch:
                    row = result.fetchone()
                    connection.commit()
                    return row

                connection.commit()
                return result
        except exc.SQLAlchemyError as e:
            error_msg = str(e)
            # Detect DuckDB lock error and provide a clearer message
            if (
                "Could not set lock on file" in error_msg
                and "Conflicting lock is held" in error_msg
            ):
                import re

                app_match = re.search(r"in ([^\(]+) \(PID", error_msg)
                app_name = (
                    app_match.group(1).strip() if app_match else "another application"
                )

                raise DatabaseLockError(
                    message=f"💾 Database is locked by {app_name}. Close it to perform write operations.",
                    query=sql,
                    details={
                        "suggestion": "Close the other application or wait for it to finish."
                    },
                )

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
        """Return column names for the given table."""

        schema = self.get_table_schema(table_name)
        if not schema:
            logger.warning("Could not retrieve columns for table '%s'", table_name)
            return []
        return [column["name"] for column in schema]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Return table schema as list of {name, type} dictionaries."""

        try:
            if self.is_duckdb:
                query = (
                    "SELECT column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_schema = current_schema() "
                    "AND table_name = :table "
                    "ORDER BY ordinal_position"
                )
                rows = self.execute_sql(query, {"table": table_name}, fetch_all=True)
                return (
                    [{"name": row[0], "type": row[1]} for row in rows] if rows else []
                )

            query = f"PRAGMA table_info('{table_name}')"
            rows = self.execute_sql(query, fetch_all=True)
            return [{"name": row[1], "type": row[2]} for row in rows] if rows else []
        except DatabaseQueryError:
            return []

    def optimize_database(self) -> None:
        """
        Run database optimization routines.

        This method can be called periodically to maintain optimal performance:
        - For SQLite: Applies PRAGMA optimizations, ANALYZE, and VACUUM
        - For DuckDB: Runs CHECKPOINT and VACUUM to compact the database
        - Creates any missing indexes (SQLite only, DuckDB doesn't support index reflection)
        """
        try:
            if self.is_sqlite:
                # SQLite optimization path
                self._apply_sqlite_optimizations()

                with self.engine.connect() as connection:
                    # Run ANALYZE to update statistics
                    connection.execute(text("ANALYZE"))
                    logger.info("Database statistics updated")

                    # Run PRAGMA optimize
                    connection.execute(text("PRAGMA optimize"))
                    logger.info("Query optimizer updated")

                    connection.commit()

                # Recreate any missing indexes
                self._create_missing_indexes()
            else:
                # DuckDB optimization path
                with self.engine.connect() as connection:
                    logger.info("Running DuckDB CHECKPOINT...")
                    connection.execute(text("CHECKPOINT"))
                    logger.info("CHECKPOINT completed")

                    logger.info("Running DuckDB VACUUM to compact database...")
                    connection.execute(text("VACUUM"))
                    logger.info("VACUUM completed - database compacted")

                    connection.commit()

            logger.info("Database optimization completed successfully")

        except exc.SQLAlchemyError as e:
            logger.warning(f"Database optimization partially failed: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics and performance metrics.

        Returns:
            Dict containing database size, page count, cache statistics, etc.
        """
        stats = {}

        try:
            with self.engine.connect() as connection:
                # Database size
                if self.is_sqlite:
                    result = connection.execute(text("PRAGMA page_count"))
                    page_count = result.scalar()

                    result = connection.execute(text("PRAGMA page_size"))
                    page_size = result.scalar()

                    stats["database_size_bytes"] = page_count * page_size
                    stats["database_size_mb"] = round(
                        (page_count * page_size) / (1024 * 1024), 2
                    )

                    # Cache statistics
                    result = connection.execute(text("PRAGMA cache_size"))
                    stats["cache_size"] = result.scalar()

                    # Journal mode
                    result = connection.execute(text("PRAGMA journal_mode"))
                    stats["journal_mode"] = result.scalar()
                else:
                    stats["database_size_bytes"] = None
                    stats["database_size_mb"] = None
                    stats["cache_size"] = None
                    stats["journal_mode"] = None

                # Number of tables
                inspector = inspect(self.engine)
                stats["table_count"] = len(inspector.get_table_names())

                # Index count
                if self.is_duckdb:
                    stats["index_count"] = None
                else:
                    index_count = 0
                    for table in inspector.get_table_names():
                        index_count += len(inspector.get_indexes(table))
                    stats["index_count"] = index_count

                logger.debug(f"Database stats: {stats}")

        except exc.SQLAlchemyError as e:
            logger.warning(f"Failed to get some database statistics: {e}")

        return stats

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
            error_msg = str(e)
            # Check for lock error
            if (
                "Could not set lock on file" in error_msg
                and "Conflicting lock is held" in error_msg
            ):
                import re

                app_match = re.search(r"in ([^\(]+) \(PID", error_msg)
                app_name = (
                    app_match.group(1).strip() if app_match else "another application"
                )

                raise DatabaseLockError(
                    message=(
                        "💾 Database is locked by {app}. Try read-only mode or close the other application."
                    ).format(app=app_name),
                    query=query,
                )

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
