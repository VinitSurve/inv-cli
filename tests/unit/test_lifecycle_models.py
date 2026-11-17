"""Unit tests for lifecycle domain models."""

from inv.constants import InstallScope, OperationState, OperationType, RiskLevel, UpdateStrategy
from inv.lifecycle.models import (
    LifecycleOperation,
    OperationEvent,
    OutdatedPackage,
    PackageInfo,
)


def test_lifecycle_operation_create() -> None:
    op = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="ripgrep",
        manager="brew_formula",
        scope=InstallScope.GLOBAL,
        proposed_version="14.1.0",
        risk_level=RiskLevel.LOW,
        actions=["brew install ripgrep"],
    )
    assert op.id.startswith("op_")
    assert op.target_package == "ripgrep"
    assert op.status == OperationState.PLANNED
    assert op.risk_level == RiskLevel.LOW
    assert op.proposed_version == "14.1.0"
    assert len(op.actions) == 1
    assert not op.rollback_available

    d = op.to_dict()
    assert d["id"] == op.id
    assert d["target_package"] == "ripgrep"


def test_operation_event_create() -> None:
    event = OperationEvent.create(
        operation_id="op_12345",
        event_type="execution_started",
        message="Started installation",
        data={"step": 1},
    )
    assert event.id.startswith("evt_")
    assert event.operation_id == "op_12345"
    assert event.event_type == "execution_started"
    assert event.data["step"] == 1


def test_outdated_package_model() -> None:
    outdated = OutdatedPackage(
        name="ruff",
        manager="uv_tool",
        installed_version="0.3.0",
        latest_version="0.4.0",
        latest_stable_version="0.4.0",
        latest_compatible_version="0.3.5",
        update_strategy=UpdateStrategy.COMPATIBLE,
        is_major_update=False,
    )
    assert outdated.name == "ruff"
    assert outdated.installed_version == "0.3.0"
    assert not outdated.is_major_update
    assert outdated.to_dict()["latest_version"] == "0.4.0"


def test_package_info_model() -> None:
    info = PackageInfo(
        name="express",
        manager="npm",
        installed_version="4.18.2",
        latest_version="4.19.2",
        dependencies=["accepts", "bytes"],
        reverse_dependencies=["my-app"],
    )
    assert info.name == "express"
    assert len(info.dependencies) == 2
    assert len(info.reverse_dependencies) == 1
