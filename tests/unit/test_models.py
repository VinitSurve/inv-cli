"""Unit tests for core models."""

from pathlib import Path

from inv.constants import DependencyStatus, EnvironmentType, InstallScope
from inv.core.models import (
    Application,
    Environment,
    ExecutableInstance,
    InstallationInstance,
    Project,
    ProjectDependency,
    Runtime,
    SoftwareIdentity,
    make_deterministic_id,
)


def test_deterministic_id() -> None:
    id1 = make_deterministic_id("brew", "ffmpeg")
    id2 = make_deterministic_id("brew", "ffmpeg")
    id3 = make_deterministic_id("npm", "ffmpeg")
    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16


def test_software_identity_creation() -> None:
    ident = SoftwareIdentity.create(
        name="Python",
        ecosystem="brew",
        description="Interpreted high-level programming language",
        homepage="https://www.python.org",
        license="PSF-2.0",
    )
    assert ident.canonical_name == "python"
    assert ident.ecosystem == "brew"
    d = ident.to_dict()
    assert d["name"] == "Python"
    assert d["license"] == "PSF-2.0"


def test_installation_instance_creation() -> None:
    inst = InstallationInstance.create(
        software_id="ident-123",
        name="ripgrep",
        version="14.1.0",
        manager="brew_formula",
        install_path=Path("/opt/homebrew/bin/rg"),
        scope=InstallScope.GLOBAL,
    )
    assert inst.name == "ripgrep"
    assert inst.version == "14.1.0"
    assert inst.manager == "brew_formula"
    d = inst.to_dict()
    assert d["scope"] == "global"
    assert d["install_path"] == "/opt/homebrew/bin/rg"


def test_executable_instance_creation() -> None:
    exe = ExecutableInstance.create(
        name="python3",
        path=Path("/usr/local/bin/python3"),
        canonical_path=Path("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"),
        is_symlink=True,
        version="3.11.7",
        source_manager="python.org",
    )
    assert exe.is_symlink is True
    assert exe.version == "3.11.7"
    assert exe.is_duplicate is False
    d = exe.to_dict()
    assert d["name"] == "python3"
    assert d["canonical_path"].endswith("python3")


def test_project_and_dependency_models() -> None:
    proj = Project.create(
        name="my-app",
        path=Path("/tmp/my-app"),
        project_types=["python", "node"],
        root_manifest=Path("/tmp/my-app/pyproject.toml"),
        has_lockfile=True,
    )
    assert proj.name == "my-app"
    assert "node" in proj.project_types
    assert proj.has_lockfile is True

    dep = ProjectDependency.create(
        project_id=proj.id,
        name="typer",
        declared_spec=">=0.9.0",
        status=DependencyStatus.INSTALLED,
        is_dev=False,
        ecosystem="python",
    )
    assert dep.name == "typer"
    assert dep.status == DependencyStatus.INSTALLED
    d = dep.to_dict()
    assert d["status"] == "installed"


def test_application_model() -> None:
    app = Application.create(
        name="Visual Studio Code",
        path=Path("/Applications/Visual Studio Code.app"),
        bundle_id="com.microsoft.VSCode",
        version="1.87.0",
        is_system=False,
    )
    assert app.name == "Visual Studio Code"
    assert app.bundle_id == "com.microsoft.VSCode"
    assert app.is_system is False


def test_environment_and_runtime_models() -> None:
    env = Environment.create(
        name="test-env",
        env_type=EnvironmentType.VENV,
        path=Path("/tmp/test-env"),
        runtime_version="3.11.7",
        is_active=True,
    )
    assert env.env_type == EnvironmentType.VENV
    assert env.is_active is True

    rt = Runtime.create(
        name="Node.js",
        version="20.11.0",
        path=Path("/usr/local/bin/node"),
        manager="nvm",
    )
    assert rt.name == "Node.js"
    assert rt.manager == "nvm"
