# Scanner Status Matrix — Inventory CLI (`inv`)

This document records the complete operational status, discovery domain, execution strategy, and supported statuses for every scanner adapter in `inv`.

---

## 1. Scanner Roster

| Scanner ID | Domain | Target Technology | CLI / Probe Command | Output Format | Supported Statuses |
|---|---|---|---|---|---|
| `brew_formula` | `package_manager` | Homebrew Formulae | `brew info --json=v2 --installed` | Structured JSON | `success`, `partial`, `unavailable`, `failed` |
| `brew_cask` | `package_manager` | Homebrew Casks | `brew list --cask --versions` | Tabular Text | `success`, `unavailable`, `failed` |
| `macports` | `package_manager` | MacPorts | `port installed` | Tabular Text | `success`, `unavailable`, `failed` |
| `npm_global` | `package_manager` | npm Global Packages | `npm list -g --json --depth=0` | Structured JSON | `success`, `partial`, `unavailable`, `failed` |
| `pnpm_global` | `package_manager` | pnpm Global Packages | `pnpm list -g --json` | Structured JSON | `success`, `partial`, `unavailable`, `failed` |
| `yarn_global` | `package_manager` | Yarn Global Packages | `yarn global list --json` | NDJSON Events | `success`, `unavailable`, `failed` |
| `bun_global` | `package_manager` | Bun Global Packages | `bun pm ls -g` / package.json | Tabular / JSON | `success`, `unavailable`, `failed` |
| `pip` | `package_manager` | Python Pip Packages | `pip list --format=json` | Structured JSON | `success`, `unavailable`, `failed` |
| `uv` | `package_manager` | uv Tools & Pythons | `uv tool list`, `uv python list` | Tabular Text | `success`, `unavailable`, `failed` |
| `conda` | `package_manager` | Conda Envs & Packages | `conda env list --json`, `conda list --json`| Structured JSON | `success`, `partial`, `unavailable`, `failed` |
| `cargo` | `package_manager` | Cargo Crates & Rustup | `cargo install --list`, `rustup toolchain list` | Tabular Text | `success`, `unavailable`, `failed` |
| `gem` | `package_manager` | RubyGems | `gem list --local` | Tabular Text | `success`, `unavailable`, `failed` |
| `composer` | `package_manager` | PHP Composer | `composer global show --format=json` | Structured JSON | `success`, `unavailable`, `failed` |
| `go` | `package_manager` | Go Global Tools | `go version -m <bin>`, `~/go/bin` | Binary Metadata | `success`, `unavailable`, `failed` |
| `path_binaries` | `binaries` | PATH Executables | Symlink resolution & probe registry | Filesystem / Probe | `success`, `failed` |
| `applications` | `applications` | macOS Applications | Info.plist XML / Binary Plist | Plist Metadata | `success`, `failed` |
| `runtimes` | `runtimes` | Language Runtimes | Controlled probe registry & version dirs | Probe Output | `success`, `failed` |
| `environments` | `environments` | Virtual Environments | `pyvenv.cfg` & known cache dirs | Filesystem Config | `success`, `failed` |
| `projects` | `projects` | Project Repositories | Manifests & lockfile static parsers | TOML / JSON / Text | `success`, `failed` |
| `docker` | `containers` | Docker Containers & Images | `docker ps`, `docker images` | Structured JSON | `success`, `unavailable`, `failed` |
| `ide_extensions`| `extensions` | VS Code & Cursor Extensions | `package.json` in extension dirs | JSON Metadata | `success`, `unavailable`, `failed` |
| `installer_receipts`| `system` | macOS Receipts | `pkgutil --pkgs` | Text Lines | `success`, `failed` |
| `macos_system` | `system` | macOS Platform | `sw_vers`, `csrutil status` | System API / Text | `success`, `failed` |

---

## 2. Host Discovery Execution Result (macOS arm64)

```
Active Scanners: 16 succeeded, 7 unavailable, 0 failed
Total Discovered Items: 3,859 entities in 6.98s
```

- **Succeeded**: `brew_formula`, `brew_cask`, `npm_global`, `pnpm_global`, `pip`, `uv`, `conda`, `cargo`, `gem`, `path_binaries`, `applications`, `runtimes`, `environments`, `projects`, `installer_receipts`, `macos_system`.
- **Unavailable (Honest Reporting)**:
  - `macports`: Not installed on host.
  - `yarn_global`: Yarn not installed on host.
  - `bun_global`: Bun not installed on host.
  - `composer`: Composer not installed on host.
  - `go`: Go binary and `~/go/bin` absent on host.
  - `docker`: Docker daemon socket inactive on host.
  - `ide_extensions`: Standard VS Code/Cursor user extension directories absent in current profile.
- **Failed**: 0 scanners failed.

