"""macOS Application bundle (.app) scanner inspecting Info.plist."""

import os
import plistlib
from pathlib import Path

from inv.constants import COMMON_APP_DIRS
from inv.core.models import Application
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


class ApplicationScanner(BaseScanner):
    """Scanner for installed macOS applications (.app bundles)."""

    @property
    def scanner_id(self) -> str:
        return "applications"

    @property
    def domain(self) -> str:
        return "applications"

    @property
    def name(self) -> str:
        return "macOS Applications"

    def is_available(self) -> bool:
        return any(d.is_dir() for d in COMMON_APP_DIRS)

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)
        search_dirs = list(COMMON_APP_DIRS) + context.config.extra_app_dirs

        seen_app_paths: set[str] = set()

        for app_dir in search_dirs:
            if not app_dir.is_dir():
                continue

            try:
                with os.scandir(str(app_dir)) as it:
                    for entry in it:
                        try:
                            if not entry.name.endswith(".app"):
                                continue

                            app_path = Path(entry.path)
                            key = str(app_path.resolve())
                            if key in seen_app_paths:
                                continue
                            seen_app_paths.add(key)

                            plist_path = app_path / "Contents" / "Info.plist"
                            if not plist_path.is_file():
                                continue

                            app_info = self._parse_app_plist(app_path, plist_path)
                            if app_info:
                                result.applications.append(app_info)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                result.warnings.append(
                    f"Permission denied accessing application directory: {app_dir}"
                )
                continue

        return result

    def _parse_app_plist(self, app_path: Path, plist_path: Path) -> Application | None:
        """Parse Info.plist binary/xml format safely using plistlib."""
        try:
            with open(plist_path, "rb") as f:
                data = plistlib.load(f)

            if not isinstance(data, dict):
                return None

            name = data.get("CFBundleDisplayName") or data.get("CFBundleName") or app_path.stem
            bundle_id = data.get("CFBundleIdentifier")
            version = data.get("CFBundleShortVersionString") or data.get("CFBundleVersion")
            build_num = data.get("CFBundleVersion")
            min_os = data.get("LSMinimumSystemVersion")
            category = data.get("LSApplicationCategoryType")

            is_system = str(app_path).startswith("/System") or (
                isinstance(bundle_id, str) and bundle_id.startswith("com.apple.")
            )

            # Architectures heuristic from binary or architectures list
            architectures: list[str] = []
            arch_list = data.get("LSArchitecturePriority")
            if isinstance(arch_list, list):
                architectures = [str(a) for a in arch_list]

            return Application.create(
                name=str(name),
                path=app_path,
                bundle_id=str(bundle_id) if bundle_id else None,
                version=str(version) if version else None,
                build_number=str(build_num) if build_num else None,
                min_os_version=str(min_os) if min_os else None,
                architectures=architectures,
                category=str(category) if category else None,
                is_system=is_system,
            )
        except Exception:
            return None
