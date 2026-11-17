"""uv tools and environments scanner."""

import re
from pathlib import Path

from inv.constants import InstallScope
from inv.core.models import InstallationInstance, Runtime, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class UvScanner(BaseScanner):
    """Scanner for uv tools and managed Python runtimes."""

    @property
    def scanner_id(self) -> str:
        return "uv"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "uv Tools & Environments"

    def is_available(self) -> bool:
        return find_executable("uv") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        uv_bin = find_executable("uv") or "uv"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        # 1. uv tool list
        res_tools = run_command([uv_bin, "tool", "list"], timeout=context.config.process_timeout)
        if res_tools.success and "No tools installed" not in res_tools.stdout:
            # Lines like: ruff v0.6.9
            for line in res_tools.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("-"):
                    continue
                parts = line.split()
                if parts:
                    name = parts[0]
                    ver = parts[1].lstrip("v") if len(parts) > 1 else "unknown"
                    ident = SoftwareIdentity.create(name=name, ecosystem="python")
                    result.identities.append(ident)
                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=ver,
                        manager="uv_tool",
                        scope=InstallScope.USER,
                        provenance="uv tool list",
                    )
                    result.installations.append(inst)

        # 2. uv python list
        res_py = run_command([uv_bin, "python", "list"], timeout=context.config.process_timeout)
        if res_py.success:
            for line in res_py.stdout.splitlines():
                line = line.strip()
                if not line or "<download available>" in line:
                    continue
                # Line format: cpython-3.12.16-macos-aarch64-none /Users/...
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    tag = parts[0]
                    path_str = parts[1].split("->")[0].strip()
                    path_obj = Path(path_str)
                    match = re.search(r"\d+\.\d+(?:\.\d+)?", tag)
                    version = match.group(0) if match else "unknown"

                    rt = Runtime.create(
                        name="Python",
                        version=version,
                        path=path_obj,
                        manager="uv",
                        metadata={"tag": tag},
                    )
                    result.runtimes.append(rt)

        return result
