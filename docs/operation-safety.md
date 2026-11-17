# Operation Safety & Controlled Execution in `inv`

`inv` adheres to a strict **Controlled Execution Model**. System modifications must be intentional, predictable, isolated, and completely verifiable.

---

## 1. Controlled Confirmation Policy

Every modification command (`inv install`, `inv remove`, `inv upgrade`, `inv audit --fix`):

1. **Calculates a plan**: Identifies targets, evaluates dependencies, determines risk level, and generates precise CLI argument arrays.
2. **Displays a rich visual preview**: Shows all target packages, version transitions, impacted dependents, and reversibility status.
3. **Requests explicit confirmation**:
   ```
   Confirm this exact operation? [y/N]:
   ```
   - Default is always **NO** (`N`).
   - Hitting `<Enter>` without typing `y` or `yes` aborts the operation cleanly.

---

## 2. Non-Interactive Environment Safety

In non-interactive shells (CI/CD environments, scripts, cron jobs, redirected `stdin`):

- `sys.stdin.isatty()` evaluates to `False`.
- `inv` will **refuse to execute any modification** and exit with code `1`:
  ```
  Error: Refusing to execute operation in non-interactive terminal without explicit confirmation.
  Hint: Use --dry-run to preview operations in automation or CI/CD pipelines.
  ```
- This prevents unattended or script-injected package installations or removals from altering system state.

---

## 3. Reverse Dependency & System Integrity Protection

### Critical Package Safeguard
`inv` maintains an internal index of system-critical packages (`python`, `node`, `git`, `openssl`, `glibc`, `bash`, `zsh`, `curl`).

If a removal or destructive operation targets a critical package:
- Risk is elevated to **CRITICAL**.
- Highlighting is rendered in bold red with prominent warnings.
- Dependent packages that would be broken by removal are listed explicitly.

### Reverse Dependency Analysis (`inv why`)
Before removing or upgrading any package, `inv` queries native package graphs:
- Homebrew: `brew uses --installed <formula>`
- npm: `npm ls <package>`
- pip: internal dependency graph resolution

If active packages depend on the target, `inv` warns:
```
WARNING: The following 3 installed packages depend on 'libuv':
  - neovim (brew)
  - node (brew)
  - cmake (brew)
Removing or altering 'libuv' may break these packages.
```

---

## 4. Shell-Free Command Execution

All subprocess executions in `inv`:
- Use `shell=False` exclusively.
- Use explicit argument vectors (e.g., `["brew", "install", package_name]`).
- Validate package names and version specifications using strict POSIX-safe regular expressions (`^[a-zA-Z0-9_@/.-]+$`), preventing command chaining (`&&`, `|`), path traversals, or shell injection attacks.
- Enforce strict execution timeouts (default 300s) to prevent runaway subprocesses or hangs.

---

## 5. Rollback Limitations & Reality-Based Recovery

Unlike transactional databases, native macOS package managers do not universally support atomic multi-package rollbacks. `inv` is transparent about these physical constraints:

| Package Ecosystem | Rollback Mechanism | Guarantee Level |
| :--- | :--- | :--- |
| **npm global** | `npm install -g <pkg>@<previous_version>` | High |
| **pnpm global** | `pnpm add -g <pkg>@<previous_version>` | High |
| **Python Virtualenv** | `pip install <pkg>==<previous_version>` | High |
| **uv tools** | `uv tool install <pkg>==<previous_version>` | High |
| **Homebrew** | Formula bottle caching / tap pinning | Best-effort (bottles frequently purged upstream) |
| **Cargo crates** | `cargo install --version <previous_version> <pkg>` | High (source rebuild required) |

For every executed operation, `inv` records the exact previous state in the `lifecycle_operations` SQLite database table. You can inspect the recorded previous state and recommended manual or automated rollback commands at any time using:

```bash
inv operations info <operation_id>
```

