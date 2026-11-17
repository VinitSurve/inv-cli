"""npm package lifecycle management adapter."""

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


class NpmAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for npm global and project packages."""

    @property
    def manager_id(self) -> str:
        return "npm"

    @property
    def display_name(self) -> str:
        return "Node Package Manager (npm)"

    @property
    def supported_capabilities(self) -> set[LifecycleCapability]:
        return {
            LifecycleCapability.INSTALL,
            LifecycleCapability.REMOVE,
            LifecycleCapability.UPGRADE,
            LifecycleCapability.CHECK_OUTDATED,
            LifecycleCapability.LIST_VERSIONS,
            LifecycleCapability.VERIFY_INSTALLATION,
            LifecycleCapability.AUDIT,
            LifecycleCapability.ROLLBACK,
        }

    def is_available(self) -> bool:
        return shutil.which("npm") is not None

    def _get_npm_cmd(self) -> str:
        return shutil.which("npm") or "npm"

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Check outdated packages via npm outdated --json."""
        self.ensure_capability(LifecycleCapability.CHECK_OUTDATED)
        if not self.is_available():
            return []

        npm_bin = self._get_npm_cmd()
        cmd = [npm_bin, "outdated", "--json"]
        if scope == InstallScope.GLOBAL:
            cmd.append("-g")

        res = run_command(cmd, timeout=30.0)
        # npm outdated returns exit code 1 when outdated packages exist!
        if not res.stdout.strip():
            return []

        outdated: list[OutdatedPackage] = []
        try:
            data = json.loads(res.stdout)
            for name, meta in data.items():
                curr = meta.get("current", "unknown")
                wanted = meta.get("wanted", curr)
                latest = meta.get("latest", curr)

                is_major = False
                try:
                    curr_m = int(curr.split(".")[0])
                    lat_m = int(latest.split(".")[0])
                    is_major = lat_m > curr_m
                except (ValueError, IndexError):
                    is_major = False

                outdated.append(
                    OutdatedPackage(
                        name=name,
                        manager="npm",
                        installed_version=curr,
                        latest_version=latest,
                        latest_stable_version=latest,
                        latest_compatible_version=wanted,
                        update_strategy=UpdateStrategy.COMPATIBLE,
                        is_major_update=is_major,
                    )
                )
        except json.JSONDecodeError:
            pass

        return outdated

    def get_package_info(self, name: str) -> PackageInfo | None:
        """Fetch package metadata via npm view --json."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return None

        npm_bin = self._get_npm_cmd()
        cmd = [npm_bin, "view", val_name, "--json"]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return None

        try:
            data = json.loads(res.stdout)
            # Find installed version if available
            inst_cmd = [npm_bin, "list", "-g", val_name, "--depth=0", "--json"]
            inst_res = run_command(inst_cmd, timeout=10.0)
            installed_ver: str | None = None
            if inst_res.stdout.strip():
                try:
                    inst_data = json.loads(inst_res.stdout)
                    deps = inst_data.get("dependencies", {})
                    if val_name in deps:
                        installed_ver = deps[val_name].get("version")
                except json.JSONDecodeError:
                    pass

            deps_list = list(data.get("dependencies", {}).keys())
            return PackageInfo(
                name=data.get("name", val_name),
                manager="npm",
                installed_version=installed_ver,
                latest_version=data.get("version"),
                latest_stable_version=data.get("version"),
                homepage=data.get("homepage"),
                description=data.get("description"),
                license=data.get("license"),
                dependencies=deps_list,
                scope="global",
            )
        except Exception:
            return None

    def list_versions(self, name: str) -> list[str]:
        """List published versions for an npm package."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return []

        npm_bin = self._get_npm_cmd()
        cmd = [npm_bin, "view", val_name, "versions", "--json"]
        res = run_command(cmd, timeout=15.0)
        if not res.success or not res.stdout.strip():
            return []

        try:
            data = json.loads(res.stdout)
            if isinstance(data, list):
                return [str(v) for v in data[-10:]]  # return top 10 recent
            if isinstance(data, str):
                return [data]
        except json.JSONDecodeError:
            pass
        return []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Install package globally via npm install -g."""
        self.ensure_capability(LifecycleCapability.INSTALL)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        npm_bin = self._get_npm_cmd()

        target = f"{val_name}@{val_ver}" if val_ver else val_name
        cmd = [npm_bin, "install", "-g", target]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Uninstall package globally via npm uninstall -g."""
        self.ensure_capability(LifecycleCapability.REMOVE)
        val_name = validate_package_name(package)
        npm_bin = self._get_npm_cmd()

        cmd = [npm_bin, "uninstall", "-g", val_name]

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
        """Upgrade package globally via npm update -g or explicit install."""
        self.ensure_capability(LifecycleCapability.UPGRADE)
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)
        npm_bin = self._get_npm_cmd()

        if val_ver:
            cmd = [npm_bin, "install", "-g", f"{val_name}@{val_ver}"]
        else:
            cmd = [npm_bin, "update", "-g", val_name]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify package is present in npm global list."""
        val_name = validate_package_name(package)
        if not self.is_available():
            return False

        npm_bin = self._get_npm_cmd()
        cmd = [npm_bin, "list", "-g", val_name, "--depth=0", "--json"]
        res = run_command(cmd, timeout=10.0)
        if not res.stdout.strip():
            return False

        try:
            data = json.loads(res.stdout)
            deps = data.get("dependencies", {})
            if val_name not in deps:
                return False
            if expected_version:
                return bool(deps[val_name].get("version") == expected_version)
            return True
        except json.JSONDecodeError:
            return False

    @property
    def rollback_guaranteed(self) -> bool:
        return True

    def rollback_guidance(self, package: str, previous_version: str | None) -> str:
        if previous_version:
            return f"Rollback available: npm install -g {package}@{previous_version}"
        return "Rollback not applicable without previous version."
