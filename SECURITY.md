# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Invariants of Inventory CLI

`inv` operates under strict security boundaries designed to protect developer machines:

1. **Read-Only Invariant**: The application is strictly a software auditing and discovery utility. It contains zero code to install, delete, mutate, or upgrade packages or binaries.
2. **Controlled Version Probing**: Arbitrary binaries discovered in system PATH are never executed with arbitrary arguments. Only binaries explicitly registered in the `PROBE_ARGUMENTS_MAP` with known safe arguments (e.g. `--version`) may be probed.
3. **Subprocess Sandboxing**: All commands are executed with `shell=False` and argument arrays. Execution times are capped by hard timeouts (default 15s; probe 3s).
4. **Untrusted Manifest Parsing**: Project manifests and lockfiles are parsed statically with standard JSON and TOML parsers. No project build scripts (`setup.py`, Makefile, npm scripts) are ever run.
5. **No Credential Access**: Directories containing keys and credentials (`.ssh`, `.gnupg`, `.aws`, `.kube`, `.env`) are explicitly excluded from traversal.
6. **Local Persistence Only**: All inventory data resides in a local SQLite database (`~/Library/Application Support/inv/inv.db`). No telemetry or network transfers occur.

## Reporting a Security Concern

If you discover a security vulnerability or a violation of our safety boundaries, please report it privately:

- **Email**: `vinit@example.com`
- **Response Target**: Within 48 hours.

Please do not open public GitHub issues for security vulnerabilities until a patch has been coordinated.

