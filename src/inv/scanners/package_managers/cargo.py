"""Cargo packages and Rust toolchains scanner."""

import re
from pathlib import Path

from inv.constants import EnvironmentType, InstallScope
from inv.core.models import Environment, InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class CargoScanner(BaseScanner):
    """Scanner for Cargo installed crates and Rust toolchains."""

    @property
    def scanner_id(self) -> str:
        return "cargo"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Cargo & Rust Toolchains"

    def is_available(self) -> bool:
        return find_executable("cargo") is not None or find_executable("rustup") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        cargo_bin = find_executable("cargo") or "cargo"
        rustup_bin = find_executable("rustup") or "rustup"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        # 1. Cargo install --list
        res_cargo = run_command(
            [cargo_bin, "install", "--list"], timeout=context.config.process_timeout
        )
        if res_cargo.success and res_cargo.stdout.strip():
            # Lines like: package v1.0.0 (path/url):
            crate_pattern = re.compile(
                r"^([a-zA-Z0-9_\-\.]+)\s+v?([0-9\.\-]+(?:[a-zA-Z0-9\.\-]+)?):"
            )
            for line in res_cargo.stdout.splitlines():
                line = line.strip()
                match = crate_pattern.match(line)
                if match:
                    name = match.group(1)
                    version = match.group(2)
                    ident = SoftwareIdentity.create(name=name, ecosystem="cargo")
                    result.identities.append(ident)
                    inst = InstallationInstance.create(
                        software_id=ident.id,
                        name=name,
                        version=version,
                        manager="cargo",
                        scope=InstallScope.USER,
                        provenance="cargo install --list",
                    )
                    result.installations.append(inst)

        # 2. Rustup toolchains
        if find_executable("rustup"):
            res_rustup = run_command(
                [rustup_bin, "toolchain", "list"], timeout=context.config.process_timeout
            )
            if res_rustup.success:
                for line in res_rustup.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    tc_name = parts[0]
                    is_active = "(active" in line
                    env_obj = Environment.create(
                        name=tc_name,
                        env_type=EnvironmentType.RUSTUP,
                        path=Path.home() / ".rustup" / "toolchains" / tc_name,
                        is_active=is_active,
                    )
                    result.environments.append(env_obj)

        return result
