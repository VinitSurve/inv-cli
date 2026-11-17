"""SQLite persistence layer and connection management."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from inv.exceptions import StorageError


class Database:
    """Manages SQLite database connections, schema migrations, and transactions."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure parent directory for database exists."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(
                f"Failed to create database directory {self.db_path.parent}: {exc}"
            ) from exc

    def get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with WAL mode and foreign keys enabled."""
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            # Configure high-performance and safe PRAGMAs
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            return conn
        except sqlite3.Error as exc:
            raise StorageError(f"Cannot connect to database at {self.db_path}: {exc}") from exc

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Transactional context manager that commits on exit or rolls back on exception."""
        conn = self.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE;")
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise StorageError(f"Transaction failed, changes rolled back: {exc}") from exc
        finally:
            conn.close()
