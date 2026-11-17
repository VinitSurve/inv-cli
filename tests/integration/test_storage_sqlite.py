"""Integration tests for SQLite storage layer and repository."""

from pathlib import Path

import pytest

from inv.constants import InstallScope
from inv.core.models import (
    ExecutableInstance,
    InstallationInstance,
    ScanSession,
    SoftwareIdentity,
)
from inv.exceptions import StorageError
from inv.storage.database import Database
from inv.storage.repositories import InventoryRepository


def test_sqlite_persistence_and_retrieval(
    mock_repo: InventoryRepository, sample_session: ScanSession
) -> None:
    # 1. Save session
    mock_repo.save_session(sample_session)
    latest = mock_repo.get_latest_session()
    assert latest is not None
    assert latest.id == sample_session.id
    assert latest.total_items == 10

    # 2. Software identity & Installation
    ident = SoftwareIdentity.create(name="ffmpeg", ecosystem="brew")
    mock_repo.save_software_identity(ident)

    inst = InstallationInstance.create(
        software_id=ident.id,
        name="ffmpeg",
        version="6.1.1",
        manager="brew_formula",
        scope=InstallScope.GLOBAL,
    )
    mock_repo.save_installation(inst, sample_session.id)

    insts = mock_repo.list_installations(sample_session.id)
    assert len(insts) == 1
    assert insts[0].name == "ffmpeg"
    assert insts[0].version == "6.1.1"

    # 3. Executable
    exe = ExecutableInstance.create(
        name="ffmpeg",
        path=Path("/opt/homebrew/bin/ffmpeg"),
        canonical_path=Path("/opt/homebrew/Cellar/ffmpeg/6.1.1/bin/ffmpeg"),
        is_symlink=True,
        version="6.1.1",
        source_manager="brew",
    )
    mock_repo.save_executable(exe, sample_session.id)
    execs = mock_repo.list_executables(sample_session.id)
    assert len(execs) == 1
    assert execs[0].name == "ffmpeg"

    # 4. Search
    results = mock_repo.search("ffmpeg", session_id=sample_session.id)
    assert len(results["packages"]) == 1
    assert len(results["executables"]) == 1


def test_sqlite_transaction_rollback_on_failure(mock_db: Database) -> None:
    # Verify transaction rolls back on exception
    with pytest.raises(StorageError), mock_db.transaction() as conn:
        conn.execute(
            "INSERT INTO scan_sessions (id, started_at, scan_type, status) VALUES ('s1', 'now', 'std', 'running');"
        )
        # Force an error
        raise ValueError("Deliberate failure inside transaction")

    # Verify s1 was NOT committed
    conn = mock_db.get_connection()
    cursor = conn.execute("SELECT * FROM scan_sessions WHERE id = 's1';")
    assert cursor.fetchone() is None
    conn.close()
