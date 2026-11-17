"""MacPorts package manager scanner."""

import re

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class MacPortsScanner(BaseScanner):
    """Scanner for MacPorts installed packages."""

    @property
    def scanner_id(self) -> str:
        return "macports"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "MacPorts"

    def is_available(self) -> bool:
        return find_executable("port") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        port_bin = find_executable("port") or "port"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [port_bin, "installed"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to list MacPorts packages: {res.stderr}")
            return result

        # MacPorts lines: "  python311 @3.11.8_0+lto (active)"
        port_pattern = re.compile(r"^\s*([a-zA-Z0-9_\-\.]+)\s+@([^\s]+)(?:\s+\(active\))?")
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("The following ports are currently installed:"):
                continue
            match = port_pattern.match(line)
            if match:
                name = match.group(1)
                ver = match.group(2)
                ident = SoftwareIdentity.create(name=name, ecosystem="macports")
                result.identities.append(ident)
                inst = InstallationInstance.create(
                    software_id=ident.id,
                    name=name,
                    version=ver,
                    manager="macports",
                    scope=InstallScope.SYSTEM,
                    provenance="port installed",
                )
                result.installations.append(inst)

        return result
