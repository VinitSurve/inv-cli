"""Performance benchmark and load tests."""

import time
from pathlib import Path

from inv.config import InvConfig
from inv.core.coordinator import ScanCoordinator
from inv.core.deduplicator import Deduplicator
from inv.core.models import ExecutableInstance
from inv.discovery.filesystem import safe_walk_projects
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


def test_large_synthetic_project_tree_traversal(temp_dir: Path) -> None:
    # Generate 50 project directories with manifests
    for i in range(50):
        p = temp_dir / f"repo_{i}"
        p.mkdir()
        (p / "pyproject.toml").write_text(f'[project]\nname="pkg-{i}"\n', encoding="utf-8")

    start = time.perf_counter()
    projects, stats = safe_walk_projects(roots=[temp_dir], max_depth=3)
    duration = time.perf_counter() - start

    assert len(projects) == 50
    # Must traverse quickly (under 1.0 second for 50 directories)
    assert duration < 1.0


def test_large_inventory_deduplication_speed() -> None:
    # 5,000 synthetic executables
    executables = []
    for i in range(5000):
        cmd_name = f"cmd_{i % 500}"  # 500 distinct command names, each with 10 duplicates
        executables.append(
            ExecutableInstance.create(
                name=cmd_name,
                path=Path(f"/dir_{i // 500}/bin/{cmd_name}"),
                canonical_path=Path(f"/dir_{i // 500}/bin/{cmd_name}"),
                is_symlink=False,
            )
        )

    dedup = Deduplicator()
    start = time.perf_counter()
    dups = dedup.find_duplicate_commands(executables)
    duration = time.perf_counter() - start

    assert len(dups) == 500
    # Must complete in under 0.2 seconds
    assert duration < 0.2


def test_parallel_scanner_execution_bounded_time() -> None:
    class SleepingScanner(BaseScanner):
        def __init__(self, idx: int) -> None:
            self.idx = idx

        @property
        def scanner_id(self) -> str:
            return f"sleep_{self.idx}"

        @property
        def domain(self) -> str:
            return "test"

        @property
        def name(self) -> str:
            return f"Sleep {self.idx}"

        def is_available(self) -> bool:
            return True

        def scan(self, context: ScanContext) -> ScanResult:
            time.sleep(0.05)
            return ScanResult(scanner_id=self.scanner_id, domain=self.domain)

    scanners = [SleepingScanner(i) for i in range(8)]
    cfg = InvConfig(max_workers=4)
    coordinator = ScanCoordinator(cfg)
    ctx = ScanContext(session_id="perf-test", config=cfg)

    start = time.perf_counter()
    results = coordinator.run_scanners(scanners, ctx)
    duration = time.perf_counter() - start

    assert len(results) == 8
    # 8 tasks * 0.05s with 4 workers should finish concurrently (bounded safely for CI runners)
    assert duration < 1.0
