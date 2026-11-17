"""Unit tests for safe symlink resolution and loop detection."""

from pathlib import Path

from inv.discovery.symlinks import resolve_symlink_safely


def test_regular_file_resolution(temp_dir: Path) -> None:
    f = temp_dir / "target.txt"
    f.write_text("hello", encoding="utf-8")

    res = resolve_symlink_safely(f)
    assert res.is_symlink is False
    assert res.is_broken is False
    assert res.canonical_path == f.resolve()


def test_valid_symlink_resolution(temp_dir: Path) -> None:
    target = temp_dir / "target.txt"
    target.write_text("hello", encoding="utf-8")
    link = temp_dir / "link.txt"
    link.symlink_to(target)

    res = resolve_symlink_safely(link)
    assert res.is_symlink is True
    assert res.is_broken is False
    assert res.is_loop is False
    assert res.canonical_path == target.resolve()


def test_broken_symlink_resolution(temp_dir: Path) -> None:
    missing_target = temp_dir / "missing.txt"
    link = temp_dir / "broken_link.txt"
    link.symlink_to(missing_target)

    res = resolve_symlink_safely(link)
    assert res.is_symlink is True
    assert res.is_broken is True


def test_symlink_cycle_detection(temp_dir: Path) -> None:
    link_a = temp_dir / "link_a"
    link_b = temp_dir / "link_b"

    # Create cycle: a -> b, b -> a
    link_a.symlink_to(link_b)
    link_b.symlink_to(link_a)

    res = resolve_symlink_safely(link_a)
    assert res.is_symlink is True
    assert res.is_loop is True
    assert res.is_broken is True
