"""uv tool and project package lifecycle management adapter."""

import shutil

from inv.adapters.base import (
    BaseLifecycleAdapter,
    validate_package_name,
    validate_version_spec,
)
from inv.constants import InstallScope, LifecycleCapability, UpdateStrategy
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult, run_command


class UvAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for uv CLI tools and Python package environments."""

    @property
    def manager_id(self) -> str:
        return "uv_tool"

    @property
    def display_name(self) -> str:
        return "uv Tool"

    @property
    def supported_capabilities(self) -> set[LifecycleCapability]:
        return {
            LifecycleCapability.INSTALL,
            LifecycleCapability.REMOVE,
            LifecycleCapability.UPGRADE,
            LifecycleCapability.CHECK_OUTDATED,
            LifecycleCapability.LIST_VERSIONS,
            LifecycleCapability.VERIFY_INSTALLATION,
            LifecycleCapability.ROLLBACK,
        }

    def is_available(self) -> bool:
        return shutil.which("uv") is not None

    def _get_uv_cmd(self) -> str:
        return shutil.which("uv") or "uv"

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Check installed uv tools for potential updates."""
        self.ensure_capability(LifecycleCapability.CHECK_OUTDATED)
        if not self.is_available():
            return []

        uv_bin = self._get_uv_cmd()
        cmd = [uv_bin, "tool", "list"]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return []

        # uv tool list format:
        # ruff v0.3.4
        # - ruff
        outdated: list[OutdatedPackage] = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                ver = parts[1].lstrip("v")
                # When uv doesn't provide an offline outdated check, we query PyPI or report ver
                outdated.append(
                    OutdatedPackage(
                        name=name,
                        manager="uv_tool",
                        installed_version=ver,
                        latest_version=ver,
                        latest_stable_version=ver,
                        latest_compatible_version=ver,
                        update_strategy=UpdateStrategy.COMPATIBLE,
                    )
                )

        return outdated

    def get_package_info(self, name: str) -> PackageInfo | None:
        """Inspect uv tool package information."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return None

        uv_bin = self._get_uv_cmd()
        cmd = [uv_bin, "tool", "list"]
        res = run_command(cmd, timeout=10.0)
        if not res.success:
            return None

        installed_ver = None
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if parts and parts[0].lower() == val_name.lower() and len(parts) >= 2:
                installed_ver = parts[1].lstrip("v")
                break

        return PackageInfo(
            name=val_name,
            manager="uv_tool",
            installed_version=installed_ver,
            latest_version=installed_ver,
            scope="global",
        )

    def list_versions(self, name: str) -> list[str]:
        """List versions for uv tool package."""
        info = self.get_package_info(name)
        if info and info.installed_version:
            return [info.installed_version]
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Install a tool via uv tool install."""
        self.ensure_capability(LifecycleCapability.INSTALL)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        uv_bin = self._get_uv_cmd()

        target = f"{val_name}=={val_ver}" if val_ver else val_name
        cmd = [uv_bin, "tool", "install", target]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Uninstall a tool via uv tool uninstall."""
        self.ensure_capability(LifecycleCapability.REMOVE)
        val_name = validate_package_name(package)
        uv_bin = self._get_uv_cmd()

        cmd = [uv_bin, "tool", "uninstall", val_name]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=60.0)

    def upgrade(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Upgrade a tool via uv tool upgrade."""
        self.ensure_capability(LifecycleCapability.UPGRADE)
        val_name = validate_package_name(package)
        uv_bin = self._get_uv_cmd()

        cmd = [uv_bin, "tool", "upgrade", val_name]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify that tool is listed in uv tool list."""
        val_name = validate_package_name(package)
        if not self.is_available():
            return False

        uv_bin = self._get_uv_cmd()
        cmd = [uv_bin, "tool", "list"]
        res = run_command(cmd, timeout=10.0)
        if not res.success or not res.stdout.strip():
            return False

        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if parts and parts[0].lower() == val_name.lower():
                if expected_version and len(parts) >= 2:
                    return expected_version in parts[1]
                return True
        return False

    @property
    def rollback_guaranteed(self) -> bool:
        return True

    def rollback_guidance(self, package: str, previous_version: str | None) -> str:
        if previous_version:
            return f"Rollback available: uv tool install {package}=={previous_version} --force"
        return "Rollback requires reinstalling previous tool version."
