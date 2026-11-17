# Changelog

All notable changes to the **Inventory CLI (`inv-cli`)** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-11-17

### Changed
- **Packaging & Distribution Identity**: Migrated PyPI distribution identity to `inv-cli` (GitHub: `VinitSurve/inv-cli`) while preserving the `inv` terminal CLI executable and `inv` Python import package.

### Added
- **Package Lifecycle Management**:
  - Unified lifecycle adapters for Homebrew (`brew_formula`, `brew_cask`), npm, pnpm, pip, uv, Cargo, Bun, and Yarn.
  - Explicit read-only lifecycle adapter for MacPorts, Gem, Composer, Go, and Conda.
  - New lifecycle CLI commands: `inv outdated`, `inv package`, `inv versions`, `inv why`, `inv install`, `inv remove`, `inv upgrade`.
  - Planning subcommands: `inv plan install`, `inv plan remove`, `inv plan upgrade`, `inv plan audit-fix`.
  - Operation history tracking: `inv operations list`, `inv operations info`, `inv operations verify`.
- **Dependency Impact Analysis**:
  - Directed `DependencyGraph` model analyzing direct, transitive, and reverse dependencies.
  - Reverse dependency detection (`brew uses --installed`, `npm ls`, pip dependency trees).
  - Risk assessment flagging system-critical packages (`python`, `node`, `git`, `openssl`) as `CRITICAL` risk and reverse dependencies as `HIGH` risk.
- **Security & Vulnerability Intelligence**:
  - Google OSV.dev batch API integration (`https://api.osv.dev/v1/querybatch`) for PyPI, npm, crates.io, Go, and Ruby.
  - Native security audit integrations (`pip-audit`, `npm audit --json`).
  - Canonical vulnerability record deduplication across CVE, GHSA, and OSV identifiers.
  - Standardized CVSS v3 severity mapping (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`).
  - Rich terminal vulnerability tables with colorized severity badges and JSON export (`inv audit`).
- **Conservative Vulnerability Remediation**:
  - Remediation plan generation targeting minimum non-vulnerable versions.
  - Preferential patch/minor SemVer upgrades with warnings for major breaking jumps.
  - Automated post-remediation verification re-audit (`inv audit --fix`).
- **Controlled Execution & Safety Engine**:
  - Mandatory interactive confirmation with default-NO (`[y/N]`) for all system modifications.
  - Non-interactive terminal safety: execution refused if `sys.stdin.isatty()` is False.
  - Strictly shell-free execution (`shell=False`) with POSIX argument vectors and input sanitization (`validate_package_name`, `validate_version_spec`).
  - PEP 668 protection: refusal to modify system Python environments.
- **Storage & Database Migrations**:
  - Schema V2 migration adding `vulnerabilities`, `lifecycle_operations`, `operation_events`, and `outdated_packages` tables with performance indexes.
  - Full CRUD and audit trail persistence in `InventoryRepository`.
- **Extended Test Suite**:
  - 34 new tests covering lifecycle adapters, dependency graphs, security models, storage repositories, mock security audits, and lifecycle CLI flows (113 total passing tests).
- **Comprehensive Documentation**:
  - Added `docs/lifecycle-management.md`, `docs/vulnerability-scanning.md`, `docs/remediation.md`, and `docs/operation-safety.md`.

---

## [1.0.0] - 2026-11-17

### Added
- **Core CLI Engine**: Implemented `inv` with 19 interactive commands using Typer and Rich.
- **13+ Package Manager Adapters**:
  - Homebrew formulae (`brew info --json=v2` and fallback tabular inspection).
  - Homebrew casks (`brew list --cask --versions`).
  - MacPorts packages (`port installed`).
  - npm global packages (`npm list -g --json`).
  - pnpm global packages (`pnpm list -g --json`).
  - Yarn global packages (`yarn global list --json`).
  - Bun global packages (`bun pm ls -g`).
  - Python pip packages in current/active environments (`pip list --format=json`).
  - uv tools and managed Python runtimes (`uv tool list`, `uv python list`).
  - Conda environments and installed packages (`conda env list --json`, `conda list --json`).
  - Cargo packages and Rustup toolchains (`cargo install --list`, `rustup toolchain list`).
  - RubyGems (`gem list --local`).
  - PHP Composer (`composer global show --format=json`).
  - Go global tools (`go version -m` and `~/go/bin` inspection).
- **Binary & PATH Discovery**:
  - Full PATH audit and symlink resolution.
  - Command shadowing and duplicate detection.
  - Controlled version probe registry for safe `--version` extraction without executing arbitrary binaries.
- **Application Discovery**:
  - Scanning `/Applications`, `/System/Applications`, `~/Applications`.
  - `Info.plist` parsing for bundle ID, versions, minimum OS, and system bundle identification.
- **Project & Dependency Discovery**:
  - Manifest parsers for Python (`pyproject.toml`, `requirements.txt`), Node (`package.json`), Rust (`Cargo.toml`), Go (`go.mod`), and Ruby (`Gemfile`).
  - Distinction between declared, installed, and missing dependencies.
- **Container Discovery**:
  - Docker containers and images with safe daemon accessibility checks.
- **SQLite Persistence & Multi-Format Export**:
  - High-performance SQLite database with WAL mode and foreign key constraints.
  - JSON, CSV, and standalone self-contained HTML report exports.
- **Comprehensive Test Suite**:
  - 79 passing unit, contract, integration, regression, security, and performance tests.
