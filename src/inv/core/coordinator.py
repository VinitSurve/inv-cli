"""Concurrency coordinator for orchestrating scanner execution."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from inv.config import InvConfig
from inv.constants import ScannerStatus
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


class ScanCoordinator:
    """Manages parallel scanner dispatching with bounded concurrency and cancellation."""

    def __init__(self, config: InvConfig) -> None:
        self.config = config
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signal ongoing scan to abort early."""
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run_scanners(
        self,
        scanners: list[BaseScanner],
        context: ScanContext,
        progress_cb: Callable[[str, int, int], None] | None = None,
    ) -> list[ScanResult]:
        """Execute a list of scanners using bounded parallel thread pool."""
        results: list[ScanResult] = []
        total = len(scanners)
        completed = 0

        # Filter enabled / disabled scanners
        active_scanners: list[BaseScanner] = []
        for s in scanners:
            if s.scanner_id in self.config.disabled_scanners:
                results.append(
                    ScanResult(
                        scanner_id=s.scanner_id,
                        domain=s.domain,
                        status=ScannerStatus.SKIPPED,
                        warnings=[f"Scanner '{s.name}' disabled by configuration."],
                    )
                )
            elif self.config.enabled_scanners and s.scanner_id not in self.config.enabled_scanners:
                results.append(
                    ScanResult(
                        scanner_id=s.scanner_id,
                        domain=s.domain,
                        status=ScannerStatus.SKIPPED,
                        warnings=[f"Scanner '{s.name}' skipped (not in enabled_scanners)."],
                    )
                )
            else:
                active_scanners.append(s)

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_scanner = {executor.submit(s.execute, context): s for s in active_scanners}

            for future in as_completed(future_to_scanner):
                if self.is_cancelled:
                    break

                scanner = future_to_scanner[future]
                completed += 1
                try:
                    res = future.result()
                    results.append(res)
                except Exception as exc:
                    results.append(
                        ScanResult(
                            scanner_id=scanner.scanner_id,
                            domain=scanner.domain,
                            status=ScannerStatus.FAILED,
                            errors=[f"Coordinator caught unhandled scanner failure: {exc}"],
                        )
                    )

                if progress_cb:
                    progress_cb(scanner.name, completed, total)

        return results
