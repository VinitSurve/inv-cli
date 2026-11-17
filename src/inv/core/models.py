"""Core domain models for the Inventory CLI."""

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inv.constants import (
    DependencyStatus,
    EnvironmentType,
    InstallScope,
    ScannerStatus,
)


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


def make_deterministic_id(*parts: str) -> str:
    """Create a deterministic SHA-256 short hash ID from string components."""
    content = ":".join(parts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


@dataclass
class SoftwareIdentity:
    """Represents the canonical identity of a software package or tool."""

    id: str
    name: str
    canonical_name: str
    ecosystem: str
    description: str | None = None
    homepage: str | None = None
    license: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        ecosystem: str,
        description: str | None = None,
        homepage: str | None = None,
        license: str | None = None,
    ) -> "SoftwareIdentity":
        canonical = name.strip().lower()
        ident_id = make_deterministic_id(ecosystem, canonical)
        return cls(
            id=ident_id,
            name=name,
            canonical_name=canonical,
            ecosystem=ecosystem,
            description=description,
            homepage=homepage,
            license=license,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InstallationInstance:
    """Represents a specific physical installation of a software package."""

    id: str
    software_id: str
    name: str
    version: str
    install_path: Path | None
    manager: str
    scope: InstallScope = InstallScope.GLOBAL
    installed_at: str | None = None
    size_bytes: int | None = None
    provenance: str = "scanner"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        software_id: str,
        name: str,
        version: str,
        manager: str,
        install_path: Path | None = None,
        scope: InstallScope = InstallScope.GLOBAL,
        installed_at: str | None = None,
        size_bytes: int | None = None,
        provenance: str = "scanner",
        metadata: dict[str, Any] | None = None,
    ) -> "InstallationInstance":
        path_str = str(install_path) if install_path else ""
        inst_id = make_deterministic_id(software_id, version, manager, path_str)
        return cls(
            id=inst_id,
            software_id=software_id,
            name=name,
            version=version,
            install_path=install_path,
            manager=manager,
            scope=scope,
            installed_at=installed_at,
            size_bytes=size_bytes,
            provenance=provenance,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["install_path"] = str(self.install_path) if self.install_path else None
        d["scope"] = self.scope.value if isinstance(self.scope, InstallScope) else self.scope
        return d


@dataclass
class ExecutableInstance:
    """Represents an executable binary discovered in PATH or well-known location."""

    id: str
    name: str
    path: Path
    canonical_path: Path
    is_symlink: bool
    version: str | None = None
    source_manager: str | None = None
    is_accessible: bool = True
    is_duplicate: bool = False
    sha256: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        path: Path,
        canonical_path: Path,
        is_symlink: bool,
        version: str | None = None,
        source_manager: str | None = None,
        is_accessible: bool = True,
        is_duplicate: bool = False,
        sha256: str | None = None,
    ) -> "ExecutableInstance":
        exec_id = make_deterministic_id(name, str(path))
        return cls(
            id=exec_id,
            name=name,
            path=path,
            canonical_path=canonical_path,
            is_symlink=is_symlink,
            version=version,
            source_manager=source_manager,
            is_accessible=is_accessible,
            is_duplicate=is_duplicate,
            sha256=sha256,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path"] = str(self.path)
        d["canonical_path"] = str(self.canonical_path)
        return d


@dataclass
class Project:
    """Represents a discovered software project repository / directory."""

    id: str
    name: str
    path: Path
    project_types: list[str] = field(default_factory=list)
    root_manifest: Path | None = None
    has_lockfile: bool = False
    manifest_paths: list[Path] = field(default_factory=list)
    dependencies_count: int = 0

    @classmethod
    def create(
        cls,
        name: str,
        path: Path,
        project_types: list[str],
        root_manifest: Path | None = None,
        has_lockfile: bool = False,
        manifest_paths: list[Path] | None = None,
        dependencies_count: int = 0,
    ) -> "Project":
        proj_id = make_deterministic_id(name, str(path.resolve()))
        return cls(
            id=proj_id,
            name=name,
            path=path,
            project_types=sorted(set(project_types)),
            root_manifest=root_manifest,
            has_lockfile=has_lockfile,
            manifest_paths=manifest_paths or [],
            dependencies_count=dependencies_count,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path"] = str(self.path)
        d["root_manifest"] = str(self.root_manifest) if self.root_manifest else None
        d["manifest_paths"] = [str(p) for p in self.manifest_paths]
        return d


@dataclass
class ProjectDependency:
    """Represents a declared or installed dependency within a project."""

    id: str
    project_id: str
    name: str
    declared_spec: str | None = None
    resolved_version: str | None = None
    status: DependencyStatus = DependencyStatus.UNVERIFIED
    is_dev: bool = False
    ecosystem: str = "generic"
    manifest_source: Path | None = None

    @classmethod
    def create(
        cls,
        project_id: str,
        name: str,
        declared_spec: str | None = None,
        resolved_version: str | None = None,
        status: DependencyStatus = DependencyStatus.UNVERIFIED,
        is_dev: bool = False,
        ecosystem: str = "generic",
        manifest_source: Path | None = None,
    ) -> "ProjectDependency":
        dep_id = make_deterministic_id(project_id, ecosystem, name.lower())
        return cls(
            id=dep_id,
            project_id=project_id,
            name=name,
            declared_spec=declared_spec,
            resolved_version=resolved_version,
            status=status,
            is_dev=is_dev,
            ecosystem=ecosystem,
            manifest_source=manifest_source,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = (
            self.status.value if isinstance(self.status, DependencyStatus) else self.status
        )
        d["manifest_source"] = str(self.manifest_source) if self.manifest_source else None
        return d


@dataclass
class Environment:
    """Represents a development runtime or virtual environment."""

    id: str
    name: str
    env_type: EnvironmentType
    path: Path
    runtime_version: str | None = None
    is_active: bool = False
    packages_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        env_type: EnvironmentType,
        path: Path,
        runtime_version: str | None = None,
        is_active: bool = False,
        packages_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> "Environment":
        env_id = make_deterministic_id(env_type.value, str(path))
        return cls(
            id=env_id,
            name=name,
            env_type=env_type,
            path=path,
            runtime_version=runtime_version,
            is_active=is_active,
            packages_count=packages_count,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path"] = str(self.path)
        d["env_type"] = (
            self.env_type.value if isinstance(self.env_type, EnvironmentType) else self.env_type
        )
        return d


@dataclass
class Application:
    """Represents an installed macOS .app bundle."""

    id: str
    name: str
    bundle_id: str | None
    path: Path
    version: str | None = None
    build_number: str | None = None
    min_os_version: str | None = None
    architectures: list[str] = field(default_factory=list)
    category: str | None = None
    is_system: bool = False

    @classmethod
    def create(
        cls,
        name: str,
        path: Path,
        bundle_id: str | None = None,
        version: str | None = None,
        build_number: str | None = None,
        min_os_version: str | None = None,
        architectures: list[str] | None = None,
        category: str | None = None,
        is_system: bool = False,
    ) -> "Application":
        app_id = make_deterministic_id(bundle_id or name, str(path))
        return cls(
            id=app_id,
            name=name,
            bundle_id=bundle_id,
            path=path,
            version=version,
            build_number=build_number,
            min_os_version=min_os_version,
            architectures=architectures or [],
            category=category,
            is_system=is_system,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path"] = str(self.path)
        return d


@dataclass
class Runtime:
    """Represents a language runtime or SDK installation."""

    id: str
    name: str
    version: str
    path: Path
    manager: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        version: str,
        path: Path,
        manager: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Runtime":
        rt_id = make_deterministic_id(name.lower(), version, str(path))
        return cls(
            id=rt_id,
            name=name,
            version=version,
            path=path,
            manager=manager,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path"] = str(self.path)
        return d


@dataclass
class Container:
    """Represents a container runtime instance."""

    id: str
    container_id: str
    name: str
    image: str
    status: str
    created_at: str | None = None
    ports: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        container_id: str,
        name: str,
        image: str,
        status: str,
        created_at: str | None = None,
        ports: list[str] | None = None,
    ) -> "Container":
        c_id = make_deterministic_id(container_id)
        return cls(
            id=c_id,
            container_id=container_id,
            name=name,
            image=image,
            status=status,
            created_at=created_at,
            ports=ports or [],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContainerImage:
    """Represents a local container image."""

    id: str
    image_id: str
    repository: str
    tag: str
    size_bytes: int | None = None
    created_at: str | None = None

    @classmethod
    def create(
        cls,
        image_id: str,
        repository: str,
        tag: str,
        size_bytes: int | None = None,
        created_at: str | None = None,
    ) -> "ContainerImage":
        ci_id = make_deterministic_id(image_id, repository, tag)
        return cls(
            id=ci_id,
            image_id=image_id,
            repository=repository,
            tag=tag,
            size_bytes=size_bytes,
            created_at=created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Extension:
    """Represents an editor / IDE extension."""

    id: str
    name: str
    ide: str
    publisher: str | None = None
    version: str | None = None
    path: Path | None = None

    @classmethod
    def create(
        cls,
        name: str,
        ide: str,
        publisher: str | None = None,
        version: str | None = None,
        path: Path | None = None,
    ) -> "Extension":
        ext_id = make_deterministic_id(ide, publisher or "", name)
        return cls(
            id=ext_id,
            name=name,
            ide=ide,
            publisher=publisher,
            version=version,
            path=path,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["path"] = str(self.path) if self.path else None
        return d


@dataclass
class ScannerObservation:
    """Records the execution outcome of an individual scanner during a session."""

    id: str
    scanner_id: str
    session_id: str
    domain: str
    status: ScannerStatus
    duration_seconds: float
    items_count: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    scanned_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def create(
        cls,
        scanner_id: str,
        session_id: str,
        domain: str,
        status: ScannerStatus,
        duration_seconds: float,
        items_count: int,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> "ScannerObservation":
        obs_id = make_deterministic_id(session_id, scanner_id)
        return cls(
            id=obs_id,
            scanner_id=scanner_id,
            session_id=session_id,
            domain=domain,
            status=status,
            duration_seconds=duration_seconds,
            items_count=items_count,
            warnings=warnings or [],
            errors=errors or [],
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, ScannerStatus) else self.status
        return d


@dataclass
class ScanSession:
    """Represents a complete or partial scan session."""

    id: str
    started_at: str
    completed_at: str | None = None
    scan_type: str = "full"
    duration_seconds: float = 0.0
    status: str = "completed"
    total_items: int = 0
    summary: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        scan_type: str = "full",
        session_id: str | None = None,
    ) -> "ScanSession":
        s_id = session_id or uuid.uuid4().hex[:12]
        return cls(
            id=s_id,
            started_at=utc_now_iso(),
            scan_type=scan_type,
            status="running",
        )

    def complete(self, total_items: int, duration_seconds: float, summary: dict[str, Any]) -> None:
        self.completed_at = utc_now_iso()
        self.duration_seconds = duration_seconds
        self.status = "completed"
        self.total_items = total_items
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
