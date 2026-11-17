"""Reporting and Rich terminal rendering for security audit findings."""

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from inv.constants import VulnerabilitySeverity
from inv.security.models import AuditReport


def render_security_audit_table(report: AuditReport, console: Console | None = None) -> None:
    """Render a comprehensive security audit report with Rich."""
    con = console or Console()

    # Summary Panel
    sev_text = (
        f"[bold red]Critical:[/bold red] {report.critical_count}  "
        f"[red]High:[/red] {report.high_count}  "
        f"[yellow]Medium:[/yellow] {report.medium_count}  "
        f"[blue]Low:[/blue] {report.low_count}"
    )
    fix_text = f"[bold green]{report.fixable_count}[/bold green] fixable"
    con.print(
        Panel(
            f"Vulnerabilities: [bold]{report.total_vulnerabilities_found}[/bold] across {report.total_packages_checked} packages audited\n"
            f"Severity Breakdown: {sev_text}\n"
            f"Fix Availability: {fix_text} | Direct: {report.direct_count} | Transitive: {report.transitive_count}",
            title="[bold red]Security Vulnerability Audit[/bold red]",
            border_style="red" if report.total_vulnerabilities_found > 0 else "green",
        )
    )

    if not report.findings:
        con.print(
            "[bold green]✓ No known vulnerabilities discovered in audited packages.[/bold green]"
        )
        return

    table = Table(title="Discovered Vulnerabilities", pad_edge=False)
    table.add_column("Package", style="bold white", min_width=18)
    table.add_column("Installed", style="cyan", min_width=10)
    table.add_column("Severity", min_width=10)
    table.add_column("Advisory", style="dim", min_width=16)
    table.add_column("Fixed In", style="bold green", min_width=10)
    table.add_column("Type", min_width=10)
    table.add_column("Status", min_width=10)

    for f in report.findings:
        sev_color = "red"
        if f.severity == VulnerabilitySeverity.CRITICAL:
            sev_color = "bold red"
        elif f.severity == VulnerabilitySeverity.HIGH:
            sev_color = "red"
        elif f.severity == VulnerabilitySeverity.MEDIUM:
            sev_color = "yellow"
        elif f.severity == VulnerabilitySeverity.LOW:
            sev_color = "blue"
        else:
            sev_color = "dim"

        fix_str = (
            f"[bold green]{f.fixed_version}[/bold green]" if f.fixed_version else "[dim]None[/dim]"
        )
        status_color = "green" if f.remediation_status == "remediated" else "yellow"

        table.add_row(
            f.package_name,
            f.installed_version,
            f"[{sev_color}]{f.severity.value.upper()}[/{sev_color}]",
            f.advisory_id,
            fix_str,
            f.dependency_type,
            f"[{status_color}]{f.remediation_status}[/{status_color}]",
        )

    con.print(table)


def export_security_report_json(report: AuditReport) -> str:
    """Format audit report into structured JSON string."""
    return json.dumps(report.to_dict(), indent=2)
