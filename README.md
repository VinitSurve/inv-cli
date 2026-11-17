# Inventory CLI (`inv`)

[![CI](https://github.com/VinitSurve/inv/actions/workflows/ci.yml/badge.svg)](https://github.com/VinitSurve/inv/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, local-first macOS software inventory and audit CLI. Discovers installed packages across 13+ package managers, applications, PATH binaries, duplicate command shadowing, programming language runtimes, virtual environments, container runtimes, project manifests, and lockfile dependencies.

---

## The Problem

Modern macOS developer machines accumulate software across fragmented ecosystems: Homebrew formulae, Homebrew casks, MacPorts, npm, pnpm, Yarn, Bun, pip, uv, conda, Cargo, RubyGems, Composer, Go tools, standalone binaries, `/Applications`, and local virtual environments.

Managing and understanding this sprawling landscape presents serious challenges:
- **Shadowed Executables**: Multiple installations of tools (e.g. Apple Python vs Homebrew Python vs Anaconda vs uv Python) silently shadow each other depending on `$PATH` ordering.
- **Untracked Software**: Manual binary downloads in `~/.local/bin` or `/usr/local/bin` escape package managers.
- **Project Dependency Drift**: Projects declare dependencies that may not be installed in their environments, or rely on undeclared global packages.
- **No Unified Inventory**: No single tool existed to give a complete, read-only, structured snapshot of all software installed on a Mac without executing arbitrary scripts.

`inv` solves this by providing a unified, read-only, high-performance inventory CLI.

---

## Key Features

- **13+ Package Managers**: Homebrew (formulae & casks), MacPorts, npm, pnpm, Yarn, Bun, pip, uv, Conda, Cargo & Rustup, RubyGems, Composer, and Go.
- **PATH Executable Discovery**: Audits all binaries across `$PATH`, resolves symlinks, detects command shadowing, and safely probes versions using a strictly controlled version probe registry.
- **macOS Applications**: Parses `/Applications`, `/System/Applications`, and `~/Applications` `Info.plist` bundles for version, bundle identifier, and architecture metadata.
- **Language Runtimes**: Discovers active and version-manager installations for Node.js, Python, Ruby, Rust, Go, Java, PHP, Swift, Bun, and Deno.
- **Virtual Environments**: Locates `.venv`, `venv`, Conda envs, Poetry virtualenvs, and Pipenv directories.
- **Project Dependency Reconciliation**: Parses project manifests (`pyproject.toml`, `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`) and verifies whether declared dependencies are installed or missing.
- **Container Discovery**: Inspects Docker containers and images with safe daemon-connectivity probing.
- **SQLite Persistence & Incremental Scans**: Fast, transactional storage in WAL mode with historical scan auditing.
- **Multiple Export Formats**: Terminal tables, formatted JSON, CSV, and self-contained interactive HTML dashboards.
- **Strict Security Guarantee**: 100% read-only. Never executes arbitrary binaries or project scripts. Never requires `sudo`.

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

# 3. List globally installed packages
inv global

# 4. Check for duplicate or shadowed commands in PATH
inv duplicates

# 5. Search for any package, application, or binary
inv search ffmpeg

# 6. Export inventory report to HTML
inv export --format html --output inventory.html
```

---

## Command Reference

| Command | Description |
|---|---|
| `inv` | Default overview dashboard of the latest inventory snapshot. |
| `inv scan` | Run an inventory discovery scan (`--deep`, `--json`, `--projects PATH`, `--no-projects`). |
| `inv global` | List globally installed packages (`--manager <name>`). |
| `inv local` | List discovered projects and declared/installed dependencies. |
| `inv tools` | List PATH executables (`--duplicates` to filter shadowed commands). |
| `inv apps` | List macOS applications from `/Applications` and `Info.plist`. |
| `inv runtimes` | List installed programming language runtimes and SDKs. |
| `inv envs` | List virtual environments, Conda envs, and version managers. |
| `inv containers` | List Docker containers and container images. |
| `inv managers` | Display detection status and availability of all package managers. |
| `inv search <query>` | Universal search across packages, executables, applications, and projects. |
| `inv info <name>` | Show detailed metadata and provenance for a specific software item. |
| `inv duplicates` | Find shadowed PATH commands and multi-manager software installations. |
| `inv stats` | Show inventory statistics, manager breakdown, and coverage metrics. |
| `inv tree` | Visual tree hierarchy of discovered projects and dependencies. |
| `inv report` | Comprehensive scanner health, execution duration, and warning report. |
| `inv export` | Export inventory dataset (`--format json\|csv\|html`, `--output <path>`). |
| `inv history` | View previous scan sessions and timing history. |
| `inv doctor` | Diagnostic health check of database, scanners, and configuration. |
| `inv config` | View and verify active CLI configuration. |

---

## Architecture Overview

```
                      ┌────────────────────────┐
                      │    inv CLI (Typer)     │
                      └───────────┬────────────┘
                                  │
                      ┌───────────▼────────────┐
                      │    InventoryEngine     │
                      └───────────┬────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
┌──────────▼──────────┐ ┌─────────▼──────────┐ ┌─────────▼──────────┐
│  ScannerRegistry    │ │   ScanCoordinator  │ │   InventoryRepo    │
│  (18+ BaseScanners) │ │(ThreadPoolExecutor)│ │ (SQLite / WAL Mode)│
└─────────────────────┘ └────────────────────┘ └────────────────────┘
           │
 ┌─────────┴────────────────────────────────────────┐
 │ Scanners:                                        │
 │ • package_managers: brew, npm, pnpm, uv, pip...  │
 │ • binaries: PATH executables, probe registry     │
 │ • applications: macOS .app bundles & Info.plist  │
 │ • projects: manifests, lockfiles & dependencies  │
 │ • runtimes: node, python, ruby, rust, go, java   │
 │ • environments: .venv, conda, poetry, pipenv     │
 │ • containers: docker containers & images         │
 └──────────────────────────────────────────────────┘
```

---

## Scanner Support Matrix

| Scanner | Domain | Availability Detection | Structured Output | Notes |
|---|---|---|---|---|
| `brew_formula` | Package Manager | `brew` in PATH | JSON (`brew info --json=v2`) | Fallback to tabular list |
| `brew_cask` | Package Manager | `brew` in PATH | Tabular (`brew list --cask --versions`) | macOS GUI applications |
| `macports` | Package Manager | `port` in PATH | Tabular (`port installed`) | System scope |
| `npm_global` | Package Manager | `npm` in PATH | JSON (`npm list -g --json`) | Global Node packages |
| `pnpm_global` | Package Manager | `pnpm` in PATH | JSON (`pnpm list -g --json`) | Global pnpm packages |
| `yarn_global` | Package Manager | `yarn` in PATH | JSON (`yarn global list --json`) | Global Yarn packages |
| `bun_global` | Package Manager | `bun` in PATH | Manifest / Tabular (`bun pm ls -g`) | Global Bun packages |
| `pip` | Package Manager | `pip` or `pip3` in PATH | JSON (`pip list --format=json`) | Python environment |
| `uv` | Package Manager | `uv` in PATH | Tabular (`uv tool list`, `uv python list`) | Managed tools & Python runtimes |
| `conda` | Package Manager | `conda` in PATH | JSON (`conda env list --json`, `conda list --json`) | Conda environments & packages |
| `cargo` | Package Manager | `cargo` or `rustup` | Tabular (`cargo install --list`) | Installed crates & toolchains |
| `gem` | Package Manager | `gem` in PATH | Tabular (`gem list --local`) | Ruby gems |
| `composer` | Package Manager | `composer` in PATH | JSON (`composer global show --format=json`) | PHP packages |
| `go` | Package Manager | `go` or `~/go/bin` | Binary module inspection (`go version -m`) | Go tools |
| `path_binaries` | Binaries | `$PATH` set | Controlled probe registry | Resolves symlinks, detects duplicates |
| `applications` | Applications | `/Applications` | `plistlib` XML/Binary Plist parser | Info.plist metadata |
| `runtimes` | Runtimes | PATH & directories | Controlled probe registry | Node, Python, Ruby, Rust, Go, etc. |
| `environments` | Environments | Filesystem | `pyvenv.cfg` parser | `.venv`, Conda, Poetry, Pipenv |
| `projects` | Projects | Filesystem | Manifest & lockfile parsers | Declared vs installed vs missing |
| `docker` | Containers | `docker` in PATH | JSON (`docker ps`, `docker images`) | Safe daemon probe |
| `ide_extensions`| Extensions | Filesystem | `package.json` parser | VS Code & Cursor extensions |

---

## Security Model

`inv` enforces strict security invariants:
1. **100% Read-Only**: Never installs, uninstalls, modifies configuration, or updates packages.
2. **Never Executes Discovered Executables Arbitrarily**: Arbitrary binaries discovered on PATH are **never executed**. Only binaries registered in the safe, controlled `PROBE_ARGUMENTS_MAP` may be executed, strictly with read-only arguments (e.g. `--version`).
3. **No Shell Execution**: `shell=False` is enforced across all subprocess executions.
4. **Subprocess Timeouts**: Every subprocess execution is bounded by a strict timeout (default 15.0s, probe 3.0s).
5. **No Manifest Code Execution**: Project files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`) are parsed statically using standard parsers (`tomllib`, `json`, regex). Never executes `setup.py` or build scripts.
6. **No Secret Crawling**: Skips sensitive directories (`~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.kube`, `.env`, tokens, credentials).
7. **Safe Symlink Resolution**: Detects cyclic symlink loops and limits traversal depth.

---

## License

MIT License. Copyright (c) 2026 Vinit.

