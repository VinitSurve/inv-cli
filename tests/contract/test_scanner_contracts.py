"""Contract tests verifying the BaseScanner lifecycle and resilience invariants."""

from unittest.mock import patch

from inv.config import InvConfig
from inv.constants import ScannerStatus
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


class MockAvailableScanner(BaseScanner):
    @property
    def scanner_id(self) -> str:
        return "mock_avail"

    @property
    def domain(self) -> str:
        return "test"

    @property
    def name(self) -> str:
        return "Mock Available"

    def is_available(self) -> bool:
        return True

    def scan(self, context: ScanContext) -> ScanResult:
        return ScanResult(
            scanner_id=self.scanner_id, domain=self.domain, status=ScannerStatus.SUCCESS
        )


class MockUnavailableScanner(BaseScanner):
    @property
    def scanner_id(self) -> str:
        return "mock_unavail"

    @property
    def domain(self) -> str:
        return "test"

    @property
    def name(self) -> str:
        return "Mock Unavailable"

    def is_available(self) -> bool:
        return False

    def scan(self, context: ScanContext) -> ScanResult:
        return ScanResult(scanner_id=self.scanner_id, domain=self.domain)


class MockFailingScanner(BaseScanner):
    @property
    def scanner_id(self) -> str:
        return "mock_failing"

    @property
    def domain(self) -> str:
        return "test"

    @property
    def name(self) -> str:
        return "Mock Failing"

    def is_available(self) -> bool:
        return True

    def scan(self, context: ScanContext) -> ScanResult:
        raise RuntimeError("Simulated crash in scan()")


def test_contract_available_manager() -> None:
    scanner = MockAvailableScanner()
    ctx = ScanContext(session_id="test-session", config=InvConfig())
    res = scanner.execute(ctx)
    assert res.status == ScannerStatus.SUCCESS
    assert res.duration_seconds >= 0.0
    assert len(res.errors) == 0


def test_contract_missing_manager() -> None:
    scanner = MockUnavailableScanner()
    ctx = ScanContext(session_id="test-session", config=InvConfig())
    res = scanner.execute(ctx)
    assert res.status == ScannerStatus.UNAVAILABLE
    assert len(res.warnings) > 0
    assert "unavailable" in res.warnings[0].lower()


def test_contract_crashing_scanner_resilience() -> None:
    scanner = MockFailingScanner()
    ctx = ScanContext(session_id="test-session", config=InvConfig())
    # execute() must NEVER raise, must return status FAILED
    res = scanner.execute(ctx)
    assert res.status == ScannerStatus.FAILED
    assert len(res.errors) > 0
    assert "Simulated crash" in res.errors[0]


def test_contract_subprocess_timeout() -> None:
    from inv.scanners.package_managers.brew import BrewFormulaScanner
    from inv.utils.process import ProcessResult

    scanner = BrewFormulaScanner()
    ctx = ScanContext(session_id="test-session", config=InvConfig())

    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.brew.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["brew", "info"],
            exit_code=-1,
            stdout="",
            stderr="timed out",
            timed_out=True,
        )
        res = scanner.execute(ctx)
        # Should not crash, returns failed status or warning
        assert res.status in (ScannerStatus.FAILED, ScannerStatus.SUCCESS, ScannerStatus.PARTIAL)
