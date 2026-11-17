"""Yarn package lifecycle management adapter."""

import shutil

from inv.adapters.base import (
    BaseLifecycleAdapter,
    validate_package_name,
    validate_version_spec,
)
from inv.constants import InstallScope, LifecycleCapability
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult, run_command


class YarnAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for Yarn global package management."""

    @property
    def manager_id(self) -> str:
        return "yarn"

    @property
    def display_name(self) -> str:
        return "Yarn"

    @property
    def supported_capabilities(self) -> set[LifecycleCapability]:
        return {
            LifecycleCapability.INSTALL,
            LifecycleCapability.REMOVE,
            LifecycleCapability.UPGRADE,
            LifecycleCapability.VERIFY_INSTALLATION,
        }

    def is_available(self) -> bool:
        return shutil.which("yarn") is not None

    def _get_yarn_cmd(self) -> str:
        return shutil.which("yarn") or "yarn"

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        return []

    def get_package_info(self, name: str) -> PackageInfo | None:
        val_name = validate_package_name(name)
        return PackageInfo(name=val_name, manager="yarn", scope="global")

    def list_versions(self, name: str) -> list[str]:
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        self.ensure_capability(LifecycleCapability.INSTALL)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        yarn_bin = self._get_yarn_cmd()

        target = f"{val_name}@{val_ver}" if val_ver else val_name
        cmd = [yarn_bin, "global", "add", target]

        if dry_run:
            return ProcessResult(
                argv=cmd, exit_code=0, stdout=f"[Dry Run] Would execute: {' '.join(cmd)}", stderr=""
            )
        return run_command(cmd, timeout=120.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        self.ensure_capability(LifecycleCapability.REMOVE)
        val_name = validate_package_name(package)
        yarn_bin = self._get_yarn_cmd()

        cmd = [yarn_bin, "global", "remove", val_name]
        if dry_run:
            return ProcessResult(
                argv=cmd, exit_code=0, stdout=f"[Dry Run] Would execute: {' '.join(cmd)}", stderr=""
            )
        return run_command(cmd, timeout=60.0)

    def upgrade(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        self.ensure_capability(LifecycleCapability.UPGRADE)
        val_name = validate_package_name(package)
        yarn_bin = self._get_yarn_cmd()

        cmd = [yarn_bin, "global", "upgrade", val_name]
        if dry_run:
            return ProcessResult(
                argv=cmd, exit_code=0, stdout=f"[Dry Run] Would execute: {' '.join(cmd)}", stderr=""
            )
        return run_command(cmd, timeout=120.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        val_name = validate_package_name(package)
        yarn_bin = self._get_yarn_cmd()
        cmd = [yarn_bin, "global", "list"]
        res = run_command(cmd, timeout=10.0)
        return res.success and val_name in res.stdout
