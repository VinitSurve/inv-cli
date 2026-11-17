"""Operation planning engine for package installation, removal, and updates."""

from inv.adapters.registry import LifecycleRegistry
from inv.constants import (
    InstallScope,
    LifecycleCapability,
    OperationType,
    RiskLevel,
    UpdateStrategy,
)
from inv.core.dependency_graph import DependencyGraph
from inv.lifecycle.models import LifecycleOperation
from inv.lifecycle.rollback import assess_rollback_capability
from inv.storage.repositories import InventoryRepository


class LifecyclePlanner:
    """Calculates modification plans, risk assessments, and impact analyses."""

    def __init__(
        self,
        repo: InventoryRepository,
        registry: LifecycleRegistry | None = None,
        session_id: str | None = None,
    ) -> None:
        self.repo = repo
        self.registry = registry or LifecycleRegistry()
        self.session_id = session_id
        self.graph = DependencyGraph(repo, session_id=session_id)

    def plan_install(
        self,
        package: str,
        version: str | None = None,
        manager: str | None = None,
        scope: InstallScope = InstallScope.GLOBAL,
    ) -> LifecycleOperation:
        """Plan a package installation operation."""
        adapter = self.registry.resolve_manager_for_package(
            package_name=package,
            explicit_manager=manager,
            repo=self.repo,
            session_id=self.session_id,
        )
        adapter.ensure_capability(LifecycleCapability.INSTALL)

        info = adapter.get_package_info(package)
        proposed_ver = version or (info.latest_stable_version if info else None)

        actions = [
            f"Invoke {adapter.display_name} to install {package}"
            + (f" at version {proposed_ver}" if proposed_ver else "")
        ]

        # Determine risk
        risk_level = RiskLevel.LOW
        risk_reasons = []
        if info and info.installed_version:
            risk_level = RiskLevel.MEDIUM
            risk_reasons.append(
                f"Package is already installed at version {info.installed_version}."
            )

        op = LifecycleOperation.create(
            operation_type=OperationType.INSTALL,
            target_package=package,
            manager=adapter.manager_id,
            scope=scope,
            target_version=version,
            previous_version=info.installed_version if info else None,
            proposed_version=proposed_ver,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            actions=actions,
            dependency_changes=info.dependencies if info else [],
            reverse_dependencies=[],
        )

        rollback_avail, rollback_inst = assess_rollback_capability(op, adapter)
        op.rollback_available = rollback_avail
        op.rollback_instructions = rollback_inst
        return op

    def plan_remove(
        self,
        package: str,
        manager: str | None = None,
        scope: InstallScope = InstallScope.GLOBAL,
    ) -> LifecycleOperation:
        """Plan a package removal operation with reverse dependency analysis."""
        adapter = self.registry.resolve_manager_for_package(
            package_name=package,
            explicit_manager=manager,
            repo=self.repo,
            session_id=self.session_id,
        )
        adapter.ensure_capability(LifecycleCapability.REMOVE)

        impact = self.graph.analyze_removal_impact(package, manager=adapter.manager_id)
        info = adapter.get_package_info(package)
        installed_ver = impact.installed_version or (info.installed_version if info else None)

        actions = [f"Invoke {adapter.display_name} to uninstall package {package}"]

        op = LifecycleOperation.create(
            operation_type=OperationType.REMOVE,
            target_package=package,
            manager=adapter.manager_id,
            scope=scope,
            previous_version=installed_ver,
            proposed_version=None,
            risk_level=impact.risk_level,
            risk_reasons=impact.risk_reasons,
            actions=actions,
            dependency_changes=[],
            reverse_dependencies=impact.reverse_dependencies,
        )

        rollback_avail, rollback_inst = assess_rollback_capability(op, adapter)
        op.rollback_available = rollback_avail
        op.rollback_instructions = rollback_inst
        return op

    def plan_upgrade(
        self,
        package: str,
        version: str | None = None,
        strategy: UpdateStrategy = UpdateStrategy.COMPATIBLE,
        manager: str | None = None,
        scope: InstallScope = InstallScope.GLOBAL,
    ) -> LifecycleOperation:
        """Plan a package upgrade with version compatibility analysis."""
        adapter = self.registry.resolve_manager_for_package(
            package_name=package,
            explicit_manager=manager,
            repo=self.repo,
            session_id=self.session_id,
        )
        adapter.ensure_capability(LifecycleCapability.UPGRADE)

        info = adapter.get_package_info(package)
        installed_ver = info.installed_version if info else None
        proposed_ver = version or (info.latest_stable_version if info else None)

        risk_level = RiskLevel.LOW
        risk_reasons = []

        # Check for major version transition
        if installed_ver and proposed_ver:
            try:
                curr_major = int(installed_ver.split(".")[0])
                new_major = int(proposed_ver.split(".")[0])
                if new_major > curr_major:
                    risk_level = RiskLevel.HIGH
                    risk_reasons.append(
                        f"Major version upgrade from {installed_ver} to {proposed_ver}. Potential breaking changes."
                    )
            except (ValueError, IndexError):
                pass

        revs = self.graph.get_reverse_dependencies(package)
        if revs:
            if risk_level != RiskLevel.HIGH:
                risk_level = RiskLevel.MEDIUM
            risk_reasons.append(f"Package is required by {len(revs)} installed packages.")

        actions = [
            f"Invoke {adapter.display_name} to upgrade {package}"
            + (f" to {proposed_ver}" if proposed_ver else "")
        ]

        op = LifecycleOperation.create(
            operation_type=OperationType.UPGRADE,
            target_package=package,
            manager=adapter.manager_id,
            scope=scope,
            target_version=version,
            previous_version=installed_ver,
            proposed_version=proposed_ver,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            actions=actions,
            dependency_changes=[],
            reverse_dependencies=revs,
        )

        rollback_avail, rollback_inst = assess_rollback_capability(op, adapter)
        op.rollback_available = rollback_avail
        op.rollback_instructions = rollback_inst
        return op

    def plan_batch_upgrade(
        self,
        strategy: UpdateStrategy = UpdateStrategy.COMPATIBLE,
        manager: str | None = None,
    ) -> list[LifecycleOperation]:
        """Generate upgrade plans for all outdated packages."""
        outdated_pkgs = self.repo.list_outdated_packages(
            manager=manager, session_id=self.session_id
        )
        plans = []
        for pkg in outdated_pkgs:
            target_ver = (
                pkg.latest_compatible_version
                if strategy == UpdateStrategy.COMPATIBLE
                else pkg.latest_version
            )
            try:
                plan = self.plan_upgrade(
                    package=pkg.name,
                    version=target_ver,
                    strategy=strategy,
                    manager=pkg.manager,
                )
                plans.append(plan)
            except Exception:
                pass
        return plans
