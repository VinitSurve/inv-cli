"""Rust Cargo tool lifecycle management adapter."""

import shutil

from inv.adapters.base import (
    BaseLifecycleAdapter,
    validate_package_name,
    validate_version_spec,
)
from inv.constants import InstallScope, LifecycleCapability, UpdateStrategy
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult, run_command


class CargoAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for Cargo installed binaries and tools."""

    @property
    def manager_id(self) -> str:
        return "cargo"

    @property
    def display_name(self) -> str:
        return "Rust Cargo"

    @property
    def supported_capabilities(self) -> set[LifecycleCapability]:
        return {
            LifecycleCapability.INSTALL,
            LifecycleCapability.REMOVE,
            LifecycleCapability.UPGRADE,
            LifecycleCapability.CHECK_OUTDATED,
            LifecycleCapability.VERIFY_INSTALLATION,
        }

    def is_available(self) -> bool:
        return shutil.which("cargo") is not None

    def _get_cargo_cmd(self) -> str:
        return shutil.which("cargo") or "cargo"

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Check installed cargo tools."""
        self.ensure_capability(LifecycleCapability.CHECK_OUTDATED)
        if not self.is_available():
            return []

        cargo_bin = self._get_cargo_cmd()
        cmd = [cargo_bin, "install", "--list"]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return []

        outdated: list[OutdatedPackage] = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith(":") or " v" not in line:
                continue
            parts = line.split(":", 1)[0].split()
            if len(parts) >= 2:
                name = parts[0]
                ver = parts[1].lstrip("v")
                outdated.append(
                    OutdatedPackage(
                        name=name,
                        manager="cargo",
                        installed_version=ver,
                        latest_version=ver,
                        latest_stable_version=ver,
                        latest_compatible_version=ver,
                        update_strategy=UpdateStrategy.COMPATIBLE,
                    )
                )
        return outdated

    def get_package_info(self, name: str) -> PackageInfo | None:
        """Inspect cargo tool info."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return None

        cargo_bin = self._get_cargo_cmd()
        cmd = [cargo_bin, "install", "--list"]
        res = run_command(cmd, timeout=10.0)
        if not res.success:
            return None

        for line in res.stdout.splitlines():
            parts = line.strip().split(":", 1)[0].split()
            if parts and parts[0].lower() == val_name.lower() and len(parts) >= 2:
                ver = parts[1].lstrip("v")
                return PackageInfo(
                    name=val_name,
                    manager="cargo",
                    installed_version=ver,
                    latest_version=ver,
                    scope="global",
                )
        return None

    def list_versions(self, name: str) -> list[str]:
        info = self.get_package_info(name)
        if info and info.installed_version:
            return [info.installed_version]
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Install cargo binary crate."""
        self.ensure_capability(LifecycleCapability.INSTALL)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        cargo_bin = self._get_cargo_cmd()

        cmd = [cargo_bin, "install", val_name]
        if val_ver:
            cmd.extend(["--version", val_ver])

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=300.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Uninstall cargo crate."""
        self.ensure_capability(LifecycleCapability.REMOVE)
        val_name = validate_package_name(package)
        cargo_bin = self._get_cargo_cmd()

        cmd = [cargo_bin, "uninstall", val_name]

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
        """Upgrade cargo crate by reinstalling with --force."""
        self.ensure_capability(LifecycleCapability.UPGRADE)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        cargo_bin = self._get_cargo_cmd()

        cmd = [cargo_bin, "install", "--force", val_name]
        if val_ver:
            cmd.extend(["--version", val_ver])

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=300.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify cargo crate installation."""
        val_name = validate_package_name(package)
        if not self.is_available():
            return False

        cargo_bin = self._get_cargo_cmd()
        cmd = [cargo_bin, "install", "--list"]
        res = run_command(cmd, timeout=10.0)
        if not res.success:
            return False

        for line in res.stdout.splitlines():
            parts = line.strip().split(":", 1)[0].split()
            if parts and parts[0].lower() == val_name.lower():
                if expected_version and len(parts) >= 2:
                    return expected_version in parts[1]
                return True
        return False
