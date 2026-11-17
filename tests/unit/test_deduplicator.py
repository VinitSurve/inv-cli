"""Unit tests for Deduplicator."""

from pathlib import Path

from inv.core.deduplicator import Deduplicator
from inv.core.models import ExecutableInstance, InstallationInstance


def test_find_duplicate_commands() -> None:
    dedup = Deduplicator()
    exe1 = ExecutableInstance.create(
        name="python3",
        path=Path("/opt/homebrew/bin/python3"),
        canonical_path=Path("/opt/homebrew/bin/python3"),
        is_symlink=False,
    )
    exe2 = ExecutableInstance.create(
        name="python3",
        path=Path("/usr/bin/python3"),
        canonical_path=Path("/usr/bin/python3"),
        is_symlink=False,
    )
    exe3 = ExecutableInstance.create(
        name="git",
        path=Path("/usr/bin/git"),
        canonical_path=Path("/usr/bin/git"),
        is_symlink=False,
    )

    duplicates = dedup.find_duplicate_commands([exe1, exe2, exe3])
    assert len(duplicates) == 1
    assert duplicates[0].name == "python3"
    assert len(duplicates[0].instances) == 2


def test_find_multi_manager_packages() -> None:
    dedup = Deduplicator()
    inst1 = InstallationInstance.create(
        software_id="id1",
        name="ripgrep",
        version="14.1.0",
        manager="brew_formula",
    )
    inst2 = InstallationInstance.create(
        software_id="id2",
        name="ripgrep",
        version="14.1.0",
        manager="cargo",
    )
    inst3 = InstallationInstance.create(
        software_id="id3",
        name="curl",
        version="8.4.0",
        manager="brew_formula",
    )

    multi = dedup.find_multi_manager_packages([inst1, inst2, inst3])
    assert len(multi) == 1
    assert multi[0].name == "ripgrep"
    assert len(multi[0].installations) == 2
