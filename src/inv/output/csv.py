"""CSV exporter for tabular inventory records."""

import csv
import io

from inv.core.models import Application, ExecutableInstance, InstallationInstance


def export_installations_csv(installations: list[InstallationInstance]) -> str:
    """Export package installations as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Version", "Manager", "Scope", "Install Path", "Provenance"])
    for inst in installations:
        writer.writerow(
            [
                inst.name,
                inst.version,
                inst.manager,
                inst.scope.value,
                str(inst.install_path) if inst.install_path else "",
                inst.provenance,
            ]
        )
    return output.getvalue()


def export_executables_csv(executables: list[ExecutableInstance]) -> str:
    """Export PATH executables as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Name",
            "Path",
            "Canonical Path",
            "Is Symlink",
            "Version",
            "Source Manager",
            "Is Duplicate",
        ]
    )
    for exe in executables:
        writer.writerow(
            [
                exe.name,
                str(exe.path),
                str(exe.canonical_path),
                exe.is_symlink,
                exe.version or "",
                exe.source_manager or "",
                exe.is_duplicate,
            ]
        )
    return output.getvalue()


def export_applications_csv(apps: list[Application]) -> str:
    """Export macOS applications as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Bundle ID", "Version", "Build Number", "Path", "Is System"])
    for app in apps:
        writer.writerow(
            [
                app.name,
                app.bundle_id or "",
                app.version or "",
                app.build_number or "",
                str(app.path),
                app.is_system,
            ]
        )
    return output.getvalue()
