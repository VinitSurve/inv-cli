# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |

---

## Security Invariants of Inventory CLI (`inv`)

`inv` operates under strict security boundaries designed to protect developer machines and operating system integrity:

### 1. Controlled Modification Policy
- `inv` **never performs unattended package modifications**.
- Every operation that alters packages (`install`, `remove`, `upgrade`, `audit --fix`) requires explicit interactive confirmation with default **NO** (`[y/N]`).
- In non-interactive environments (`!sys.stdin.isatty()`), execution is strictly refused unless using read-only dry-run commands (`--dry-run` or `inv plan`).

### 2. Controlled Version Probing & Shell Safety
- Discovered binaries on `$PATH` are **never executed arbitrarily**. Only binaries registered in the safe, controlled `PROBE_ARGUMENTS_MAP` with known read-only arguments (e.g. `--version`) are executed.
- All subprocesses use `shell=False` and explicit argument vectors. No string commands are passed to the shell.
- Package names and version specifications are strictly validated against POSIX-safe patterns (`validate_package_name`, `validate_version_spec`), preventing command injection or directory traversal.
- Every subprocess execution is bounded by a hard timeout (default 15.0s; probe 3.0s; lifecycle operations 300.0s).

### 3. Static Manifest Parsing
- Project manifests and lockfiles (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`) are parsed statically with standard parsers (`tomllib`, `json`, regex).
- `inv` never runs project build scripts (`setup.py`, Makefile, npm postinstall scripts).

### 4. System Protection & PEP 668 Compliance
- `inv` refuses to mutate Python packages installed into macOS system Python (`/usr/bin/python3`) or externally managed environments.
- Critical system packages (`python`, `node`, `git`, `openssl`, `glibc`, `bash`, `zsh`, `curl`) are protected with **CRITICAL** risk warnings and reverse dependency analysis.

### 5. No Credential Access & Data Isolation
- Directories containing keys and credentials (`.ssh`, `.gnupg`, `.aws`, `.kube`, `.env`) are explicitly excluded from filesystem traversal.
- All inventory snapshots and operation audit trails reside exclusively in a local SQLite database (`~/Library/Application Support/inv/inv.db`).
- Network requests are strictly limited to official, authenticated advisory endpoints (Google OSV.dev batch API `https://api.osv.dev/v1/querybatch`) for vulnerability auditing.

---

## Reporting a Security Concern

If you discover a security vulnerability or a violation of our safety boundaries, please report it privately:

- **Email**: `vinit@example.com`
- **Response Target**: Within 48 hours.

Please do not open public GitHub issues for security vulnerabilities until a patch has been coordinated.
