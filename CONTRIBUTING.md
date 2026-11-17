# Contributing to Inventory CLI (`inv`)

Thank you for your interest in contributing to **Inventory CLI (`inv`)**! We welcome contributions to expand package manager adapters, enhance deep filesystem discovery, improve security vulnerability intelligence, and maintain macOS system integrity.

---

## 1. Core Engineering Principles

`inv` is designed with strict boundaries separating read-only inspection from controlled modifications:

1. **Read-Only Discovery by Default**:
   All core discovery commands (`inv`, `inv scan`, `inv global`, `inv local`, `inv tools`, `inv apps`, `inv runtimes`, `inv envs`, `inv containers`, `inv duplicates`, `inv why`) are strictly read-only. They never install, upgrade, modify, or uninstall packages, touch user configurations, or mutate `$PATH`.
2. **Explicitly Confirmed Package Lifecycle Modifications**:
   Modification commands (`inv install`, `inv remove`, `inv upgrade`, `inv audit --fix`) operate under a strict **Controlled Execution Model**:
   - Every modification requires an explicit interactive confirmation prompt: `Confirm this exact operation? [y/N]`.
   - The default choice is always **NO** (`N`). Hitting Enter without typing `y` or `yes` immediately aborts the operation.
3. **Non-Interactive Environment Refusal**:
   In non-interactive environments (`!sys.stdin.isatty()`), such as CI/CD pipelines, cron jobs, or redirected input, all package modifications are strictly refused. Automated pipelines must use read-only dry-run commands (`--dry-run` or `inv plan`).
4. **Shell-Free Subprocess Execution**:
   All subprocess executions must use `shell=False` and explicit argument arrays. Input parameters (package names, version specs) must be validated against strict POSIX-safe patterns (`validate_package_name`, `validate_version_spec`) before execution. Arbitrary string shell commands are prohibited.
5. **Controlled Version Probing**:
   Arbitrary binaries discovered on `$PATH` must **never** be executed with arbitrary arguments. All executable version probing must go through the controlled `PROBE_ARGUMENTS_MAP` in `inv.scanners.probe`.
6. **No Code Execution During Manifest Discovery**:
   Project manifests and lockfiles must be parsed statically using safe parsers (`tomllib`, `json`, regex) without executing project scripts, build tools, or setup hooks.
7. **Supported vs. Unsupported Manager Capabilities**:
   Different package managers have different capability profiles:
   - Full lifecycle management is implemented for Homebrew formulae/casks, npm, pnpm, Python virtualenvs (PEP 668 protected), uv tools, and Cargo.
   - Managers without safe CLI lifecycle APIs (MacPorts, RubyGems, Composer, Go tools, Conda) are designated as **discovery-only** (`ReadOnlyLifecycleAdapter`). Contributors must not implement unverified or fragile lifecycle operations for read-only managers.
8. **Security Auditing & Remediation**:
   Vulnerability scanning integrates Google OSV.dev and native tools (`pip-audit`, `npm audit`). Remediation (`inv audit --fix`) must be conservative, targeting the minimum non-vulnerable version, favoring patch/minor updates, warning on breaking major changes, and requiring post-fix re-audit verification.
9. **Honest Reporting & Realistic Claims**:
   Never fabricate scanner results or claim completeness when a manager is unavailable or a scan was skipped. Every scanner reports its actual status: `success`, `partial`, `unavailable`, `unsupported`, `failed`, or `skipped`. Do not make unsupported claims such as "100% secure", "detects every package", or "guaranteed rollback".
10. **Insulated Error Handling**:
    Individual scanner or adapter failures must never crash the entire application.

---

## 2. Development Setup

`inv` requires **Python 3.11+** and uses [uv](https://github.com/astral-sh/uv) for high-speed package and environment management.

```bash
# 1. Clone the repository
git clone https://github.com/VinitSurve/inv.git
cd inv

# 2. Create virtual environment with Python 3.11+
uv venv --python 3.11
source .venv/bin/activate

# 3. Synchronize environment with all development dependencies
uv sync --all-extras
```

---

## 3. Code Standards & Testing Expectations

We enforce strict linting, formatting, type safety, and testing standards:

```bash
# Run full test suite with coverage
pytest --cov=inv --cov-report=term-missing

# Run Ruff linter and formatter checks
ruff check src tests
ruff format --check src tests

# Run strict MyPy type checking
mypy src
```

### Testing Expectations for New Features:
- **Unit Tests**: Every new model, parser, or utility function must have focused unit tests in `tests/unit/`.
- **Contract Tests**: Any new scanner or lifecycle adapter must pass the contract tests in `tests/contract/test_scanner_contracts.py` or `tests/contract/test_adapter_contracts.py`.
- **Security Tests**: Any code handling package names, arguments, or file paths must include malicious input tests in `tests/security/`.
- **No Real Host Mutations**: Tests must never perform real package installations, upgrades, removals, or system modifications on the host. Always use isolated mocks, temporary directories, or virtual test fixtures.

---

## 4. Submitting a Pull Request

1. Fork the repository and create your feature branch from `main`.
2. Ensure your changes adhere to the Core Engineering Principles.
3. Run the full verification suite (`pytest`, `ruff check`, `ruff format --check`, `mypy`).
4. Update relevant documentation in `docs/` and `CHANGELOG.md`.
5. Submit a pull request with clear evidence of test execution and output.
