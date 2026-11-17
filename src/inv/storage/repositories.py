"""Repository implementations for database entity persistence and querying."""

import contextlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from inv.constants import (
    DependencyStatus,
    EnvironmentType,
    InstallScope,
    OperationState,
    OperationType,
    RiskLevel,
    ScannerStatus,
    UpdateStrategy,
    VulnerabilitySeverity,
)
from inv.core.models import (
    Application,
    Container,
    ContainerImage,
    Environment,
    ExecutableInstance,
    Extension,
    InstallationInstance,
    Project,
    ProjectDependency,
    Runtime,
    ScannerObservation,
    ScanSession,
    SoftwareIdentity,
)
from inv.lifecycle.models import (
    LifecycleOperation,
    OperationEvent,
    OutdatedPackage,
)
from inv.security.models import (
    VulnerabilityRecord,
)


class InventoryRepository:
    """Provides structured storage and retrieval for all inventory entities."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def close(self) -> None:
        """Close the underlying SQLite database connection."""
        if self.conn:
            with contextlib.suppress(sqlite3.Error):
                self.conn.close()

    def __enter__(self) -> "InventoryRepository":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # ---------------------------------------------------------
    # Sessions
    # ---------------------------------------------------------
    def save_session(self, session: ScanSession) -> None:
        """Insert or replace a scan session."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO scan_sessions (
                id, started_at, completed_at, scan_type, duration_seconds, status, total_items, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                session.id,
                session.started_at,
                session.completed_at,
                session.scan_type,
                session.duration_seconds,
                session.status,
                session.total_items,
                json.dumps(session.summary),
            ),
        )

    def get_latest_session(self) -> ScanSession | None:
        """Retrieve the most recent completed scan session."""
        cursor = self.conn.execute(
            "SELECT * FROM scan_sessions WHERE status = 'completed' ORDER BY started_at DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            # Fall back to any session
            cursor = self.conn.execute(
                "SELECT * FROM scan_sessions ORDER BY started_at DESC LIMIT 1;"
            )
            row = cursor.fetchone()
            if not row:
                return None
        return self._row_to_session(row)

    def list_sessions(self, limit: int = 20) -> list[ScanSession]:
        """List scan sessions ordered by timestamp."""
        cursor = self.conn.execute(
            "SELECT * FROM scan_sessions ORDER BY started_at DESC LIMIT ?;",
            (limit,),
        )
        return [self._row_to_session(r) for r in cursor.fetchall()]

    def _row_to_session(self, row: sqlite3.Row) -> ScanSession:
        return ScanSession(
            id=row["id"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            scan_type=row["scan_type"],
            duration_seconds=row["duration_seconds"] or 0.0,
            status=row["status"],
            total_items=row["total_items"] or 0,
            summary=json.loads(row["summary_json"] or "{}"),
        )

    # ---------------------------------------------------------
    # Observations
    # ---------------------------------------------------------
    def save_observation(self, obs: ScannerObservation) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO scanner_observations (
                id, session_id, scanner_id, domain, status, duration_seconds, items_count, warnings_json, errors_json, scanned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                obs.id,
                obs.session_id,
                obs.scanner_id,
                obs.domain,
                obs.status.value if isinstance(obs.status, ScannerStatus) else str(obs.status),
                obs.duration_seconds,
                obs.items_count,
                json.dumps(obs.warnings),
                json.dumps(obs.errors),
                obs.scanned_at,
            ),
        )

    def get_observations(self, session_id: str) -> list[ScannerObservation]:
        cursor = self.conn.execute(
            "SELECT * FROM scanner_observations WHERE session_id = ? ORDER BY domain, scanner_id;",
            (session_id,),
        )
        results: list[ScannerObservation] = []
        for r in cursor.fetchall():
            results.append(
                ScannerObservation(
                    id=r["id"],
                    scanner_id=r["scanner_id"],
                    session_id=r["session_id"],
                    domain=r["domain"],
                    status=ScannerStatus(r["status"]),
                    duration_seconds=r["duration_seconds"],
                    items_count=r["items_count"],
                    warnings=json.loads(r["warnings_json"] or "[]"),
                    errors=json.loads(r["errors_json"] or "[]"),
                    scanned_at=r["scanned_at"],
                )
            )
        return results

    # ---------------------------------------------------------
    # Software Identities & Installations
    # ---------------------------------------------------------
    def save_software_identity(self, ident: SoftwareIdentity) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO software_identities (
                id, name, canonical_name, ecosystem, description, homepage, license
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ident.id,
                ident.name,
                ident.canonical_name,
                ident.ecosystem,
                ident.description,
                ident.homepage,
                ident.license,
            ),
        )

    def save_installation(self, inst: InstallationInstance, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO installation_instances (
                id, software_id, name, version, install_path, manager, scope, installed_at, size_bytes, provenance, metadata_json, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                inst.id,
                inst.software_id,
                inst.name,
                inst.version,
                str(inst.install_path) if inst.install_path else None,
                inst.manager,
                inst.scope.value if isinstance(inst.scope, InstallScope) else str(inst.scope),
                inst.installed_at,
                inst.size_bytes,
                inst.provenance,
                json.dumps(inst.metadata),
                session_id,
            ),
        )

    def list_installations(
        self,
        session_id: str | None = None,
        manager: str | None = None,
        scope: InstallScope | None = None,
    ) -> list[InstallationInstance]:
        query = "SELECT * FROM installation_instances WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if manager:
            query += " AND manager = ?"
            params.append(manager)
        if scope:
            query += " AND scope = ?"
            params.append(scope.value)
        query += " ORDER BY name ASC, version ASC;"

        cursor = self.conn.execute(query, params)
        results: list[InstallationInstance] = []
        for r in cursor.fetchall():
            results.append(
                InstallationInstance(
                    id=r["id"],
                    software_id=r["software_id"],
                    name=r["name"],
                    version=r["version"],
                    install_path=Path(r["install_path"]) if r["install_path"] else None,
                    manager=r["manager"],
                    scope=InstallScope(r["scope"]),
                    installed_at=r["installed_at"],
                    size_bytes=r["size_bytes"],
                    provenance=r["provenance"] or "scanner",
                    metadata=json.loads(r["metadata_json"] or "{}"),
                )
            )
        return results

    # ---------------------------------------------------------
    # Executables
    # ---------------------------------------------------------
    def save_executable(self, exe: ExecutableInstance, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO executable_instances (
                id, name, path, canonical_path, is_symlink, version, source_manager, is_accessible, is_duplicate, sha256, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                exe.id,
                exe.name,
                str(exe.path),
                str(exe.canonical_path),
                1 if exe.is_symlink else 0,
                exe.version,
                exe.source_manager,
                1 if exe.is_accessible else 0,
                1 if exe.is_duplicate else 0,
                exe.sha256,
                session_id,
            ),
        )

    def list_executables(
        self, session_id: str | None = None, name: str | None = None, duplicates_only: bool = False
    ) -> list[ExecutableInstance]:
        query = "SELECT * FROM executable_instances WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if name:
            query += " AND name = ?"
            params.append(name)
        if duplicates_only:
            query += " AND is_duplicate = 1"
        query += " ORDER BY name ASC, path ASC;"

        cursor = self.conn.execute(query, params)
        return [
            ExecutableInstance(
                id=r["id"],
                name=r["name"],
                path=Path(r["path"]),
                canonical_path=Path(r["canonical_path"]),
                is_symlink=bool(r["is_symlink"]),
                version=r["version"],
                source_manager=r["source_manager"],
                is_accessible=bool(r["is_accessible"]),
                is_duplicate=bool(r["is_duplicate"]),
                sha256=r["sha256"],
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Applications
    # ---------------------------------------------------------
    def save_application(self, app: Application, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO applications (
                id, name, bundle_id, path, version, build_number, min_os_version, architectures_json, category, is_system, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                app.id,
                app.name,
                app.bundle_id,
                str(app.path),
                app.version,
                app.build_number,
                app.min_os_version,
                json.dumps(app.architectures),
                app.category,
                1 if app.is_system else 0,
                session_id,
            ),
        )

    def list_applications(self, session_id: str | None = None) -> list[Application]:
        query = "SELECT * FROM applications WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC;"

        cursor = self.conn.execute(query, params)
        return [
            Application(
                id=r["id"],
                name=r["name"],
                bundle_id=r["bundle_id"],
                path=Path(r["path"]),
                version=r["version"],
                build_number=r["build_number"],
                min_os_version=r["min_os_version"],
                architectures=json.loads(r["architectures_json"] or "[]"),
                category=r["category"],
                is_system=bool(r["is_system"]),
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Projects & Dependencies
    # ---------------------------------------------------------
    def save_project(self, project: Project, session_id: str, manifest_mtime: float = 0.0) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO projects (
                id, name, path, project_types_json, root_manifest, has_lockfile, manifest_paths_json, dependencies_count, manifest_mtime, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                project.id,
                project.name,
                str(project.path),
                json.dumps(project.project_types),
                str(project.root_manifest) if project.root_manifest else None,
                1 if project.has_lockfile else 0,
                json.dumps([str(p) for p in project.manifest_paths]),
                project.dependencies_count,
                manifest_mtime,
                session_id,
            ),
        )

    def save_project_dependency(self, dep: ProjectDependency, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO project_dependencies (
                id, project_id, name, declared_spec, resolved_version, status, is_dev, ecosystem, manifest_source, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                dep.id,
                dep.project_id,
                dep.name,
                dep.declared_spec,
                dep.resolved_version,
                dep.status.value if isinstance(dep.status, DependencyStatus) else str(dep.status),
                1 if dep.is_dev else 0,
                dep.ecosystem,
                str(dep.manifest_source) if dep.manifest_source else None,
                session_id,
            ),
        )

    def list_projects(self, session_id: str | None = None) -> list[Project]:
        query = "SELECT * FROM projects WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC;"

        cursor = self.conn.execute(query, params)
        return [
            Project(
                id=r["id"],
                name=r["name"],
                path=Path(r["path"]),
                project_types=json.loads(r["project_types_json"] or "[]"),
                root_manifest=Path(r["root_manifest"]) if r["root_manifest"] else None,
                has_lockfile=bool(r["has_lockfile"]),
                manifest_paths=[Path(p) for p in json.loads(r["manifest_paths_json"] or "[]")],
                dependencies_count=r["dependencies_count"],
            )
            for r in cursor.fetchall()
        ]

    def list_project_dependencies(
        self, project_id: str | None = None, session_id: str | None = None
    ) -> list[ProjectDependency]:
        query = "SELECT * FROM project_dependencies WHERE 1=1"
        params: list[Any] = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC;"

        cursor = self.conn.execute(query, params)
        return [
            ProjectDependency(
                id=r["id"],
                project_id=r["project_id"],
                name=r["name"],
                declared_spec=r["declared_spec"],
                resolved_version=r["resolved_version"],
                status=DependencyStatus(r["status"]),
                is_dev=bool(r["is_dev"]),
                ecosystem=r["ecosystem"],
                manifest_source=Path(r["manifest_source"]) if r["manifest_source"] else None,
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Environments
    # ---------------------------------------------------------
    def save_environment(self, env: Environment, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO environments (
                id, name, env_type, path, runtime_version, is_active, packages_count, metadata_json, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                env.id,
                env.name,
                env.env_type.value
                if isinstance(env.env_type, EnvironmentType)
                else str(env.env_type),
                str(env.path),
                env.runtime_version,
                1 if env.is_active else 0,
                env.packages_count,
                json.dumps(env.metadata),
                session_id,
            ),
        )

    def list_environments(self, session_id: str | None = None) -> list[Environment]:
        query = "SELECT * FROM environments WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC;"

        cursor = self.conn.execute(query, params)
        return [
            Environment(
                id=r["id"],
                name=r["name"],
                env_type=EnvironmentType(r["env_type"]),
                path=Path(r["path"]),
                runtime_version=r["runtime_version"],
                is_active=bool(r["is_active"]),
                packages_count=r["packages_count"],
                metadata=json.loads(r["metadata_json"] or "{}"),
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Runtimes
    # ---------------------------------------------------------
    def save_runtime(self, rt: Runtime, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO runtimes (
                id, name, version, path, manager, metadata_json, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                rt.id,
                rt.name,
                rt.version,
                str(rt.path),
                rt.manager,
                json.dumps(rt.metadata),
                session_id,
            ),
        )

    def list_runtimes(self, session_id: str | None = None) -> list[Runtime]:
        query = "SELECT * FROM runtimes WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC, version ASC;"

        cursor = self.conn.execute(query, params)
        return [
            Runtime(
                id=r["id"],
                name=r["name"],
                version=r["version"],
                path=Path(r["path"]),
                manager=r["manager"],
                metadata=json.loads(r["metadata_json"] or "{}"),
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Containers
    # ---------------------------------------------------------
    def save_container(self, c: Container, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO containers (
                id, container_id, name, image, status, created_at, ports_json, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                c.id,
                c.container_id,
                c.name,
                c.image,
                c.status,
                c.created_at,
                json.dumps(c.ports),
                session_id,
            ),
        )

    def list_containers(self, session_id: str | None = None) -> list[Container]:
        query = "SELECT * FROM containers WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC;"

        cursor = self.conn.execute(query, params)
        return [
            Container(
                id=r["id"],
                container_id=r["container_id"],
                name=r["name"],
                image=r["image"],
                status=r["status"],
                created_at=r["created_at"],
                ports=json.loads(r["ports_json"] or "[]"),
            )
            for r in cursor.fetchall()
        ]

    def save_container_image(self, ci: ContainerImage, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO container_images (
                id, image_id, repository, tag, size_bytes, created_at, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ci.id,
                ci.image_id,
                ci.repository,
                ci.tag,
                ci.size_bytes,
                ci.created_at,
                session_id,
            ),
        )

    def list_container_images(self, session_id: str | None = None) -> list[ContainerImage]:
        query = "SELECT * FROM container_images WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY repository ASC, tag ASC;"

        cursor = self.conn.execute(query, params)
        return [
            ContainerImage(
                id=r["id"],
                image_id=r["image_id"],
                repository=r["repository"],
                tag=r["tag"],
                size_bytes=r["size_bytes"],
                created_at=r["created_at"],
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Extensions
    # ---------------------------------------------------------
    def save_extension(self, ext: Extension, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO extensions (
                id, name, ide, publisher, version, path, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ext.id,
                ext.name,
                ext.ide,
                ext.publisher,
                ext.version,
                str(ext.path) if ext.path else None,
                session_id,
            ),
        )

    def list_extensions(self, session_id: str | None = None) -> list[Extension]:
        query = "SELECT * FROM extensions WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY ide ASC, name ASC;"

        cursor = self.conn.execute(query, params)
        return [
            Extension(
                id=r["id"],
                name=r["name"],
                ide=r["ide"],
                publisher=r["publisher"],
                version=r["version"],
                path=Path(r["path"]) if r["path"] else None,
            )
            for r in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # Universal Search
    # ---------------------------------------------------------
    def search(
        self, query_str: str, session_id: str | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Search across packages, executables, applications, and projects."""
        term = f"%{query_str.strip()}%"
        results: dict[str, list[dict[str, Any]]] = {
            "packages": [],
            "executables": [],
            "applications": [],
            "projects": [],
        }

        # Packages
        q_pkg = "SELECT * FROM installation_instances WHERE (name LIKE ? OR manager LIKE ?)"
        p_pkg: list[Any] = [term, term]
        if session_id:
            q_pkg += " AND session_id = ?"
            p_pkg.append(session_id)
        for r in self.conn.execute(q_pkg, p_pkg).fetchall():
            results["packages"].append(
                {
                    "name": r["name"],
                    "version": r["version"],
                    "manager": r["manager"],
                    "scope": r["scope"],
                    "path": r["install_path"],
                }
            )

        # Executables
        q_exe = "SELECT * FROM executable_instances WHERE name LIKE ?"
        p_exe: list[Any] = [term]
        if session_id:
            q_exe += " AND session_id = ?"
            p_exe.append(session_id)
        for r in self.conn.execute(q_exe, p_exe).fetchall():
            results["executables"].append(
                {
                    "name": r["name"],
                    "path": r["path"],
                    "canonical_path": r["canonical_path"],
                    "version": r["version"],
                    "source_manager": r["source_manager"],
                }
            )

        # Applications
        q_app = "SELECT * FROM applications WHERE (name LIKE ? OR bundle_id LIKE ?)"
        p_app: list[Any] = [term, term]
        if session_id:
            q_app += " AND session_id = ?"
            p_app.append(session_id)
        for r in self.conn.execute(q_app, p_app).fetchall():
            results["applications"].append(
                {
                    "name": r["name"],
                    "bundle_id": r["bundle_id"],
                    "version": r["version"],
                    "path": r["path"],
                }
            )

        # Projects
        q_proj = "SELECT * FROM projects WHERE (name LIKE ? OR path LIKE ?)"
        p_proj: list[Any] = [term, term]
        if session_id:
            q_proj += " AND session_id = ?"
            p_proj.append(session_id)
        for r in self.conn.execute(q_proj, p_proj).fetchall():
            results["projects"].append(
                {
                    "name": r["name"],
                    "path": r["path"],
                    "types": json.loads(r["project_types_json"] or "[]"),
                    "dependencies": r["dependencies_count"],
                }
            )

        return results

    # ---------------------------------------------------------
    # Vulnerabilities
    # ---------------------------------------------------------
    def save_vulnerability(self, vuln: VulnerabilityRecord) -> None:
        """Insert or replace a discovered vulnerability record."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO vulnerabilities (
                id, advisory_id, package_name, ecosystem, installed_version,
                severity, title, affected_range, fixed_version, cve_id,
                ghsa_id, osv_id, cvss_score, advisory_url, details,
                dependency_type, introduced_by, data_source, fix_available,
                remediation_status, published_at, scanned_at, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                vuln.id,
                vuln.advisory_id,
                vuln.package_name,
                vuln.ecosystem,
                vuln.installed_version,
                vuln.severity.value,
                vuln.title,
                vuln.affected_range,
                vuln.fixed_version,
                vuln.cve_id,
                vuln.ghsa_id,
                vuln.osv_id,
                vuln.cvss_score,
                vuln.advisory_url,
                vuln.details,
                vuln.dependency_type,
                vuln.introduced_by,
                vuln.data_source,
                1 if vuln.fix_available else 0,
                vuln.remediation_status,
                vuln.published_at,
                vuln.scanned_at,
                vuln.session_id,
            ),
        )

    def list_vulnerabilities(
        self,
        session_id: str | None = None,
        severity: str | None = None,
        ecosystem: str | None = None,
    ) -> list[VulnerabilityRecord]:
        """Query stored vulnerabilities with optional filters."""
        query = "SELECT * FROM vulnerabilities WHERE 1=1"
        params: list[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if severity:
            query += " AND severity = ?"
            params.append(severity.lower())
        if ecosystem:
            query += " AND ecosystem = ?"
            params.append(ecosystem.lower())

        query += " ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END;"
        rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            result.append(
                VulnerabilityRecord(
                    id=r["id"],
                    advisory_id=r["advisory_id"],
                    package_name=r["package_name"],
                    ecosystem=r["ecosystem"],
                    installed_version=r["installed_version"],
                    severity=VulnerabilitySeverity(r["severity"]),
                    title=r["title"],
                    affected_range=r["affected_range"],
                    fixed_version=r["fixed_version"],
                    cve_id=r["cve_id"],
                    ghsa_id=r["ghsa_id"],
                    osv_id=r["osv_id"],
                    cvss_score=r["cvss_score"],
                    advisory_url=r["advisory_url"],
                    details=r["details"],
                    dependency_type=r["dependency_type"] or "direct",
                    introduced_by=r["introduced_by"],
                    data_source=r["data_source"] or "osv",
                    fix_available=bool(r["fix_available"]),
                    remediation_status=r["remediation_status"] or "open",
                    published_at=r["published_at"],
                    scanned_at=r["scanned_at"],
                    session_id=r["session_id"],
                )
            )
        return result

    def get_vulnerability(self, vuln_id: str) -> VulnerabilityRecord | None:
        """Fetch a single vulnerability by ID or advisory ID."""
        row = self.conn.execute(
            "SELECT * FROM vulnerabilities WHERE id = ? OR advisory_id = ? LIMIT 1;",
            (vuln_id, vuln_id),
        ).fetchone()
        if not row:
            return None
        return VulnerabilityRecord(
            id=row["id"],
            advisory_id=row["advisory_id"],
            package_name=row["package_name"],
            ecosystem=row["ecosystem"],
            installed_version=row["installed_version"],
            severity=VulnerabilitySeverity(row["severity"]),
            title=row["title"],
            affected_range=row["affected_range"],
            fixed_version=row["fixed_version"],
            cve_id=row["cve_id"],
            ghsa_id=row["ghsa_id"],
            osv_id=row["osv_id"],
            cvss_score=row["cvss_score"],
            advisory_url=row["advisory_url"],
            details=row["details"],
            dependency_type=row["dependency_type"] or "direct",
            introduced_by=row["introduced_by"],
            data_source=row["data_source"] or "osv",
            fix_available=bool(row["fix_available"]),
            remediation_status=row["remediation_status"] or "open",
            published_at=row["published_at"],
            scanned_at=row["scanned_at"],
            session_id=row["session_id"],
        )

    def update_vulnerability_remediation(self, vuln_id: str, status: str) -> None:
        """Update remediation status of a vulnerability record."""
        self.conn.execute(
            "UPDATE vulnerabilities SET remediation_status = ? WHERE id = ? OR advisory_id = ?;",
            (status, vuln_id, vuln_id),
        )

    # ---------------------------------------------------------
    # Lifecycle Operations & Events
    # ---------------------------------------------------------
    def save_lifecycle_operation(self, op: LifecycleOperation) -> None:
        """Insert or replace a lifecycle operation record."""
        self.conn.execute(
            """
            INSERT OR REPLACE INTO lifecycle_operations (
                id, operation_type, target_package, manager, scope,
                target_version, previous_version, proposed_version,
                status, risk_level, risk_reasons_json, actions_json,
                dependency_changes_json, reverse_dependencies_json,
                rollback_available, rollback_instructions, created_at,
                approved_at, executed_at, verified_at, logs_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                op.id,
                op.operation_type.value,
                op.target_package,
                op.manager,
                op.scope.value,
                op.target_version,
                op.previous_version,
                op.proposed_version,
                op.status.value,
                op.risk_level.value,
                json.dumps(op.risk_reasons),
                json.dumps(op.actions),
                json.dumps(op.dependency_changes),
                json.dumps(op.reverse_dependencies),
                1 if op.rollback_available else 0,
                op.rollback_instructions,
                op.created_at,
                op.approved_at,
                op.executed_at,
                op.verified_at,
                json.dumps(op.logs),
                json.dumps(op.metadata),
            ),
        )

    def get_lifecycle_operation(self, op_id: str) -> LifecycleOperation | None:
        """Retrieve a lifecycle operation by ID."""
        row = self.conn.execute(
            "SELECT * FROM lifecycle_operations WHERE id = ?;", (op_id,)
        ).fetchone()
        if not row:
            return None
        return LifecycleOperation(
            id=row["id"],
            operation_type=OperationType(row["operation_type"]),
            target_package=row["target_package"],
            manager=row["manager"],
            scope=InstallScope(row["scope"]),
            target_version=row["target_version"],
            previous_version=row["previous_version"],
            proposed_version=row["proposed_version"],
            status=OperationState(row["status"]),
            risk_level=RiskLevel(row["risk_level"]),
            risk_reasons=json.loads(row["risk_reasons_json"] or "[]"),
            actions=json.loads(row["actions_json"] or "[]"),
            dependency_changes=json.loads(row["dependency_changes_json"] or "[]"),
            reverse_dependencies=json.loads(row["reverse_dependencies_json"] or "[]"),
            rollback_available=bool(row["rollback_available"]),
            rollback_instructions=row["rollback_instructions"],
            created_at=row["created_at"],
            approved_at=row["approved_at"],
            executed_at=row["executed_at"],
            verified_at=row["verified_at"],
            logs=json.loads(row["logs_json"] or "[]"),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    def list_lifecycle_operations(
        self, status: str | None = None, limit: int = 50
    ) -> list[LifecycleOperation]:
        """List lifecycle operations sorted by creation timestamp descending."""
        query = "SELECT * FROM lifecycle_operations"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status.lower())
        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        result = []
        for row in rows:
            result.append(
                LifecycleOperation(
                    id=row["id"],
                    operation_type=OperationType(row["operation_type"]),
                    target_package=row["target_package"],
                    manager=row["manager"],
                    scope=InstallScope(row["scope"]),
                    target_version=row["target_version"],
                    previous_version=row["previous_version"],
                    proposed_version=row["proposed_version"],
                    status=OperationState(row["status"]),
                    risk_level=RiskLevel(row["risk_level"]),
                    risk_reasons=json.loads(row["risk_reasons_json"] or "[]"),
                    actions=json.loads(row["actions_json"] or "[]"),
                    dependency_changes=json.loads(row["dependency_changes_json"] or "[]"),
                    reverse_dependencies=json.loads(row["reverse_dependencies_json"] or "[]"),
                    rollback_available=bool(row["rollback_available"]),
                    rollback_instructions=row["rollback_instructions"],
                    created_at=row["created_at"],
                    approved_at=row["approved_at"],
                    executed_at=row["executed_at"],
                    verified_at=row["verified_at"],
                    logs=json.loads(row["logs_json"] or "[]"),
                    metadata=json.loads(row["metadata_json"] or "{}"),
                )
            )
        return result

    def update_lifecycle_operation_status(
        self,
        op_id: str,
        status: OperationState,
        logs: list[str] | None = None,
        verified_at: str | None = None,
    ) -> None:
        """Update operation status, optional logs, and verification timestamp."""
        if logs is not None and verified_at is not None:
            self.conn.execute(
                "UPDATE lifecycle_operations SET status = ?, logs_json = ?, verified_at = ? WHERE id = ?;",
                (status.value, json.dumps(logs), verified_at, op_id),
            )
        elif logs is not None:
            self.conn.execute(
                "UPDATE lifecycle_operations SET status = ?, logs_json = ? WHERE id = ?;",
                (status.value, json.dumps(logs), op_id),
            )
        else:
            self.conn.execute(
                "UPDATE lifecycle_operations SET status = ? WHERE id = ?;",
                (status.value, op_id),
            )

    def save_operation_event(self, event: OperationEvent) -> None:
        """Insert an operation audit trail event."""
        self.conn.execute(
            """
            INSERT INTO operation_events (id, operation_id, event_type, timestamp, message, data_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                event.id,
                event.operation_id,
                event.event_type,
                event.timestamp,
                event.message,
                json.dumps(event.data),
            ),
        )

    def list_operation_events(self, operation_id: str) -> list[OperationEvent]:
        """Fetch all events for a specific operation."""
        rows = self.conn.execute(
            "SELECT * FROM operation_events WHERE operation_id = ? ORDER BY timestamp ASC;",
            (operation_id,),
        ).fetchall()
        result = []
        for r in rows:
            result.append(
                OperationEvent(
                    id=r["id"],
                    operation_id=r["operation_id"],
                    event_type=r["event_type"],
                    timestamp=r["timestamp"],
                    message=r["message"],
                    data=json.loads(r["data_json"] or "{}"),
                )
            )
        return result

    # ---------------------------------------------------------
    # Outdated Packages
    # ---------------------------------------------------------
    def save_outdated_package(self, pkg: OutdatedPackage, session_id: str | None = None) -> None:
        """Insert or replace an outdated package observation."""
        outdated_id = f"out_{pkg.manager}_{pkg.name}"
        self.conn.execute(
            """
            INSERT OR REPLACE INTO outdated_packages (
                id, name, manager, installed_version, latest_version,
                latest_stable_version, latest_compatible_version,
                update_strategy, is_major_update, checked_at, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                outdated_id,
                pkg.name,
                pkg.manager,
                pkg.installed_version,
                pkg.latest_version,
                pkg.latest_stable_version,
                pkg.latest_compatible_version,
                pkg.update_strategy.value,
                1 if pkg.is_major_update else 0,
                pkg.checked_at,
                session_id,
            ),
        )

    def list_outdated_packages(
        self, manager: str | None = None, session_id: str | None = None
    ) -> list[OutdatedPackage]:
        """List tracked outdated packages."""
        query = "SELECT * FROM outdated_packages WHERE 1=1"
        params: list[Any] = []
        if manager:
            query += " AND manager = ?"
            params.append(manager.lower())
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY name ASC;"

        rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            result.append(
                OutdatedPackage(
                    name=r["name"],
                    manager=r["manager"],
                    installed_version=r["installed_version"],
                    latest_version=r["latest_version"],
                    latest_stable_version=r["latest_stable_version"],
                    latest_compatible_version=r["latest_compatible_version"],
                    update_strategy=UpdateStrategy(r["update_strategy"]),
                    is_major_update=bool(r["is_major_update"]),
                    checked_at=r["checked_at"],
                )
            )
        return result

    def clear_outdated_packages(self, session_id: str | None = None) -> None:
        """Clear outdated package records."""
        if session_id:
            self.conn.execute("DELETE FROM outdated_packages WHERE session_id = ?;", (session_id,))
        else:
            self.conn.execute("DELETE FROM outdated_packages;")
