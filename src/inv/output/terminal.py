"""Rich terminal rendering components and tables."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from inv.constants import APP_DISPLAY_NAME, RiskLevel, ScannerStatus
from inv.core.coverage import InventoryCoverage
from inv.core.models import (
    Application,
    Container,
    Environment,
    ExecutableInstance,
    InstallationInstance,
    Project,
    ProjectDependency,
    Runtime,
    ScannerObservation,
    ScanSession,
)
from inv.lifecycle.models import (
    LifecycleOperation,
    OutdatedPackage,
    PackageInfo,
)

console = Console()


def render_overview(
    session: ScanSession | None,
    coverage: InventoryCoverage,
    counts: dict[str, int],
) -> None:
    """Render the default inventory summary dashboard."""
    if not session:
        console.print(
            Panel(
                "[bold yellow]No inventory scan found.[/bold yellow]\n\n"
                "Run [bold cyan]inv scan[/bold cyan] to perform your first inventory discovery scan.",
                title=f"[bold blue]{APP_DISPLAY_NAME}[/bold blue]",
                border_style="blue",
            )
        )
        return

    # Header info
    header = (
        f"[bold]Latest Scan:[/bold] {coverage.scan_age_human}  |  "
        f"[bold]Session:[/bold] {session.id}  |  "
        f"[bold]Coverage:[/bold] {coverage.completeness_percentage}% ({coverage.successful_scanners}/{coverage.total_scanners} scanners)\n"
        f"[bold]Duration:[/bold] {session.duration_seconds:.2f}s  |  "
        f"[bold]Total Discovered Entities:[/bold] {session.total_items:,}"
    )

    console.print(
        Panel(
            header,
            title=f"[bold cyan]{APP_DISPLAY_NAME} — Overview[/bold cyan]",
            border_style="cyan",
        )
    )

    # Metrics table
    table = Table(title="Inventory Entities", box=None, pad_edge=False)
    table.add_column("Category", style="bold white", min_width=24)
    table.add_column("Count", justify="right", style="cyan", min_width=10)
    table.add_column("Details / CLI Shortcut", style="dim")

    table.add_row(
        "Package Installations",
        f"{counts.get('installations', 0):,}",
        "inv global (brew, npm, pip, cargo, gem...)",
    )
    table.add_row(
        "PATH Executables",
        f"{counts.get('executables', 0):,}",
        "inv tools (CLI binaries & duplicate commands)",
    )
    table.add_row(
        "macOS Applications",
        f"{counts.get('applications', 0):,}",
        "inv apps (/Applications, bundle IDs, versions)",
    )
    table.add_row(
        "Language Runtimes",
        f"{counts.get('runtimes', 0):,}",
        "inv runtimes (Python, Node, Rust, Go, Java...)",
    )
    table.add_row(
        "Virtual Environments",
        f"{counts.get('environments', 0):,}",
        "inv envs (venv, conda, poetry, nvm...)",
    )
    table.add_row(
        "Software Projects",
        f"{counts.get('projects', 0):,}",
        "inv local (monorepos, manifests, dependencies)",
    )
    table.add_row(
        "Containers & Images",
        f"{counts.get('containers', 0):,}",
        "inv containers (Docker containers & images)",
    )
    table.add_row(
        "IDE Extensions",
        f"{counts.get('extensions', 0):,}",
        "inv report (VS Code & Cursor extensions)",
    )

    console.print(table)
    console.print(
        "\n[dim]Tip: Run [bold cyan]inv scan[/bold cyan] to refresh inventory, or [bold cyan]inv --help[/bold cyan] for all commands.[/dim]"
    )


def render_installations_table(
    installations: list[InstallationInstance], title: str = "Installed Packages"
) -> None:
    """Render table of package manager installations."""
    table = Table(title=title, pad_edge=False)
    table.add_column("Package Name", style="bold white", min_width=25)
    table.add_column("Version", style="green", min_width=15)
    table.add_column("Manager", style="cyan", min_width=14)
    table.add_column("Scope", style="magenta", min_width=10)
    table.add_column("Install Path / Provenance", style="dim")

    for inst in installations:
        path_str = str(inst.install_path) if inst.install_path else inst.provenance
        table.add_row(inst.name, inst.version, inst.manager, inst.scope.value, path_str)

    console.print(table)
    console.print(f"[dim]Total: {len(installations)} packages[/dim]\n")


def render_executables_table(
    executables: list[ExecutableInstance], duplicates_only: bool = False
) -> None:
    """Render table of PATH executables."""
    title = "Duplicate Command Candidates in PATH" if duplicates_only else "PATH Executables"
    table = Table(title=title, pad_edge=False)
    table.add_column("Command Name", style="bold white", min_width=20)
    table.add_column("Version", style="green", min_width=12)
    table.add_column("Source", style="cyan", min_width=10)
    table.add_column("Duplicate?", style="yellow", min_width=12)
    table.add_column("Path", style="dim")

    for exe in executables:
        dup_text = "[bold yellow]YES (shadowed)[/bold yellow]" if exe.is_duplicate else "no"
        table.add_row(
            exe.name,
            exe.version or "-",
            exe.source_manager or "-",
            dup_text,
            str(exe.path),
        )

    console.print(table)
    console.print(f"[dim]Total: {len(executables)} executables[/dim]\n")


def render_applications_table(apps: list[Application]) -> None:
    """Render table of macOS applications."""
    table = Table(title="Installed macOS Applications (.app)", pad_edge=False)
    table.add_column("Application", style="bold white", min_width=25)
    table.add_column("Version", style="green", min_width=12)
    table.add_column("Bundle Identifier", style="cyan", min_width=28)
    table.add_column("Type", style="magenta", min_width=10)
    table.add_column("Path", style="dim")

    for app in apps:
        app_type = "System" if app.is_system else "User/App"
        table.add_row(
            app.name,
            app.version or "-",
            app.bundle_id or "-",
            app_type,
            str(app.path),
        )

    console.print(table)
    console.print(f"[dim]Total: {len(apps)} applications[/dim]\n")


def render_runtimes_table(runtimes: list[Runtime]) -> None:
    """Render table of programming language runtimes."""
    table = Table(title="Installed Language Runtimes & SDKs", pad_edge=False)
    table.add_column("Language", style="bold white", min_width=16)
    table.add_column("Version", style="green", min_width=14)
    table.add_column("Manager", style="cyan", min_width=12)
    table.add_column("Path", style="dim")

    for rt in runtimes:
        table.add_row(rt.name, rt.version, rt.manager or "system", str(rt.path))

    console.print(table)
    console.print(f"[dim]Total: {len(runtimes)} runtimes[/dim]\n")


def render_environments_table(envs: list[Environment]) -> None:
    """Render table of virtual and development environments."""
    table = Table(title="Development & Virtual Environments", pad_edge=False)
    table.add_column("Environment Name", style="bold white", min_width=25)
    table.add_column("Type", style="cyan", min_width=12)
    table.add_column("Runtime Version", style="green", min_width=16)
    table.add_column("Active?", style="yellow", min_width=10)
    table.add_column("Path", style="dim")

    for env in envs:
        active_str = "[bold green]ACTIVE[/bold green]" if env.is_active else "inactive"
        table.add_row(
            env.name,
            env.env_type.value,
            env.runtime_version or "-",
            active_str,
            str(env.path),
        )

    console.print(table)
    console.print(f"[dim]Total: {len(envs)} environments[/dim]\n")


def render_projects_table(projects: list[Project]) -> None:
    """Render table of discovered projects."""
    table = Table(title="Software Projects", pad_edge=False)
    table.add_column("Project Name", style="bold white", min_width=22)
    table.add_column("Ecosystems", style="cyan", min_width=16)
    table.add_column("Lockfile?", style="green", min_width=10)
    table.add_column("Dependencies", justify="right", style="yellow", min_width=14)
    table.add_column("Root Directory", style="dim")

    for proj in projects:
        lock_str = "Yes" if proj.has_lockfile else "No"
        types_str = ", ".join(proj.project_types) or "unknown"
        table.add_row(
            proj.name,
            types_str,
            lock_str,
            str(proj.dependencies_count),
            str(proj.path),
        )

    console.print(table)
    console.print(f"[dim]Total: {len(projects)} projects[/dim]\n")


def render_containers_table(containers: list[Container]) -> None:
    """Render table of Docker containers."""
    table = Table(title="Docker Containers", pad_edge=False)
    table.add_column("ID", style="dim", min_width=12)
    table.add_column("Name", style="bold white", min_width=20)
    table.add_column("Image", style="cyan", min_width=25)
    table.add_column("Status", style="green", min_width=15)
    table.add_column("Ports", style="yellow")

    for c in containers:
        ports_str = ", ".join(c.ports) if c.ports else "-"
        table.add_row(c.container_id[:12], c.name, c.image, c.status, ports_str)

    console.print(table)
    console.print(f"[dim]Total: {len(containers)} containers[/dim]\n")


def render_scanner_status_table(observations: list[ScannerObservation]) -> None:
    """Render status and timing table for scanners."""
    table = Table(title="Scanner Health & Coverage Status", pad_edge=False)
    table.add_column("Scanner", style="bold white", min_width=24)
    table.add_column("Domain", style="dim", min_width=16)
    table.add_column("Status", min_width=14)
    table.add_column("Duration", justify="right", style="cyan", min_width=10)
    table.add_column("Discovered", justify="right", style="green", min_width=12)
    table.add_column("Notes / Warnings", style="yellow")

    status_styles = {
        ScannerStatus.SUCCESS: "[bold green]success[/bold green]",
        ScannerStatus.PARTIAL: "[bold yellow]partial[/bold yellow]",
        ScannerStatus.UNAVAILABLE: "[dim]unavailable[/dim]",
        ScannerStatus.UNSUPPORTED: "[dim red]unsupported[/dim red]",
        ScannerStatus.FAILED: "[bold red]failed[/bold red]",
        ScannerStatus.SKIPPED: "[dim]skipped[/dim]",
    }

    for obs in observations:
        status_disp = status_styles.get(obs.status, str(obs.status))
        notes = "; ".join(obs.warnings + obs.errors) or "-"
        table.add_row(
            obs.scanner_id,
            obs.domain,
            status_disp,
            f"{obs.duration_seconds:.2f}s",
            f"{obs.items_count:,}",
            notes,
        )

    console.print(table)


def render_project_tree(projects: list[Project], dependencies: list[ProjectDependency]) -> None:
    """Render hierarchical tree of projects and their dependencies."""
    tree = Tree("[bold cyan]Inventory Project Hierarchy[/bold cyan]")
    deps_by_proj: dict[str, list[ProjectDependency]] = {}
    for dep in dependencies:
        deps_by_proj.setdefault(dep.project_id, []).append(dep)

    for proj in projects:
        proj_node = tree.add(f"[bold white]{proj.name}[/bold white] [dim]({proj.path!s})[/dim]")
        proj_deps = deps_by_proj.get(str(proj.path), [])
        if not proj_deps:
            proj_node.add("[dim](no dependencies declared)[/dim]")
            continue

        for dep in proj_deps:
            status_color = (
                "green"
                if dep.status.value == "installed"
                else "yellow"
                if dep.status.value == "missing"
                else "white"
            )
            ver_str = dep.resolved_version or dep.declared_spec or "*"
            proj_node.add(
                f"[{status_color}]{dep.name}[/{status_color}] [dim]@{ver_str} ({dep.status.value})[/dim]"
            )

    console.print(tree)


def render_operation_plan_panel(
    op: LifecycleOperation, title: str = "INV — OPERATION PLAN"
) -> None:
    """Render a detailed modification plan preview panel."""
    risk_color = "green"
    if op.risk_level == RiskLevel.CRITICAL:
        risk_color = "bold red"
    elif op.risk_level == RiskLevel.HIGH:
        risk_color = "red"
    elif op.risk_level == RiskLevel.MEDIUM:
        risk_color = "yellow"

    prev_str = op.previous_version or "[dim]Not installed[/dim]"
    prop_str = op.proposed_version or "[dim]None[/dim]"
    rollback_str = (
        "[green]Guaranteed restoration supported[/green]"
        if op.rollback_available
        else "[yellow]Previous version restoration not guaranteed[/yellow]"
    )

    lines = [
        f"[bold white]Target Package:[/bold white] [bold cyan]{op.target_package}[/bold cyan]",
        f"[bold white]Package Manager:[/bold white] {op.manager}",
        f"[bold white]Current Version:[/bold white] {prev_str}",
        f"[bold white]Proposed Version:[/bold white] [bold green]{prop_str}[/bold green]",
        f"[bold white]Operation Type:[/bold white] {op.operation_type.value.upper()}",
        f"[bold white]Assessed Risk:[/bold white] [{risk_color}]{op.risk_level.value.upper()}[/{risk_color}]",
    ]

    if op.risk_reasons:
        lines.append("\n[bold]Risk Factors:[/bold]")
        for r in op.risk_reasons:
            lines.append(f"  • [{risk_color}]{r}[/{risk_color}]")

    if op.actions:
        lines.append("\n[bold]Proposed Actions:[/bold]")
        for a in op.actions:
            lines.append(f"  • {a}")

    if op.reverse_dependencies:
        lines.append(
            f"\n[bold red]Reverse Dependencies Affected ({len(op.reverse_dependencies)}):[/bold red]"
        )
        for rev in op.reverse_dependencies[:8]:
            lines.append(f"  • [yellow]{rev}[/yellow]")
        if len(op.reverse_dependencies) > 8:
            lines.append(f"  • [dim]...and {len(op.reverse_dependencies) - 8} more[/dim]")

    lines.append(f"\n[bold white]Rollback Status:[/bold white] {rollback_str}")
    if op.rollback_instructions:
        lines.append(f"[dim]Guidance: {op.rollback_instructions}[/dim]")

    lines.append("\n[bold yellow]No changes have been made yet.[/bold yellow]")

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan" if op.risk_level == RiskLevel.LOW else risk_color,
        )
    )


def render_outdated_table(outdated: list[OutdatedPackage]) -> None:
    """Render a table of packages with available updates."""
    if not outdated:
        console.print("[bold green]✓ All installed packages are currently up-to-date.[/bold green]")
        return

    table = Table(title=f"Outdated Packages ({len(outdated)} update(s) available)", pad_edge=False)
    table.add_column("Package", style="bold white", min_width=18)
    table.add_column("Manager", style="cyan", min_width=14)
    table.add_column("Installed", min_width=10)
    table.add_column("Latest Compatible", style="green", min_width=14)
    table.add_column("Latest Stable", style="bold green", min_width=14)
    table.add_column("Type", min_width=10)

    for p in outdated:
        type_str = "[bold red]MAJOR[/bold red]" if p.is_major_update else "[dim]minor/patch[/dim]"
        table.add_row(
            p.name,
            p.manager,
            p.installed_version,
            p.latest_compatible_version,
            p.latest_stable_version,
            type_str,
        )

    console.print(table)


def render_operations_table(operations: list[LifecycleOperation]) -> None:
    """Render a table summarizing past lifecycle modification operations."""
    if not operations:
        console.print("[dim]No past modification operations recorded in history.[/dim]")
        return

    table = Table(title="Lifecycle Operations History", pad_edge=False)
    table.add_column("Operation ID", style="bold white", min_width=16)
    table.add_column("Type", min_width=12)
    table.add_column("Target Package", style="cyan", min_width=16)
    table.add_column("Manager", min_width=14)
    table.add_column("Previous", min_width=10)
    table.add_column("Proposed", style="green", min_width=10)
    table.add_column("Status", min_width=14)
    table.add_column("Timestamp", style="dim", min_width=20)

    for op in operations:
        status_color = "green" if op.status.value == "completed" else "red"
        if op.status.value in ("planned", "awaiting_approval"):
            status_color = "yellow"
        elif op.status.value == "executing":
            status_color = "cyan"

        prev_str = op.previous_version or "-"
        prop_str = op.proposed_version or "-"
        table.add_row(
            op.id,
            op.operation_type.value.upper(),
            op.target_package,
            op.manager,
            prev_str,
            prop_str,
            f"[{status_color}]{op.status.value}[/{status_color}]",
            op.created_at[:19].replace("T", " "),
        )

    console.print(table)


def render_package_info(info: PackageInfo) -> None:
    """Render detailed information for a specific package."""
    inst_str = info.installed_version or "[dim]Not installed[/dim]"
    latest_str = info.latest_version or "[dim]Unknown[/dim]"
    lines = [
        f"[bold white]Package Name:[/bold white] [bold cyan]{info.name}[/bold cyan]",
        f"[bold white]Manager:[/bold white] {info.manager}",
        f"[bold white]Installed Version:[/bold white] {inst_str}",
        f"[bold white]Latest Version:[/bold white] [bold green]{latest_str}[/bold green]",
        f"[bold white]Scope:[/bold white] {info.scope}",
    ]
    if info.description:
        lines.append(f"[bold white]Description:[/bold white] {info.description}")
    if info.homepage:
        lines.append(f"[bold white]Homepage:[/bold white] {info.homepage}")
    if info.license:
        lines.append(f"[bold white]License:[/bold white] {info.license}")
    if info.install_path:
        lines.append(f"[bold white]Location:[/bold white] {info.install_path}")
    if info.dependencies:
        lines.append(
            f"[bold white]Direct Dependencies ({len(info.dependencies)}):[/bold white] {', '.join(info.dependencies[:10])}"
        )
    if info.reverse_dependencies:
        lines.append(
            f"[bold white]Required By ({len(info.reverse_dependencies)}):[/bold white] [yellow]{', '.join(info.reverse_dependencies[:10])}[/yellow]"
        )

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold cyan]Package Information — {info.name}[/bold cyan]",
            border_style="cyan",
        )
    )
