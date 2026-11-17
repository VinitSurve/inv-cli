"""Custom exceptions for the Inventory CLI."""


class InvError(Exception):
    """Base exception for all inv errors."""


class ConfigurationError(InvError):
    """Raised when configuration is invalid or missing."""


class StorageError(InvError):
    """Raised when SQLite storage fails or is corrupted."""


class ScannerError(InvError):
    """Raised when an error occurs during scanner execution."""


class ProcessExecutionError(InvError):
    """Raised when a subprocess fails, times out, or encounters permission issues."""

    def __init__(self, message: str, exit_code: int | None = None, stderr: str = "") -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class SecurityViolationError(InvError):
    """Raised when a security boundary (symlink cycle, path traversal) is breached."""


class SafeSymlinkError(SecurityViolationError):
    """Raised when a symlink violates safety invariants."""


class ReconcilerError(InvError):
    """Raised during inventory reconciliation or deduplication."""

