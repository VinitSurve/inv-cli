"""Filesystem path utilities and security validations."""

from pathlib import Path

# Paths that must never be traversed or inspected for security / privacy
RESTRICTED_DIR_NAMES = {
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    ".config/gcloud",
    ".kube",
    ".password-store",
    ".keychain",
    ".vault",
}

RESTRICTED_FILE_PATTERNS = {
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    ".env",
    ".env.local",
    ".env.production",
    "credentials",
    "secrets.json",
    "secrets.yaml",
    "token",
}


def normalize_path(path: str | Path) -> Path:
    """Expand user tilde and convert to absolute Path."""
    p = Path(path).expanduser()
    try:
        return p.resolve()
    except (OSError, RuntimeError):
        return p.absolute()


def is_sensitive_path(path: Path) -> bool:
    """Check whether a path points to sensitive credentials or secret storage."""
    # Check directory parts
    for part in path.parts:
        if part in RESTRICTED_DIR_NAMES:
            return True
    # Check filename
    return path.name in RESTRICTED_FILE_PATTERNS


def is_safe_subpath(target: Path, base: Path) -> bool:
    """Ensure target path does not escape base directory via traversal."""
    try:
        norm_target = target.resolve()
        norm_base = base.resolve()
        return norm_target == norm_base or norm_base in norm_target.parents
    except (OSError, RuntimeError):
        return False
