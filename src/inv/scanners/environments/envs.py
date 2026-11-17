"""Scanner for virtual environments, conda envs, and version manager environments."""

import os
from pathlib import Path

from inv.constants import EnvironmentType
from inv.core.models import Environment
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


class EnvironmentScanner(BaseScanner):
    """Scanner for virtual environments and managed runtime environments."""

    @property
    def scanner_id(self) -> str:
        return "environments"

    @property
    def domain(self) -> str:
        return "environments"

    @property
    def name(self) -> str:
        return "Virtual & Development Environments"

    def is_available(self) -> bool:
        return True

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)
        seen_paths: set[str] = set()

        # 1. Local project virtual environments in project roots or cwd
        roots = context.config.project_roots or [Path.cwd()]
        candidate_names = [".venv", "venv", ".env", "env"]

        for root in roots:
            for name in candidate_names:
                venv_dir = root / name
                pyvenv_cfg = venv_dir / "pyvenv.cfg"
                if pyvenv_cfg.is_file():
                    key = str(venv_dir.resolve())
                    if key in seen_paths:
                        continue
                    seen_paths.add(key)

                    version = self._parse_pyvenv_cfg(pyvenv_cfg)
                    env_obj = Environment.create(
                        name=f"{root.name}/{name}",
                        env_type=EnvironmentType.VENV,
                        path=venv_dir,
                        runtime_version=version,
                        is_active=os.environ.get("VIRTUAL_ENV") == str(venv_dir),
                    )
                    result.environments.append(env_obj)

        # 2. Poetry virtualenvs: ~/Library/Caches/pypoetry/virtualenvs
        poetry_dir = Path.home() / "Library" / "Caches" / "pypoetry" / "virtualenvs"
        if poetry_dir.is_dir():
            for entry in poetry_dir.iterdir():
                if entry.is_dir():
                    key = str(entry.resolve())
                    if key not in seen_paths:
                        seen_paths.add(key)
                        version = None
                        cfg = entry / "pyvenv.cfg"
                        if cfg.is_file():
                            version = self._parse_pyvenv_cfg(cfg)
                        env_obj = Environment.create(
                            name=entry.name,
                            env_type=EnvironmentType.POETRY,
                            path=entry,
                            runtime_version=version,
                        )
                        result.environments.append(env_obj)

        # 3. Pipenv virtualenvs: ~/.local/share/virtualenvs
        pipenv_dir = Path.home() / ".local" / "share" / "virtualenvs"
        if pipenv_dir.is_dir():
            for entry in pipenv_dir.iterdir():
                if entry.is_dir():
                    key = str(entry.resolve())
                    if key not in seen_paths:
                        seen_paths.add(key)
                        cfg = entry / "pyvenv.cfg"
                        version = self._parse_pyvenv_cfg(cfg) if cfg.is_file() else None
                        env_obj = Environment.create(
                            name=entry.name,
                            env_type=EnvironmentType.PIPENV,
                            path=entry,
                            runtime_version=version,
                        )
                        result.environments.append(env_obj)

        return result

    def _parse_pyvenv_cfg(self, cfg_path: Path) -> str | None:
        """Parse version from pyvenv.cfg."""
        try:
            with open(cfg_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("version =") or line.startswith("version="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass
        return None
