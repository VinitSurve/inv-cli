"""Integration tests for InventoryEngine and end-to-end scan pipeline."""

from pathlib import Path

from inv.config import InvConfig
from inv.core.engine import InventoryEngine


def test_engine_end_to_end_scan(temp_dir: Path) -> None:
    # Set up synthetic project in temp_dir
    proj_dir = temp_dir / "my_project"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text(
        '{"name": "test-pkg", "dependencies": {"express": "4.18.2"}}', encoding="utf-8"
    )

    db_path = temp_dir / "engine_test.db"
    cfg = InvConfig(
        db_path=db_path,
        project_roots=[proj_dir],
        scan_projects=True,
        deep_scan=False,
    )

    engine = InventoryEngine(cfg)
    session, results = engine.run_scan(
        deep=False,
        scan_projects=True,
        project_roots=[proj_dir],
    )

    assert session.status == "completed"
    assert session.total_items > 0

    with engine.get_repository() as repo:
        latest_sess = repo.get_latest_session()
        assert latest_sess is not None
        assert latest_sess.id == session.id

        projects = repo.list_projects(session.id)
        assert len(projects) == 1
        assert projects[0].name == "my_project"

        deps = repo.list_project_dependencies(session_id=session.id)
        assert len(deps) == 1
        assert deps[0].name == "express"
