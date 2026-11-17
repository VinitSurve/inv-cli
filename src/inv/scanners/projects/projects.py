"""Projects scanner discovering repositories, manifests, and reconciling dependencies."""

from pathlib import Path

from inv.constants import DependencyStatus
from inv.core.models import Project, ProjectDependency
from inv.discovery.filesystem import safe_walk_projects
from inv.discovery.manifests import LOCK_FILES, parse_manifest
from inv.scanners.base import BaseScanner, ScanContext, ScanResult


class ProjectsScanner(BaseScanner):
    """Scanner for software projects, lockfiles, and dependency resolution state."""

    @property
    def scanner_id(self) -> str:
        return "projects"

    @property
    def domain(self) -> str:
        return "projects"

    @property
    def name(self) -> str:
        return "Software Projects & Dependencies"

    def is_available(self) -> bool:
        return True

    def scan(self, context: ScanContext) -> ScanResult:
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)
        if not context.config.scan_projects:
            return result

        roots = context.config.project_roots or [Path.cwd()]
        discovered_projects, stats = safe_walk_projects(
            roots=roots,
            max_depth=context.config.max_depth,
        )

        for proj_root, entry in discovered_projects.items():
            has_lock = any(p.name in LOCK_FILES for p in entry.manifest_paths)
            root_manifest = entry.manifest_paths[0] if entry.manifest_paths else None

            project_obj = Project.create(
                name=proj_root.name,
                path=proj_root,
                project_types=list(entry.project_types),
                root_manifest=root_manifest,
                has_lockfile=has_lock,
                manifest_paths=entry.manifest_paths,
                dependencies_count=0,
            )

            # Collect dependencies across all project manifests
            all_deps: list[ProjectDependency] = []
            seen_dep_names: set[str] = set()

            # Pre-scan local installation artifacts (node_modules, .venv)
            node_modules_dir = proj_root / "node_modules"
            installed_node_pkgs = (
                self._get_installed_node_modules(node_modules_dir)
                if node_modules_dir.is_dir()
                else None
            )

            venv_dir = proj_root / ".venv"
            if not venv_dir.is_dir():
                venv_dir = proj_root / "venv"
            installed_python_pkgs = (
                self._get_installed_python_pkgs(venv_dir) if venv_dir.is_dir() else None
            )

            for m_path in entry.manifest_paths:
                parsed_list = parse_manifest(m_path)
                for p_dep in parsed_list:
                    dep_key = f"{p_dep.ecosystem}:{p_dep.name.lower()}"
                    if dep_key in seen_dep_names:
                        continue
                    seen_dep_names.add(dep_key)

                    # Determine installation status
                    status = DependencyStatus.DECLARED
                    resolved_ver = p_dep.resolved_version

                    if p_dep.ecosystem == "npm":
                        if installed_node_pkgs is not None:
                            if p_dep.name in installed_node_pkgs:
                                status = DependencyStatus.INSTALLED
                                resolved_ver = installed_node_pkgs[p_dep.name] or resolved_ver
                            else:
                                status = DependencyStatus.MISSING
                        else:
                            status = DependencyStatus.DECLARED

                    elif p_dep.ecosystem == "python":
                        canonical_py_name = p_dep.name.lower().replace("-", "_")
                        if installed_python_pkgs is not None:
                            if canonical_py_name in installed_python_pkgs:
                                status = DependencyStatus.INSTALLED
                                resolved_ver = (
                                    installed_python_pkgs[canonical_py_name] or resolved_ver
                                )
                            else:
                                status = DependencyStatus.MISSING
                        else:
                            status = DependencyStatus.DECLARED

                    dep_obj = ProjectDependency.create(
                        project_id=project_obj.id,
                        name=p_dep.name,
                        declared_spec=p_dep.declared_spec,
                        resolved_version=resolved_ver,
                        status=status,
                        is_dev=p_dep.is_dev,
                        ecosystem=p_dep.ecosystem,
                        manifest_source=m_path,
                    )
                    all_deps.append(dep_obj)

            project_obj.dependencies_count = len(all_deps)
            result.projects.append(project_obj)
            result.project_dependencies.extend(all_deps)

        return result

    def _get_installed_node_modules(self, node_modules: Path) -> dict[str, str | None]:
        """Detect installed packages in node_modules directory."""
        installed: dict[str, str | None] = {}
        try:
            for item in node_modules.iterdir():
                if item.name.startswith("@"):
                    for scoped in item.iterdir():
                        installed[f"{item.name}/{scoped.name}"] = None
                elif not item.name.startswith("."):
                    installed[item.name] = None
        except Exception:
            pass
        return installed

    def _get_installed_python_pkgs(self, venv_path: Path) -> dict[str, str | None]:
        """Detect installed packages in virtualenv site-packages directory."""
        installed: dict[str, str | None] = {}
        try:
            for sp in venv_path.glob("lib/python*/site-packages/*"):
                name = sp.name
                if name.endswith(".dist-info"):
                    # Name is like mypy-1.10.0.dist-info
                    parts = name.replace(".dist-info", "").split("-")
                    pkg_name = parts[0].lower().replace("-", "_")
                    version = parts[1] if len(parts) > 1 else None
                    installed[pkg_name] = version
        except Exception:
            pass
        return installed
