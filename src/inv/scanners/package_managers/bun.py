"""Bun global packages scanner."""

import json
from pathlib import Path

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class BunGlobalScanner(BaseScanner):
    """Scanner for globally installed Bun packages."""

    @property
    def scanner_id(self) -> str:
        return "bun_global"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Bun Global Packages"

    def is_available(self) -> bool:
        return find_executable("bun") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        bun_bin = find_executable("bun") or "bun"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [bun_bin, "pm", "ls", "-g"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success:
            # Fallback to inspecting ~/.bun/install/global/package.json
            global_pkg = Path.home() / ".bun" / "install" / "global" / "package.json"
            if global_pkg.exists():
                try:
                    with open(global_pkg, encoding="utf-8") as f:
                        data = json.load(f)
                    for name, spec in data.get("dependencies", {}).items():
                        ident = SoftwareIdentity.create(name=name, ecosystem="npm")
                        result.identities.append(ident)
                        inst = InstallationInstance.create(
                            software_id=ident.id,
                            name=name,
                            version=str(spec),
                            manager="bun",
                            scope=InstallScope.GLOBAL,
                            provenance="~/.bun/install/global/package.json",
                        )
                        result.installations.append(inst)
                    return result
                except Exception:
                    pass

            result.status = ScannerStatus.FAILED
            result.errors.append(f"bun pm ls -g failed: {res.stderr}")
            return result

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("├── ") or line.startswith("└── "):
                clean = line.replace("├── ", "").replace("└── ", "")
                if "@" in clean:
                    parts = clean.rsplit("@", 1)
                    name, version = parts[0], parts[1]
                    ident = SoftwareIdentity.create(name=name, ecosystem="npm")
                    result.identities.append(ident)
                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=version,
                        manager="bun",
                        scope=InstallScope.GLOBAL,
                        provenance="bun pm ls -g",
                    )
                    result.installations.append(inst)

        return result
