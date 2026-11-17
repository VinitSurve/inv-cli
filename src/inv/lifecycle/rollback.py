"""Rollback assessment and project backup management."""

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from inv.adapters.base import BaseLifecycleAdapter
from inv.lifecycle.models import LifecycleOperation
from inv.utils.process import run_command


@dataclass
class ProjectBackup:
    """Snapshot of project manifest or lockfile before modification."""

    original_path: Path
    backup_path: Path
    created_at: float

    def restore(self) -> bool:
        """Restore the backup file back to the original path."""
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.original_path)
            return True
        return False


def create_manifest_backup(file_path: Path) -> ProjectBackup | None:
    """Create a temporary backup of a manifest or lockfile prior to modification."""
    if not file_path.exists():
        return None

    timestamp = int(time.time())
    backup_path = file_path.with_name(f"{file_path.name}.inv_backup_{timestamp}")
    shutil.copy2(file_path, backup_path)
    return ProjectBackup(
        original_path=file_path,
        backup_path=backup_path,
        created_at=time.time(),
    )


def check_git_cleanliness(project_root: Path) -> dict[str, Any]:
    """Inspect Git status to ensure uncommitted changes are detected."""
    git_dir = project_root / ".git"
    if not git_dir.exists():
        return {"is_git_repo": False, "is_clean": True, "uncommitted_files": []}

    res = run_command(["git", "-C", str(project_root), "status", "--porcelain"], timeout=5.0)
    if not res.success:
        return {"is_git_repo": True, "is_clean": False, "uncommitted_files": []}

    uncommitted = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    return {
        "is_git_repo": True,
        "is_clean": len(uncommitted) == 0,
        "uncommitted_files": uncommitted,
    }


def assess_rollback_capability(
    operation: LifecycleOperation, adapter: BaseLifecycleAdapter
) -> tuple[bool, str]:
    """Determine rollback availability and formulated restoration instructions."""
    available = adapter.rollback_guaranteed and operation.previous_version is not None
    instructions = adapter.rollback_guidance(operation.target_package, operation.previous_version)
    return available, instructions
