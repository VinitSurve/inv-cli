# Contributing to Inventory CLI (`inv`)

Thank you for your interest in contributing to **Inventory CLI (`inv`)**! We welcome contributions to expand package manager adapters, enhance deep filesystem discovery, and improve macOS system intelligence.

---

## 1. Core Engineering Principles

1. **Read-Only Invariant**: `inv` is strictly a discovery and audit tool. It must never install, upgrade, modify, or uninstall packages, touch user configurations, or mutate `$PATH`.
2. **Never Execute Arbitrary Discovered Binaries**: Arbitrary binaries discovered on PATH must **never** be executed with arbitrary arguments. All executable version probing must go through the controlled `PROBE_ARGUMENTS_MAP` in `inv.scanners.probe`.
3. **No Code Execution During Manifest Discovery**: Project manifests and lockfiles must be parsed statically without executing project scripts or setup hooks.
4. **Honest Reporting**: Never fabricate scanner results or claim completeness when a manager is unavailable or a scan was skipped. Every scanner reports its actual status: `success`, `partial`, `unavailable`, `unsupported`, `failed`, or `skipped`.
5. **Robust Error Insulation**: Individual scanner failures must never crash the entire discovery session.
6. **Local-First & Zero Telemetry**: `inv` never transmits inventory data or contacts remote servers without explicit user invocation.

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

# 3. Install in editable mode with all development dependencies
uv pip install -e ".[dev]"
```

---

## 3. Code Standards & Tooling

We enforce strict linting, formatting, and typing standards using `ruff`, `mypy`, and `pytest`.

```bash
# Run full test suite with coverage
pytest --cov=inv --cov-report=term-missing

# Run Ruff linter and formatter checks
ruff check src tests
ruff format --check src tests

# Run strict MyPy type checking
mypy src
```

---

## 4. Submitting a Pull Request

1. Fork the repository and create your branch from `main`.
2. If you've added a new scanner or modified models, add corresponding unit and contract tests in `tests/`.
3. Ensure all tests, linter checks, and type checks pass cleanly.
4. Update relevant documentation in `docs/` and `SCANNER_STATUS.md`.
5. Submit a pull request with a clear description of the problem solved and test evidence.

