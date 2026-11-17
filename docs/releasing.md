# Release Guide for Inventory CLI (`inv`)

This document outlines the end-to-end release process for `inv`, including prerequisites, local validation, OIDC PyPI Trusted Publishing configuration, GitHub environment setup, TestPyPI staging, and post-release verification.

---

## 1. PyPI Distribution Name Notice

> [!WARNING]
> **PyPI Name Availability Blocker**:
> The project name `inv` is currently registered on production PyPI (`https://pypi.org/project/inv/`) by Dan Trickey (`dgt`, 2019).
>
> To release to production PyPI:
> 1. Contact the current owner or submit a PEP 541 name transfer request, **OR**
> 2. Coordinate a new distribution name (such as `inv-cli` or `inventory-cli`).
>
> On **TestPyPI**, the name `inv` is currently **available** (returns 404).

---

## 2. Release Prerequisites & Account Setup

### Step A: Configure PyPI Trusted Publisher (Manual)
`inv` uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) via OpenID Connect (OIDC). No long-lived API tokens or passwords are stored in GitHub.

1. Log into your account on [PyPI](https://pypi.org/manage/account/publishing/).
2. Under **"Add a publisher"**, select **GitHub**.
3. Fill in the exact details:
   - **PyPI Project Name**: `inv` (or designated distribution name)
   - **Owner**: `VinitSurve`
   - **Repository name**: `inv`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click **Add publisher**.

### Step B: Configure GitHub `pypi` Environment (Manual)
1. Navigate to your GitHub repository: `https://github.com/VinitSurve/inv/settings/environments`.
2. Click **New environment** and enter name: `pypi`.
3. (Recommended) Under **Deployment branches and tags**, select **Selected tags** and enter rule `v*.*.*`.
4. (Optional) Configure **Required reviewers** for manual gatekeeping prior to publish.

### Step C: Configure TestPyPI Trusted Publisher (Optional / Staging)
1. Log into [TestPyPI](https://test.pypi.org/manage/account/publishing/).
2. Add a publisher:
   - **PyPI Project Name**: `inv`
   - **Owner**: `VinitSurve`
   - **Repository name**: `inv`
   - **Workflow name**: `release-testpypi.yml`
   - **Environment name**: `testpypi`
3. On GitHub (`settings/environments`), create the environment: `testpypi`.

---

## 3. Step-by-Step Release Procedure

### 1. Verify Clean Working Tree
```bash
git status
# Must output: "nothing to commit, working tree clean"
```

### 2. Verify Version Consistency
Ensure version numbers match across all locations:
- `pyproject.toml`: `version = "1.1.0"`
- `src/inv/__init__.py`: `__version__ = "1.1.0"`
- `CHANGELOG.md`: Section `## [1.1.0] - <Date>`

### 3. Run Quality & Test Suite Locally
```bash
# 1. Sync environment
uv sync --all-extras

# 2. Code style & formatting
ruff check src tests
ruff format --check src tests

# 3. Static type analysis
mypy src

# 4. Complete test suite
pytest tests/ --cov=inv
```

### 4. Build & Validate Artifacts
```bash
# Clean previous builds
rm -rf dist/

# Build sdist and wheel
uv build

# Validate with twine
uvx twine check --strict dist/*
```

Inspect the generated wheel contents to ensure development files and tests are not bundled:
```bash
uvx wheel pack dist/inv-1.1.0-py3-none-any.whl --dest-dir /tmp/check-wheel
unzip -l dist/inv-1.1.0-py3-none-any.whl
```

### 5. Staging on TestPyPI (Recommended Prior to Production)
1. Go to **Actions** > **Publish to TestPyPI** on GitHub.
2. Click **Run workflow** and type `testpypi` in the confirmation input.
3. Once completed, test installation from TestPyPI:
   ```bash
   # Use --extra-index-url so runtime dependencies (typer, rich, pydantic) resolve from production PyPI
   python -m venv /tmp/test-inv-venv
   /tmp/test-inv-venv/bin/pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ inv==1.1.0

   # Verify CLI works
   /tmp/test-inv-venv/bin/inv --version
   /tmp/test-inv-venv/bin/inv --help
   rm -rf /tmp/test-inv-venv
   ```

### 6. Production Release: Tag & Push
Once verified and PyPI name/publisher setup is confirmed:
```bash
# Create annotated signed git tag
git tag -a v1.1.0 -m "Release v1.1.0: Package lifecycle management & security audits"

# Push tag to GitHub
git push origin v1.1.0
```

### 7. Monitor Deployment & Verify
1. Monitor the GitHub Actions workflow at `https://github.com/VinitSurve/inv/actions/workflows/release.yml`.
2. The workflow will:
   - Build distributions in an isolated environment.
   - Run `twine check --strict`.
   - Mint an OIDC token via GitHub Actions and authenticate with PyPI.
   - Publish artifacts to PyPI without long-lived tokens.
3. Check the published package page on PyPI: `https://pypi.org/project/inv/`.

### 8. Post-Release Smoke Testing
Test installation using isolated global runners:

```bash
# Test with uv tool
uv tool install inv
inv --version
uv tool uninstall inv

# Test with pipx
pipx install inv
inv --version
pipx uninstall inv
```

### 9. Publish GitHub Release Notes
1. Go to `https://github.com/VinitSurve/inv/releases/new`.
2. Select tag `v1.1.0`.
3. Copy relevant notes from `CHANGELOG.md`.
4. Attach the wheel and source tarball if desired, and publish.
