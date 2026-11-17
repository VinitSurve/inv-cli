"""PATH executables scanner with controlled probe registry and duplicate detection."""

import os
from collections import defaultdict
from pathlib import Path

from inv.core.models import ExecutableInstance
from inv.discovery.path import get_system_path_dirs, is_executable_file
from inv.discovery.symlinks import resolve_symlink_safely
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.scanners.probe import can_probe_version, probe_executable_version


def infer_source_manager(path: Path) -> str | None:
    """Infer source package manager or system provenance from file path."""
    p_str = str(path)
    if "/opt/homebrew" in p_str or "/usr/local/Cellar" in p_str:
        return "brew"
    if "anaconda" in p_str or "miniconda" in p_str:
        return "conda"
    if ".cargo/bin" in p_str:
        return "cargo"
    if ".local/share/uv" in p_str:
        return "uv"
    if ".npm-global" in p_str or "node_modules/.bin" in p_str:
        return "npm"
    if ".pnpm" in p_str or "pnpm/bin" in p_str:
        return "pnpm"
    if ".bun/bin" in p_str:
        return "bun"
    if p_str.startswith("/usr/bin") or p_str.startswith("/bin") or p_str.startswith("/System"):
        return "system"
    if "/Library/Frameworks/Python.framework" in p_str:
        return "python.org"
    return None


class PathBinaryScanner(BaseScanner):
    """Scanner for all executable commands in system PATH."""

    @property
    def scanner_id(self) -> str:
        return "path_binaries"

    @property
    def domain(self) -> str:
        return "binaries"

    @property
    def name(self) -> str:
        return "PATH Executables"

    def is_available(self) -> bool:
        return bool(os.environ.get("PATH"))

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)
        path_dirs = get_system_path_dirs(context.config.extra_path_dirs)

        # Track occurrences of each command name to detect duplicates
        name_to_instances: dict[str, list[ExecutableInstance]] = defaultdict(list)
        seen_paths: set[str] = set()

        for directory in path_dirs:
            try:
                with os.scandir(str(directory)) as entries:
                    for entry in entries:
                        try:
                            entry_path = Path(entry.path)
                            key = str(entry_path)
                            if key in seen_paths:
                                continue
                            seen_paths.add(key)

                            if not is_executable_file(entry_path):
                                continue

                            res = resolve_symlink_safely(entry_path)
                            if res.is_broken or res.is_loop:
                                continue

                            canonical = res.canonical_path
                            source_mgr = infer_source_manager(canonical) or infer_source_manager(
                                entry_path
                            )

                            # Controlled probe registry for safe version discovery
                            version = None
                            if can_probe_version(entry.name):
                                version = probe_executable_version(entry.name, entry_path)

                            exe = ExecutableInstance.create(
                                name=entry.name,
                                path=entry_path,
                                canonical_path=canonical,
                                is_symlink=res.is_symlink,
                                version=version,
                                source_manager=source_mgr,
                                is_accessible=True,
                                is_duplicate=False,
                            )
                            name_to_instances[entry.name].append(exe)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                result.warnings.append(f"Permission denied accessing directory: {directory}")
                continue

        # Mark duplicates and collect into results
        for _name, instances in name_to_instances.items():
            is_dup = len(instances) > 1
            for inst in instances:
                inst.is_duplicate = is_dup
                result.executables.append(inst)

        return result
