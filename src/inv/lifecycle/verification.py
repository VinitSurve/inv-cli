"""Post-operation state verification logic."""

from inv.adapters.base import BaseLifecycleAdapter
from inv.constants import OperationType
from inv.lifecycle.models import LifecycleOperation


def verify_operation_outcome(operation: LifecycleOperation, adapter: BaseLifecycleAdapter) -> bool:
    """Verify system state reflects the completed operation."""
    pkg = operation.target_package
    expected_ver = operation.proposed_version

    if operation.operation_type in (
        OperationType.INSTALL,
        OperationType.UPGRADE,
        OperationType.AUDIT_FIX,
    ):
        return adapter.verify_installation(pkg, expected_version=expected_ver)

    if operation.operation_type == OperationType.REMOVE:
        # After removal, package should not be present
        is_still_installed = adapter.verify_installation(pkg)
        return not is_still_installed

    return True
