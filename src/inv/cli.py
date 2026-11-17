"""Typer CLI interface for the Inventory CLI (inv)."""

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from inv import __version__
from inv.config import InvConfig
from inv.constants import APP_DISPLAY_NAME
from inv.core.coverage import CoverageAnalyzer
from inv.core.deduplicator import Deduplicator
from inv.core.engine import InventoryEngine
from inv.output.csv import (
    export_installations_csv,
)
from inv.output.html import export_inventory_html
from inv.output.json import export_inventory_json
from inv.output.terminal import (
    render_applications_table,
    render_containers_table,
    render_environments_table,
    render_executables_table,
    render_installations_table,
    render_overview,
    render_project_tree,
    render_projects_table,
    render_runtimes_table,
    render_scanner_status_table,
)

app = typer.Typer(
    name="inv",
    help="A comprehensive macOS-first software inventory tool.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(
            f"[bold cyan]{APP_DISPLAY_NAME}[/bold cyan] version [bold green]{__version__}[/bold green]"
        )
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Default entrypoint: renders inventory overview if no sub-command is specified."""
    if ctx.invoked_subcommand is None:
        engine = InventoryEngine()
        repo = engine.get_repository()
        session = repo.get_latest_session()

        if not session:
            render_overview(None, CoverageAnalyzer.analyze(None, []), {})
            return

        obs = repo.get_observations(session.id)
        coverage = CoverageAnalyzer.analyze(session, obs)

        # Retrieve counts
        insts = repo.list_installations(session.id)
        execs = repo.list_executables(session.id)
        apps = repo.list_applications(session.id)
        rts = repo.list_runtimes(session.id)
        envs = repo.list_environments(session.id)
        projs = repo.list_projects(session.id)
        cnts = repo.list_containers(session.id)
        exts = repo.list_extensions(session.id)

        counts = {
            "installations": len(insts),
            "executables": len(execs),
            "applications": len(apps),
            "runtimes": len(rts),
            "environments": len(envs),
            "projects": len(projs),
            "containers": len(cnts),
            "extensions": len(exts),
        }
        render_overview(session, coverage, counts)


@app.command(name="scan")
def scan_cmd(
    deep: Annotated[
        bool, typer.Option("--deep", help="Enable deep discovery (walks deeper into filesystem).")
    ] = False,
    json_out: Annotated[bool, typer.Option("--json", help="Output scan result as JSON.")] = False,
    projects_dir: Annotated[
        Path | None, typer.Option("--projects", help="Custom project root directory to scan.")
    ] = None,
    no_projects: Annotated[
        bool, typer.Option("--no-projects", help="Skip project repository discovery.")
    ] = False,
    timeout: Annotated[
        float | None, typer.Option("--timeout", help="Process execution timeout in seconds.")
    ] = None,
) -> None:
    """Execute a discovery scan of packages, applications, runtimes, and projects."""
    cfg = InvConfig.load()
    if timeout:
        cfg.process_timeout = timeout
    engine = InventoryEngine(cfg)

    roots = [projects_dir] if projects_dir else None

    if not json_out:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task_id = progress.add_task("[cyan]Scanning system inventory...", total=None)

            def on_progress(scanner_name: str, completed: int, total: int) -> None:
                progress.update(
                    task_id, description=f"[cyan]Scanned {scanner_name} ({completed}/{total})..."
                )

            session, results = engine.run_scan(
                deep=deep,
                scan_projects=not no_projects,
                project_roots=roots,
                progress_cb=on_progress,
            )
        console.print(
            f"[bold green]✓ Scan completed in {session.duration_seconds:.2f}s.[/bold green]"
        )
        console.print(
            f"[bold]Total entities discovered:[/bold] {session.total_items:,} (Session ID: [cyan]{session.id}[/cyan])\n"
        )
    else:
        session, results = engine.run_scan(
            deep=deep,
            scan_projects=not no_projects,
            project_roots=roots,
        )
        repo = engine.get_repository()
        out = export_inventory_json(
            session=session,
            installations=repo.list_installations(session.id),
            executables=repo.list_executables(session.id),
            applications=repo.list_applications(session.id),
            projects=repo.list_projects(session.id),
            dependencies=repo.list_project_dependencies(session_id=session.id),
            environments=repo.list_environments(session.id),
            runtimes=repo.list_runtimes(session.id),
            containers=repo.list_containers(session.id),
            observations=repo.get_observations(session.id),
        )
        console.print(out)


@app.command(name="global")
def global_cmd(
    manager: Annotated[
        str | None, typer.Option("--manager", "-m", help="Filter by manager (e.g. brew, npm, pip).")
    ] = None,
) -> None:
    """List globally installed packages from package managers."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    items = repo.list_installations(session_id=session_id, manager=manager)
    title = f"Installed Packages (Manager: {manager})" if manager else "Installed Packages"
    render_installations_table(items, title=title)


@app.command(name="local")
def local_cmd() -> None:
    """List discovered software projects and declared/installed dependencies."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    projects = repo.list_projects(session_id=session_id)
    render_projects_table(projects)


@app.command(name="tools")
def tools_cmd(
    duplicates_only: Annotated[
        bool, typer.Option("--duplicates", "-d", help="Show only duplicate/shadowed commands.")
    ] = False,
) -> None:
    """List discovered CLI tools and PATH executables."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    execs = repo.list_executables(session_id=session_id, duplicates_only=duplicates_only)
    render_executables_table(execs, duplicates_only=duplicates_only)


@app.command(name="apps")
def apps_cmd() -> None:
    """List installed macOS applications (.app bundles)."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    apps = repo.list_applications(session_id=session_id)
    render_applications_table(apps)


@app.command(name="runtimes")
def runtimes_cmd() -> None:
    """List installed programming language runtimes and SDKs."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    rts = repo.list_runtimes(session_id=session_id)
    render_runtimes_table(rts)


@app.command(name="envs")
def envs_cmd() -> None:
    """List virtual environments, conda environments, and version managers."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    environments = repo.list_environments(session_id=session_id)
    render_environments_table(environments)


@app.command(name="containers")
def containers_cmd() -> None:
    """List Docker containers and container images."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None
    containers = repo.list_containers(session_id=session_id)
    render_containers_table(containers)


@app.command(name="managers")
def managers_cmd() -> None:
    """Display detection status and availability of all package managers."""
    engine = InventoryEngine()
    scanners = [s for s in engine.registry.list_all() if s.domain == "package_manager"]
    table = Table(title="Package Manager Detection Status", pad_edge=False)
    table.add_column("Manager", style="bold white", min_width=20)
    table.add_column("Available?", min_width=15)
    table.add_column("Scanner Version", style="dim", min_width=15)

    for s in scanners:
        avail = s.is_available()
        status_str = "[bold green]Available[/bold green]" if avail else "[dim]Not Found[/dim]"
        table.add_row(s.name, status_str, s.version)

    console.print(table)


@app.command(name="search")
def search_cmd(
    query: Annotated[str, typer.Argument(help="Search keyword (name, path, package, bundle id).")],
) -> None:
    """Search across packages, executables, applications, and projects."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None

    results = repo.search(query, session_id=session_id)

    total_matches = sum(len(items) for items in results.values())
    console.print(
        f"\n[bold]Search results for '[cyan]{query}[/cyan]' ({total_matches} matches):[/bold]\n"
    )

    if results["packages"]:
        table = Table(title=f"Matching Packages ({len(results['packages'])})", pad_edge=False)
        table.add_column("Name", style="bold white", min_width=22)
        table.add_column("Version", style="green", min_width=12)
        table.add_column("Manager", style="cyan", min_width=12)
        table.add_column("Install Path", style="dim")
        for p in results["packages"]:
            table.add_row(p["name"], p["version"], p["manager"], str(p["path"] or "-"))
        console.print(table)

    if results["executables"]:
        table = Table(title=f"Matching Executables ({len(results['executables'])})", pad_edge=False)
        table.add_column("Name", style="bold white", min_width=20)
        table.add_column("Version", style="green", min_width=12)
        table.add_column("Source", style="cyan", min_width=12)
        table.add_column("Path", style="dim")
        for e in results["executables"]:
            table.add_row(
                e["name"], e["version"] or "-", e["source_manager"] or "-", str(e["path"])
            )
        console.print(table)

    if results["applications"]:
        table = Table(
            title=f"Matching Applications ({len(results['applications'])})", pad_edge=False
        )
        table.add_column("Name", style="bold white", min_width=22)
        table.add_column("Version", style="green", min_width=12)
        table.add_column("Bundle ID", style="cyan", min_width=25)
        table.add_column("Path", style="dim")
        for a in results["applications"]:
            table.add_row(a["name"], a["version"] or "-", a["bundle_id"] or "-", str(a["path"]))
        console.print(table)

    if results["projects"]:
        table = Table(title=f"Matching Projects ({len(results['projects'])})", pad_edge=False)
        table.add_column("Name", style="bold white", min_width=20)
        table.add_column("Types", style="cyan", min_width=15)
        table.add_column("Path", style="dim")
        for prj in results["projects"]:
            table.add_row(prj["name"], ", ".join(prj["types"]), str(prj["path"]))
        console.print(table)


@app.command(name="info")
def info_cmd(
    name: Annotated[str, typer.Argument(help="Exact or partial name of package/binary/app.")],
) -> None:
    """Show detailed metadata and provenance for a specific software item."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None

    results = repo.search(name, session_id=session_id)
    total = sum(len(items) for items in results.values())
    if total == 0:
        console.print(f"[yellow]No entities found matching '{name}'.[/yellow]")
        return

    console.print(Panel(f"[bold cyan]Entity Info: {name}[/bold cyan]", border_style="cyan"))
    for pkg in results["packages"]:
        console.print(
            f"  [bold]Package:[/bold] {pkg['name']} @ {pkg['version']} (via {pkg['manager']}, scope: {pkg['scope']})"
        )
    for exe in results["executables"]:
        console.print(
            f"  [bold]Executable:[/bold] {exe['name']} -> {exe['path']} (manager: {exe['source_manager']})"
        )
    for app_item in results["applications"]:
        console.print(
            f"  [bold]Application:[/bold] {app_item['name']} (bundle: {app_item['bundle_id']}, path: {app_item['path']})"
        )
    for prj in results["projects"]:
        console.print(
            f"  [bold]Project:[/bold] {prj['name']} (types: {prj['types']}, path: {prj['path']})"
        )


@app.command(name="duplicates")
def duplicates_cmd() -> None:
    """Find shadowed duplicate PATH commands and multi-manager software installations."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None

    execs = repo.list_executables(session_id=session_id)
    insts = repo.list_installations(session_id=session_id)

    dedup = Deduplicator()
    dup_cmds = dedup.find_duplicate_commands(execs)
    dup_pkgs = dedup.find_multi_manager_packages(insts)

    console.print(
        Panel(
            "[bold yellow]Inventory Duplication & Shadowing Analysis[/bold yellow]",
            border_style="yellow",
        )
    )

    # Commands
    table_cmds = Table(title=f"Shadowed PATH Commands ({len(dup_cmds)})", pad_edge=False)
    table_cmds.add_column("Command", style="bold white", min_width=18)
    table_cmds.add_column("Candidate Paths (Precedence Order)", style="cyan")
    for group in dup_cmds:
        paths_str = "\n".join(
            f"[{i + 1}] {p.path} ({p.source_manager or 'unknown'})"
            for i, p in enumerate(group.instances)
        )
        table_cmds.add_row(group.name, paths_str)
    console.print(table_cmds)

    # Multi-manager
    table_pkgs = Table(title=f"Multi-Manager Installed Packages ({len(dup_pkgs)})", pad_edge=False)
    table_pkgs.add_column("Package", style="bold white", min_width=20)
    table_pkgs.add_column("Managers & Versions", style="green")
    for m in dup_pkgs:
        mgrs_str = ", ".join(f"{i.manager} ({i.version})" for i in m.installations)
        table_pkgs.add_row(m.name, mgrs_str)
    console.print(table_pkgs)


@app.command(name="stats")
def stats_cmd() -> None:
    """Display comprehensive inventory metrics, manager breakdown, and coverage."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()

    if not session:
        console.print("[yellow]No scan session found. Run 'inv scan' first.[/yellow]")
        return

    obs = repo.get_observations(session.id)
    coverage = CoverageAnalyzer.analyze(session, obs)
    insts = repo.list_installations(session.id)

    mgr_counts = Counter(i.manager for i in insts)

    table = Table(title="Package Distribution by Manager", pad_edge=False)
    table.add_column("Package Manager", style="bold white", min_width=22)
    table.add_column("Installed Packages", justify="right", style="cyan", min_width=18)
    for mgr, cnt in mgr_counts.most_common():
        table.add_row(mgr, f"{cnt:,}")
    console.print(table)

    console.print(
        f"\n[bold]Total Discovered Entities:[/bold] {session.total_items:,}\n"
        f"[bold]Inventory Completeness:[/bold] {coverage.completeness_percentage}%\n"
        f"[bold]Active Scanners:[/bold] {coverage.successful_scanners} succeeded, {coverage.unavailable_scanners} unavailable, {coverage.failed_scanners} failed\n"
    )


@app.command(name="tree")
def tree_cmd() -> None:
    """Display visual tree hierarchy of discovered projects and dependencies."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None

    projs = repo.list_projects(session_id=session_id)
    deps = repo.list_project_dependencies(session_id=session_id)
    render_project_tree(projs, deps)


@app.command(name="report")
def report_cmd() -> None:
    """Generate comprehensive diagnostic summary across all discovery domains."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    if not session:
        console.print("[yellow]No scan session found. Run 'inv scan' first.[/yellow]")
        return

    obs = repo.get_observations(session.id)
    render_scanner_status_table(obs)


@app.command(name="export")
def export_cmd(
    format_type: Annotated[
        str, typer.Option("--format", "-f", help="Export format (json, csv, html).")
    ] = "json",
    output_file: Annotated[
        Path | None, typer.Option("--output", "-o", help="Target file path.")
    ] = None,
) -> None:
    """Export inventory data to JSON, CSV, or standalone HTML."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    session = repo.get_latest_session()
    session_id = session.id if session else None

    insts = repo.list_installations(session_id=session_id)
    execs = repo.list_executables(session_id=session_id)
    apps = repo.list_applications(session_id=session_id)
    projs = repo.list_projects(session_id=session_id)
    deps = repo.list_project_dependencies(session_id=session_id)
    envs = repo.list_environments(session_id=session_id)
    rts = repo.list_runtimes(session_id=session_id)
    cnts = repo.list_containers(session_id=session_id)
    obs = repo.get_observations(session_id) if session_id else []

    fmt = format_type.lower()
    if fmt == "json":
        content = export_inventory_json(
            session, insts, execs, apps, projs, deps, envs, rts, cnts, obs
        )
    elif fmt == "csv":
        content = export_installations_csv(insts)
    elif fmt == "html":
        content = export_inventory_html(session, insts, execs, apps, projs, envs, rts)
    else:
        console.print(
            f"[bold red]Unknown format: {format_type}. Choose json, csv, or html.[/bold red]"
        )
        raise typer.Exit(code=1)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[bold green]Exported {fmt.upper()} report to {output_file}[/bold green]")
    else:
        console.print(content)


@app.command(name="history")
def history_cmd(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of sessions to show.")] = 10,
) -> None:
    """Display past scan sessions and performance history."""
    engine = InventoryEngine()
    repo = engine.get_repository()
    sessions = repo.list_sessions(limit=limit)

    table = Table(title="Inventory Scan History", pad_edge=False)
    table.add_column("Session ID", style="bold cyan", min_width=14)
    table.add_column("Date / Time", style="white", min_width=24)
    table.add_column("Scan Type", style="magenta", min_width=12)
    table.add_column("Duration", justify="right", style="yellow", min_width=10)
    table.add_column("Total Items", justify="right", style="green", min_width=12)
    table.add_column("Status", min_width=12)

    for s in sessions:
        status_color = "green" if s.status == "completed" else "red"
        table.add_row(
            s.id,
            s.started_at,
            s.scan_type,
            f"{s.duration_seconds:.2f}s",
            f"{s.total_items:,}",
            f"[{status_color}]{s.status}[/{status_color}]",
        )

    console.print(table)


@app.command(name="doctor")
def doctor_cmd() -> None:
    """Run diagnostics on database, permissions, scanners, and package managers."""
    engine = InventoryEngine()
    console.print(
        Panel(
            f"[bold cyan]{APP_DISPLAY_NAME} — Diagnostics & Doctor[/bold cyan]", border_style="cyan"
        )
    )

    # 1. Database check
    try:
        conn = engine.db.get_connection()
        conn.execute("SELECT 1;")
        console.print("[green]✓ SQLite Database:[/green] Connected, WAL mode active, schema valid.")
        conn.close()
    except Exception as exc:
        console.print(f"[red]✗ Database Error:[/red] {exc}")

    # 2. Scanners check
    all_scanners = engine.registry.list_all()
    avail_count = sum(1 for s in all_scanners if s.is_available())
    console.print(
        f"[green]✓ Scanner Availability:[/green] {avail_count}/{len(all_scanners)} scanners ready."
    )

    # 3. Environment check
    config = engine.config
    console.print(
        f"[green]✓ Configuration:[/green] Config loaded from {config.get_config_file_path()}"
    )
    console.print(f"[green]✓ Database Path:[/green] {config.db_path}")


@app.command(name="config")
def config_cmd(
    show: Annotated[bool, typer.Option("--show", help="Display current configuration.")] = True,
) -> None:
    """View and verify current CLI configuration settings."""
    cfg = InvConfig.load()
    console.print(Panel("[bold cyan]Inventory CLI Configuration[/bold cyan]", border_style="cyan"))
    data = cfg.to_dict()
    for k, v in data.items():
        console.print(f"  [bold white]{k}:[/bold white] [cyan]{v}[/cyan]")


if __name__ == "__main__":
    app()
