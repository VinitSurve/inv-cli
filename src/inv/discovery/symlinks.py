"""Safe symlink handling and loop prevention."""

import os
from dataclasses import dataclass
from pathlib import Path

from inv.constants import MAX_SYMLINK_DEPTH
from inv.exceptions import SafeSymlinkError


@dataclass
class SymlinkResolution:
    """Outcome of resolving a symlink."""

    original_path: Path
    canonical_path: Path
    is_symlink: bool
    is_broken: bool = False
    is_loop: bool = False
    depth: int = 0


def resolve_symlink_safely(path: Path, max_depth: int = MAX_SYMLINK_DEPTH) -> SymlinkResolution:
    """Safely resolve symlinks with cycle detection and depth boundaries.

    Guarantees:
    - Never loops infinitely on cyclic symlinks
    - Bounded resolution depth
    - Gracefully flags broken or cyclic links
    """
    if not path.is_symlink():
        try:
            resolved = path.resolve()
            return SymlinkResolution(
                original_path=path,
                canonical_path=resolved,
                is_symlink=False,
                is_broken=not resolved.exists(),
                is_loop=False,
                depth=0,
            )
        except (OSError, RuntimeError):
            return SymlinkResolution(
                original_path=path,
                canonical_path=path,
                is_symlink=False,
                is_broken=True,
                is_loop=False,
                depth=0,
            )

    visited: set[str] = set()
    current = path
    depth = 0

    while current.is_symlink():
        if depth >= max_depth:
            raise SafeSymlinkError(f"Symlink depth limit ({max_depth}) exceeded at {path}")

        try:
            target_str = os.readlink(str(current))
        except (OSError, PermissionError):
            return SymlinkResolution(
                original_path=path,
                canonical_path=current,
                is_symlink=True,
                is_broken=True,
                is_loop=False,
                depth=depth,
            )

        target_path = Path(target_str)
        if not target_path.is_absolute():
            target_path = (current.parent / target_path).resolve()

        resolved_key = str(target_path)
        if resolved_key in visited:
            # Cycle detected
            return SymlinkResolution(
                original_path=path,
                canonical_path=target_path,
                is_symlink=True,
                is_broken=True,
                is_loop=True,
                depth=depth + 1,
            )

        visited.add(resolved_key)
        current = target_path
        depth += 1

    is_broken = not current.exists()
    try:
        final_canonical = current.resolve() if not is_broken else current
    except (OSError, RuntimeError):
        final_canonical = current

    return SymlinkResolution(
        original_path=path,
        canonical_path=final_canonical,
        is_symlink=True,
        is_broken=is_broken,
        is_loop=False,
        depth=depth,
    )
