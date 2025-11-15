"""Database utilities for API routes."""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Union

from niamoto.common.database import Database


@contextmanager
def open_database(
    path: Union[Path, str], *, read_only: bool = False
) -> Iterator[Database]:
    """Yield a Database instance and ensure connections are released.

    This context manager is essential for DuckDB which uses file locks.
    It ensures that connections are properly closed and engine is disposed
    after use, releasing file locks for other processes.

    Args:
        path: Path to the database file
        read_only: If True, open in read-only mode (allows concurrent reads)

    Yields:
        Database instance

    Example:
        with open_database(db_path, read_only=True) as db:
            result = db.execute_sql("SELECT * FROM table")
        # Connections automatically closed here
    """
    db = Database(str(path), read_only=read_only)
    try:
        yield db
    finally:
        try:
            db.close_db_session()
        except Exception:
            pass
        try:
            db.engine.dispose()
        except Exception:
            pass
