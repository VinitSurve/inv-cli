"""Unit tests for user approval safety policy."""

import os
from unittest.mock import patch

import pytest

from inv.constants import OperationState, OperationType
from inv.lifecycle.approvals import (
    ModificationRefusedError,
    request_operation_approval,
)
from inv.lifecycle.models import LifecycleOperation


def test_approval_accepts_yes() -> None:
    op = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="test-pkg",
        manager="npm",
    )
    with patch.dict(os.environ, {"INV_FORCE_INTERACTIVE": "1"}):
        with patch("builtins.input", return_value="y"):
            approved = request_operation_approval(op)
            assert approved is True

        with patch("builtins.input", return_value="yes"):
            approved = request_operation_approval(op)
            assert approved is True


def test_approval_rejects_no_and_empty() -> None:
    op = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="test-pkg",
        manager="npm",
    )
    with (
        patch.dict(os.environ, {"INV_FORCE_INTERACTIVE": "1"}),
        patch("builtins.input", return_value="n"),
    ):
        approved = request_operation_approval(op)
        assert approved is False
        assert op.status == OperationState.CANCELLED

    op.status = OperationState.PLANNED
    with (
        patch.dict(os.environ, {"INV_FORCE_INTERACTIVE": "1"}),
        patch("builtins.input", return_value=""),
    ):
        approved = request_operation_approval(op)
        assert approved is False
        assert op.status == OperationState.CANCELLED


def test_approval_refuses_non_interactive_environment() -> None:
    op = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="test-pkg",
        manager="npm",
    )
    # Ensure non-interactive without authorization token
    with (
        patch.dict(os.environ, {"INV_FORCE_INTERACTIVE": "0"}, clear=True),
        patch("sys.stdin.isatty", return_value=False),
        pytest.raises(ModificationRefusedError) as exc_info,
    ):
        request_operation_approval(op)
    assert "non-interactive" in str(exc_info.value).lower()
    assert op.status == OperationState.CANCELLED


def test_approval_rejects_already_approved_or_executed_plan() -> None:
    op = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="test-pkg",
        manager="npm",
    )
    op.status = OperationState.COMPLETED
    with pytest.raises(ModificationRefusedError):
        request_operation_approval(op)
