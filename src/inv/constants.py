"""Constants and enumerations for the Inventory CLI."""

from enum import StrEnum
from pathlib import Path


class ScannerStatus(StrEnum):
    """Scanner execution outcome status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"
    SKIPPED = "skipped"


class InstallScope(StrEnum):
    """Scope of an installed package or tool."""

    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"
    SYSTEM = "system"


class DependencyStatus(StrEnum):
    """Status of a declared project dependency."""

    INSTALLED = "installed"
    DECLARED = "declared"
    MISSING = "missing"
    UNVERIFIED = "unverified"


class EnvironmentType(StrEnum):
    """Types of development and virtual environments."""

    VENV = "venv"
    CONDA = "conda"
    UV = "uv"
    POETRY = "poetry"
    PIPENV = "pipenv"
    NVM = "nvm"
    FNM = "fnm"
    ASDF = "asdf"
    VOLTA = "volta"
    PYENV = "pyenv"
    RUSTUP = "rustup"
    GOENV = "goenv"
    RBENV = "rbenv"


class PackageManagerType(StrEnum):
    """Supported package managers."""

    BREW_FORMULA = "brew_formula"
    BREW_CASK = "brew_cask"
    MACPORTS = "macports"
    NPM = "npm"
    PNPM = "pnpm"
    YARN = "yarn"
    BUN = "bun"
    PIP = "pip"
    UV_TOOL = "uv_tool"
    UV_PROJECT = "uv_project"
    CONDA = "conda"
    CARGO = "cargo"
    GEM = "gem"
    COMPOSER = "composer"
    GO = "go"


# Default application metadata
APP_NAME = "inv"
APP_DISPLAY_NAME = "Inventory CLI"
DEFAULT_DB_FILENAME = "inv.db"

# Subprocess & traversal safety limits
DEFAULT_PROCESS_TIMEOUT = 15.0  # seconds
PROBE_PROCESS_TIMEOUT = 3.0  # seconds for version probe executions
DEFAULT_MAX_WALK_DEPTH = 5
MAX_FILESYSTEM_ENTRIES = 50_000
MAX_SYMLINK_DEPTH = 10

# Well-known macOS binary directories
COMMON_BIN_DIRS = [
    Path("/usr/local/bin"),
    Path("/opt/homebrew/bin"),
    Path("/opt/homebrew/sbin"),
    Path("/usr/bin"),
    Path("/bin"),
    Path("/usr/sbin"),
    Path("/sbin"),
    Path.home() / ".local" / "bin",
    Path.home() / ".cargo" / "bin",
    Path.home() / "go" / "bin",
    Path.home() / ".npm-global" / "bin",
    Path.home() / "Library" / "pnpm",
    Path.home() / ".bun" / "bin",
]

# Well-known macOS application directories
COMMON_APP_DIRS = [
    Path("/Applications"),
    Path("/System/Applications"),
    Path("/System/Applications/Utilities"),
    Path.home() / "Applications",
]

# Traversal directory exclusions (safety & performance)
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cvs",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    ".cache",
    "Library/Caches",
    ".Trash",
    "Pods",
    "DerivedData",
    "build",
    "dist",
    "target",
}
