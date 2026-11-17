"""Database schema migrations manager."""

import sqlite3

from inv.core.models import utc_now_iso

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    scan_type TEXT NOT NULL,
    duration_seconds REAL DEFAULT 0.0,
    status TEXT NOT NULL,
    total_items INTEGER DEFAULT 0,
    summary_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS scanner_observations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    scanner_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    items_count INTEGER NOT NULL,
    warnings_json TEXT DEFAULT '[]',
    errors_json TEXT DEFAULT '[]',
    scanned_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS software_identities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    ecosystem TEXT NOT NULL,
    description TEXT,
    homepage TEXT,
    license TEXT
);

CREATE TABLE IF NOT EXISTS installation_instances (
    id TEXT PRIMARY KEY,
    software_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    install_path TEXT,
    manager TEXT NOT NULL,
    scope TEXT NOT NULL,
    installed_at TEXT,
    size_bytes INTEGER,
    provenance TEXT DEFAULT 'scanner',
    metadata_json TEXT DEFAULT '{}',
    session_id TEXT NOT NULL,
    FOREIGN KEY(software_id) REFERENCES software_identities(id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS executable_instances (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    canonical_path TEXT NOT NULL,
    is_symlink INTEGER NOT NULL,
    version TEXT,
    source_manager TEXT,
    is_accessible INTEGER DEFAULT 1,
    is_duplicate INTEGER DEFAULT 0,
    sha256 TEXT,
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    project_types_json TEXT DEFAULT '[]',
    root_manifest TEXT,
    has_lockfile INTEGER DEFAULT 0,
    manifest_paths_json TEXT DEFAULT '[]',
    dependencies_count INTEGER DEFAULT 0,
    manifest_mtime REAL DEFAULT 0.0,
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_dependencies (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    declared_spec TEXT,
    resolved_version TEXT,
    status TEXT NOT NULL,
    is_dev INTEGER DEFAULT 0,
    ecosystem TEXT NOT NULL,
    manifest_source TEXT,
    session_id TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS environments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    env_type TEXT NOT NULL,
    path TEXT NOT NULL,
    runtime_version TEXT,
    is_active INTEGER DEFAULT 0,
    packages_count INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    bundle_id TEXT,
    path TEXT NOT NULL,
    version TEXT,
    build_number TEXT,
    min_os_version TEXT,
    architectures_json TEXT DEFAULT '[]',
    category TEXT,
    is_system INTEGER DEFAULT 0,
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS runtimes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    path TEXT NOT NULL,
    manager TEXT,
    metadata_json TEXT DEFAULT '{}',
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS containers (
    id TEXT PRIMARY KEY,
    container_id TEXT NOT NULL,
    name TEXT NOT NULL,
    image TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT,
    ports_json TEXT DEFAULT '[]',
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS container_images (
    id TEXT PRIMARY KEY,
    image_id TEXT NOT NULL,
    repository TEXT NOT NULL,
    tag TEXT NOT NULL,
    size_bytes INTEGER,
    created_at TEXT,
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS extensions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ide TEXT NOT NULL,
    publisher TEXT,
    version TEXT,
    path TEXT,
    session_id TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_inst_software ON installation_instances(software_id);
CREATE INDEX IF NOT EXISTS idx_inst_manager ON installation_instances(manager);
CREATE INDEX IF NOT EXISTS idx_inst_session ON installation_instances(session_id);
CREATE INDEX IF NOT EXISTS idx_exec_name ON executable_instances(name);
CREATE INDEX IF NOT EXISTS idx_exec_session ON executable_instances(session_id);
CREATE INDEX IF NOT EXISTS idx_proj_session ON projects(session_id);
CREATE INDEX IF NOT EXISTS idx_pdep_proj ON project_dependencies(project_id);
CREATE INDEX IF NOT EXISTS idx_apps_session ON applications(session_id);
CREATE INDEX IF NOT EXISTS idx_runtimes_session ON runtimes(session_id);
CREATE INDEX IF NOT EXISTS idx_envs_session ON environments(session_id);
"""


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply database migrations up to current version."""
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);"
    )
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;")
    row = cursor.fetchone()
    current_version = row[0] if row else 0

    if current_version < 1:
        cursor.executescript(SCHEMA_V1)
        cursor.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
            (1, utc_now_iso()),
        )

