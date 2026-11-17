"""PATH environment variable and binary discovery."""

import os
from pathlib import Path

from inv.constants import COMMON_BIN_DIRS
from inv.utils.paths import is_sensitive_path, normalize_path


def get_system_path_dirs(extra_dirs: list[Path] | None = None) -> list[Path]:
    """Retrieve normalized, existing binary directories from PATH and standard locations."""
    path_str = os.environ.get("PATH", "")
    raw_dirs = [Path(p) for p in path_str.split(os.pathsep) if p.strip()]

    # Append standard well-known binary directories
    all_dirs = raw_dirs + COMMON_BIN_DIRS
    if extra_dirs:
        all_dirs.extend(extra_dirs)

    seen: set[str] = set()
    valid_dirs: list[Path] = []

    for d in all_dirs:
        try:
            norm = normalize_path(d)
            if not norm.is_dir() or is_sensitive_path(norm):
                continue
            key = str(norm)
            if key not in seen:
                seen.add(key)
                valid_dirs.append(norm)
        except (PermissionError, OSError):
            continue

    return valid_dirs


def is_executable_file(path: Path) -> bool:
    """Check if path is a regular file or symlink to a regular file and has execute permissions."""
    try:
        if path.is_dir():
            return False
        # Must be executable by current user and not sensitive
        if is_sensitive_path(path):
            return False
        return os.access(str(path), os.X_OK)
    except (OSError, PermissionError):
        return False

