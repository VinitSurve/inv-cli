"""Go tools and binaries scanner."""

import re
from pathlib import Path

from inv.constants import InstallScope
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class GoToolsScanner(BaseScanner):
    """Scanner for installed Go tools in GOBIN or ~/go/bin."""

    @property
    def scanner_id(self) -> str:
        return "go"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Go Tools"

    def is_available(self) -> bool:
        go_bin = find_executable("go")
        go_path = Path.home() / "go" / "bin"
        return go_bin is not None or go_path.is_dir()

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)
        go_bin = find_executable("go")

        # Discover GOBIN path
        target_dirs: list[Path] = [Path.home() / "go" / "bin"]
        if go_bin:
            res_env = run_command([go_bin, "env", "GOBIN"], timeout=context.config.process_timeout)
            if res_env.success and res_env.stdout.strip():
                target_dirs.append(Path(res_env.stdout.strip()))

        seen_bins: set[str] = set()

        for gdir in target_dirs:
            if not gdir.is_dir():
                continue

            for entry in gdir.iterdir():
                if entry.is_file() and not entry.name.startswith("."):
                    name = entry.name
                    if name in seen_bins:
                        continue
                    seen_bins.add(name)

                    version = "installed"
                    # If go CLI is present, run go version -m <binary> to extract module version safely
                    if go_bin:
                        res_m = run_command(
                            [go_bin, "version", "-m", str(entry)],
                            timeout=context.config.process_timeout,
                        )
                        if res_m.success:
                            # Search for mod ... line
                            match = re.search(r"\bmod\s+([^\s]+)\s+([^\s]+)", res_m.stdout)
                            if match:
                                mod_path = match.group(1)
                                version = match.group(2)
                                name = mod_path.split("/")[-1]

                    ident = SoftwareIdentity.create(name=name, ecosystem="go")
                    result.identities.append(ident)
                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=version,
                        manager="go",
                        install_path=entry,
                        scope=InstallScope.USER,
                        provenance="go bin inspection",
                    )
                    result.installations.append(inst)

        return result
