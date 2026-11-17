"""Reconciliation engine for inventory entities and project dependencies."""

from inv.constants import DependencyStatus
from inv.core.models import (
    InstallationInstance,
    Project,
    ProjectDependency,
)


class InventoryReconciler:
    """Reconciles discovered raw scanner items into coherent domain models."""

    def reconcile_project_dependencies(
        self,
        projects: list[Project],
        dependencies: list[ProjectDependency],
        global_installations: list[InstallationInstance],
    ) -> list[ProjectDependency]:
        """Verify unverified dependencies against available installation sources."""
        # Index global packages by ecosystem and lowercase name
        installed_map: set[str] = {
            f"{inst.manager}:{inst.name.lower()}" for inst in global_installations
        }

        reconciled: list[ProjectDependency] = []
        for dep in dependencies:
            if dep.status == DependencyStatus.UNVERIFIED:
                key = f"{dep.ecosystem}:{dep.name.lower()}"
                if key in installed_map:
                    dep.status = DependencyStatus.INSTALLED
                else:
                    dep.status = DependencyStatus.DECLARED
            reconciled.append(dep)

        return reconciled
