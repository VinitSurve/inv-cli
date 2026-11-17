"""Python pip lifecycle management adapter with PEP 668 externally-managed safety."""

import json
import os
import sys
from pathlib import Path

from inv.adapters.base import (
    AdapterSecurityError,
    BaseLifecycleAdapter,
    validate_package_name,
    validate_version_spec,
)
from inv.constants import InstallScope, LifecycleCapability, UpdateStrategy
from inv.lifecycle.models import OutdatedPackage, PackageInfo
from inv.utils.process import ProcessResult, run_command


class PipAdapter(BaseLifecycleAdapter):
    """Lifecycle adapter for Python pip packages with strict environment boundary checks."""

    def __init__(self, target_python: Path | None = None) -> None:
        self.target_python = target_python or self._detect_safe_python()

    @property
    def manager_id(self) -> str:
        return "pip"

    @property
    def display_name(self) -> str:
        return "Python Pip"

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

    def _detect_safe_python(self) -> Path:
        """Detect the active safe Python environment (preferring active virtualenv)."""
        venv_dir = os.environ.get("VIRTUAL_ENV")
        if venv_dir:
            v_py = Path(venv_dir) / "bin" / "python"
            if v_py.exists():
                return v_py

        # Fallback to current sys.executable
        return Path(sys.executable)

    def is_available(self) -> bool:
        return self.target_python.exists() and os.access(self.target_python, os.X_OK)

    def _check_pep668_safety(self) -> None:
        """Verify target environment is not a system-managed or externally managed environment."""
        p_str = str(self.target_python)
        # Block macOS system python and developer tools
        if (
            p_str.startswith("/usr/bin")
            or p_str.startswith("/System")
            or "/XcodeDefault.xctoolchain/" in p_str
        ):
            raise AdapterSecurityError(
                f"PEP 668: Cannot modify system-managed Python at '{self.target_python}'. "
                "Use a dedicated virtual environment or uv tool instead."
            )

        # Check for EXTERNALLY-MANAGED marker
        stdlib_marker = self.target_python.parent.parent / "lib"
        if stdlib_marker.exists():
            for child in stdlib_marker.iterdir():
                if (child / "EXTERNALLY-MANAGED").exists():
                    raise AdapterSecurityError(
                        f"PEP 668: Target Python at '{self.target_python}' is externally managed. "
                        "Direct package modification is restricted."
                    )

    def check_outdated(self, scope: InstallScope = InstallScope.GLOBAL) -> list[OutdatedPackage]:
        """Check outdated packages via python -m pip list --outdated --format=json."""
        self.ensure_capability(LifecycleCapability.CHECK_OUTDATED)
        if not self.is_available():
            return []

        cmd = [str(self.target_python), "-m", "pip", "list", "--outdated", "--format=json"]
        res = run_command(cmd, timeout=30.0)
        if not res.success or not res.stdout.strip():
            return []

        outdated: list[OutdatedPackage] = []
        try:
            data = json.loads(res.stdout)
            for item in data:
                name = item.get("name")
                if not name:
                    continue
                curr = item.get("version", "unknown")
                latest = item.get("latest_version", curr)

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
                        manager="pip",
                        installed_version=curr,
                        latest_version=latest,
                        latest_stable_version=latest,
                        latest_compatible_version=latest,
                        update_strategy=UpdateStrategy.COMPATIBLE,
                        is_major_update=is_major,
                    )
                )
        except json.JSONDecodeError:
            pass

        return outdated

    def get_package_info(self, name: str) -> PackageInfo | None:
        """Inspect package details via pip show."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return None

        cmd = [str(self.target_python), "-m", "pip", "show", val_name]
        res = run_command(cmd, timeout=10.0)
        if not res.success or not res.stdout.strip():
            return None

        fields: dict[str, str] = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip().lower()] = v.strip()

        requires = [r.strip() for r in fields.get("requires", "").split(",") if r.strip()]
        required_by = [r.strip() for r in fields.get("required-by", "").split(",") if r.strip()]

        return PackageInfo(
            name=fields.get("name", val_name),
            manager="pip",
            installed_version=fields.get("version"),
            latest_version=fields.get("version"),
            homepage=fields.get("home-page"),
            description=fields.get("summary"),
            license=fields.get("license"),
            dependencies=requires,
            reverse_dependencies=required_by,
            install_path=fields.get("location"),
            scope="environment",
        )

    def list_versions(self, name: str) -> list[str]:
        """Fetch available versions via pip index or pip show."""
        val_name = validate_package_name(name)
        if not self.is_available():
            return []

        cmd = [str(self.target_python), "-m", "pip", "index", "versions", val_name]
        res = run_command(cmd, timeout=15.0)
        if res.success and "Available versions:" in res.stdout:
            for line in res.stdout.splitlines():
                if "Available versions:" in line:
                    _, vers = line.split("Available versions:", 1)
                    return [v.strip() for v in vers.split(",")[:10] if v.strip()]

        info = self.get_package_info(val_name)
        return [info.installed_version] if info and info.installed_version else []

    def install(
        self, package: str, version: str | None = None, dry_run: bool = False
    ) -> ProcessResult:
        """Install package via python -m pip install."""
        self.ensure_capability(LifecycleCapability.INSTALL)
        self._check_pep668_safety()
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)

        target = f"{val_name}=={val_ver}" if val_ver else val_name
        cmd = [str(self.target_python), "-m", "pip", "install", target]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def remove(self, package: str, dry_run: bool = False) -> ProcessResult:
        """Uninstall package via python -m pip uninstall -y."""
        self.ensure_capability(LifecycleCapability.REMOVE)
        self._check_pep668_safety()
        val_name = validate_package_name(package)

        cmd = [str(self.target_python), "-m", "pip", "uninstall", "-y", val_name]

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
        """Upgrade package via python -m pip install --upgrade."""
        self.ensure_capability(LifecycleCapability.UPGRADE)
        self._check_pep668_safety()
        val_name = validate_package_name(package)
        val_ver = validate_version_spec(version)

        if val_ver:
            cmd = [str(self.target_python), "-m", "pip", "install", f"{val_name}=={val_ver}"]
        else:
            cmd = [str(self.target_python), "-m", "pip", "install", "--upgrade", val_name]

        if dry_run:
            return ProcessResult(
                argv=cmd,
                exit_code=0,
                stdout=f"[Dry Run] Would execute: {' '.join(cmd)}",
                stderr="",
            )

        return run_command(cmd, timeout=180.0)

    def verify_installation(self, package: str, expected_version: str | None = None) -> bool:
        """Verify package is installed in the target Python environment."""
        val_name = validate_package_name(package)
        info = self.get_package_info(val_name)
        if not info or not info.installed_version:
            return False
        if expected_version:
            return info.installed_version == expected_version
        return True

    @property
    def rollback_guaranteed(self) -> bool:
        return True

    def rollback_guidance(self, package: str, previous_version: str | None) -> str:
        if previous_version:
            return f"Rollback available: pip install {package}=={previous_version}"
        return "Rollback requires reinstalling previous wheel or package version."
