"""Security tests for package lifecycle operations, boundaries, and tamper resistance."""

from pathlib import Path

import pytest

from inv.adapters.base import AdapterSecurityError
from inv.adapters.pip import PipAdapter
from inv.constants import OperationState, OperationType
from inv.lifecycle.executor import LifecycleExecutor
from inv.lifecycle.models import LifecycleOperation
from inv.lifecycle.planner import LifecyclePlanner
from inv.storage.repositories import InventoryRepository


def test_command_injection_prevented_in_adapter_planning(mock_repo: InventoryRepository) -> None:
    planner = LifecyclePlanner(mock_repo)

    # Injections via package names must fail early in validation
    with pytest.raises(AdapterSecurityError):
        planner.plan_install("pkg; cat /etc/passwd", manager="npm")

    with pytest.raises(AdapterSecurityError):
        planner.plan_remove("pkg | rm -rf ~", manager="brew")

    with pytest.raises(AdapterSecurityError):
        planner.plan_upgrade("pkg`whoami`", manager="uv")


def test_executor_refuses_unapproved_plan(mock_repo: InventoryRepository) -> None:
    executor = LifecycleExecutor(mock_repo)
    plan = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="test-pkg",
        manager="npm",
    )
    # Plan is in PLANNED state, not APPROVED
    assert plan.status == OperationState.PLANNED
    with pytest.raises(RuntimeError) as exc_info:
        executor.execute(plan, dry_run=False)
    assert "must be 'approved'" in str(exc_info.value).lower()


def test_pep668_blocks_unauthorized_system_modifications() -> None:
    adapter = PipAdapter(
        target_python=Path(
            "/System/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
        )
    )
    with pytest.raises(AdapterSecurityError) as exc_info:
        adapter.install("some-package")
    assert "pep 668" in str(exc_info.value).lower()
