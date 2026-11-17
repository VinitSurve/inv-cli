"""Conda environments and packages scanner."""

import json
from pathlib import Path

from inv.constants import EnvironmentType, InstallScope
from inv.core.models import Environment, InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class CondaScanner(BaseScanner):
    """Scanner for Conda environments and installed packages."""

    @property
    def scanner_id(self) -> str:
        return "conda"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Conda"

    def is_available(self) -> bool:
        return find_executable("conda") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        conda_bin = find_executable("conda") or "conda"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        # 1. Discover environments: conda env list --json
        res_envs = run_command(
            [conda_bin, "env", "list", "--json"], timeout=context.config.process_timeout
        )
        if res_envs.success and res_envs.stdout.strip():
            try:
                env_data = json.loads(res_envs.stdout)
                for env_path_str in env_data.get("envs", []):
                    env_path = Path(env_path_str)
                    name = env_path.name
                    env_obj = Environment.create(
                        name=name,
                        env_type=EnvironmentType.CONDA,
                        path=env_path,
                    )
                    result.environments.append(env_obj)
            except Exception as exc:
                result.warnings.append(f"Failed to parse conda env list: {exc}")

        # 2. Discover packages in base/active environment: conda list --json
        res_pkgs = run_command(
            [conda_bin, "list", "--json"], timeout=context.config.process_timeout
        )
        if res_pkgs.success and res_pkgs.stdout.strip():
            try:
                pkg_data = json.loads(res_pkgs.stdout)
                for item in pkg_data:
                    name = item.get("name", "")
                    ver = item.get("version", "unknown")
                    channel = item.get("channel", "conda")
                    if not name:
                        continue

                    ident = SoftwareIdentity.create(name=name, ecosystem="conda")
                    result.identities.append(ident)

                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=ver,
                        manager="conda",
                        scope=InstallScope.GLOBAL,
                        provenance=f"conda ({channel})",
                        metadata={"build_string": item.get("build_string"), "channel": channel},
                    )
                    result.installations.append(inst)
            except Exception as exc:
                result.warnings.append(f"Failed to parse conda list packages: {exc}")

        return result
