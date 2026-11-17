"""Domain models for security audit findings, advisories, and remediation."""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from inv.constants import VulnerabilitySeverity


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).isoformat()


@dataclass
class VulnerabilityRecord:
    """Represents a discovered security vulnerability advisory."""

    id: str
    advisory_id: str
    package_name: str
    ecosystem: str
    installed_version: str
    severity: VulnerabilitySeverity
    title: str
    affected_range: str
    fixed_version: str | None = None
    cve_id: str | None = None
    ghsa_id: str | None = None
    osv_id: str | None = None
    cvss_score: float | None = None
    advisory_url: str | None = None
    details: str | None = None
    dependency_type: str = "direct"  # "direct" | "transitive"
    introduced_by: str | None = None  # parent package if transitive
    data_source: str = "osv"
    fix_available: bool = False
    remediation_status: str = "open"  # "open" | "remediated" | "unfixable" | "ignored"
    published_at: str | None = None
    scanned_at: str = field(default_factory=utc_now_iso)
    session_id: str | None = None

    @classmethod
    def create(
        cls,
        advisory_id: str,
        package_name: str,
        ecosystem: str,
        installed_version: str,
        severity: VulnerabilitySeverity,
        title: str,
        affected_range: str,
        fixed_version: str | None = None,
        cve_id: str | None = None,
        ghsa_id: str | None = None,
        osv_id: str | None = None,
        cvss_score: float | None = None,
        advisory_url: str | None = None,
        details: str | None = None,
        dependency_type: str = "direct",
        introduced_by: str | None = None,
        data_source: str = "osv",
        fix_available: bool = False,
        remediation_status: str = "open",
        published_at: str | None = None,
        session_id: str | None = None,
    ) -> "VulnerabilityRecord":
        return cls(
            id=f"vuln_{uuid.uuid4().hex[:12]}",
            advisory_id=advisory_id,
            package_name=package_name,
            ecosystem=ecosystem,
            installed_version=installed_version,
            severity=severity,
            title=title,
            affected_range=affected_range,
            fixed_version=fixed_version,
            cve_id=cve_id,
            ghsa_id=ghsa_id,
            osv_id=osv_id,
            cvss_score=cvss_score,
            advisory_url=advisory_url,
            details=details,
            dependency_type=dependency_type,
            introduced_by=introduced_by,
            data_source=data_source,
            fix_available=fix_available or bool(fixed_version),
            remediation_status=remediation_status,
            published_at=published_at,
            session_id=session_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    """Summary and details of an execution of the vulnerability security audit."""

    session_id: str
    audited_at: str = field(default_factory=utc_now_iso)
    total_packages_checked: int = 0
    total_vulnerabilities_found: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    unknown_count: int = 0
    direct_count: int = 0
    transitive_count: int = 0
    fixable_count: int = 0
    findings: list[VulnerabilityRecord] = field(default_factory=list)
    ecosystems_checked: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
