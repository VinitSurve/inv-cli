"""OSV.dev advisory data integration and vulnerability matching."""

import json
import urllib.error
import urllib.request
from typing import Any

from inv.security.models import VulnerabilityRecord
from inv.security.severity import parse_severity


class OSVClient:
    """Client for querying the OSV.dev open vulnerability database."""

    OSV_API_URL = "https://api.osv.dev/v1/querybatch"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def query_packages(
        self,
        package_queries: list[dict[str, str]],
        session_id: str | None = None,
    ) -> list[VulnerabilityRecord]:
        """Query OSV batch endpoint for a list of packages and versions.

        Each query is a dict: {"name": str, "version": str, "ecosystem": str}
        Ecosystems: PyPI, npm, crates.io, Go, etc.
        """
        if not package_queries:
            return []

        # Batch queries into chunks of 100 to stay within API limits
        chunk_size = 100
        all_records: list[VulnerabilityRecord] = []

        for i in range(0, len(package_queries), chunk_size):
            chunk = package_queries[i : i + chunk_size]
            payload = {
                "queries": [
                    {
                        "package": {"name": q["name"], "ecosystem": q["ecosystem"]},
                        "version": q["version"],
                    }
                    for q in chunk
                ]
            }

            try:
                data = self._post_json(payload)
                results = data.get("results", [])
                for idx, res in enumerate(results):
                    vulns = res.get("vulns", [])
                    orig_q = chunk[idx]
                    for v in vulns:
                        rec = self._parse_osv_vuln(v, orig_q, session_id=session_id)
                        if rec:
                            all_records.append(rec)
            except Exception:
                # Network or timeout failure gracefully handled
                pass

        return all_records

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send JSON POST request with controlled timeout."""
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            self.OSV_API_URL,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "inv-security-scanner/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            res: dict[str, Any] = json.loads(body)
            return res

    def _parse_osv_vuln(
        self,
        vuln: dict[str, Any],
        query: dict[str, str],
        session_id: str | None = None,
    ) -> VulnerabilityRecord | None:
        """Parse raw OSV JSON vulnerability schema into VulnerabilityRecord."""
        advisory_id = vuln.get("id", "")
        if not advisory_id:
            return None

        aliases = vuln.get("aliases", [])
        cve_id = next((a for a in aliases if a.startswith("CVE-")), None)
        ghsa_id = next((a for a in aliases if a.startswith("GHSA-")), None)
        osv_id = advisory_id if advisory_id.startswith("OSV-") else None

        title = vuln.get("summary") or vuln.get("details") or f"Vulnerability in {query['name']}"
        # Truncate title to first line or 100 chars
        title = title.splitlines()[0][:120].strip()

        # Severity
        severity_score = None
        db_spec = vuln.get("database_specific", {})
        raw_sev = db_spec.get("severity")
        if not raw_sev:
            for aff in vuln.get("affected", []):
                eco_spec = aff.get("ecosystem_specific", {})
                if eco_spec.get("severity"):
                    raw_sev = eco_spec.get("severity")
                    break

        severity_entries = vuln.get("severity", [])
        for entry in severity_entries:
            if entry.get("type") in ("CVSS_V3", "CVSS_V2") and not raw_sev:
                raw_sev = entry.get("score")
                break
        severity = parse_severity(raw_sev, cvss_score=severity_score)

        # Fixed version and affected range from affected[]
        fixed_version = None
        affected_range = "unknown"
        for aff in vuln.get("affected", []):
            ranges = aff.get("ranges", [])
            for r in ranges:
                events = r.get("events", [])
                for ev in events:
                    if "fixed" in ev:
                        fixed_version = ev["fixed"]
                        break
            if aff.get("versions"):
                affected_range = f"< {fixed_version}" if fixed_version else "affected"

        # Advisory URL
        advisory_url = None
        for ref in vuln.get("references", []):
            if ref.get("type") in ("ADVISORY", "WEB"):
                advisory_url = ref.get("url")
                break
        if not advisory_url and advisory_id.startswith("GHSA-"):
            advisory_url = f"https://github.com/advisories/{advisory_id}"
        elif not advisory_url and cve_id:
            advisory_url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"

        return VulnerabilityRecord.create(
            advisory_id=advisory_id,
            package_name=query["name"],
            ecosystem=query["ecosystem"],
            installed_version=query["version"],
            severity=severity,
            title=title,
            affected_range=affected_range,
            fixed_version=fixed_version,
            cve_id=cve_id,
            ghsa_id=ghsa_id,
            osv_id=osv_id,
            cvss_score=severity_score,
            advisory_url=advisory_url,
            details=vuln.get("details"),
            dependency_type="direct",
            data_source="osv.dev",
            fix_available=bool(fixed_version),
            published_at=vuln.get("published"),
            session_id=session_id,
        )
