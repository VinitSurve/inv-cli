"""Pytest fixtures and configuration."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from inv.core.models import (
    ScanSession,
)
from inv.storage.database import Database
from inv.storage.migrations.manager import apply_migrations
from inv.storage.repositories import InventoryRepository


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory that is automatically cleaned up."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def mock_db(temp_dir: Path) -> Generator[Database, None, None]:
    """Provide a fresh SQLite database initialized with migrations."""
    db_path = temp_dir / "test_inv.db"
    db = Database(db_path)
    with db.transaction() as conn:
        apply_migrations(conn)
    yield db


@pytest.fixture
def mock_repo(mock_db: Database) -> Generator[InventoryRepository, None, None]:
    """Provide an InventoryRepository connected to a test database."""
    conn = mock_db.get_connection()
    repo = InventoryRepository(conn)
    yield repo
    conn.close()


@pytest.fixture
def sample_session() -> ScanSession:
    """Provide a sample ScanSession."""
    session = ScanSession.create(scan_type="standard", session_id="test-session-01")
    session.complete(total_items=10, duration_seconds=1.23, summary={"installations": 5})
    return session
