"""RubyGems package manager scanner."""

import re

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class GemScanner(BaseScanner):
    """Scanner for installed Ruby gems."""

    @property
    def scanner_id(self) -> str:
        return "gem"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "RubyGems"

    def is_available(self) -> bool:
        return find_executable("gem") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        gem_bin = find_executable("gem") or "gem"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [gem_bin, "list", "--local"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"gem list failed: {res.stderr}")
            return result

        gem_pattern = re.compile(r"^([a-zA-Z0-9_\-\.]+)\s+\((.*?)\)")
        for line in res.stdout.splitlines():
            line = line.strip()
            match = gem_pattern.match(line)
            if match:
                name = match.group(1)
                versions_raw = match.group(2)
                # Split versions, clean "default: "
                ver_tokens = [v.replace("default:", "").strip() for v in versions_raw.split(",")]
                ident = SoftwareIdentity.create(name=name, ecosystem="gem")
                result.identities.append(ident)

                for ver in ver_tokens:
                    if ver:
                        inst = InstallationInstance.create(
                            software_id=ident.id,
                            name=name,
                            version=ver,
                            manager="gem",
                            scope=InstallScope.GLOBAL,
                            provenance="gem list --local",
                        )
                        result.installations.append(inst)

        return result
