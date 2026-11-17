"""Base scanner interface and result data structures."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from inv.config import InvConfig
from inv.constants import ScannerStatus
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
    SoftwareIdentity,
)


@dataclass
class ScanContext:
    """Runtime context passed to scanners during execution."""

    session_id: str
    config: InvConfig
    deep: bool = False
    incremental: bool = False
    custom_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanResult:
    """Structured output returned by an executed scanner."""

    scanner_id: str
    domain: str
    status: ScannerStatus = ScannerStatus.SUCCESS
    duration_seconds: float = 0.0
    identities: list[SoftwareIdentity] = field(default_factory=list)
    installations: list[InstallationInstance] = field(default_factory=list)
    executables: list[ExecutableInstance] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    project_dependencies: list[ProjectDependency] = field(default_factory=list)
    environments: list[Environment] = field(default_factory=list)
    applications: list[Application] = field(default_factory=list)
    runtimes: list[Runtime] = field(default_factory=list)
    containers: list[Container] = field(default_factory=list)
    container_images: list[ContainerImage] = field(default_factory=list)
    extensions: list[Extension] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        """Count total items discovered across all entity collections."""
        return (
            len(self.identities)
            + len(self.installations)
            + len(self.executables)
            + len(self.projects)
            + len(self.project_dependencies)
            + len(self.environments)
            + len(self.applications)
            + len(self.runtimes)
            + len(self.containers)
            + len(self.container_images)
            + len(self.extensions)
        )


class BaseScanner(ABC):
    """Abstract base class for all inventory scanners."""

    @property
    @abstractmethod
    def scanner_id(self) -> str:
        """Unique identifier for the scanner (e.g. 'brew_formula', 'npm_global')."""

    @property
    @abstractmethod
    def domain(self) -> str:
        """Category domain (e.g. 'package_manager', 'binaries', 'applications')."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name."""

    @property
    def version(self) -> str:
        """Scanner version."""
        return "1.0.0"

    @abstractmethod
    def is_available(self) -> bool:
        """Check if scanner dependencies/executables are available on the system."""

    @abstractmethod
    def scan(self, context: ScanContext) -> ScanResult:
        """Perform the actual discovery scan."""

    def execute(self, context: ScanContext) -> ScanResult:
        """Safely execute scanner with timing, availability detection, and error insulation.

        Guarantees:
        - Never raises uncaught exceptions.
        - Accurately reports unavailable/unsupported status.
        - Records execution duration.
        """
        start_time = time.perf_counter()

        if not self.is_available():
            duration = time.perf_counter() - start_time
            return ScanResult(
                scanner_id=self.scanner_id,
                domain=self.domain,
                status=ScannerStatus.UNAVAILABLE,
                duration_seconds=duration,
                warnings=[f"Scanner '{self.name}' is unavailable on this system."],
            )

        try:
            result = self.scan(context)
            result.duration_seconds = time.perf_counter() - start_time
            return result
        except Exception as exc:
            duration = time.perf_counter() - start_time
            return ScanResult(
                scanner_id=self.scanner_id,
                domain=self.domain,
                status=ScannerStatus.FAILED,
                duration_seconds=duration,
                errors=[f"Scanner '{self.name}' failed with error: {exc}"],
            )
