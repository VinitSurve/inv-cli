# Security Architecture & Threat Model — Inventory CLI (`inv`)

## 1. Security Architecture

`inv` is designed with defensive programming principles:

```
[System Input]
       │
       ▼
 ┌──────────────────────────────────────────────┐
 │             Input Sanitization               │
 │ • No shell=True execution                    │
 │ • Path traversal validation                  │
 │ • Sensitive path exclusion (.ssh, .env, etc) │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │         Controlled Version Probe             │
 │ • Pre-approved binary allowlist only         │
 │ • Bounded timeouts (3.0s)                    │
 │ • Read-only arguments only (--version)       │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │         Static Manifest Parsers              │
 │ • No script execution (no setup.py / hooks) │
 │ • Safe tomllib, json, regex parsing only     │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │         Local SQLite Persistence             │
 │ • No remote network requests                 │
 │ • Transactional WAL mode                     │
 └──────────────────────────────────────────────┘
```

## 2. Threat Analysis & Mitigations

### 2.1 Untrusted Projects & Manifests
- **Threat**: A scanned directory contains a malicious `setup.py`, `Makefile`, or package install hook.
- **Mitigation**: `inv` **never** runs project scripts, build tools, or installers. It inspects manifests via static text, JSON, and TOML parsers only.

### 2.2 Malicious Symlink Traversal
- **Threat**: An attacker creates circular symlinks or symlinks pointing outside the repository to consume CPU or escape boundaries.
- **Mitigation**: `resolve_symlink_safely` tracks visited inodes to detect loops and enforce a strict recursion depth limit (10).

### 2.3 Secret and Credential Exposure
- **Threat**: The scanner discovers private SSH keys, AWS credentials, or API tokens.
- **Mitigation**: `ExclusionRules` and `is_sensitive_path` explicitly reject `.ssh`, `.gnupg`, `.aws`, `.azure`, `.kube`, `.env`, and secret file patterns.

### 2.4 Command Injection via Subprocesses
- **Threat**: Discovered paths or package names contain shell operators (`;`, `|`, `&&`).
- **Mitigation**: All subprocess calls pass explicit `list[str]` arguments with `shell=False`. Shell interpreters are never invoked.
