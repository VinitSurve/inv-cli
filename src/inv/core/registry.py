"""Scanner registration and lifecycle registry."""

from inv.scanners.applications.apps import ApplicationScanner
from inv.scanners.base import BaseScanner
from inv.scanners.binaries.path import PathBinaryScanner
from inv.scanners.containers.docker import DockerScanner
from inv.scanners.environments.envs import EnvironmentScanner
from inv.scanners.extensions.ide import IdeExtensionScanner
from inv.scanners.package_managers.brew import BrewCaskScanner, BrewFormulaScanner
from inv.scanners.package_managers.bun import BunGlobalScanner
from inv.scanners.package_managers.cargo import CargoScanner
from inv.scanners.package_managers.composer import ComposerScanner
from inv.scanners.package_managers.conda import CondaScanner
from inv.scanners.package_managers.gem import GemScanner
from inv.scanners.package_managers.go import GoToolsScanner
from inv.scanners.package_managers.macports import MacPortsScanner
from inv.scanners.package_managers.npm import NpmGlobalScanner
from inv.scanners.package_managers.pip import PipScanner
from inv.scanners.package_managers.pnpm import PnpmGlobalScanner
from inv.scanners.package_managers.uv import UvScanner
from inv.scanners.package_managers.yarn import YarnGlobalScanner
from inv.scanners.projects.projects import ProjectsScanner
from inv.scanners.runtimes.runtimes import RuntimeScanner
from inv.scanners.system.macos import MacOSSystemScanner
from inv.scanners.system.receipts import PkgutilReceiptScanner


class ScannerRegistry:
    """Registry maintaining all available scanner implementations."""

    def __init__(self) -> None:
        self._scanners: dict[str, BaseScanner] = {}
        self._register_default_scanners()

    def register(self, scanner: BaseScanner) -> None:
        """Register a scanner instance."""
        self._scanners[scanner.scanner_id] = scanner

    def get(self, scanner_id: str) -> BaseScanner | None:
        """Get scanner by its identifier."""
        return self._scanners.get(scanner_id)

    def list_all(self) -> list[BaseScanner]:
        """List all registered scanners."""
        return list(self._scanners.values())

    def list_by_domain(self, domain: str) -> list[BaseScanner]:
        """List scanners belonging to a specific domain."""
        return [s for s in self._scanners.values() if s.domain == domain]

    def _register_default_scanners(self) -> None:
        """Register all built-in scanners."""
        default_scanners: list[BaseScanner] = [
            # System
            MacOSSystemScanner(),
            PkgutilReceiptScanner(),
            # Package Managers
            BrewFormulaScanner(),
            BrewCaskScanner(),
            MacPortsScanner(),
            NpmGlobalScanner(),
            PnpmGlobalScanner(),
            YarnGlobalScanner(),
            BunGlobalScanner(),
            PipScanner(),
            UvScanner(),
            CondaScanner(),
            CargoScanner(),
            GemScanner(),
            ComposerScanner(),
            GoToolsScanner(),
            # Binaries
            PathBinaryScanner(),
            # Applications
            ApplicationScanner(),
            # Runtimes & Environments
            RuntimeScanner(),
            EnvironmentScanner(),
            # Projects
            ProjectsScanner(),
            # Containers
            DockerScanner(),
            # Extensions
            IdeExtensionScanner(),
        ]
        for s in default_scanners:
            self.register(s)

