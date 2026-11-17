# Security Audit Report — Inventory CLI (`inv`)

Date: 2026-11-17  
Auditor: Antigravity Security Assessment  
Target: `inv` version 1.0.0 codebase (`src/inv/`)  
Result: **PASSED (Zero High/Medium Vulnerabilities)**  

---

## 1. Threat Model & Scope

`inv` operates locally on macOS systems, interacting with filesystem paths, external package manager CLIs, and project manifests. The threat model evaluates:
1. **Malicious / Corrupted Project Repositories**: Untrusted manifests attempting arbitrary code execution via build hooks.
2. **Path Traversal & Malicious Symlinks**: Directory structures crafted with cyclic symlinks or traversing into restricted parent directories.
3. **Command Injection**: Package names or CLI arguments containing shell metacharacters.
4. **Credential Leakage**: Unintended scanning or exposure of SSH keys, cloud credentials, or secrets.
5. **Denial of Service**: Giant directory trees or stalled subprocesses hanging the tool.

---

## 2. Security Assessment & Audit Findings

### 2.1 Subprocess & Command Execution
- **Finding**: Strict prohibition of `shell=True`. All command invocations throughout the codebase utilize `run_command(argv, ...)` with explicit list arguments.
- **Controlled Version Probe Registry**: Arbitrary discovered binaries in PATH are **never executed**. Only binaries present in `PROBE_ARGUMENTS_MAP` (`inv.scanners.probe`) with pre-approved read-only argument lists (e.g. `["--version"]`) can be executed.
- **Process Timeouts**: Every subprocess execution is guarded by `subprocess.TimeoutExpired` handling with a maximum timeout (default 15.0s; probe 3.0s).
- **Status**: **PASS**.

### 2.2 Filesystem Traversal & Symlink Safety
- **Cycle Detection**: `resolve_symlink_safely` implements a visited-inode set to identify and terminate symlink cycles immediately (`is_loop=True`).
- **Depth Boundaries**: Max walk depth defaults to 5 (`DEFAULT_MAX_WALK_DEPTH`), and max entry count is capped at 50,000 entries.
- **Sensitive Directory Exclusion**: Paths containing `.ssh`, `.gnupg`, `.aws`, `.azure`, `.kube`, `.password-store`, `.env`, and secret keys are automatically rejected before traversal.
- **Status**: **PASS**.

### 2.3 Untrusted Manifest Parsing
- **Static Parsing**: `parse_package_json`, `parse_pyproject_toml`, `parse_requirements_txt`, `parse_cargo_toml`, `parse_go_mod`, and `parse_gemfile` use standard `tomllib`, `json`, and regular expressions.
- **No Hook Execution**: No `setup.py`, `Makefile`, or arbitrary build scripts are evaluated.
- **Status**: **PASS**.

### 2.4 Data Storage & Local Invariant
- **SQLite Transactions**: Schema migrations and session saves execute inside atomic transactions with WAL mode.
- **Zero Remote Communications**: No network requests or telemetry endpoints exist in the application.
- **Status**: **PASS**.

---

## 3. Residual Risks & Operational Guidance

- **macOS Permissions**: Traversal of user directories like `~/Library` or external volumes may trigger macOS TCC (Transparency, Consent, and Control) prompts. `inv` gracefully handles `PermissionError` and records diagnostic warnings rather than failing.
- **Read-Only Guarantee**: `inv` contains zero mutation routines (no install, uninstall, or write routines outside its own SQLite database).

