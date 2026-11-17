"""Read-only and unsupported lifecycle adapters."""

import shutil

from inv.adapters.base import (
    AdapterUnsupportedError,
    BaseLifecycleAdapter,
)
from inv.constants import InstallScope, LifecycleCapability
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult


class ReadOnlyLifecycleAdapter(BaseLifecycleAdapter):
    """Adapter for managers that support inventory discovery but do not support modification."""

    def __init__(self, manager_id: str, display_name: str, executable_name: str) -> None:
        self._manager_id = manager_id
        self._display_name = display_name
        self._executable_name = executable_name

    @property
    def manager_id(self) -> str:
        return self._manager_id

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def supported_capabilities(self) -> set[LifecycleCapability]:
        return set()

    def is_available(self) -> bool:
        return shutil.which(self._executable_name) is not None

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        return []

    def get_package_info(self, name: str) -> PackageInfo | None:
        return None

    def list_versions(self, name: str) -> list[str]:
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        raise AdapterUnsupportedError(
            f"Package manager '{self.display_name}' supports software discovery only. "
            f"Package installation via 'inv install' is not supported for {self.display_name}."
        )

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        raise AdapterUnsupportedError(
            f"Package manager '{self.display_name}' supports software discovery only. "
            f"Package removal via 'inv remove' is not supported for {self.display_name}."
        )

    def upgrade(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        raise AdapterUnsupportedError(
            f"Package manager '{self.display_name}' supports software discovery only. "
            f"Package upgrade via 'inv upgrade' is not supported for {self.display_name}."
        )

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        return False
