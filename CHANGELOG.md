# Changelog

All notable changes to the **Inventory CLI (`inv`)** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

