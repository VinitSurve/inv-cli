"""Parsers for project manifests and lockfiles without executing code."""

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from inv.constants import DependencyStatus


@dataclass
class ParsedManifestDependency:
    """A dependency parsed statically from a project manifest or lockfile."""

    name: str
    declared_spec: str | None
    resolved_version: str | None
    is_dev: bool
    ecosystem: str
    status: DependencyStatus = DependencyStatus.DECLARED


MANIFEST_FILES = {
    # Python
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "setup.py": "python",
    "Pipfile": "python",
    "Pipfile.lock": "python",
    "poetry.lock": "python",
    "uv.lock": "python",
    # JavaScript / TypeScript
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "npm",
    "pnpm-lock.yaml": "npm",
    "bun.lockb": "npm",
    "bun.lock": "npm",
    # Rust
    "Cargo.toml": "cargo",
    "Cargo.lock": "cargo",
    # Go
    "go.mod": "go",
    "go.sum": "go",
    # Ruby
    "Gemfile": "gem",
    "Gemfile.lock": "gem",
    # PHP
    "composer.json": "composer",
    "composer.lock": "composer",
    # Java / Kotlin
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
}

LOCK_FILES = {
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "bun.lock",
    "Cargo.lock",
    "go.sum",
    "Gemfile.lock",
    "composer.lock",
}


def parse_package_json(path: Path) -> list[ParsedManifestDependency]:
    """Parse dependencies from package.json."""
    deps: list[ParsedManifestDependency] = []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return deps

        for name, spec in data.get("dependencies", {}).items():
            if isinstance(name, str):
                deps.append(
                    ParsedManifestDependency(
                        name=name,
                        declared_spec=str(spec) if spec else None,
                        resolved_version=None,
                        is_dev=False,
                        ecosystem="npm",
                    )
                )

        for name, spec in data.get("devDependencies", {}).items():
            if isinstance(name, str):
                deps.append(
                    ParsedManifestDependency(
                        name=name,
                        declared_spec=str(spec) if spec else None,
                        resolved_version=None,
                        is_dev=True,
                        ecosystem="npm",
                    )
                )
    except Exception:
        pass
    return deps


def parse_pyproject_toml(path: Path) -> list[ParsedManifestDependency]:
    """Parse dependencies from pyproject.toml."""
    deps: list[ParsedManifestDependency] = []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Standard PEP 621 [project.dependencies]
        project = data.get("project", {})
        if isinstance(project, dict):
            for dep_str in project.get("dependencies", []):
                if isinstance(dep_str, str):
                    dep = _parse_python_req_line(dep_str, is_dev=False)
                    if dep:
                        deps.append(dep)

            # optional-dependencies
            opt = project.get("optional-dependencies", {})
            if isinstance(opt, dict):
                for group, group_deps in opt.items():
                    is_dev = "dev" in group.lower() or "test" in group.lower()
                    if isinstance(group_deps, list):
                        for dep_str in group_deps:
                            if isinstance(dep_str, str):
                                dep = _parse_python_req_line(dep_str, is_dev=is_dev)
                                if dep:
                                    deps.append(dep)

        # Poetry [tool.poetry.dependencies]
        poetry = data.get("tool", {}).get("poetry", {})
        if isinstance(poetry, dict):
            for name, spec in poetry.get("dependencies", {}).items():
                if name.lower() != "python" and isinstance(name, str):
                    spec_str = spec if isinstance(spec, str) else json.dumps(spec)
                    deps.append(
                        ParsedManifestDependency(
                            name=name,
                            declared_spec=spec_str,
                            resolved_version=None,
                            is_dev=False,
                            ecosystem="python",
                        )
                    )
            # dev-dependencies
            for name, spec in poetry.get("dev-dependencies", {}).items():
                if isinstance(name, str):
                    spec_str = spec if isinstance(spec, str) else json.dumps(spec)
                    deps.append(
                        ParsedManifestDependency(
                            name=name,
                            declared_spec=spec_str,
                            resolved_version=None,
                            is_dev=True,
                            ecosystem="python",
                        )
                    )
    except Exception:
        pass
    return deps


def parse_requirements_txt(path: Path) -> list[ParsedManifestDependency]:
    """Parse dependencies from requirements.txt."""
    deps: list[ParsedManifestDependency] = []
    is_dev = "dev" in path.name.lower() or "test" in path.name.lower()
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                dep = _parse_python_req_line(line, is_dev=is_dev)
                if dep:
                    deps.append(dep)
    except Exception:
        pass
    return deps


def _parse_python_req_line(line: str, is_dev: bool = False) -> ParsedManifestDependency | None:
    # Remove inline comments
    clean = line.split("#")[0].strip()
    if not clean:
        return None
    match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", clean)
    if not match:
        return None
    name = match.group(1).strip()
    spec = match.group(2).strip() or None
    return ParsedManifestDependency(
        name=name,
        declared_spec=spec,
        resolved_version=None,
        is_dev=is_dev,
        ecosystem="python",
    )


def parse_cargo_toml(path: Path) -> list[ParsedManifestDependency]:
    """Parse dependencies from Cargo.toml."""
    deps: list[ParsedManifestDependency] = []
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        for name, spec in data.get("dependencies", {}).items():
            if isinstance(name, str):
                spec_str = (
                    spec
                    if isinstance(spec, str)
                    else spec.get("version")
                    if isinstance(spec, dict)
                    else None
                )
                deps.append(
                    ParsedManifestDependency(
                        name=name,
                        declared_spec=str(spec_str) if spec_str else None,
                        resolved_version=None,
                        is_dev=False,
                        ecosystem="cargo",
                    )
                )

        for name, spec in data.get("dev-dependencies", {}).items():
            if isinstance(name, str):
                spec_str = (
                    spec
                    if isinstance(spec, str)
                    else spec.get("version")
                    if isinstance(spec, dict)
                    else None
                )
                deps.append(
                    ParsedManifestDependency(
                        name=name,
                        declared_spec=str(spec_str) if spec_str else None,
                        resolved_version=None,
                        is_dev=True,
                        ecosystem="cargo",
                    )
                )
    except Exception:
        pass
    return deps


def parse_go_mod(path: Path) -> list[ParsedManifestDependency]:
    """Parse dependencies from go.mod."""
    deps: list[ParsedManifestDependency] = []
    try:
        in_require = False
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                if line.startswith("require ("):
                    in_require = True
                    continue
                if in_require and line == ")":
                    in_require = False
                    continue

                if line.startswith("require "):
                    parts = line.split()
                    if len(parts) >= 3:
                        deps.append(
                            ParsedManifestDependency(
                                name=parts[1],
                                declared_spec=parts[2],
                                resolved_version=parts[2],
                                is_dev=False,
                                ecosystem="go",
                            )
                        )
                elif in_require:
                    parts = line.split()
                    if len(parts) >= 2:
                        deps.append(
                            ParsedManifestDependency(
                                name=parts[0],
                                declared_spec=parts[1],
                                resolved_version=parts[1],
                                is_dev=False,
                                ecosystem="go",
                            )
                        )
    except Exception:
        pass
    return deps


def parse_gemfile(path: Path) -> list[ParsedManifestDependency]:
    """Parse dependencies from Gemfile."""
    deps: list[ParsedManifestDependency] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("gem "):
                    continue
                match = re.match(r"""gem\s+['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""", line)
                if match:
                    name = match.group(1)
                    spec = match.group(2)
                    deps.append(
                        ParsedManifestDependency(
                            name=name,
                            declared_spec=spec,
                            resolved_version=None,
                            is_dev=False,
                            ecosystem="gem",
                        )
                    )
    except Exception:
        pass
    return deps


def parse_manifest(path: Path) -> list[ParsedManifestDependency]:
    """Dispatcher to parse any known manifest file."""
    fname = path.name
    if fname == "package.json":
        return parse_package_json(path)
    if fname == "pyproject.toml":
        return parse_pyproject_toml(path)
    if fname == "requirements.txt" or fname.endswith(".requirements.txt"):
        return parse_requirements_txt(path)
    if fname == "Cargo.toml":
        return parse_cargo_toml(path)
    if fname == "go.mod":
        return parse_go_mod(path)
    if fname == "Gemfile":
        return parse_gemfile(path)
    return []
