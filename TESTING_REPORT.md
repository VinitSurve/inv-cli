# Testing & Verification Report — Inventory CLI (`inv`)

Date: 2026-11-17  
Test Framework: pytest 9.2.0, pytest-cov 7.1.0, pytest-timeout 2.4.0  
Python: 3.11.7 (CPython darwin arm64)  
Status: **100% Passing**  

---

## 1. Executive Summary

| Category | Tests | Passed | Failed | Skipped |
|---|---|---|---|---|
| Unit Tests | 22 | 22 | 0 | 0 |
| Contract Tests | 4 | 4 | 0 | 0 |
| Integration Tests | 28 | 28 | 0 | 0 |
| Security Tests | 6 | 6 | 0 | 0 |
| Regression Tests | 3 | 3 | 0 | 0 |
| Performance Tests | 3 | 3 | 0 | 0 |
| Smoke Tests | 13 | 13 | 0 | 0 |
| **Total** | **79** | **79** | **0** | **0** |

---

## 2. Test Suites Breakdown

### Unit Tests (`tests/unit/`)
- `test_models.py`: Verification of deterministic ID generation, `SoftwareIdentity`, `InstallationInstance`, `ExecutableInstance`, `Project`, `ProjectDependency`, `Application`, `Environment`, and `Runtime` models.
- `test_normalizer.py`: Cross-ecosystem package name normalization, scoped package handling (`@babel/core`), and version string sanitization.
- `test_deduplicator.py`: PATH duplicate command candidate detection and multi-manager software installation clustering.
- `test_reconciler.py`: Project dependency verification against global packages.
- `test_paths.py`: Sensitive directory identification (`.ssh`, `.aws`, `.env`) and subpath traversal boundaries.
- `test_symlinks.py`: Safe resolution, broken link detection, and circular symlink loop guards.
- `test_versions.py`: Semver regex extraction and numerical component parsing.
- `test_config.py`: Default settings, serialization, and deserialization from JSON.

### Scanner Contract Tests (`tests/contract/`)
- `test_contract_available_manager`: Tests scanner execution under standard operational conditions.
- `test_contract_missing_manager`: Verifies missing manager triggers `ScannerStatus.UNAVAILABLE` with clear diagnostic warnings.
- `test_contract_crashing_scanner_resilience`: Verifies uncaught exceptions inside `scan()` are trapped by `execute()` without crashing the scan process.
- `test_contract_subprocess_timeout`: Verifies subprocess timeout handling.

### Integration Tests (`tests/integration/`)
- `test_cli_smoke.py`: Smoke execution of all 19 CLI commands via Typer `CliRunner`.
- `test_manifests.py`: Static parsing of `package.json`, `pyproject.toml`, `requirements.txt`, `Cargo.toml`, and `go.mod`.
- `test_storage_sqlite.py`: SQLite persistence, WAL mode, foreign keys, and transaction rollback on simulated failures.
- `test_package_managers_mocked.py`: Mocked structured output parsing for Homebrew, npm, pip, uv, conda, cargo, gem, composer, and docker.
- `test_engine_integration.py`: End-to-end scan pipeline execution and repository retrieval.

### Security Tests (`tests/security/`)
- Command injection defense verification (`shell=False`).
- Controlled version probe registry enforcement (blocks probing arbitrary binaries).
- Sensitive credentials directory exclusion.
- Symlink circular loop protection.
- Malformed manifest recovery.
- Traversal depth bounds enforcement.

### Performance Tests (`tests/performance/`)
- Large synthetic project tree traversal (50 repos in < 1.0s).
- Large inventory deduplication speed (5,000 executables in < 0.2s).
- Parallel scanner execution bounded time (8 scanners with thread pool in < 0.35s).

---

## 3. Linter & Static Analysis Verification

- **Ruff Linting**: `ruff check src tests` passed with 0 errors.
- **Ruff Formatting**: `ruff format --check src tests` passed with 0 errors.
- **MyPy Type Checking**: `mypy src` passed with 0 issues in 68 source files (strict mode).
- **Packaging Build**: `python -m build` successfully produced `inv-1.0.0.tar.gz` and `inv-1.0.0-py3-none-any.whl`.
- **Clean Wheel Install**: Verified wheel installation in an isolated virtual environment.
