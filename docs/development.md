# Development & Contributor Guide — Inventory CLI (`inv`)

## 1. Quick Development Setup

```bash
# Clone the repository
git clone https://github.com/VinitSurve/inv.git
cd inv

# Initialize virtual environment with Python 3.11+
uv venv --python 3.11
source .venv/bin/activate

# Install in editable mode with development dependencies
uv pip install -e ".[dev]"
```

---

## 2. Running Quality Checks

### Run Unit, Contract, and Integration Tests
```bash
pytest -v
```

### Run Test Coverage
```bash
pytest --cov=inv --cov-report=term-missing
```

### Run Linter & Formatter Verification
```bash
ruff check src tests
ruff format --check src tests
```

### Run Type Checking
```bash
mypy src
```

---

## 3. Adding a New Scanner

To add a new scanner adapter:
1. Create a module under `src/inv/scanners/` (e.g. `src/inv/scanners/package_managers/myscanner.py`).
2. Subclass `BaseScanner`.
3. Implement `scanner_id`, `domain`, `name`, `is_available()`, and `scan(context: ScanContext)`.
4. Register your scanner in `src/inv/core/registry.py`.
5. Add unit and contract tests in `tests/contract/` and `tests/integration/`.
6. Run `ruff format` and `mypy src`.

