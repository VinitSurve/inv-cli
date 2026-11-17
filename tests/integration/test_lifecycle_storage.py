"""Integration tests for SQLite schema migration V2 and lifecycle persistence."""

from inv.constants import (
    InstallScope,
    OperationState,
    OperationType,
    RiskLevel,
    UpdateStrategy,
    VulnerabilitySeverity,
)
from inv.core.models import ScanSession
from inv.lifecycle.models import (
    LifecycleOperation,
    OperationEvent,
    OutdatedPackage,
)
from inv.security.models import VulnerabilityRecord
from inv.storage.repositories import InventoryRepository


def test_lifecycle_and_security_repository_persistence(mock_repo: InventoryRepository) -> None:
    session_id = "test-session-storage"
    mock_repo.save_session(ScanSession.create(session_id=session_id))

    # 1. Test Vulnerabilities persistence
    vuln = VulnerabilityRecord.create(
        advisory_id="GHSA-test-9999",
        package_name="flask",
        ecosystem="PyPI",
        installed_version="2.0.1",
        severity=VulnerabilitySeverity.MEDIUM,
        title="Sample vulnerability in Flask",
        affected_range="< 2.0.2",
        fixed_version="2.0.2",
        session_id=session_id,
    )
    mock_repo.save_vulnerability(vuln)

    stored = mock_repo.get_vulnerability(vuln.id)
    assert stored is not None
    assert stored.package_name == "flask"
    assert stored.severity == VulnerabilitySeverity.MEDIUM
    assert stored.fixed_version == "2.0.2"

    vuln_list = mock_repo.list_vulnerabilities(session_id=session_id)
    assert len(vuln_list) == 1

    mock_repo.update_vulnerability_remediation(vuln.id, "remediated")
    updated_vuln = mock_repo.get_vulnerability(vuln.id)
    assert updated_vuln is not None
    assert updated_vuln.remediation_status == "remediated"

    # 2. Test Lifecycle Operation persistence
    op = LifecycleOperation.create(
        operation_type=OperationType.INSTALL,
        target_package="jq",
        manager="brew_formula",
        scope=InstallScope.GLOBAL,
        proposed_version="1.7.1",
        risk_level=RiskLevel.LOW,
        actions=["brew install jq"],
    )
    mock_repo.save_lifecycle_operation(op)

    stored_op = mock_repo.get_lifecycle_operation(op.id)
    assert stored_op is not None
    assert stored_op.target_package == "jq"
    assert stored_op.status == OperationState.PLANNED

    # Update operation status
    mock_repo.update_lifecycle_operation_status(
        op.id, OperationState.COMPLETED, logs=["Installed successfully"]
    )
    updated_op = mock_repo.get_lifecycle_operation(op.id)
    assert updated_op is not None
    assert updated_op.status == OperationState.COMPLETED
    assert "Installed successfully" in updated_op.logs

    # 3. Test Operation Events
    ev1 = OperationEvent.create(
        operation_id=op.id,
        event_type="started",
        message="Operation started",
    )
    ev2 = OperationEvent.create(
        operation_id=op.id,
        event_type="finished",
        message="Operation completed",
    )
    mock_repo.save_operation_event(ev1)
    mock_repo.save_operation_event(ev2)

    events = mock_repo.list_operation_events(op.id)
    assert len(events) == 2
    assert events[0].event_type == "started"
    assert events[1].event_type == "finished"

    # 4. Test Outdated Packages
    outdated = OutdatedPackage(
        name="pytest",
        manager="pip",
        installed_version="8.0.0",
        latest_version="8.1.0",
        latest_stable_version="8.1.0",
        latest_compatible_version="8.0.2",
        update_strategy=UpdateStrategy.COMPATIBLE,
        is_major_update=False,
    )
    mock_repo.save_outdated_package(outdated, session_id=session_id)

    outdated_list = mock_repo.list_outdated_packages(session_id=session_id)
    assert len(outdated_list) == 1
    assert outdated_list[0].name == "pytest"
    assert outdated_list[0].latest_version == "8.1.0"

    mock_repo.clear_outdated_packages(session_id=session_id)
    assert len(mock_repo.list_outdated_packages(session_id=session_id)) == 0
