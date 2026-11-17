"""Unit tests for InventoryReconciler."""

from pathlib import Path

from inv.constants import DependencyStatus
from inv.core.models import InstallationInstance, Project, ProjectDependency
from inv.core.reconciler import InventoryReconciler


def test_reconcile_dependencies() -> None:
    reconciler = InventoryReconciler()
    proj = Project.create(
        name="test-proj",
        path=Path("/tmp/test-proj"),
        project_types=["python"],
    )

    dep1 = ProjectDependency.create(
        project_id=proj.id,
        name="rich",
        status=DependencyStatus.UNVERIFIED,
        ecosystem="pip",
    )
    dep2 = ProjectDependency.create(
        project_id=proj.id,
        name="nonexistent-pkg",
        status=DependencyStatus.UNVERIFIED,
        ecosystem="pip",
    )

    inst = InstallationInstance.create(
        software_id="rich-id",
        name="rich",
        version="13.7.1",
        manager="pip",
    )

    reconciled = reconciler.reconcile_project_dependencies([proj], [dep1, dep2], [inst])
    assert len(reconciled) == 2
    r_map = {d.name: d.status for d in reconciled}
    assert r_map["rich"] == DependencyStatus.INSTALLED
    assert r_map["nonexistent-pkg"] == DependencyStatus.DECLARED

