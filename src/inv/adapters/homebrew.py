"""Homebrew Formula and Cask lifecycle management adapter."""

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


class HomebrewAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for macOS Homebrew package manager (formulae and casks)."""

    def __init__(self, is_cask: bool = False) -> None:
        self.is_cask = is_cask

    @property
    def manager_id(self) -> str:
        return "brew_cask" if self.is_cask else "brew_formula"

    @property
    def display_name(self) -> str:
        return "Homebrew Cask" if self.is_cask else "Homebrew Formula"

    @property
    def supported_capabilities(self) -> set[LifecycleCapability]:
        caps = {
            LifecycleCapability.INSTALL,
            LifecycleCapability.REMOVE,
            LifecycleCapability.UPGRADE,
            LifecycleCapability.CHECK_OUTDATED,
            LifecycleCapability.LIST_VERSIONS,
            LifecycleCapability.VERIFY_INSTALLATION,
            LifecycleCapability.RESOLVE_DEPENDENCIES,
        }
        return caps

    def is_available(self) -> bool:
        return shutil.which("brew") is not None

    def _get_brew_cmd(self) -> str:
        return shutil.which("brew") or "brew"

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Fetch outdated Homebrew packages via structured JSON inspection."""
        self.ensure_capability(LifecycleCapability.CHECK_OUTDATED)
        if not self.is_available():
            return []

        brew_bin = self._get_brew_cmd()
        cmd = [brew_bin, "outdated", "--json=v2"]
        res = run_command(cmd, timeout=30.0)
        if not res.success or not res.stdout.strip():
            return []

        outdated: list[OutdatedPackage] = []
        try:
            data = json.loads(res.stdout)
            key = "casks" if self.is_cask else "formulae"
            items = data.get(key, [])
            for item in items:
                name = item.get("name")
                if not name:
                    continue
                installed_versions = item.get("installed_versions", [])
                inst_ver = installed_versions[0] if installed_versions else "unknown"
                curr_ver = item.get("current_version", "unknown")

                # Check if major version changed
                is_major = False
                try:
                    inst_major = int(inst_ver.split(".")[0])
                    curr_major = int(curr_ver.split(".")[0])
                    is_major = curr_major > inst_major
                except (ValueError, IndexError):
                    is_major = False

                outdated.append(
                    OutdatedPackage(
                        name=name,
                        manager=self.manager_id,
                        installed_version=inst_ver,
                        latest_version=curr_ver,
                        latest_stable_version=curr_ver,
                        latest_compatible_version=curr_ver,
                        update_strategy=UpdateStrategy.COMPATIBLE,
                        is_major_update=is_major,
                    )
                )
        except json.JSONDecodeError:
            pass

        return outdated

    def get_package_info(self, name: str) -> PackageInfo | None:
        """Inspect package details via brew info --json=v2."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return None

        brew_bin = self._get_brew_cmd()
        flag = "--cask" if self.is_cask else "--formula"
        cmd = [brew_bin, "info", "--json=v2", flag, val_name]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return None

        try:
            data = json.loads(res.stdout)
            key = "casks" if self.is_cask else "formulae"
            items = data.get(key, [])
            if not items:
                return None
            info = items[0]
            pkg_name = info.get("token" if self.is_cask else "name", val_name)
            desc = info.get("desc")
            homepage = info.get("homepage")
            lic = info.get("license")

            installed_ver: str | None = None
            if self.is_cask:
                installed_ver = info.get("version") if info.get("installed") else None
                latest_ver = info.get("version")
                deps = []
            else:
                installed_entries = info.get("installed", [])
                if installed_entries:
                    installed_ver = installed_entries[0].get("version")
                latest_ver = info.get("versions", {}).get("stable")
                deps = info.get("dependencies", [])

            # Get reverse dependencies if formula is installed
            rev_deps: list[str] = []
            if not self.is_cask and installed_ver:
                uses_cmd = [brew_bin, "uses", "--installed", val_name]
                uses_res = run_command(uses_cmd, timeout=10.0)
                if uses_res.success:
                    rev_deps = [u.strip() for u in uses_res.stdout.splitlines() if u.strip()]

            return PackageInfo(
                name=pkg_name,
                manager=self.manager_id,
                installed_version=installed_ver,
                latest_version=latest_ver,
                latest_stable_version=latest_ver,
                homepage=homepage,
                description=desc,
                license=lic,
                dependencies=deps,
                reverse_dependencies=rev_deps,
                scope="global",
            )
        except Exception:
            return None

    def list_versions(self, name: str) -> list[str]:
        """List current available stable version for a formula/cask."""
        info = self.get_package_info(name)
        if info and info.latest_version:
            return [info.latest_version]
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Install a Homebrew formula or cask."""
        self.ensure_capability(LifecycleCapability.INSTALL)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        brew_bin = self._get_brew_cmd()

        target = f"{val_name}@{val_ver}" if val_ver else val_name
        cmd = [brew_bin, "install"]
        if self.is_cask:
            cmd.append("--cask")
        cmd.append(target)

        if dry_run:
            # Return preview result without executing
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Uninstall a Homebrew formula or cask."""
        self.ensure_capability(LifecycleCapability.REMOVE)
        val_name = validate_package_name(package)
        brew_bin = self._get_brew_cmd()

        cmd = [brew_bin, "uninstall"]
        if self.is_cask:
            cmd.append("--cask")
        cmd.append(val_name)

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
        """Upgrade a Homebrew formula or cask."""
        self.ensure_capability(LifecycleCapability.UPGRADE)
        val_name = validate_package_name(package)
        brew_bin = self._get_brew_cmd()

        cmd = [brew_bin, "upgrade"]
        if self.is_cask:
            cmd.append("--cask")
        cmd.append(val_name)

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=300.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify that package is installed according to brew list."""
        val_name = validate_package_name(package)
        if not self.is_available():
            return False

        brew_bin = self._get_brew_cmd()
        cmd = [brew_bin, "list", "--cask" if self.is_cask else "--formula", "--versions", val_name]
        res = run_command(cmd, timeout=10.0)
        if not res.success or not res.stdout.strip():
            return False

        if expected_version:
            # Verify version substring in output
            return expected_version in res.stdout
        return True

    @property
    def rollback_guaranteed(self) -> bool:
        return False

    def rollback_guidance(self, package: str, previous_version: str | None) -> str:
        if previous_version and not self.is_cask:
            return f"To attempt restore: brew extract --version={previous_version} {package} <tap> && brew install {package}@{previous_version}"
        return "Homebrew uninstalls older versions during cleanup. Rollback to older version is not guaranteed."
