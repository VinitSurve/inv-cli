"""Execution engine for approved lifecycle modification operations."""

from datetime import UTC, datetime

from inv.adapters.registry import LifecycleRegistry
from inv.constants import OperationState, OperationType
from inv.lifecycle.models import LifecycleOperation, OperationEvent
from inv.lifecycle.verification import verify_operation_outcome
from inv.storage.repositories import InventoryRepository


class LifecycleExecutor:
    """Executes approved package operations with auditing and verification."""

    def __init__(
        self,
        repo: InventoryRepository,
        registry: LifecycleRegistry | None = None,
    ) -> None:
        self.repo = repo
        self.registry = registry or LifecycleRegistry()

    def execute(self, operation: LifecycleOperation, dry_run: bool = False) -> LifecycleOperation:
        """Execute an operation that has received explicit user approval."""
        if operation.status != OperationState.APPROVED and not dry_run:
            raise RuntimeError(
                f"Cannot execute operation {operation.id} in state '{operation.status.value}'. Must be 'approved'."
            )

        adapter = self.registry.get(operation.manager)
        if not adapter:
            operation.status = OperationState.FAILED
            operation.logs.append(f"Lifecycle adapter for '{operation.manager}' is unavailable.")
            self.repo.save_lifecycle_operation(operation)
            return operation

        now_iso = datetime.now(UTC).isoformat()
        operation.status = OperationState.EXECUTING
        operation.executed_at = now_iso
        self.repo.save_lifecycle_operation(operation)

        event_start = OperationEvent.create(
            operation_id=operation.id,
            event_type="execution_started",
            message=f"Started {operation.operation_type.value} operation on {operation.target_package}",
        )
        self.repo.save_operation_event(event_start)

        # Dispatch operation
        proc_res = None
        if operation.operation_type in (OperationType.INSTALL, OperationType.AUDIT_FIX):
            proc_res = adapter.install(
                package=operation.target_package,
                version=operation.target_version or operation.proposed_version,
                dry_run=dry_run,
            )
        elif operation.operation_type == OperationType.REMOVE:
            proc_res = adapter.remove(
                package=operation.target_package,
                dry_run=dry_run,
            )
        elif operation.operation_type == OperationType.UPGRADE:
            proc_res = adapter.upgrade(
                package=operation.target_package,
                version=operation.target_version or operation.proposed_version,
                dry_run=dry_run,
            )

        if proc_res:
            operation.logs.append(f"Command: {' '.join(proc_res.argv)}")
            if proc_res.stdout.strip():
                operation.logs.append(proc_res.stdout.strip())
            if proc_res.stderr.strip():
                operation.logs.append(proc_res.stderr.strip())

            if not proc_res.success and not dry_run:
                operation.status = OperationState.FAILED
                event_fail = OperationEvent.create(
                    operation_id=operation.id,
                    event_type="execution_failed",
                    message=f"Subprocess failed with exit code {proc_res.exit_code}: {proc_res.stderr}",
                )
                self.repo.save_operation_event(event_fail)
                self.repo.save_lifecycle_operation(operation)
                return operation

        if dry_run:
            operation.status = OperationState.COMPLETED
            self.repo.save_lifecycle_operation(operation)
            return operation

        # Verification step
        verified = verify_operation_outcome(operation, adapter)
        if verified:
            operation.status = OperationState.COMPLETED
            operation.verified_at = datetime.now(UTC).isoformat()
            event_success = OperationEvent.create(
                operation_id=operation.id,
                event_type="verification_passed",
                message="Post-operation state verified successfully.",
            )
            self.repo.save_operation_event(event_success)
        else:
            operation.status = OperationState.VERIFICATION_FAILED
            event_vfail = OperationEvent.create(
                operation_id=operation.id,
                event_type="verification_failed",
                message="Post-operation verification failed. Package state does not match expected result.",
            )
            self.repo.save_operation_event(event_vfail)

        self.repo.save_lifecycle_operation(operation)
        return operation
