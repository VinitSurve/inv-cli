"""Yarn global packages scanner."""

import json

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class YarnGlobalScanner(BaseScanner):
    """Scanner for globally installed Yarn packages."""

    @property
    def scanner_id(self) -> str:
        return "yarn_global"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Yarn Global Packages"

    def is_available(self) -> bool:
        return find_executable("yarn") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        yarn_bin = find_executable("yarn") or "yarn"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [yarn_bin, "global", "list", "--json"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.stdout.strip():
            result.status = ScannerStatus.FAILED
            result.errors.append(f"yarn global list failed: {res.stderr}")
            return result

        try:
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("type") == "info" and isinstance(event.get("data"), str):
                    # Data lines like "package@version"
                    data = event["data"]
                    if "@" in data and not data.startswith("@"):
                        parts = data.rsplit("@", 1)
                        name, version = parts[0], parts[1]
                        ident = SoftwareIdentity.create(name=name, ecosystem="npm")
                        result.identities.append(ident)
                        inst = InstallationInstance.create(
                            software_id=ident.id,
                            name=name,
                            version=version,
                            manager="yarn",
                            scope=InstallScope.GLOBAL,
                            provenance="yarn global list --json",
                        )
                        result.installations.append(inst)

            return result
        except Exception as exc:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Error parsing Yarn global output: {exc}")
            return result

