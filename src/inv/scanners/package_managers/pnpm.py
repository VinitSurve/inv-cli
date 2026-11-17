"""pnpm global packages scanner."""

import json
from pathlib import Path

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class PnpmGlobalScanner(BaseScanner):
    """Scanner for globally installed pnpm packages."""

    @property
    def scanner_id(self) -> str:
        return "pnpm_global"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "pnpm Global Packages"

    def is_available(self) -> bool:
        return find_executable("pnpm") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        pnpm_bin = find_executable("pnpm") or "pnpm"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [pnpm_bin, "list", "-g", "--json"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success or not res.stdout.strip():
            result.status = ScannerStatus.FAILED
            result.errors.append(f"pnpm list -g failed: {res.stderr}")
            return result

        try:
            data = json.loads(res.stdout)
            # data is usually a list of packages root objects
            roots = data if isinstance(data, list) else [data]
            for item in roots:
                deps = item.get("dependencies", {})
                for name, info in deps.items():
                    if isinstance(info, dict):
                        version = info.get("version", "unknown")
                        path_str = info.get("path")
                    else:
                        version = str(info)
                        path_str = None

                    ident = SoftwareIdentity.create(name=name, ecosystem="npm")
                    result.identities.append(ident)

                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=version,
                        manager="pnpm",
                        install_path=Path(path_str) if path_str else None,
                        scope=InstallScope.GLOBAL,
                        provenance="pnpm list -g --json",
                    )
                    result.installations.append(inst)

            return result
        except json.JSONDecodeError as exc:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to parse pnpm json: {exc}")
            return result

