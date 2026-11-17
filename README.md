# Inventory CLI (`inv`)

[![CI](https://github.com/VinitSurve/inv/actions/workflows/ci.yml/badge.svg)](https://github.com/VinitSurve/inv/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, local-first macOS software inventory, controlled package lifecycle management, and security audit CLI.

`inv` discovers installed packages across 13+ package managers, applications, PATH binaries, duplicate command shadowing, programming language runtimes, virtual environments, container runtimes, project manifests, and lockfile dependencies. It also provides unified package lifecycle operations (`outdated`, `install`, `remove`, `upgrade`), reverse dependency impact analysis, vulnerability detection (OSV.dev + native tools), and conservative vulnerability remediation under a strict **Controlled Execution Model**.

---

## The Problem

Modern macOS developer machines accumulate software across fragmented ecosystems: Homebrew formulae, Homebrew casks, MacPorts, npm, pnpm, Yarn, Bun, pip, uv, Conda, Cargo, RubyGems, Composer, Go tools, standalone binaries, `/Applications`, and local virtual environments.

Managing and understanding this sprawling landscape presents serious challenges:
- **Shadowed Executables**: Multiple installations of tools (e.g. Apple Python vs Homebrew Python vs Anaconda vs uv Python) silently shadow each other depending on `$PATH` ordering.
- **Untracked Software**: Manual binary downloads in `~/.local/bin` or `/usr/local/bin` escape package managers.
- **Project Dependency Drift**: Projects declare dependencies that may not be installed in their environments, or rely on undeclared global packages.
- **Security Exposure**: Undetected Common Vulnerabilities and Exposures (CVEs) linger in global and project packages without a unified audit mechanism.
- **Risky Blind Updates**: Auto-fixers and unguided package managers break system environments or remove shared libraries unexpectedly.

`inv` unifies discovery, lifecycle management, and security intelligence into a single CLI with strict safety guarantees.

---

## Core Capabilities

### 1. Unified Software Discovery
- **13+ Package Managers**: Homebrew (formulae & casks), MacPorts, npm, pnpm, Yarn, Bun, pip, uv, Conda, Cargo & Rustup, RubyGems, Composer, and Go.
- **PATH Executable Discovery**: Audits all binaries across `$PATH`, resolves symlinks, detects command shadowing, and safely probes versions.
- **macOS Applications**: Parses `/Applications`, `/System/Applications`, and `~/Applications` `Info.plist` bundles for version, bundle ID, and architecture.
- **Language Runtimes**: Discovers active and version-manager installations for Node.js, Python, Ruby, Rust, Go, Java, PHP, Swift, Bun, and Deno.
- **Virtual Environments**: Locates `.venv`, `venv`, Conda envs, Poetry virtualenvs, and Pipenv directories.
- **Project Dependency Reconciliation**: Parses project manifests (`pyproject.toml`, `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`) and verifies declared vs installed vs missing dependencies.
- **Container Discovery**: Inspects Docker containers and images with safe daemon-connectivity probing.

### 2. Controlled Package Lifecycle Management
- **Outdated Package Inspection**: Unified `inv outdated` across Homebrew, npm, pnpm, pip, uv, Cargo.
- **Dependency Impact Analysis**: `inv why <pkg>` reveals both upstream dependencies and downstream reverse dependencies that depend on the package.
- **Controlled Modifications**: Safe, preview-first `inv install`, `inv remove`, and `inv upgrade`.
- **System Integrity Protection**: Protects critical system packages (`python`, `node`, `git`, `openssl`) from accidental removal.
- **Operations Audit Log**: Every lifecycle operation is logged in SQLite (`inv operations`) with execution time, command args, status, and rollback guidance.

### 3. Vulnerability Intelligence & Remediation
- **Multi-Source Advisory Intelligence**: Aggregates vulnerability data from Google's OSV.dev batch API (PyPI, npm, crates.io, Go, etc.) and native audit tools (`pip-audit`, `npm audit`).
- **Normalized Severity Scoring**: Maps CVSS v3 vectors to standardized severity ratings (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`).
- **Conservative Remediation**: `inv audit --fix` targets the minimum non-vulnerable version, favoring compatible patch/minor upgrades and alerting on breaking major jumps.
- **Mandatory Verification**: Every remediation automatically re-audits the host system post-execution to verify that the vulnerability has been resolved.

---

## Installation

### Using `uv` (Recommended)

```bash
uv tool install inv
```

### Using `pipx`

```bash
pipx install inv
```

### From Source

```bash
git clone https://github.com/VinitSurve/inv.git
cd inv
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## Quick Start

```bash
# 1. Run full inventory discovery scan
inv scan

# 2. View summary dashboard
inv

# 3. Check for outdated packages across all managers
inv outdated

# 4. Run a security vulnerability audit
inv audit

# 5. Inspect reverse dependencies before touching a package
inv why libuv

# 6. Preview an upgrade without modifying anything
inv plan upgrade ruff --strategy latest

# 7. Check for duplicate or shadowed commands in PATH
inv duplicates

# 8. Export inventory report to HTML
inv export --format html --output inventory.html
```

---

## Command Reference

| Command | Category | Description |
|---|---|---|
| `inv` | Discovery | Default overview dashboard of latest inventory snapshot. |
| `inv scan` | Discovery | Run inventory discovery scan (`--deep`, `--json`, `--projects PATH`). |
| `inv global` | Discovery | List globally installed packages (`--manager <name>`). |
| `inv local` | Discovery | List discovered projects and declared/installed dependencies. |
| `inv tools` | Discovery | List PATH executables (`--duplicates` to filter shadowed commands). |
| `inv apps` | Discovery | List macOS applications from `/Applications` and `Info.plist`. |
| `inv runtimes` | Discovery | List installed programming language runtimes and SDKs. |
| `inv envs` | Discovery | List virtual environments, Conda envs, and version managers. |
| `inv containers` | Discovery | List Docker containers and container images. |
| `inv managers` | Discovery | Display detection status & lifecycle capabilities of package managers. |
| `inv search <query>`| Discovery | Universal search across packages, executables, apps, and projects. |
| `inv info <name>` | Discovery | Show detailed metadata and provenance for a specific software item. |
| `inv duplicates` | Discovery | Find shadowed PATH commands and multi-manager software installations. |
| `inv stats` | Discovery | Show inventory statistics, manager breakdown, and coverage metrics. |
| `inv tree` | Discovery | Visual tree hierarchy of discovered projects and dependencies. |
| `inv report` | Discovery | Comprehensive scanner health, execution duration, and warning report. |
| `inv export` | Discovery | Export inventory dataset (`--format json\|csv\|html`, `--output <path>`). |
| `inv history` | Discovery | View previous scan sessions and timing history. |
| `inv doctor` | Diagnostics | Diagnostic health check of database, scanners, and configuration. |
| `inv config` | Diagnostics | View and verify active CLI configuration. |
| `inv outdated` | Lifecycle | Check for outdated packages across all supported package managers. |
| `inv package <name>`| Lifecycle | Inspect package details, lifecycle status, and provenance. |
| `inv versions <pkg>`| Lifecycle | List available versions for a package from registry. |
| `inv why <pkg>` | Lifecycle | Show why a package is installed and what packages depend on it. |
| `inv install <pkg>` | Lifecycle | Install package with explicit confirmation (`--manager`, `--dry-run`). |
| `inv remove <pkg>` | Lifecycle | Remove package with reverse dependency warning (`--manager`, `--dry-run`).|
| `inv upgrade [pkg]` | Lifecycle | Upgrade specific package or all outdated packages (`--strategy`, `--all`). |
| `inv plan <subcmd>` | Lifecycle | Dry-run planning group (`install`, `remove`, `upgrade`, `audit-fix`). |
| `inv operations` | Operations | Audit log of lifecycle operations (`list`, `info <id>`, `verify <id>`). |
| `inv audit` | Security | Scan packages for known vulnerabilities via OSV.dev and native tools. |

---

## Safety & Security Model

`inv` is built around a **Controlled Execution Model**:

1. **No Unattended Modifications**: Every modification (`install`, `remove`, `upgrade`, `audit --fix`) requires explicit confirmation with default **NO** (`Confirm this exact operation? [y/N]`).
2. **Non-Interactive Terminal Safety**: If `sys.stdin.isatty()` is false (CI/CD scripts, automated pipes), `inv` **refuses execution** unless explicitly running dry-run planning commands.
3. **Shell-Free Execution**: Subprocesses strictly use `shell=False` and argument arrays. No shell interpolation, pipes, or command injection vectors exist.
4. **Input Sanitization**: Package names and version specifications are strictly validated against POSIX-safe patterns (`validate_package_name`, `validate_version_spec`).
5. **Reverse Dependency Protection**: Critical system packages (`python`, `node`, `git`, `openssl`) are flagged with **CRITICAL** risk and protected against accidental removal.
6. **No Secret Crawling**: Sensitive directories (`~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.kube`, `.env`, tokens) are explicitly excluded from traversal.
7. **Transparent Rollback**: All operations record prior state and recommended rollback commands in SQLite.

---

## Known Limitations & Scope

To ensure realistic expectations, `inv` operates within defined engineering boundaries:
- **Discovery Completeness**: macOS does not expose a universal registry of all software. `inv` discovers software via 23 targeted scanners across supported package managers, `$PATH`, `/Applications`, language runtimes, virtual environments, and project manifests. Unregistered or custom binaries in non-standard paths outside `$PATH` are not discovered unless explicitly configured.
- **Rollback Feasibility**: Rollbacks rely on package manager capabilities and upstream registry availability. If a prior package version was yanked from PyPI/npm or a Homebrew bottle was purged upstream, rollback will require manual intervention.
- **Vulnerability Data Scope**: Security advisories are fetched live from Google OSV.dev and native tools (`pip-audit`, `npm audit`). Undisclosed zero-days or uncataloged vulnerabilities cannot be detected.
- **Automation / Headless Environments**: By design, package modifications are rejected in headless non-interactive environments without an interactive TTY. Use `--dry-run` or `inv plan` subcommands in CI/CD.

---

## Documentation

Detailed documentation is available in the `docs/` directory:
- [Lifecycle Management Guide](docs/lifecycle-management.md): Architecture, supported manager capabilities, and rollback matrix.
- [Vulnerability Scanning](docs/vulnerability-scanning.md): OSV.dev API, native audit integration, CVSS normalization, and freshness limitations.
- [Remediation Guide](docs/remediation.md): Conservative update strategy, breaking change handling, and verification re-audit.
- [Operation Safety](docs/operation-safety.md): Controlled confirmation flow, non-interactive refusal, and shell-free subprocess safety.
- [Architecture & Design](docs/architecture.md): Subsystem breakdown, concurrency, and SQLite schema.
- [Scanner Reference](docs/scanners.md): Complete list of all 23 discovery scanners.

---

## License

MIT License. Copyright (c) 2026 Vinit.
