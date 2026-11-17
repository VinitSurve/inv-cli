"""Domain models for package lifecycle, operations, planning, and outdated tracking."""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from inv.constants import InstallScope, OperationState, OperationType, RiskLevel, UpdateStrategy


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


@dataclass
class PackageInfo:
    """Detailed metadata for a package across package managers."""

    name: str
    manager: str
    installed_version: str | None = None
    latest_version: str | None = None
    latest_stable_version: str | None = None
    homepage: str | None = None
    description: str | None = None
    license: str | None = None
    dependencies: list[str] = field(default_factory=list)
    reverse_dependencies: list[str] = field(default_factory=list)
    install_path: str | None = None
    scope: str = "global"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutdatedPackage:
    """Represents an installed package that has a newer version available."""

    name: str
    manager: str
    installed_version: str
    latest_version: str
    latest_stable_version: str
    latest_compatible_version: str
    update_strategy: UpdateStrategy = UpdateStrategy.COMPATIBLE
    is_major_update: bool = False
    checked_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LifecycleOperation:
    """A tracked package lifecycle modification operation with two-stage approval."""

    id: str
    operation_type: OperationType
    target_package: str
    manager: str
    scope: InstallScope = InstallScope.GLOBAL
    target_version: str | None = None
    previous_version: str | None = None
    proposed_version: str | None = None
    status: OperationState = OperationState.PLANNED
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    dependency_changes: list[str] = field(default_factory=list)
    reverse_dependencies: list[str] = field(default_factory=list)
    rollback_available: bool = False
    rollback_instructions: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    approved_at: str | None = None
    executed_at: str | None = None
    verified_at: str | None = None
    logs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        operation_type: OperationType,
        target_package: str,
        manager: str,
        scope: InstallScope = InstallScope.GLOBAL,
        target_version: str | None = None,
        previous_version: str | None = None,
        proposed_version: str | None = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        risk_reasons: list[str] | None = None,
        actions: list[str] | None = None,
        dependency_changes: list[str] | None = None,
        reverse_dependencies: list[str] | None = None,
        rollback_available: bool = False,
        rollback_instructions: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "LifecycleOperation":
        op_id = f"op_{uuid.uuid4().hex[:12]}"
        return cls(
            id=op_id,
            operation_type=operation_type,
            target_package=target_package,
            manager=manager,
            scope=scope,
            target_version=target_version,
            previous_version=previous_version,
            proposed_version=proposed_version,
            status=OperationState.PLANNED,
            risk_level=risk_level,
            risk_reasons=risk_reasons or [],
            actions=actions or [],
            dependency_changes=dependency_changes or [],
            reverse_dependencies=reverse_dependencies or [],
            rollback_available=rollback_available,
            rollback_instructions=rollback_instructions,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationEvent:
    """Audit log entry recorded during an operation lifecycle transition."""

    id: str
    operation_id: str
    event_type: str
    timestamp: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        operation_id: str,
        event_type: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> "OperationEvent":
        return cls(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            operation_id=operation_id,
            event_type=event_type,
            timestamp=utc_now_iso(),
            message=message,
            data=data or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
