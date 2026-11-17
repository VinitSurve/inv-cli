"""Base lifecycle adapter interface and controlled execution primitives."""

import re
from abc import ABC, abstractmethod

from inv.constants import InstallScope, LifecycleCapability
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult


class AdapterSecurityError(Exception):
    """Raised when a package name or argument violates safety boundaries."""


class AdapterUnsupportedError(Exception):
    """Raised when an adapter does not support a requested lifecycle operation."""


# Disallow dangerous shell metacharacters and directory traversal sequences
DISALLOWED_PATTERN = re.compile(r"[\s;&|`$<>{}\[\]\n\r\\]")


def validate_package_name(name: str) -> str:
    """Validate package name against shell injection and malformed identifiers."""
    cleaned = name.strip()
    if not cleaned:
        raise AdapterSecurityError("Package name cannot be empty.")
    if (".." in cleaned or ("/" in cleaned and not cleaned.startswith("@"))) and (
        ".." in cleaned or cleaned.count("/") > 1
    ):
        raise AdapterSecurityError(f"Invalid package identifier (path traversal): {name}")
    if DISALLOWED_PATTERN.search(cleaned):
        raise AdapterSecurityError(
            f"Package name '{name}' contains disallowed characters or shell metacharacters."
        )
    return cleaned


def validate_version_spec(version: str | None) -> str | None:
    """Validate version string against command injection."""
    if version is None:
        return None
    cleaned = version.strip()
    if not cleaned:
        return None
    if DISALLOWED_PATTERN.search(cleaned):
        raise AdapterSecurityError(
            f"Version specification '{version}' contains disallowed shell metacharacters."
        )
    return cleaned


class BaseLifecycleAdapter(ABC):
    """Abstract base class for package manager lifecycle management."""

    @property
    @abstractmethod
    def manager_id(self) -> str:
        """Unique manager identifier matching PackageManagerType."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name of the package manager."""

    @property
    @abstractmethod
    def supported_capabilities(self) -> set[LifecycleCapability]:
        """Set of capabilities explicitly implemented by this adapter."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the underlying CLI executable is installed and accessible."""

    def supports(self, cap: LifecycleCapability) -> bool:
        """Check if a specific capability is supported."""
        return cap in self.supported_capabilities

    def ensure_capability(self, cap: LifecycleCapability) -> None:
        """Raise AdapterUnsupportedError if capability is unsupported."""
        if not self.supports(cap):
            raise AdapterUnsupportedError(
                f"Manager '{self.display_name}' does not support operation '{cap.value}'."
            )

    @abstractmethod
    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Query manager for packages with available updates."""

    @abstractmethod
    def get_package_info(self, name: str) -> PackageInfo | None:
        """Retrieve detailed metadata for a specific package."""

    @abstractmethod
    def list_versions(self, name: str) -> list[str]:
        """List available releases/versions for a package."""

    @abstractmethod
    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Execute or preview package installation."""

    @abstractmethod
    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Execute or preview package removal."""

    @abstractmethod
    def upgrade(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Execute or preview package upgrade."""

    @abstractmethod
    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify that package exists and matches expected version post-operation."""

    @property
    def rollback_guaranteed(self) -> bool:
        """Indicate whether exact previous versions can be restored reliably."""
        return False

    def rollback_guidance(self, package: str, previous_version: str | None) -> str:
        """Provide instructions for restoring a previous version."""
        if previous_version:
            return f"Re-install previous version using: inv install {package}@{previous_version} --manager {self.manager_id}"
        return f"Rollback for {self.display_name} requires reinstalling previous package manually."
