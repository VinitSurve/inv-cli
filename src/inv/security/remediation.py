"""Conservative vulnerability remediation engine."""

from inv.adapters.registry import LifecycleRegistry
from inv.constants import OperationState, OperationType, RiskLevel
from inv.lifecycle.approvals import request_operation_approval
from inv.lifecycle.executor import LifecycleExecutor
from inv.lifecycle.models import LifecycleOperation
from inv.security.models import VulnerabilityRecord
from inv.security.osv import OSVClient
from inv.storage.repositories import InventoryRepository


class RemediationEngine:
    """Calculates, plans, and applies conservative vulnerability fixes with verification."""

    def __init__(
        self,
        repo: InventoryRepository,
        registry: LifecycleRegistry | None = None,
        session_id: str | None = None,
    ) -> None:
        self.repo = repo
        self.registry = registry or LifecycleRegistry()
        self.session_id = session_id
        self.executor = LifecycleExecutor(self.repo, self.registry)

    def plan_remediation(self, vuln: VulnerabilityRecord) -> LifecycleOperation | None:
        """Formulate a remediation upgrade plan for a vulnerable package."""
        if not vuln.fix_available or not vuln.fixed_version:
            return None

        # Resolve package manager
        adapter = self.registry.resolve_manager_for_package(
            package_name=vuln.package_name,
            explicit_manager=None,
            repo=self.repo,
            session_id=self.session_id,
        )

        risk_level = RiskLevel.LOW
        risk_reasons = []

        # Check if major version transition
        try:
            curr_major = int(vuln.installed_version.split(".")[0])
            fix_major = int(vuln.fixed_version.split(".")[0])
            if fix_major > curr_major:
                risk_level = RiskLevel.HIGH
                risk_reasons.append(
                    f"Remediation requires major upgrade from {vuln.installed_version} to {vuln.fixed_version}. "
                    "Potential API breaking changes."
                )
        except (ValueError, IndexError):
            pass

        actions = [
            f"Upgrade {vuln.package_name} from {vuln.installed_version} to {vuln.fixed_version} "
            f"to remediate {vuln.advisory_id} ({vuln.severity.value.upper()})"
        ]

        op = LifecycleOperation.create(
            operation_type=OperationType.AUDIT_FIX,
            target_package=vuln.package_name,
            manager=adapter.manager_id,
            previous_version=vuln.installed_version,
            proposed_version=vuln.fixed_version,
            target_version=vuln.fixed_version,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            actions=actions,
            dependency_changes=[f"{vuln.package_name}=={vuln.fixed_version}"],
            reverse_dependencies=[],
            metadata={"advisory_id": vuln.advisory_id, "vulnerability_id": vuln.id},
        )
        return op

    def apply_remediation(
        self,
        operation: LifecycleOperation,
        vuln: VulnerabilityRecord,
        dry_run: bool = False,
        prompt_user: bool = True,
    ) -> bool:
        """Prompt for explicit approval, execute the remediation, and verify via re-audit."""
        if not dry_run and prompt_user:
            approved = request_operation_approval(operation)
            if not approved:
                return False
            operation.status = OperationState.APPROVED

        # Execute
        executed_op = self.executor.execute(operation, dry_run=dry_run)
        if executed_op.status != OperationState.COMPLETED:
            vuln.remediation_status = "failed"
            self.repo.update_vulnerability_remediation(vuln.id, "failed")
            return False

        if dry_run:
            return True

        # Re-audit verification: Query OSV to check if the new version is still vulnerable
        osv = OSVClient()
        post_vulns = osv.query_packages(
            [
                {
                    "name": vuln.package_name,
                    "version": operation.proposed_version or "",
                    "ecosystem": vuln.ecosystem,
                }
            ]
        )
        is_fixed = not any(pv.advisory_id == vuln.advisory_id for pv in post_vulns)

        if is_fixed:
            vuln.remediation_status = "remediated"
            self.repo.update_vulnerability_remediation(vuln.id, "remediated")
            return True
        else:
            vuln.remediation_status = "unresolved"
            self.repo.update_vulnerability_remediation(vuln.id, "unresolved")
            return False
