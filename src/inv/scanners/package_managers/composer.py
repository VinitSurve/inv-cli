"""PHP Composer global package scanner."""

import json

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class ComposerScanner(BaseScanner):
    """Scanner for globally installed PHP Composer packages."""

    @property
    def scanner_id(self) -> str:
        return "composer"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "PHP Composer"

    def is_available(self) -> bool:
        return find_executable("composer") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        composer_bin = find_executable("composer") or "composer"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [composer_bin, "global", "show", "--format=json"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success or not res.stdout.strip():
            # Fall back to text
            res_txt = run_command(
                [composer_bin, "global", "show"], timeout=context.config.process_timeout
            )
            if not res_txt.success:
                result.status = ScannerStatus.FAILED
                result.errors.append(f"composer global show failed: {res.stderr}")
                return result

            for line in res_txt.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    name = parts[0]
                    ver = parts[1]
                    ident = SoftwareIdentity.create(name=name, ecosystem="composer")
                    result.identities.append(ident)
                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=ver,
                        manager="composer",
                        scope=InstallScope.GLOBAL,
                        provenance="composer global show",
                    )
                    result.installations.append(inst)
            return result

        try:
            data = json.loads(res.stdout)
            for pkg in data.get("installed", []):
                name = pkg.get("name", "")
                ver = pkg.get("version", "unknown")
                desc = pkg.get("description")
                if not name:
                    continue
                ident = SoftwareIdentity.create(name=name, ecosystem="composer", description=desc)
                result.identities.append(ident)
                inst = InstallationInstance.create(
                    software_id=ident.id,
                    name=name,
                    version=ver,
                    manager="composer",
                    scope=InstallScope.GLOBAL,
                    provenance="composer global show --format=json",
                )
                result.installations.append(inst)
            return result
        except json.JSONDecodeError as exc:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to parse composer json: {exc}")
            return result
