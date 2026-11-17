"""Safe bounded filesystem traversal for project and package discovery."""

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from inv.constants import DEFAULT_MAX_WALK_DEPTH, MAX_FILESYSTEM_ENTRIES
from inv.discovery.exclusions import ExclusionRules
from inv.discovery.manifests import MANIFEST_FILES
from inv.discovery.symlinks import resolve_symlink_safely
from inv.utils.paths import is_sensitive_path


@dataclass
class TraversalStats:
    """Statistics gathered during a filesystem traversal."""

    directories_visited: int = 0
    files_inspected: int = 0
    manifests_found: int = 0
    symlinks_skipped: int = 0
    permission_errors: int = 0
    max_depth_reached: int = 0


@dataclass
class DiscoveredProjectEntry:
    """Discovered project candidate based on manifests."""

    root_path: Path
    manifest_paths: list[Path] = field(default_factory=list)
    project_types: set[str] = field(default_factory=set)


def safe_walk_projects(
    roots: list[Path],
    max_depth: int = DEFAULT_MAX_WALK_DEPTH,
    max_entries: int = MAX_FILESYSTEM_ENTRIES,
    exclusions: ExclusionRules | None = None,
    progress_cb: Callable[[str, int], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[dict[Path, DiscoveredProjectEntry], TraversalStats]:
    """Safely traverse project directory roots to locate manifests without descending infinitely.

    Guarantees:
    - Bounded traversal depth
    - Bounded entry limit
    - Never descends into sensitive directories (.ssh, credentials)
    - Safe symlink resolution
    - Cancellation responsiveness
    """
    rules = exclusions or ExclusionRules()
    stats = TraversalStats()
    projects: dict[Path, DiscoveredProjectEntry] = {}

    for root in roots:
        try:
            if not root.exists() or is_sensitive_path(root):
                continue
            root_norm = root.resolve()
        except (PermissionError, OSError):
            stats.permission_errors += 1
            continue

        # BFS queue: (directory_path, current_depth)
        queue: list[tuple[Path, int]] = [(root_norm, 0)]
        visited_dirs: set[str] = {str(root_norm)}

        while queue:
            if cancel_check and cancel_check():
                break

            if stats.directories_visited + stats.files_inspected >= max_entries:
                break

            current_dir, depth = queue.pop(0)
            stats.directories_visited += 1
            if depth > stats.max_depth_reached:
                stats.max_depth_reached = depth

            if progress_cb and stats.directories_visited % 50 == 0:
                progress_cb(str(current_dir), stats.directories_visited)

            try:
                with os.scandir(str(current_dir)) as it:
                    entries = list(it)
            except (PermissionError, OSError):
                stats.permission_errors += 1
                continue

            subdirs: list[Path] = []

            for entry in entries:
                if cancel_check and cancel_check():
                    break

                try:
                    stats.files_inspected += 1
                    entry_name = entry.name
                    entry_path = Path(entry.path)

                    if entry.is_symlink():
                        res = resolve_symlink_safely(entry_path)
                        if res.is_broken or res.is_loop:
                            stats.symlinks_skipped += 1
                            continue

                    if entry.is_dir(follow_symlinks=False):
                        if rules.should_exclude_dir(entry_name) or is_sensitive_path(entry_path):
                            continue
                        subdirs.append(entry_path)
                    elif entry.is_file(follow_symlinks=True) and entry_name in MANIFEST_FILES:
                        proj_type = MANIFEST_FILES[entry_name]
                        if current_dir not in projects:
                            projects[current_dir] = DiscoveredProjectEntry(root_path=current_dir)
                        projects[current_dir].manifest_paths.append(entry_path)
                        projects[current_dir].project_types.add(proj_type)
                        stats.manifests_found += 1
                except (PermissionError, OSError):
                    stats.permission_errors += 1
                    continue

            # If depth limit not reached, queue subdirectories
            if depth < max_depth:
                for s in subdirs:
                    try:
                        resolved_s = s.resolve()
                        k = str(resolved_s)
                        if k not in visited_dirs:
                            visited_dirs.add(k)
                            queue.append((resolved_s, depth + 1))
                    except (PermissionError, OSError):
                        continue

    return projects, stats
