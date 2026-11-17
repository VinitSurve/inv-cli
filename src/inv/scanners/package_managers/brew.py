"""Homebrew formulae and casks scanner."""

import json

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class BrewFormulaScanner(BaseScanner):
    """Scanner for Homebrew installed formulae."""

    @property
    def scanner_id(self) -> str:
        return "brew_formula"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Homebrew Formulae"

    def is_available(self) -> bool:
        return find_executable("brew") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        brew_bin = find_executable("brew") or "brew"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        # Attempt structured json inspection first
        cmd = [brew_bin, "info", "--json=v2", "--installed"]
        res = run_command(cmd, timeout=context.config.process_timeout)

        if res.success and res.stdout.strip():
            try:
                data = json.loads(res.stdout)
                formulae = data.get("formulae", [])
                for f in formulae:
                    name = f.get("name", "")
                    if not name:
                        continue
                    desc = f.get("desc")
                    homepage = f.get("homepage")
                    lic = f.get("license")

                    ident = SoftwareIdentity.create(
                        name=name,
                        ecosystem="brew",
                        description=desc,
                        homepage=homepage,
                        license=lic,
                    )
                    result.identities.append(ident)

                    installed_entries = f.get("installed", [])
                    if installed_entries:
                        for inst in installed_entries:
                            ver = inst.get("version", "unknown")
                            cellar_path = None
                            if "installed_as_dependency" in inst:
                                # Cellar paths are under /opt/homebrew/Cellar or /usr/local/Cellar
                                pass
                            inst_obj = InstallationInstance.create(
                                software_id=ident.id,
                                name=name,
                                version=ver,
                                manager="brew_formula",
                                install_path=cellar_path,
                                scope=InstallScope.GLOBAL,
                                provenance="brew info --json=v2",
                                metadata={"tap": f.get("tap"), "pinned": f.get("pinned", False)},
                            )
                            result.installations.append(inst_obj)
                    else:
                        stable_ver = f.get("versions", {}).get("stable", "unknown")
                        inst_obj = InstallationInstance.create(
                            software_id=ident.id,
                            name=name,
                            version=stable_ver,
                            manager="brew_formula",
                            scope=InstallScope.GLOBAL,
                            provenance="brew info --json=v2",
                        )
                        result.installations.append(inst_obj)
                return result
            except json.JSONDecodeError:
                result.warnings.append(
                    "Failed to parse brew info JSON output; falling back to tabular list."
                )

        # Fallback to tabular syntax: brew list --formula --versions
        fb_cmd = [brew_bin, "list", "--formula", "--versions"]
        fb_res = run_command(fb_cmd, timeout=context.config.process_timeout)
        if not fb_res.success:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to list brew formulae: {fb_res.stderr}")
            return result

        for line in fb_res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            versions = parts[1:] if len(parts) > 1 else ["unknown"]
            ident = SoftwareIdentity.create(name=name, ecosystem="brew")
            result.identities.append(ident)
            for v in versions:
                inst_obj = InstallationInstance.create(
                    software_id=ident.id,
                    name=name,
                    version=v,
                    manager="brew_formula",
                    scope=InstallScope.GLOBAL,
                    provenance="brew list --formula --versions",
                )
                result.installations.append(inst_obj)

        return result


class BrewCaskScanner(BaseScanner):
    """Scanner for Homebrew installed casks (macOS GUI apps / binary packages)."""

    @property
    def scanner_id(self) -> str:
        return "brew_cask"

    @property
    def domain(self) -> str:
        return "package_manager"

    @property
    def name(self) -> str:
        return "Homebrew Casks"

    def is_available(self) -> bool:
        return find_executable("brew") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        brew_bin = find_executable("brew") or "brew"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [brew_bin, "list", "--cask", "--versions"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"Failed to list brew casks: {res.stderr}")
            return result

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            version = parts[1] if len(parts) > 1 else "latest"
            ident = SoftwareIdentity.create(name=name, ecosystem="brew_cask")
            result.identities.append(ident)
            inst_obj = InstallationInstance.create(
                software_id=ident.id,
                name=name,
                version=version,
                manager="brew_cask",
                scope=InstallScope.GLOBAL,
                provenance="brew list --cask --versions",
            )
            result.installations.append(inst_obj)

        return result
