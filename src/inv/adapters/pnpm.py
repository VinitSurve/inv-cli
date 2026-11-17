"""pnpm package lifecycle management adapter."""

import json
import shutil

from inv.adapters.base import (
    BaseLifecycleAdapter,
    validate_package_name,
    validate_version_spec,
)
from inv.constants import InstallScope, LifecycleCapability, UpdateStrategy
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult, run_command


class PnpmAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for pnpm global package management."""

    @property
    def manager_id(self) -> str:
        return "pnpm"

    @property
    def display_name(self) -> str:
        return "Fast Node Package Manager (pnpm)"

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
        return shutil.which("pnpm") is not None

    def _get_pnpm_cmd(self) -> str:
        return shutil.which("pnpm") or "pnpm"

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Check outdated packages via pnpm outdated -g --format json."""
        self.ensure_capability(LifecycleCapability.CHECK_OUTDATED)
        if not self.is_available():
            return []

        pnpm_bin = self._get_pnpm_cmd()
        cmd = [pnpm_bin, "outdated", "--format", "json"]
        if scope == InstallScope.GLOBAL:
            cmd.append("-g")

        res = run_command(cmd, timeout=30.0)
        if not res.stdout.strip():
            return []

        outdated: list[OutdatedPackage] = []
        try:
            data = json.loads(res.stdout)
            for name, meta in data.items():
                curr = meta.get("current", "unknown")
                latest = meta.get("latest", curr)
                wanted = meta.get("wanted", curr)
                outdated.append(
                    OutdatedPackage(
                        name=name,
                        manager="pnpm",
                        installed_version=curr,
                        latest_version=latest,
                        latest_stable_version=latest,
                        latest_compatible_version=wanted,
                        update_strategy=UpdateStrategy.COMPATIBLE,
                    )
                )
        except json.JSONDecodeError:
            pass

        return outdated

    def get_package_info(self, name: str) -> PackageInfo | None:
        """Inspect package metadata via pnpm view."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return None

        pnpm_bin = self._get_pnpm_cmd()
        cmd = [pnpm_bin, "view", val_name, "--json"]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return None

        try:
            data = json.loads(res.stdout)
            return PackageInfo(
                name=data.get("name", val_name),
                manager="pnpm",
                installed_version=None,
                latest_version=data.get("version"),
                latest_stable_version=data.get("version"),
                homepage=data.get("homepage"),
                description=data.get("description"),
                license=data.get("license"),
                scope="global",
            )
        except json.JSONDecodeError:
            return None

    def list_versions(self, name: str) -> list[str]:
        """List versions for pnpm package."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return []

        pnpm_bin = self._get_pnpm_cmd()
        cmd = [pnpm_bin, "view", val_name, "versions", "--json"]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return []

        try:
            data = json.loads(res.stdout)
            if isinstance(data, list):
                return [str(v) for v in data[-10:]]
            if isinstance(data, str):
                return [data]
        except json.JSONDecodeError:
            pass
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Install package globally via pnpm add -g."""
        self.ensure_capability(LifecycleCapability.INSTALL)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        pnpm_bin = self._get_pnpm_cmd()

        target = f"{val_name}@{val_ver}" if val_ver else val_name
        cmd = [pnpm_bin, "add", "-g", target]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Remove global package via pnpm remove -g."""
        self.ensure_capability(LifecycleCapability.REMOVE)
        val_name = validate_package_name(package)
        pnpm_bin = self._get_pnpm_cmd()

        cmd = [pnpm_bin, "remove", "-g", val_name]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=120.0)

    def upgrade(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Upgrade global package via pnpm update -g."""
        self.ensure_capability(LifecycleCapability.UPGRADE)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        pnpm_bin = self._get_pnpm_cmd()

        if val_ver:
            cmd = [pnpm_bin, "add", "-g", f"{val_name}@{val_ver}"]
        else:
            cmd = [pnpm_bin, "update", "-g", val_name]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify package is present in pnpm list -g."""
        val_name = validate_package_name(package)
        if not self.is_available():
            return False

        pnpm_bin = self._get_pnpm_cmd()
        cmd = [pnpm_bin, "list", "-g", "--depth", "0", "--json"]
        res = run_command(cmd, timeout=10.0)
        if not res.stdout.strip():
            return False

        try:
            data = json.loads(res.stdout)
            if isinstance(data, list) and data:
                deps = data[0].get("dependencies", {})
                if val_name in deps:
                    if expected_version:
                        return bool(deps[val_name].get("version") == expected_version)
                    return True
        except json.JSONDecodeError:
            pass
        return False

    @property
    def rollback_guaranteed(self) -> bool:
        return True

    def rollback_guidance(self, package: str, previous_version: str | None) -> str:
        if previous_version:
            return f"Rollback available: pnpm add -g {package}@{previous_version}"
        return "Rollback requires reinstalling previous package version."
