"""Duplicate detector across executables and multiple installation instances."""

from collections import defaultdict
from dataclasses import dataclass

from inv.core.models import ExecutableInstance, InstallationInstance


@dataclass
class DuplicateCommandGroup:
    """A command name present in multiple PATH locations."""

    name: str
    instances: list[ExecutableInstance]


@dataclass
class MultiManagerPackage:
    """A software package installed under multiple different package managers."""

    name: str
    installations: list[InstallationInstance]


class Deduplicator:
    """Detects command shadowing and multi-manager software duplications."""

    def find_duplicate_commands(
        self, executables: list[ExecutableInstance]
    ) -> list[DuplicateCommandGroup]:
        """Find executable commands that exist in multiple locations in PATH."""
        by_name: dict[str, list[ExecutableInstance]] = defaultdict(list)
        for exe in executables:
            by_name[exe.name].append(exe)

        duplicates: list[DuplicateCommandGroup] = []
        for name, insts in by_name.items():
            if len(insts) > 1:
                duplicates.append(DuplicateCommandGroup(name=name, instances=insts))

        return sorted(duplicates, key=lambda d: d.name)

    def find_multi_manager_packages(
        self, installations: list[InstallationInstance]
    ) -> list[MultiManagerPackage]:
        """Find packages installed under multiple distinct package managers."""
        by_name: dict[str, list[InstallationInstance]] = defaultdict(list)
        for inst in installations:
            by_name[inst.name.lower()].append(inst)

        duplicates: list[MultiManagerPackage] = []
        for name, insts in by_name.items():
            distinct_managers = {i.manager for i in insts}
            if len(distinct_managers) > 1:
                duplicates.append(MultiManagerPackage(name=name, installations=insts))

        return sorted(duplicates, key=lambda d: d.name)
