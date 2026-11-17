"""Dependency graph construction and reverse dependency impact analysis."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from inv.constants import RiskLevel
from inv.storage.repositories import InventoryRepository


@dataclass
class DependencyImpact:
    """Assessment of the impact of removing or upgrading a package."""

    package_name: str
    manager: str
    is_directly_installed: bool
    installed_version: str | None
    direct_dependencies: list[str] = field(default_factory=list)
    reverse_dependencies: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reasons: list[str] = field(default_factory=list)
    can_safely_remove: bool = True


class DependencyGraph:
    """Maintains package relationship graphs and computes reverse dependencies."""

    def __init__(self, repo: InventoryRepository, session_id: str | None = None) -> None:
        self.repo = repo
        self.session_id = session_id
        # package -> set of packages it depends on
        self._forward_deps: dict[str, set[str]] = defaultdict(set)
        # package -> set of packages that depend on it
        self._reverse_deps: dict[str, set[str]] = defaultdict(set)
        # package name -> manager name
        self._package_managers: dict[str, str] = {}
        # package name -> installed version
        self._package_versions: dict[str, str] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Construct graph from installations and project dependencies in the repository."""
        # 1. Installations
        insts = self.repo.list_installations(self.session_id)
        for inst in insts:
            norm_name = inst.name.lower()
            self._package_managers[norm_name] = inst.manager
            self._package_versions[norm_name] = inst.version
            if inst.metadata:
                deps = inst.metadata.get("dependencies", [])
                for d in deps:
                    norm_dep = d.lower()
                    self._forward_deps[norm_name].add(norm_dep)
                    self._reverse_deps[norm_dep].add(norm_name)

        # 2. Project dependencies
        proj_deps = self.repo.list_project_dependencies(session_id=self.session_id)
        for pd in proj_deps:
            norm_name = pd.name.lower()
            if norm_name not in self._package_managers:
                self._package_managers[norm_name] = pd.ecosystem
            if pd.resolved_version:
                self._package_versions[norm_name] = pd.resolved_version

    def get_dependencies(self, package_name: str) -> list[str]:
        """Get list of packages that package_name depends on."""
        return sorted(self._forward_deps.get(package_name.lower(), set()))

    def get_reverse_dependencies(self, package_name: str) -> list[str]:
        """Get list of installed packages that depend on package_name."""
        return sorted(self._reverse_deps.get(package_name.lower(), set()))

    def get_why(self, package_name: str) -> dict[str, Any]:
        """Explain why a package is installed in the system/projects."""
        norm = package_name.lower()
        mgr = self._package_managers.get(norm, "unknown")
        ver = self._package_versions.get(norm, "unknown")
        revs = self.get_reverse_dependencies(norm)
        fwds = self.get_dependencies(norm)

        explanation = []
        if revs:
            explanation.append(f"Required by {len(revs)} installed packages: {', '.join(revs[:5])}")
        else:
            explanation.append("Directly installed or standalone top-level package.")

        return {
            "name": package_name,
            "manager": mgr,
            "installed_version": ver,
            "reverse_dependencies": revs,
            "dependencies": fwds,
            "explanation": explanation,
        }

    def analyze_removal_impact(
        self, package_name: str, manager: str | None = None
    ) -> DependencyImpact:
        """Analyze risks and impact of removing a package."""
        norm = package_name.lower()
        installed_ver = self._package_versions.get(norm)
        pkg_manager = manager or self._package_managers.get(norm, "unknown")
        revs = self.get_reverse_dependencies(norm)
        fwds = self.get_dependencies(norm)

        risk_level = RiskLevel.LOW
        risk_reasons = []
        can_safely_remove = True

        if revs:
            risk_level = RiskLevel.HIGH
            risk_reasons.append(
                f"Package is required by {len(revs)} other package(s): {', '.join(revs[:5])}"
            )
            can_safely_remove = False

        # System or critical packages
        critical_packages = {
            "python",
            "python3",
            "node",
            "npm",
            "git",
            "openssl",
            "glib",
            "bash",
            "zsh",
            "coreutils",
            "curl",
            "sqlite",
        }
        if norm in critical_packages:
            risk_level = RiskLevel.CRITICAL
            risk_reasons.append("Package is a core system runtime or shared foundation library.")
            can_safely_remove = False

        return DependencyImpact(
            package_name=package_name,
            manager=pkg_manager,
            is_directly_installed=installed_ver is not None,
            installed_version=installed_ver,
            direct_dependencies=fwds,
            reverse_dependencies=revs,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            can_safely_remove=can_safely_remove,
        )
