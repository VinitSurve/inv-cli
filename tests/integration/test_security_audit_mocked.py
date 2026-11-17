"""Integration tests for SecurityEngine and RemediationEngine with mocked OSV advisories."""

from unittest.mock import patch

from inv.constants import InstallScope, VulnerabilitySeverity
from inv.core.models import InstallationInstance, ScanSession, SoftwareIdentity
from inv.security.engine import SecurityEngine
from inv.security.models import VulnerabilityRecord
from inv.security.osv import OSVClient
from inv.security.remediation import RemediationEngine
from inv.storage.repositories import InventoryRepository


def test_security_audit_and_remediation_mocked(mock_repo: InventoryRepository) -> None:
    session_id = "test-sec-session"
    mock_repo.save_session(ScanSession.create(session_id=session_id))

    # Save a package to repository
    ident = SoftwareIdentity.create(name="urllib3", ecosystem="pypi")
    mock_repo.save_software_identity(ident)
    inst = InstallationInstance.create(
        software_id=ident.id,
        name="urllib3",
        version="1.26.4",
        manager="pip",
        scope=InstallScope.GLOBAL,
    )
    mock_repo.save_installation(inst, session_id)

    mock_vuln = VulnerabilityRecord.create(
        advisory_id="GHSA-r64q-w8jr-3hhg",
        package_name="urllib3",
        ecosystem="PyPI",
        installed_version="1.26.4",
        severity=VulnerabilitySeverity.HIGH,
        title="CRLF injection in urllib3",
        affected_range="< 1.26.5",
        fixed_version="1.26.5",
        cve_id="CVE-2021-33503",
        session_id=session_id,
    )

    with (
        patch.object(OSVClient, "query_packages", return_value=[mock_vuln]),
        patch("inv.security.engine.run_pip_audit", return_value=[]),
    ):
        sec_engine = SecurityEngine(mock_repo, session_id=session_id)
        report = sec_engine.run_audit()

        assert report.total_vulnerabilities_found == 1
        assert report.high_count == 1
        assert report.fixable_count == 1
        assert report.findings[0].package_name == "urllib3"
        assert report.findings[0].fixed_version == "1.26.5"

        # Check repository persistence
        stored_vulns = mock_repo.list_vulnerabilities(session_id=session_id)
        assert len(stored_vulns) == 1
        assert stored_vulns[0].advisory_id == "GHSA-r64q-w8jr-3hhg"

        # Plan remediation
        remediation_engine = RemediationEngine(mock_repo, session_id=session_id)
        rem_plan = remediation_engine.plan_remediation(mock_vuln)
        assert rem_plan is not None
        assert rem_plan.target_package == "urllib3"
        assert rem_plan.proposed_version == "1.26.5"

        # Apply in dry-run mode
        applied = remediation_engine.apply_remediation(
            rem_plan, mock_vuln, dry_run=True, prompt_user=False
        )
        assert applied is True
