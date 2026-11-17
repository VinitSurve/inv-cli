"""macOS installer receipts scanner via pkgutil."""

from inv.constants import InstallScope, ScannerStatus
from inv.core.models import InstallationInstance, SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class PkgutilReceiptScanner(BaseScanner):
    """Scanner for macOS installer receipts via pkgutil.

    Important: Installer receipts represent installation history and must not be
    treated as definitive proof that the software is currently present.
    """

    @property
    def scanner_id(self) -> str:
        return "installer_receipts"

    @property
    def domain(self) -> str:
        return "system"

    @property
    def name(self) -> str:
        return "macOS Installer Receipts"

    def is_available(self) -> bool:
        return find_executable("pkgutil") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        pkgutil_bin = find_executable("pkgutil") or "/usr/sbin/pkgutil"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        cmd = [pkgutil_bin, "--pkgs"]
        res = run_command(cmd, timeout=context.config.process_timeout)
        if not res.success:
            result.status = ScannerStatus.FAILED
            result.errors.append(f"pkgutil --pkgs failed: {res.stderr}")
            return result

        # Collect receipts up to a sensible limit to avoid flooding if tens of thousands
        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        max_receipts = 2000 if not context.deep else 10000

        for pkg_id in lines[:max_receipts]:
            ident = SoftwareIdentity.create(name=pkg_id, ecosystem="macos_pkg")
            result.identities.append(ident)
            inst = InstallationInstance.create(
                software_id=ident.id,
                name=pkg_id,
                version="receipt",
                manager="pkgutil",
                scope=InstallScope.SYSTEM,
                provenance="pkgutil --pkgs (installer receipt)",
                metadata={"is_receipt_only": True},
            )
            result.installations.append(inst)

        return result

