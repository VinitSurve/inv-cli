"""Severity classification and CVSS mapping utilities."""

from inv.constants import VulnerabilitySeverity


def parse_severity(raw: str | None, cvss_score: float | None = None) -> VulnerabilitySeverity:
    """Classify advisory severity from textual rating or numeric CVSS score."""
    if cvss_score is not None:
        if cvss_score >= 9.0:
            return VulnerabilitySeverity.CRITICAL
        if cvss_score >= 7.0:
            return VulnerabilitySeverity.HIGH
        if cvss_score >= 4.0:
            return VulnerabilitySeverity.MEDIUM
        if cvss_score > 0.0:
            return VulnerabilitySeverity.LOW

    if not raw:
        return VulnerabilitySeverity.UNKNOWN

    norm = raw.strip().lower()
    if norm in ("critical", "crit"):
        return VulnerabilitySeverity.CRITICAL
    if norm in ("high", "severe"):
        return VulnerabilitySeverity.HIGH
    if norm in ("medium", "moderate", "mod"):
        return VulnerabilitySeverity.MEDIUM
    if norm in ("low",):
        return VulnerabilitySeverity.LOW

    return VulnerabilitySeverity.UNKNOWN
