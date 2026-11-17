# Vulnerability Remediation in `inv`

`inv` provides conservative, transparent vulnerability remediation. Unlike aggressive auto-fixers that blindly update packages and break production code, `inv` follows a strict principle: **No unattended changes, no breaking major upgrades without explicit consent, and mandatory post-fix verification**.

---

## 1. Remediation Architecture

```
Vulnerability Findings
         │
         ▼
RemediationEngine.generate_remediation_plan()
         │
         ├─ Filter for fixable vulnerabilities (fixed_version present)
         ├─ Group by package manager and environment
         ├─ Target minimum non-vulnerable version (conservative SemVer)
         └─ Assess blast radius & breaking change risks
         │
         ▼
LifecyclePlan Generated (state: PROPOSED, requires approval)
         │
         ▼
Controlled Interactive Preview & Confirmation
         │
    User Confirms?
    ├── NO  ──► Abort operation (0 changes made)
    └── YES ──► LifecycleExecutor runs update commands with timeouts
                     │
                     ▼
             Post-Fix Verification Re-Audit
             - Was target package upgraded?
             - Has advisory been cleared?
             - Log verification to operations history
```

---

## 2. Conservative Update Strategy

When remedying a vulnerability, `inv` calculates the safest viable target version:

1. **Patch / Minor Preference**: If the fixed version is within the same major version range (e.g., current: `1.2.0`, fixed: `1.2.4`), `inv` prefers the patch release to prevent breaking API changes.
2. **Minimum Viable Fix**: If fixing requires crossing a major version boundary (e.g., current: `2.8.0`, fixed: `3.0.0`), `inv` marks the risk level as **HIGH** or **CRITICAL** and explicitly warns the user that breaking changes may occur.
3. **Unfixable Advisories**: If no fixed version is known (0-day or discontinued package), `inv` flags the advisory as `UNFIXABLE`, provides upstream references, and does **not** attempt dummy upgrades.

---

## 3. What `inv` Refuses to Touch

To protect system integrity, `inv` strictly refuses to modify:

1. **System Python (`/usr/bin/python3`, PEP 668)**:
   - Python packages installed into macOS system Python or externally managed environments without virtual environments will not be modified by `inv`.
   - `inv` will suggest activating a virtualenv or using `uv tool` / `pipx`.
2. **Critical Core System Packages**:
   - `python`, `node`, `git`, `openssl`, `glibc`, `bash` when identified as root dependencies of the host system.
3. **Read-Only / Discovery-Only Managers**:
   - Packages installed via MacPorts, system installer receipts (`.pkg`), PHP Composer, or Conda environments are reported as discovery-only; `inv` will not execute unverified commands against them.
4. **Git Dirty Workspaces**:
   - In project lockfile remediation, uncommitted Git changes in project manifests trigger a warning before modification.

---

## 4. Remediation Workflow

### Step 1: Preview the Remediation Plan
```bash
inv audit --plan
```
This lists every vulnerability with its target package, current version, required fixed version, and risk rating without modifying anything.

### Step 2: Review and Execute Fix
```bash
inv audit --fix
```
Output preview:
```
Operation ID: op_c09e84d2a10f
Action: REMEDIATION / BATCH UPGRADE
Packages affected:
  • requests: 2.25.1 -> 2.31.0 (Fixes CVE-2023-32681)
  • urllib3: 1.26.4 -> 1.26.18 (Fixes CVE-2023-45803)

Risk Level: MEDIUM
Reversible: YES (via pip rollback)

Confirm this exact operation? [y/N]:
```

### Step 3: Automated Verification
Following execution, `inv` immediately re-runs the security audit on the affected targets. If any vulnerability remains unmitigated, `inv` flags the operation status as `FAILED_VERIFICATION` in the operations history and alerts the user.

---

## 5. Rollback Guidance

Every lifecycle operation stores a complete snapshot in the SQLite operations log (`inv operations`):

```bash
# Inspect operation log
inv operations info op_c09e84d2a10f
```

- **Python Virtualenv**: Rollback commands are provided (e.g., `pip install requests==2.25.1`).
- **npm / pnpm / uv**: Previous exact versions are retained in event metadata for 1-command restoration.
- **Homebrew**: Homebrew bottles are purged by default upstream; `inv` documents specific commit-based or tap-based rollback commands when available.
