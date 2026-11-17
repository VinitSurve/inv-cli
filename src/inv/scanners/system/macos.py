"""macOS system environment and platform scanner."""

import platform
import sys

from inv.core.models import SoftwareIdentity
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class MacOSSystemScanner(BaseScanner):
    """Scanner for macOS system version and base OS platform properties."""

    @property
    def scanner_id(self) -> str:
        return "macos_system"

    @property
    def domain(self) -> str:
        return "system"

    @property
    def name(self) -> str:
        return "macOS System Information"

    def is_available(self) -> bool:
        return sys.platform == "darwin"

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        os_version = platform.mac_ver()[0]
        arch = platform.machine()

        # Check sw_vers for build version
        build_id = ""
        sw_vers_bin = find_executable("sw_vers")
        if sw_vers_bin:
            res_sw = run_command(
                [sw_vers_bin, "-buildVersion"], timeout=context.config.process_timeout
            )
            if res_sw.success:
                build_id = res_sw.stdout.strip()

        # Check SIP status safely
        sip_status = "unknown"
        csrutil_bin = find_executable("csrutil")
        if csrutil_bin:
            res_csr = run_command([csrutil_bin, "status"], timeout=context.config.process_timeout)
            if res_csr.success:
                sip_status = "enabled" if "enabled" in res_csr.stdout.lower() else "disabled"

        ident = SoftwareIdentity.create(
            name=f"macOS {os_version}",
            ecosystem="system",
            description=f"Apple macOS Darwin ({arch}, build {build_id}, SIP {sip_status})",
        )
        result.identities.append(ident)

        return result
