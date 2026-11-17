"""Coverage and inventory completeness analytics."""

from dataclasses import dataclass
from datetime import UTC, datetime

from inv.constants import ScannerStatus
from inv.core.models import ScannerObservation, ScanSession


@dataclass
class InventoryCoverage:
    """Detailed coverage report across all scanners."""

    total_scanners: int
    successful_scanners: int
    partial_scanners: int
    unavailable_scanners: int
    failed_scanners: int
    skipped_scanners: int
    completeness_percentage: float
    is_full_coverage: bool
    scan_age_human: str


class CoverageAnalyzer:
    """Analyzes scanner observations to determine inventory coverage and health."""

    @staticmethod
    def analyze(
        session: ScanSession | None, observations: list[ScannerObservation]
    ) -> InventoryCoverage:
        total = len(observations)
        if total == 0:
            return InventoryCoverage(
                total_scanners=0,
                successful_scanners=0,
                partial_scanners=0,
                unavailable_scanners=0,
                failed_scanners=0,
                skipped_scanners=0,
                completeness_percentage=0.0,
                is_full_coverage=False,
                scan_age_human="Never scanned",
            )

        success = sum(1 for o in observations if o.status == ScannerStatus.SUCCESS)
        partial = sum(1 for o in observations if o.status == ScannerStatus.PARTIAL)
        unavail = sum(1 for o in observations if o.status == ScannerStatus.UNAVAILABLE)
        failed = sum(1 for o in observations if o.status == ScannerStatus.FAILED)
        skipped = sum(1 for o in observations if o.status == ScannerStatus.SKIPPED)

        # Completeness considers successfully scanned domains vs applicable domains
        completeness = ((success + partial) / total) * 100.0 if total > 0 else 0.0
        is_full = failed == 0 and skipped == 0 and partial == 0

        age_human = "Unknown"
        if session and session.started_at:
            try:
                start_dt = datetime.fromisoformat(session.started_at)
                delta = datetime.now(UTC) - start_dt
                if delta.total_seconds() < 60:
                    age_human = "Just now"
                elif delta.total_seconds() < 3600:
                    age_human = f"{int(delta.total_seconds() // 60)} minutes ago"
                elif delta.total_seconds() < 86400:
                    age_human = f"{int(delta.total_seconds() // 3600)} hours ago"
                else:
                    age_human = f"{delta.days} days ago"
            except Exception:
                age_human = session.started_at

        return InventoryCoverage(
            total_scanners=total,
            successful_scanners=success,
            partial_scanners=partial,
            unavailable_scanners=unavail,
            failed_scanners=failed,
            skipped_scanners=skipped,
            completeness_percentage=round(completeness, 1),
            is_full_coverage=is_full,
            scan_age_human=age_human,
        )
