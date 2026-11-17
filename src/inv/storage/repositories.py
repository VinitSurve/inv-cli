"""Repository implementations for database entity persistence and querying."""

import contextlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from inv.constants import DependencyStatus, EnvironmentType, InstallScope, ScannerStatus
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
