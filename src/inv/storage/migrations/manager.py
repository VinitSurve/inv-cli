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


SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id TEXT PRIMARY KEY,
    advisory_id TEXT NOT NULL,
    package_name TEXT NOT NULL,
    ecosystem TEXT NOT NULL,
    installed_version TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    affected_range TEXT NOT NULL,
    fixed_version TEXT,
    cve_id TEXT,
    ghsa_id TEXT,
    osv_id TEXT,
    cvss_score REAL,
    advisory_url TEXT,
    details TEXT,
    dependency_type TEXT DEFAULT 'direct',
    introduced_by TEXT,
    data_source TEXT DEFAULT 'osv',
    fix_available INTEGER DEFAULT 0,
    remediation_status TEXT DEFAULT 'open',
    published_at TEXT,
    scanned_at TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lifecycle_operations (
    id TEXT PRIMARY KEY,
    operation_type TEXT NOT NULL,
    target_package TEXT NOT NULL,
    manager TEXT NOT NULL,
    scope TEXT NOT NULL,
    target_version TEXT,
    previous_version TEXT,
    proposed_version TEXT,
    status TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_reasons_json TEXT DEFAULT '[]',
    actions_json TEXT DEFAULT '[]',
    dependency_changes_json TEXT DEFAULT '[]',
    reverse_dependencies_json TEXT DEFAULT '[]',
    rollback_available INTEGER DEFAULT 0,
    rollback_instructions TEXT,
    created_at TEXT NOT NULL,
    approved_at TEXT,
    executed_at TEXT,
    verified_at TEXT,
    logs_json TEXT DEFAULT '[]',
    metadata_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS operation_events (
    id TEXT PRIMARY KEY,
    operation_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    message TEXT NOT NULL,
    data_json TEXT DEFAULT '{}',
    FOREIGN KEY(operation_id) REFERENCES lifecycle_operations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS outdated_packages (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    manager TEXT NOT NULL,
    installed_version TEXT NOT NULL,
    latest_version TEXT NOT NULL,
    latest_stable_version TEXT NOT NULL,
    latest_compatible_version TEXT NOT NULL,
    update_strategy TEXT NOT NULL,
    is_major_update INTEGER DEFAULT 0,
    checked_at TEXT NOT NULL,
    session_id TEXT,
    FOREIGN KEY(session_id) REFERENCES scan_sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_vuln_pkg ON vulnerabilities(package_name);
CREATE INDEX IF NOT EXISTS idx_vuln_severity ON vulnerabilities(severity);
CREATE INDEX IF NOT EXISTS idx_vuln_session ON vulnerabilities(session_id);
CREATE INDEX IF NOT EXISTS idx_op_status ON lifecycle_operations(status);
CREATE INDEX IF NOT EXISTS idx_op_target ON lifecycle_operations(target_package);
CREATE INDEX IF NOT EXISTS idx_op_events ON operation_events(operation_id);
CREATE INDEX IF NOT EXISTS idx_outdated_mgr ON outdated_packages(manager);
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

    if current_version < 2:
        cursor.executescript(SCHEMA_V2)
        cursor.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
            (2, utc_now_iso()),
        )
