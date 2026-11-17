"""Vulnerability audit coordinator and security engine."""

from collections import Counter

from inv.constants import VulnerabilitySeverity
from inv.security.advisories import run_pip_audit
from inv.security.models import AuditReport, VulnerabilityRecord
from inv.security.osv import OSVClient
from inv.storage.repositories import InventoryRepository


class SecurityEngine:
    """Coordinates vulnerability auditing across packages, environments, and projects."""

    def __init__(
        self,
        repo: InventoryRepository,
        osv_client: OSVClient | None = None,
        session_id: str | None = None,
    ) -> None:
        self.repo = repo
        self.osv_client = osv_client or OSVClient()
        self.session_id = session_id

    def run_audit(
        self,
        severity_filter: VulnerabilitySeverity | None = None,
        manager_filter: str | None = None,
    ) -> AuditReport:
        """Audit installed software and project dependencies for known CVEs/advisories."""
        all_records: list[VulnerabilityRecord] = []
        ecosystems_checked: set[str] = set()
        warnings: list[str] = []

        # 1. Collect installations
        insts = self.repo.list_installations(self.session_id)
        package_queries: list[dict[str, str]] = []

        for inst in insts:
            if manager_filter and inst.manager.lower() != manager_filter.lower():
                continue

            ecosystem = self._map_manager_to_ecosystem(inst.manager)
            if ecosystem and inst.version and inst.version != "unknown":
                package_queries.append(
                    {"name": inst.name, "version": inst.version, "ecosystem": ecosystem}
                )
                ecosystems_checked.add(ecosystem)

        # 2. Collect project dependencies
        proj_deps = self.repo.list_project_dependencies(session_id=self.session_id)
        for pd in proj_deps:
            if manager_filter and pd.ecosystem.lower() != manager_filter.lower():
                continue
            eco = self._map_manager_to_ecosystem(pd.ecosystem)
            if eco and pd.resolved_version and pd.resolved_version != "unknown":
                package_queries.append(
                    {"name": pd.name, "version": pd.resolved_version, "ecosystem": eco}
                )
                ecosystems_checked.add(eco)

        # 3. Query OSV database
        if package_queries:
            try:
                osv_records = self.osv_client.query_packages(
                    package_queries, session_id=self.session_id
                )
                all_records.extend(osv_records)
            except Exception as exc:
                warnings.append(f"OSV database query warning: {exc}")

        # 4. Run native pip-audit if Python was checked
        if not manager_filter or manager_filter in ("pip", "uv", "python"):
            try:
                pip_records = run_pip_audit(session_id=self.session_id)
                all_records.extend(pip_records)
            except Exception:
                pass

        # Deduplicate records by (advisory_id, package_name)
        seen_keys: set[tuple[str, str]] = set()
        unique_records: list[VulnerabilityRecord] = []
        for r in all_records:
            key = (r.advisory_id, r.package_name.lower())
            if key not in seen_keys:
                seen_keys.add(key)
                if severity_filter is None or r.severity == severity_filter:
                    unique_records.append(r)
                    self.repo.save_vulnerability(r)

        # Compute summary counts
        sev_counts: Counter[VulnerabilitySeverity] = Counter()
        fixable_count = 0
        direct_count = 0
        transitive_count = 0

        for r in unique_records:
            sev_counts[r.severity] += 1
            if r.fix_available:
                fixable_count += 1
            if r.dependency_type == "direct":
                direct_count += 1
            else:
                transitive_count += 1

        return AuditReport(
            session_id=self.session_id or "latest",
            total_packages_checked=len(package_queries),
            total_vulnerabilities_found=len(unique_records),
            critical_count=sev_counts[VulnerabilitySeverity.CRITICAL],
            high_count=sev_counts[VulnerabilitySeverity.HIGH],
            medium_count=sev_counts[VulnerabilitySeverity.MEDIUM],
            low_count=sev_counts[VulnerabilitySeverity.LOW],
            unknown_count=sev_counts[VulnerabilitySeverity.UNKNOWN],
            direct_count=direct_count,
            transitive_count=transitive_count,
            fixable_count=fixable_count,
            findings=unique_records,
            ecosystems_checked=sorted(ecosystems_checked),
            warnings=warnings,
        )

    def _map_manager_to_ecosystem(self, manager_str: str) -> str | None:
        """Map package manager or project ecosystem to OSV ecosystem name."""
        norm = manager_str.lower()
        if norm in ("npm", "pnpm", "yarn", "bun", "node", "javascript"):
            return "npm"
        if norm in ("pip", "uv_tool", "uv_project", "python", "pypi"):
            return "PyPI"
        if norm in ("cargo", "rust"):
            return "crates.io"
        if norm in ("go", "golang"):
            return "Go"
        if norm in ("composer", "php"):
            return "Packagist"
        if norm in ("gem", "rubygems", "ruby"):
            return "RubyGems"
        if norm in ("brew_formula", "brew"):
            return "Homebrew"
        return None
