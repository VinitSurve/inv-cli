"""Scanner for installed language runtimes, compilers, and version managers."""

import shutil
from pathlib import Path

from inv.core.models import Runtime
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.scanners.binaries.path import infer_source_manager
from inv.scanners.probe import probe_executable_version

LANGUAGES_TO_CHECK = [
    ("Python", "python3"),
    ("Node.js", "node"),
    ("Ruby", "ruby"),
    ("Rust", "rustc"),
    ("Go", "go"),
    ("Java", "java"),
    ("PHP", "php"),
    ("Swift", "swift"),
    ("Bun", "bun"),
    ("Deno", "deno"),
    ("Dotnet", "dotnet"),
    ("Perl", "perl"),
    ("Lua", "lua"),
]


class RuntimeScanner(BaseScanner):
    """Scanner for programming language runtimes and SDKs."""

    @property
    def scanner_id(self) -> str:
        return "runtimes"

    @property
    def domain(self) -> str:
        return "runtimes"

    @property
    def name(self) -> str:
        return "Language Runtimes & SDKs"

    def is_available(self) -> bool:
        return True

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)
        seen_paths: set[str] = set()

        for lang_name, bin_cmd in LANGUAGES_TO_CHECK:
            bin_path_str = shutil.which(bin_cmd)
            if not bin_path_str:
                continue

            bin_path = Path(bin_path_str)
            try:
                resolved = bin_path.resolve()
            except (OSError, RuntimeError):
                resolved = bin_path

            key = str(resolved)
            if key in seen_paths:
                continue
            seen_paths.add(key)

            version = probe_executable_version(bin_cmd, bin_path) or "detected"
            manager = infer_source_manager(resolved) or infer_source_manager(bin_path)

            rt = Runtime.create(
                name=lang_name,
                version=version,
                path=bin_path,
                manager=manager,
                metadata={"resolved_path": str(resolved)},
            )
            result.runtimes.append(rt)

        # Check version manager directories
        # 1. nvm versions: ~/.nvm/versions/node/*
        nvm_node_dir = Path.home() / ".nvm" / "versions" / "node"
        if nvm_node_dir.is_dir():
            for entry in nvm_node_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("v"):
                    rt = Runtime.create(
                        name="Node.js",
                        version=entry.name.lstrip("v"),
                        path=entry / "bin" / "node",
                        manager="nvm",
                    )
                    result.runtimes.append(rt)

        # 2. pyenv versions: ~/.pyenv/versions/*
        pyenv_dir = Path.home() / ".pyenv" / "versions"
        if pyenv_dir.is_dir():
            for entry in pyenv_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    rt = Runtime.create(
                        name="Python",
                        version=entry.name,
                        path=entry / "bin" / "python",
                        manager="pyenv",
                    )
                    result.runtimes.append(rt)

        return result
