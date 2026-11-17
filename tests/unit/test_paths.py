"""Unit tests for path utilities and safety checks."""

from pathlib import Path

from inv.utils.paths import is_safe_subpath, is_sensitive_path, normalize_path


def test_is_sensitive_path() -> None:
    assert is_sensitive_path(Path("/Users/user/.ssh/id_rsa")) is True
    assert is_sensitive_path(Path("/Users/user/project/.env")) is True
    assert is_sensitive_path(Path("/Users/user/.aws/credentials")) is True
    assert is_sensitive_path(Path("/Users/user/project/src/main.py")) is False
    assert is_sensitive_path(Path("/usr/local/bin/git")) is False


def test_is_safe_subpath() -> None:
    base = Path("/tmp/base_dir")
    safe_child = Path("/tmp/base_dir/subdir/file.txt")
    unsafe_escape = Path("/tmp/other_dir/file.txt")

    assert is_safe_subpath(safe_child, base) is True
    assert is_safe_subpath(unsafe_escape, base) is False


def test_normalize_path() -> None:
    norm = normalize_path(".")
    assert norm.is_absolute()
