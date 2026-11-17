"""Ecosystem audit adapters for pip-audit and npm audit."""

import json
import shutil
from pathlib import Path

from inv.constants import VulnerabilitySeverity
from inv.security.models import VulnerabilityRecord
from inv.security.severity import parse_severity
from inv.utils.process import run_command


def run_pip_audit(
    python_path: Path | None = None, session_id: str | None = None
) -> list[VulnerabilityRecord]:
    """Execute pip-audit in target Python environment if available."""
    pip_audit_bin = shutil.which("pip-audit")
    if not pip_audit_bin:
        return []

    cmd = [pip_audit_bin, "-f", "json"]
    if python_path:
        cmd.extend(["--python", str(python_path)])

    res = run_command(cmd, timeout=45.0)
    # pip-audit returns non-zero when vulnerabilities are found
    if not res.stdout.strip():
        return []

    records: list[VulnerabilityRecord] = []
    try:
        data = json.loads(res.stdout)
        dependencies = data.get("dependencies", [])
        for dep in dependencies:
            name = dep.get("name", "")
            ver = dep.get("version", "")
            vulns = dep.get("vulns", [])
            for v in vulns:
                advisory_id = v.get("id", "")
                aliases = v.get("aliases", [])
                cve_id = next((a for a in aliases if a.startswith("CVE-")), None)
                ghsa_id = next((a for a in aliases if a.startswith("GHSA-")), None)
                fix_vers = v.get("fix_versions", [])
                fixed_ver = fix_vers[0] if fix_vers else None

                records.append(
                    VulnerabilityRecord.create(
                        advisory_id=advisory_id,
                        package_name=name,
                        ecosystem="PyPI",
                        installed_version=ver,
                        severity=VulnerabilitySeverity.HIGH,  # default for pip-audit findings
                        title=v.get("description", f"Vulnerability in {name}"),
                        affected_range=f"< {fixed_ver}" if fixed_ver else "affected",
                        fixed_version=fixed_ver,
                        cve_id=cve_id,
                        ghsa_id=ghsa_id,
                        advisory_url=f"https://osv.dev/vulnerability/{advisory_id}",
                        details=v.get("description"),
                        data_source="pip-audit",
                        fix_available=bool(fixed_ver),
                        session_id=session_id,
                    )
                )
    except json.JSONDecodeError:
        pass

    return records


def run_npm_audit(project_dir: Path, session_id: str | None = None) -> list[VulnerabilityRecord]:
    """Execute npm audit in project directory containing package.json and lockfile."""
    npm_bin = shutil.which("npm")
    if not npm_bin:
        return []

    if not (project_dir / "package.json").exists():
        return []

    cmd = [npm_bin, "audit", "--json"]
    res = run_command(cmd, cwd=str(project_dir), timeout=30.0)
    if not res.stdout.strip():
        return []

    records: list[VulnerabilityRecord] = []
    try:
        data = json.loads(res.stdout)
        vulnerabilities = data.get("vulnerabilities", {})
        for name, meta in vulnerabilities.items():
            advisory_sev = parse_severity(meta.get("severity"))
            effects = meta.get("effects", [])
            fix_avail = meta.get("fixAvailable", False)
            fixed_version = None
            if isinstance(fix_avail, dict):
                fixed_version = fix_avail.get("version")

            records.append(
                VulnerabilityRecord.create(
                    advisory_id=f"npm-{name}",
                    package_name=name,
                    ecosystem="npm",
                    installed_version=meta.get("range", "unknown"),
                    severity=advisory_sev,
                    title=f"Vulnerability in npm package {name}",
                    affected_range=meta.get("range", "unknown"),
                    fixed_version=fixed_version,
                    advisory_url=meta.get("url"),
                    dependency_type="transitive" if effects else "direct",
                    data_source="npm-audit",
                    fix_available=bool(fix_avail),
                    session_id=session_id,
                )
            )
    except json.JSONDecodeError:
        pass

    return records
