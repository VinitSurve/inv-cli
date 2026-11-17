# Scanners Reference & Contract — Inventory CLI (`inv`)

## 1. Scanner Contract Specification

Every scanner adapter in `inv` must inherit from `BaseScanner` and satisfy the following interface:

```python
class BaseScanner(ABC):
    @property
    @abstractmethod
    def scanner_id(self) -> str:
        """Unique machine-readable scanner identifier."""

    @property
    @abstractmethod
    def domain(self) -> str:
        """Target domain: 'package_manager', 'binaries', 'applications', etc."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if prerequisites or manager binaries exist on the machine."""

    @abstractmethod
    def scan(self, context: ScanContext) -> ScanResult:
        """Execute discovery and return structured ScanResult."""
```

### 1.1 Supported Statuses

- **`success`**: Scanner completed normally with full data discovery.
- **`partial`**: Scanner discovered some items but encountered non-fatal issues (e.g. Docker client present but daemon socket unavailable).
- **`unavailable`**: Prerequisites or CLI tools are not installed on the host machine.
- **`unsupported`**: Host operating system or platform cannot run this scanner.
- **`failed`**: Execution crashed or timed out.
- **`skipped`**: Explicitly excluded by configuration (`disabled_scanners`).

---

## 2. Controlled Version Probe Registry

Arbitrary discovered binaries in `$PATH` are **never executed directly**.
To discover tool versions, `inv` maintains `PROBE_ARGUMENTS_MAP` in `src/inv/scanners/probe.py`:

```python
PROBE_ARGUMENTS_MAP = {
    "python": ["--version"],
    "python3": ["--version"],
    "node": ["--version"],
    "git": ["--version"],
    "cargo": ["--version"],
    "docker": ["--version"],
    # ...
}
```

If a binary is not registered in this map, `can_probe_version()` returns `False`, and no process is spawned.
When probed, commands execute with a strict 3.0s timeout and `shell=False`.

