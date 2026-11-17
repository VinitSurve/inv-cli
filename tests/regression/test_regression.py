"""Regression tests for edge cases, multi-version identity, and monorepos."""

from pathlib import Path

from inv.constants import DependencyStatus
from inv.core.models import (
    InstallationInstance,
    Project,
    ProjectDependency,
    SoftwareIdentity,
)
from inv.core.reconciler import InventoryReconciler
from inv.discovery.manifests import parse_manifest


def test_multiple_versions_identities_distinct() -> None:
    # Multiple installations of python must have unique installation IDs
    ident = SoftwareIdentity.create(name="python", ecosystem="brew")
    inst1 = InstallationInstance.create(
        software_id=ident.id,
        name="python@3.11",
        version="3.11.8",
        manager="brew_formula",
        install_path=Path("/opt/homebrew/Cellar/python@3.11/3.11.8"),
    )
    inst2 = InstallationInstance.create(
        software_id=ident.id,
        name="python@3.12",
        version="3.12.2",
        manager="brew_formula",
        install_path=Path("/opt/homebrew/Cellar/python@3.12/3.12.2"),
    )

    assert inst1.id != inst2.id
    assert inst1.version != inst2.version


def test_mixed_language_monorepo(temp_dir: Path) -> None:
    # Monorepo with package.json and pyproject.toml in same root
    (temp_dir / "package.json").write_text(
        '{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8"
    )
    (temp_dir / "pyproject.toml").write_text(
        '[project]\nname="backend"\ndependencies=["fastapi>=0.100.0"]', encoding="utf-8"
    )

    js_deps = parse_manifest(temp_dir / "package.json")
    py_deps = parse_manifest(temp_dir / "pyproject.toml")

    assert len(js_deps) == 1
    assert js_deps[0].ecosystem == "npm"
    assert len(py_deps) == 1
    assert py_deps[0].ecosystem == "python"


def test_missing_vs_installed_dependencies() -> None:
    reconciler = InventoryReconciler()
    proj = Project.create(
        name="my-proj",
        path=Path("/tmp/my-proj"),
        project_types=["python"],
    )

    dep_installed = ProjectDependency.create(
        project_id=proj.id,
        name="flask",
        status=DependencyStatus.UNVERIFIED,
        ecosystem="pip",
    )
    dep_missing = ProjectDependency.create(
        project_id=proj.id,
        name="nonexistent-lib-xyz",
        status=DependencyStatus.UNVERIFIED,
        ecosystem="pip",
    )

    global_inst = [
        InstallationInstance.create(
            software_id="s1",
            name="flask",
            version="3.0.0",
            manager="pip",
        )
    ]

    reconciled = reconciler.reconcile_project_dependencies(
        [proj], [dep_installed, dep_missing], global_inst
    )
    status_map = {d.name: d.status for d in reconciled}
    assert status_map["flask"] == DependencyStatus.INSTALLED
    assert status_map["nonexistent-lib-xyz"] == DependencyStatus.DECLARED
