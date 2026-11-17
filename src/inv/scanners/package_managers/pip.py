"""Pip package manager scanner."""

import json

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class PipScanner(BaseScanner):
    """Scanner for Python pip packages in current/active Python environment."""

    @property
    def scanner_id(self) -> str:
        return "pip"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Pip Packages"

    def is_available(self) -> bool:
        return find_executable("pip") is not None or find_executable("pip3") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        pip_bin = find_executable("pip") or find_executable("pip3") or "pip"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [pip_bin, "list", "--format=json"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success or not res.stdout.strip():
            result.status = ScannerStatus.FAILED
            result.errors.append(f"pip list failed: {res.stderr}")
            return result

        try:
            packages = json.loads(res.stdout)
            for pkg in packages:
                if not isinstance(pkg, dict):
                    continue
                name = pkg.get("name", "")
                version = pkg.get("version", "unknown")
                if not name:
                    continue

                ident = SoftwareIdentity.create(name=name, ecosystem="python")
                result.identities.append(ident)

                inst = InstallationInstance.create(
                    software_id=ident.id,
                    name=name,
                    version=version,
                    manager="pip",
                    scope=InstallScope.GLOBAL,
                    provenance="pip list --format=json",
                )
                result.installations.append(inst)

            return result
        except json.JSONDecodeError as exc:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to parse pip list JSON: {exc}")
            return result

