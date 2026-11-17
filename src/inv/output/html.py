"""HTML standalone report generator for software inventory."""

import html

from inv.core.models import (
    Application,
    Environment,
    ExecutableInstance,
    InstallationInstance,
    Project,
    Runtime,
    ScanSession,
)


def export_inventory_html(
    session: ScanSession | None,
    installations: list[InstallationInstance],
    executables: list[ExecutableInstance],
    applications: list[Application],
    projects: list[Project],
    environments: list[Environment],
    runtimes: list[Runtime],
) -> str:
    """Generate self-contained HTML inventory dashboard."""
    session_id = session.id if session else "N/A"
    total_items = session.total_items if session else 0
    duration = f"{session.duration_seconds:.2f}s" if session else "0s"
    started = session.started_at if session else "N/A"

    # HTML rows for installations
    inst_rows = "".join(
        f"<tr><td><b>{html.escape(i.name)}</b></td>"
        f"<td><span class='badge badge-ver'>{html.escape(i.version)}</span></td>"
        f"<td><span class='badge badge-mgr'>{html.escape(i.manager)}</span></td>"
        f"<td>{html.escape(i.scope.value)}</td>"
        f"<td class='dim'>{html.escape(str(i.install_path or i.provenance))}</td></tr>\n"
        for i in installations[:1000]
    )

    # HTML rows for executables
    exec_rows_list = []
    for e in executables[:1000]:
        dup_badge = "<span class='badge badge-dup'>DUPLICATE</span>" if e.is_duplicate else "No"
        exec_rows_list.append(
            f"<tr><td><b>{html.escape(e.name)}</b></td>"
            f"<td>{html.escape(e.version or '-')}</td>"
            f"<td>{html.escape(e.source_manager or '-')}</td>"
            f"<td>{dup_badge}</td>"
            f"<td class='dim'>{html.escape(str(e.path))}</td></tr>\n"
        )
    exec_rows = "".join(exec_rows_list)

    # HTML rows for applications
    app_rows = "".join(
        f"<tr><td><b>{html.escape(a.name)}</b></td>"
        f"<td>{html.escape(a.version or '-')}</td>"
        f"<td class='dim'>{html.escape(a.bundle_id or '-')}</td>"
        f"<td>{'System' if a.is_system else 'App'}</td>"
        f"<td class='dim'>{html.escape(str(a.path))}</td></tr>\n"
        for a in applications[:1000]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Inventory CLI Report - {session_id}</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-bright: #f0f6fc;
      --accent: #58a6ff;
      --success: #3fb950;
      --warning: #d29922;
      --badge-bg: #21262d;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    h1 {{
      color: var(--text-bright);
      margin: 0 0 8px 0;
      font-size: 28px;
    }}
    .meta {{
      font-size: 14px;
      color: #8b949e;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}
    .card-title {{
      font-size: 13px;
      color: #8b949e;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .card-value {{
      font-size: 24px;
      font-weight: bold;
      color: var(--text-bright);
    }}
    .tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    .tab {{
      background: transparent;
      border: none;
      color: var(--text);
      padding: 8px 16px;
      cursor: pointer;
      font-size: 14px;
      border-bottom: 2px solid transparent;
    }}
    .tab.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
      font-weight: bold;
    }}
    .tab-content {{
      display: none;
    }}
    .tab-content.active {{
      display: block;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      background: var(--card-bg);
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      background: #1c2128;
      color: var(--text-bright);
      font-weight: 600;
    }}
    tr:hover {{
      background: rgba(255,255,255,0.02);
    }}
    .dim {{
      color: #8b949e;
      font-size: 12px;
      word-break: break-all;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
    }}
    .badge-ver {{ background: rgba(63, 185, 80, 0.15); color: var(--success); }}
    .badge-mgr {{ background: rgba(88, 166, 255, 0.15); color: var(--accent); }}
    .badge-dup {{ background: rgba(210, 153, 34, 0.15); color: var(--warning); }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Inventory CLI Report</h1>
      <div class="meta">
        Scan Session: <b>{session_id}</b> &bull; Scanned: <b>{started}</b> &bull; Duration: <b>{duration}</b>
      </div>
    </header>

    <div class="cards">
      <div class="card">
        <div class="card-title">Discovered Entities</div>
        <div class="card-value">{total_items:,}</div>
      </div>
      <div class="card">
        <div class="card-title">Packages Installed</div>
        <div class="card-value">{len(installations):,}</div>
      </div>
      <div class="card">
        <div class="card-title">PATH Executables</div>
        <div class="card-value">{len(executables):,}</div>
      </div>
      <div class="card">
        <div class="card-title">Applications</div>
        <div class="card-value">{len(applications):,}</div>
      </div>
      <div class="card">
        <div class="card-title">Projects</div>
        <div class="card-value">{len(projects):,}</div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab active" onclick="switchTab('packages')">Packages ({len(installations)})</button>
      <button class="tab" onclick="switchTab('executables')">Executables ({len(executables)})</button>
      <button class="tab" onclick="switchTab('apps')">Applications ({len(applications)})</button>
    </div>

    <div id="tab-packages" class="tab-content active">
      <table>
        <thead>
          <tr><th>Name</th><th>Version</th><th>Manager</th><th>Scope</th><th>Install Path / Provenance</th></tr>
        </thead>
        <tbody>{inst_rows}</tbody>
      </table>
    </div>

    <div id="tab-executables" class="tab-content">
      <table>
        <thead>
          <tr><th>Name</th><th>Version</th><th>Source</th><th>Duplicate?</th><th>Path</th></tr>
        </thead>
        <tbody>{exec_rows}</tbody>
      </table>
    </div>

    <div id="tab-apps" class="tab-content">
      <table>
        <thead>
          <tr><th>Application Name</th><th>Version</th><th>Bundle Identifier</th><th>Type</th><th>Path</th></tr>
        </thead>
        <tbody>{app_rows}</tbody>
      </table>
    </div>
  </div>

  <script>
    function switchTab(name) {{
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + name).classList.add('active');
    }}
  </script>
</body>
</html>
"""
