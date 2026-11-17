"""Exclusion rules for filesystem discovery."""

from pathlib import Path

from inv.constants import DEFAULT_EXCLUDED_DIRS
from inv.utils.paths import RESTRICTED_DIR_NAMES


class ExclusionRules:
    """Evaluates whether paths or directory names should be excluded during scans."""

    def __init__(self, additional_exclusions: set[str] | None = None) -> None:
        self.excluded_names = set(DEFAULT_EXCLUDED_DIRS)
        self.excluded_names.update(RESTRICTED_DIR_NAMES)
        if additional_exclusions:
            self.excluded_names.update(additional_exclusions)

    def should_exclude_dir(self, dir_name: str) -> bool:
        """Check if directory name matches excluded patterns."""
        if dir_name.startswith(".") and dir_name != ".venv":
            return True
        return dir_name in self.excluded_names

    def is_excluded_path(self, path: Path) -> bool:
        """Check if any segment in the path is in the exclusion set."""
        return any(part in self.excluded_names for part in path.parts)
