"""Contract tests verifying Lifecycle Adapters, capabilities, and safety bounds."""

import pytest

from inv.adapters.base import (
    AdapterSecurityError,
    AdapterUnsupportedError,
    validate_package_name,
    validate_version_spec,
)
from inv.adapters.homebrew import HomebrewAdapter
from inv.adapters.npm import NpmAdapter
from inv.adapters.pip import PipAdapter
from inv.adapters.registry import LifecycleRegistry
from inv.adapters.unsupported import ReadOnlyLifecycleAdapter
from inv.adapters.uv import UvAdapter


def test_package_name_validation() -> None:
    # Valid names
    assert validate_package_name("ripgrep") == "ripgrep"
    assert validate_package_name("@types/node") == "@types/node"
    assert validate_package_name("python-3.11") == "python-3.11"

    # Shell injection and metacharacters
    with pytest.raises(AdapterSecurityError):
        validate_package_name("pkg; rm -rf /")

    with pytest.raises(AdapterSecurityError):
        validate_package_name("pkg && echo pwned")

    with pytest.raises(AdapterSecurityError):
        validate_package_name("pkg`id`")

    with pytest.raises(AdapterSecurityError):
        validate_package_name("pkg$(whoami)")

    with pytest.raises(AdapterSecurityError):
        validate_package_name("../../../etc/passwd")

    with pytest.raises(AdapterSecurityError):
        validate_package_name("")


def test_version_spec_validation() -> None:
    assert validate_version_spec("1.2.3") == "1.2.3"
    assert validate_version_spec("2.0.0-rc.1") == "2.0.0-rc.1"
    assert validate_version_spec(None) is None

    with pytest.raises(AdapterSecurityError):
        validate_version_spec("1.0.0; rm -rf /")


def test_dry_run_never_executes_subprocesses() -> None:
    brew = HomebrewAdapter(is_cask=False)
    npm = NpmAdapter()
    uv = UvAdapter()

    res_brew = brew.install("ripgrep", dry_run=True)
    assert res_brew.exit_code == 0
    assert "[Dry Run]" in res_brew.stdout

    res_npm = npm.remove("typescript", dry_run=True)
    assert res_npm.exit_code == 0
    assert "[Dry Run]" in res_npm.stdout

    res_uv = uv.upgrade("ruff", dry_run=True)
    assert res_uv.exit_code == 0
    assert "[Dry Run]" in res_uv.stdout


def test_unsupported_adapter_refuses_operations() -> None:
    ro = ReadOnlyLifecycleAdapter("macports", "MacPorts", "port")
    assert ro.manager_id == "macports"
    assert ro.supported_capabilities == set()

    with pytest.raises(AdapterUnsupportedError) as exc_info:
        ro.install("pkg")
    assert "not supported" in str(exc_info.value).lower()

    with pytest.raises(AdapterUnsupportedError):
        ro.remove("pkg")

    with pytest.raises(AdapterUnsupportedError):
        ro.upgrade("pkg")


def test_pep668_system_python_protection() -> None:
    from pathlib import Path

    # Point PipAdapter to macOS system Python
    pip_adapter = PipAdapter(target_python=Path("/usr/bin/python3"))
    with pytest.raises(AdapterSecurityError) as exc_info:
        pip_adapter.install("malicious-pkg")
    assert "pep 668" in str(exc_info.value).lower()


def test_lifecycle_registry_ambiguity_handling() -> None:
    reg = LifecycleRegistry()
    assert reg.get("brew") is not None
    assert reg.get("npm") is not None
    assert reg.get("pip") is not None
    assert reg.get("uv") is not None

    with pytest.raises(ValueError) as exc_info:
        reg.resolve_manager_for_package("pkg", explicit_manager="unknown_manager_xyz")
    assert "unknown or unsupported" in str(exc_info.value).lower()
