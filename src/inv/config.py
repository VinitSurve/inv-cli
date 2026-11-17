"""Configuration manager for the Inventory CLI."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir

from inv.constants import (
    APP_NAME,
    DEFAULT_DB_FILENAME,
    DEFAULT_MAX_WALK_DEPTH,
    DEFAULT_PROCESS_TIMEOUT,
)


@dataclass
class InvConfig:
    """Configuration settings for inv scanning and storage."""

    db_path: Path = field(
        default_factory=lambda: Path(user_data_dir(APP_NAME)) / DEFAULT_DB_FILENAME
    )
    project_roots: list[Path] = field(default_factory=lambda: [Path.cwd()])
    scan_projects: bool = True
    deep_scan: bool = False
    max_depth: int = DEFAULT_MAX_WALK_DEPTH
    process_timeout: float = DEFAULT_PROCESS_TIMEOUT
    disabled_scanners: list[str] = field(default_factory=list)
    enabled_scanners: list[str] = field(default_factory=list)
    extra_path_dirs: list[Path] = field(default_factory=list)
    extra_app_dirs: list[Path] = field(default_factory=list)
    show_progress: bool = True
    max_workers: int = 4

    @classmethod
    def get_config_dir(cls) -> Path:
        """Return the configuration directory."""
        cfg_dir = Path(user_config_dir(APP_NAME))
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir

    @classmethod
    def get_config_file_path(cls) -> Path:
        """Return the config file path."""
        return cls.get_config_dir() / "config.json"

    @classmethod
    def load(cls, config_path: Path | None = None) -> "InvConfig":
        """Load configuration from disk or create default."""
        path = config_path or cls.get_config_file_path()
        if not path.exists():
            return cls()

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            # Fall back to default config on parse error
            return cls()

    def save(self, config_path: Path | None = None) -> None:
        """Save configuration to disk."""
        path = config_path or self.get_config_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "db_path": str(self.db_path),
            "project_roots": [str(p) for p in self.project_roots],
            "scan_projects": self.scan_projects,
            "deep_scan": self.deep_scan,
            "max_depth": self.max_depth,
            "process_timeout": self.process_timeout,
            "disabled_scanners": self.disabled_scanners,
            "enabled_scanners": self.enabled_scanners,
            "extra_path_dirs": [str(p) for p in self.extra_path_dirs],
            "extra_app_dirs": [str(p) for p in self.extra_app_dirs],
            "show_progress": self.show_progress,
            "max_workers": self.max_workers,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvConfig":
        """Construct InvConfig from dictionary."""
        cfg = cls()
        if "db_path" in data:
            cfg.db_path = Path(data["db_path"])
        if "project_roots" in data and isinstance(data["project_roots"], list):
            cfg.project_roots = [Path(p) for p in data["project_roots"]]
        if "scan_projects" in data:
            cfg.scan_projects = bool(data["scan_projects"])
        if "deep_scan" in data:
            cfg.deep_scan = bool(data["deep_scan"])
        if "max_depth" in data:
            cfg.max_depth = int(data["max_depth"])
        if "process_timeout" in data:
            cfg.process_timeout = float(data["process_timeout"])
        if "disabled_scanners" in data and isinstance(data["disabled_scanners"], list):
            cfg.disabled_scanners = [str(s) for s in data["disabled_scanners"]]
        if "enabled_scanners" in data and isinstance(data["enabled_scanners"], list):
            cfg.enabled_scanners = [str(s) for s in data["enabled_scanners"]]
        if "extra_path_dirs" in data and isinstance(data["extra_path_dirs"], list):
            cfg.extra_path_dirs = [Path(p) for p in data["extra_path_dirs"]]
        if "extra_app_dirs" in data and isinstance(data["extra_app_dirs"], list):
            cfg.extra_app_dirs = [Path(p) for p in data["extra_app_dirs"]]
        if "show_progress" in data:
            cfg.show_progress = bool(data["show_progress"])
        if "max_workers" in data:
            cfg.max_workers = int(data["max_workers"])
        return cfg
