# Package Lifecycle Management in `inv`

`inv` extends from a comprehensive software discovery tool into an explicit, controlled package lifecycle manager. It unifies operations across package managers (Homebrew, npm, pnpm, Python/pip, uv, Cargo, Bun, Yarn) without hiding native package manager mechanics or performing unattended system changes.

---

## 1. Supported Capabilities by Manager

A package manager can be supported for discovery only, or for full lifecycle modification. This distinction is visible via `inv managers`:

| Package Manager | ID | Scope | Supported Operations | Rollback Status |
| :--- | :--- | :--- | :--- | :--- |
| **Homebrew Formulae** | `brew_formula` | Global / System | `check_outdated`, `install`, `remove`, `upgrade`, `list_versions`, `resolve_dependencies`, `verify_installation` | Best-effort (bottles cleaned up by default) |
| **Homebrew Casks** | `brew_cask` | Applications | `check_outdated`, `install`, `remove`, `upgrade`, `verify_installation` | Best-effort |
| **npm** | `npm` | Global | `audit`, `check_outdated`, `install`, `remove`, `upgrade`, `list_versions`, `rollback`, `verify_installation` | Guaranteed via version tag |
| **pnpm** | `pnpm` | Global | `check_outdated`, `install`, `remove`, `upgrade`, `list_versions`, `rollback`, `verify_installation` | Guaranteed via version tag |
| **Python pip** | `pip` | Environment | `check_outdated`, `install`, `remove`, `upgrade`, `list_versions`, `rollback`, `verify_installation` | Guaranteed in virtualenv (PEP 668 protected) |
| **uv** | `uv_tool` | Global Tools | `check_outdated`, `install`, `remove`, `upgrade`, `list_versions`, `rollback`, `verify_installation` | Guaranteed via tool reinstall |
| **Rust Cargo** | `cargo` | Global Tools | `check_outdated`, `install`, `remove`, `upgrade`, `verify_installation` | Reinstall crate |
| **Bun** | `bun` | Global | `install`, `remove`, `upgrade`, `verify_installation` | Reinstall |
| **Yarn** | `yarn` | Global | `install`, `remove`, `upgrade`, `verify_installation` | Reinstall |
| **MacPorts** | `macports` | System | *Discovery Only* (Read-only) | N/A |
| **RubyGems** | `gem` | Global / Env | *Discovery Only* (Read-only) | N/A |
| **PHP Composer** | `composer` | Global / Env | *Discovery Only* (Read-only) | N/A |
| **Go Tools** | `go` | Global | *Discovery Only* (Read-only) | N/A |
| **Conda** | `conda` | Environments | *Discovery Only* (Read-only) | N/A |

---

## 2. Command Reference

### Outdated Package Detection
```bash
# Check all available managers for outdated packages
inv outdated

# Filter by package manager
inv outdated --manager brew
inv outdated --manager npm
```

### Inspect Package Details & Provenance
```bash
inv package ripgrep
inv package express --manager npm
```

### Available Versions
```bash
inv versions ruff
```

### Dependency Explanation & Reverse Dependencies
```bash
inv why python
inv why libuv
```

### Installation
```bash
# Install latest stable release
inv install ripgrep --manager brew

# Install pinned version
inv install ruff@0.3.4 --manager uv

# Dry-run preview
inv install express --manager npm --dry-run
```

### Removal
```bash
# Remove with reverse dependency impact analysis
inv remove jq --manager brew

# Preview removal
inv remove typescript --manager npm --dry-run
```

### Upgrading
```bash
# Upgrade specific package with compatible strategy
inv upgrade ruff --strategy compatible

# Upgrade specific package to latest stable
inv upgrade ruff --strategy latest

# Upgrade all outdated packages in batch mode
inv upgrade --all
```

### Planning (Strictly Read-Only)
```bash
inv plan install ripgrep --manager brew
inv plan remove python --manager brew
inv plan upgrade ruff --strategy latest
inv plan audit-fix
```

### Operations History & Audit Trails
```bash
# List past modification operations
inv operations

# Inspect execution logs and event history
inv operations info op_9b2e1f408a2c

# Re-verify system state matches recorded operation
inv operations verify op_9b2e1f408a2c
```
