"""VS Code and Cursor IDE extensions scanner."""

import json
from pathlib import Path

from inv.core.models import Extension
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


class IdeExtensionScanner(BaseScanner):
    """Scanner for installed VS Code and Cursor extensions."""

    @property
    def scanner_id(self) -> str:
        return "ide_extensions"

    @property
    def domain(self) -> str:
        return "extensions"

    @property
    def name(self) -> str:
        return "IDE Extensions"

    def is_available(self) -> bool:
        vscode_dir = Path.home() / ".vscode" / "extensions"
        cursor_dir = Path.home() / ".cursor" / "extensions"
        return vscode_dir.is_dir() or cursor_dir.is_dir()

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        targets = [
            ("vscode", Path.home() / ".vscode" / "extensions"),
            ("cursor", Path.home() / ".cursor" / "extensions"),
        ]

        for ide_name, ext_root in targets:
            if not ext_root.is_dir():
                continue

            for ext_dir in ext_root.iterdir():
                if not ext_dir.is_dir() or ext_dir.name.startswith("."):
                    continue

                pkg_json = ext_dir / "package.json"
                if not pkg_json.is_file():
                    continue

                try:
                    with open(pkg_json, encoding="utf-8") as f:
                        data = json.load(f)
                    name = data.get("name", ext_dir.name)
                    publisher = data.get("publisher")
                    version = data.get("version")

                    ext_obj = Extension.create(
                        name=name,
                        ide=ide_name,
                        publisher=publisher,
                        version=version,
                        path=ext_dir,
                    )
                    result.extensions.append(ext_obj)
                except Exception:
                    continue

        return result
