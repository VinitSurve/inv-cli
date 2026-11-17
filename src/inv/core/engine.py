"""High-level Inventory Engine executing end-to-end discovery and storage."""

import time
from collections.abc import Callable
from pathlib import Path

from inv.config import InvConfig
from inv.core.coordinator import ScanCoordinator
from inv.core.deduplicator import Deduplicator
from inv.core.models import ScannerObservation, ScanSession
from inv.core.reconciler import InventoryReconciler
from inv.core.registry import ScannerRegistry
from inv.scanners.base import ScanContext, ScanResult
from inv.storage.database import Database
from inv.storage.migrations.manager import apply_migrations
from inv.storage.repositories import InventoryRepository


class InventoryEngine:
    """Coordinates scanners, deduplication, reconciliation, and database persistence."""

    def __init__(self, config: InvConfig | None = None) -> None:
        self.config = config or InvConfig.load()
        self.db = Database(self.config.db_path)
        self._init_db()
        self.registry = ScannerRegistry()
        self.reconciler = InventoryReconciler()
        self.deduplicator = Deduplicator()

    def _init_db(self) -> None:
        """Run database migrations on start."""
        with self.db.transaction() as conn:
            apply_migrations(conn)

    def run_scan(
        self,
        deep: bool = False,
        scan_projects: bool = True,
        project_roots: list[Path] | None = None,
        progress_cb: Callable[[str, int, int], None] | None = None,
        scanner_filter: list[str] | None = None,
    ) -> tuple[ScanSession, list[ScanResult]]:
        """Perform a complete inventory scan and persist snapshot transactionally."""
        start_time = time.perf_counter()
        session = ScanSession.create(scan_type="deep" if deep else "standard")

        # Prepare scan config
        active_config = InvConfig.from_dict(self.config.to_dict())
        active_config.deep_scan = deep
        active_config.scan_projects = scan_projects
        if project_roots:
            active_config.project_roots = project_roots
        if scanner_filter:
            active_config.enabled_scanners = scanner_filter

        context = ScanContext(
            session_id=session.id,
            config=active_config,
            deep=deep,
        )

        coordinator = ScanCoordinator(active_config)
        all_scanners = self.registry.list_all()
        scan_results = coordinator.run_scanners(all_scanners, context, progress_cb)

        # Aggregate items
        all_identities = []
        all_installations = []
        all_executables = []
        all_projects = []
        all_dependencies = []
        all_environments = []
        all_applications = []
        all_runtimes = []
        all_containers = []
        all_container_images = []
        all_extensions = []
        observations = []

        for res in scan_results:
            all_identities.extend(res.identities)
            all_installations.extend(res.installations)
            all_executables.extend(res.executables)
            all_projects.extend(res.projects)
            all_dependencies.extend(res.project_dependencies)
            all_environments.extend(res.environments)
            all_applications.extend(res.applications)
            all_runtimes.extend(res.runtimes)
            all_containers.extend(res.containers)
            all_container_images.extend(res.container_images)
            all_extensions.extend(res.extensions)

            obs = ScannerObservation.create(
                scanner_id=res.scanner_id,
                session_id=session.id,
                domain=res.domain,
                status=res.status,
                duration_seconds=res.duration_seconds,
                items_count=res.total_items,
                warnings=res.warnings,
                errors=res.errors,
            )
            observations.append(obs)

        # Reconcile project dependencies against discovered global packages
        all_dependencies = self.reconciler.reconcile_project_dependencies(
            projects=all_projects,
            dependencies=all_dependencies,
            global_installations=all_installations,
        )

        total_items = (
            len(all_installations)
            + len(all_executables)
            + len(all_applications)
            + len(all_projects)
            + len(all_environments)
            + len(all_runtimes)
            + len(all_containers)
            + len(all_extensions)
        )

        duration = time.perf_counter() - start_time
        summary = {
            "installations": len(all_installations),
            "executables": len(all_executables),
            "applications": len(all_applications),
            "projects": len(all_projects),
            "dependencies": len(all_dependencies),
            "environments": len(all_environments),
            "runtimes": len(all_runtimes),
            "containers": len(all_containers),
            "extensions": len(all_extensions),
            "scanners_executed": len(scan_results),
        }
        session.complete(total_items=total_items, duration_seconds=duration, summary=summary)

        # Atomic transaction save
        with self.db.transaction() as conn:
            repo = InventoryRepository(conn)
            repo.save_session(session)

            for obs in observations:
                repo.save_observation(obs)

            for ident in all_identities:
                repo.save_software_identity(ident)

            for inst in all_installations:
                repo.save_installation(inst, session.id)

            for exe in all_executables:
                repo.save_executable(exe, session.id)

            for app in all_applications:
                repo.save_application(app, session.id)

            for proj in all_projects:
                repo.save_project(proj, session.id)

            for dep in all_dependencies:
                repo.save_project_dependency(dep, session.id)

            for env in all_environments:
                repo.save_environment(env, session.id)

            for rt in all_runtimes:
                repo.save_runtime(rt, session.id)

            for c in all_containers:
                repo.save_container(c, session.id)

            for ci in all_container_images:
                repo.save_container_image(ci, session.id)

            for ext in all_extensions:
                repo.save_extension(ext, session.id)

        return session, scan_results

    def get_repository(self) -> InventoryRepository:
        """Get a repository instance bound to an open connection."""
        conn = self.db.get_connection()
        return InventoryRepository(conn)
