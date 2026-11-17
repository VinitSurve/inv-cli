"""npm global packages scanner."""

import json
from pathlib import Path

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class NpmGlobalScanner(BaseScanner):
    """Scanner for globally installed npm packages."""

    @property
    def scanner_id(self) -> str:
        return "npm_global"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "npm Global Packages"

    def is_available(self) -> bool:
        return find_executable("npm") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        npm_bin = find_executable("npm") or "npm"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [npm_bin, "list", "-g", "--json", "--depth=0"]
        res = run_command(cmd, timeout=context.config.process_timeout)

        # npm sometimes exits with code 1 if there are minor peer dep warnings even with valid json
        if not res.stdout.strip():
            result.status = ScannerStatus.FAILED
            result.errors.append(f"npm failed: {res.stderr}")
            return result

        try:
            data = json.loads(res.stdout)
            deps = data.get("dependencies", {})
            for name, info in deps.items():
                if not isinstance(info, dict):
                    continue
                version = info.get("version", "unknown")
                raw_path = info.get("path")
                pkg_path = Path(str(raw_path)) if raw_path else None

                ident = SoftwareIdentity.create(name=name, ecosystem="npm")
                result.identities.append(ident)

                inst = InstallationInstance.create(
                    software_id=ident.id,
                    name=name,
                    version=version,
                    manager="npm",
                    install_path=pkg_path,
                    scope=InstallScope.GLOBAL,
                    provenance="npm list -g --json",
                )
                result.installations.append(inst)

            return result
        except json.JSONDecodeError as exc:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to parse npm json: {exc}")
            return result
