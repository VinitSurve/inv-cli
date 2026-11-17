# Data Model Specification — Inventory CLI (`inv`)

## 1. Important Inventory Distinctions

A fundamental principle of `inv` is never confusing:
- **Declared dependencies** (dependencies specified in manifests like `pyproject.toml` or `package.json`).
- **Installed dependencies** (packages physically present in `site-packages` or `node_modules`).
- **Package-manager metadata** (receipts and package registries).
- **Executable binaries** (executable files discovered on `$PATH`).
- **Applications** (`.app` bundles in `/Applications`).
- **Virtual environments** (isolated runtime environments).
- **Container contents** (images and running containers).

---

## 2. Core Entities

### 2.1 SoftwareIdentity
Represents the canonical identity of a package across ecosystems.
- `id`: Deterministic hash (`ecosystem:canonical_name`).
- `name`: Human-readable package name.
- `canonical_name`: Lowercased and normalized name.
- `ecosystem`: Target ecosystem (`brew`, `npm`, `python`, `cargo`, etc.).
- `description`: Summary text.
- `homepage`: Upstream URL.
- `license`: Software license.

### 2.2 InstallationInstance
Represents a physical installation of a software package. Multiple installations of the same package across different managers (e.g. `rg` via brew and `rg` via cargo) remain independently identifiable.
- `id`: Deterministic hash (`software_id:version:manager:path`).
- `software_id`: Foreign key referencing `SoftwareIdentity`.
- `name`: Installation package name.
- `version`: Installed version string.
- `install_path`: Physical filesystem path.
- `manager`: Package manager (`brew_formula`, `npm`, `pip`, etc.).
- `scope`: `global`, `user`, `project`, or `system`.
- `provenance`: How this installation was discovered.

### 2.3 ExecutableInstance
Represents a discovered executable command file in `$PATH`.
- `id`: Deterministic hash (`name:path`).
- `name`: Command name (e.g. `python3`).
- `path`: Discovered file path.
- `canonical_path`: Resolved real path after symlink resolution.
- `is_symlink`: Boolean.
- `version`: Version string extracted via controlled probe registry.
- `source_manager`: Inferred manager (`brew`, `conda`, `system`, etc.).
- `is_duplicate`: Flagged True if shadowed by another executable earlier in `$PATH`.

### 2.4 Project & ProjectDependency
- **`Project`**: Discovered software repository containing manifests or lockfiles.
- **`ProjectDependency`**: A dependency entry declared in a manifest, tracked with status:
  - `installed`: Verified in local project `.venv` or `node_modules`.
  - `declared`: Specified in manifest but not verified locally.
  - `missing`: Project install directory exists, but the package is absent.
  - `unverified`: No local installation directory found.

### 2.5 Application
Represents an installed macOS `.app` bundle.
- `name`: Application name from `CFBundleDisplayName` or `CFBundleName`.
- `bundle_id`: `CFBundleIdentifier` (e.g. `com.apple.Safari`).
- `version`: `CFBundleShortVersionString`.
- `build_number`: `CFBundleVersion`.
- `is_system`: True if in `/System` or owned by Apple.

### 2.6 Environment & Runtime
- **`Environment`**: Development runtime environment (`venv`, `conda`, `poetry`, `nvm`).
- **`Runtime`**: Installed programming language interpreter or SDK (`Python`, `Node.js`, `Rust`, `Go`).

### 2.7 ScannerObservation & ScanSession
- **`ScannerObservation`**: Records duration, status, item counts, warnings, and errors per scanner.
- **`ScanSession`**: Records scan duration, timestamp, total items, and execution summary.

