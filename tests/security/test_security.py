"""Security verification tests for read-only invariants and untrusted input defense."""

from pathlib import Path

from inv.discovery.exclusions import ExclusionRules
from inv.discovery.filesystem import safe_walk_projects
from inv.discovery.manifests import parse_manifest
from inv.discovery.symlinks import resolve_symlink_safely
from inv.scanners.probe import can_probe_version, probe_executable_version
from inv.utils.paths import is_sensitive_path
from inv.utils.process import run_command


def test_command_injection_defense() -> None:
    # Attempt command injection in run_command
    # Shell operators must NOT execute because shell=False
    payload = "echo hello; touch /tmp/inv_pwned_marker"
    run_command([payload], timeout=2.0)
    # The binary name itself is the whole payload string, which should fail or not execute second command
    assert not Path("/tmp/inv_pwned_marker").exists()


def test_probe_registry_blocks_arbitrary_binaries() -> None:
    # Unknown binaries must NEVER be probeable
    assert can_probe_version("rm") is False
    assert can_probe_version("sudo") is False
    assert can_probe_version("nc") is False
    assert can_probe_version("my_custom_script.sh") is False
    assert can_probe_version("python3") is True
    assert can_probe_version("git") is True

    # Calling probe_executable_version on unlisted binary returns None without execution
    res = probe_executable_version("sh", Path("/bin/sh"))
    assert res is None


def test_sensitive_path_exclusion() -> None:
    rules = ExclusionRules()
    assert is_sensitive_path(Path("/Users/test/.ssh/id_rsa")) is True
    assert is_sensitive_path(Path("/Users/test/.gnupg/secring.gpg")) is True
    assert is_sensitive_path(Path("/Users/test/.aws/credentials")) is True
    assert is_sensitive_path(Path("/Users/test/.env")) is True

    assert rules.is_excluded_path(Path("/Users/test/.ssh")) is True
    assert rules.is_excluded_path(Path("/Users/test/.git")) is True


def test_symlink_traversal_cycle_guard(temp_dir: Path) -> None:
    # Deep nested symlink cycle
    dir1 = temp_dir / "dir1"
    dir2 = temp_dir / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    cycle_link = dir1 / "loop"
    cycle_link.symlink_to(dir2)
    back_link = dir2 / "back"
    back_link.symlink_to(dir1)

    res = resolve_symlink_safely(cycle_link)
    # Must not hang in infinite loop!
    assert res.is_symlink is True


def test_malformed_manifest_safety(temp_dir: Path) -> None:
    # Manifest with corrupted JSON / garbage bytes
    corrupt_pkg = temp_dir / "package.json"
    corrupt_pkg.write_text("{ unclosed json: [garbage, bytes! }", encoding="utf-8")
    deps = parse_manifest(corrupt_pkg)
    # Must return empty list gracefully without throwing an uncaught exception
    assert deps == []

    # Manifest with corrupted TOML
    corrupt_pyproject = temp_dir / "pyproject.toml"
    corrupt_pyproject.write_text("invalid = = = toml [[ [", encoding="utf-8")
    deps = parse_manifest(corrupt_pyproject)
    assert deps == []


def test_oversized_filesystem_traversal_limit(temp_dir: Path) -> None:
    # Create 20 subdirectories
    curr = temp_dir
    for i in range(15):
        curr = curr / f"depth_{i}"
        curr.mkdir()
        (curr / "package.json").write_text("{}", encoding="utf-8")

    # Walk with max_depth=3
    discovered, stats = safe_walk_projects(roots=[temp_dir], max_depth=3)
    # Depth must not exceed max_depth
    assert stats.max_depth_reached <= 3
