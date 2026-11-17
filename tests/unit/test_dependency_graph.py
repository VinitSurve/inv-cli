"""Unit tests for DependencyGraph and reverse dependency impact analysis."""

from inv.constants import InstallScope, RiskLevel
from inv.core.dependency_graph import DependencyGraph
from inv.core.models import InstallationInstance, ScanSession, SoftwareIdentity
from inv.storage.repositories import InventoryRepository


def test_dependency_graph_relationships(mock_repo: InventoryRepository) -> None:
    session_id = "test-session-dep"
    mock_repo.save_session(ScanSession.create(session_id=session_id))
    # Create library ident
    ident_lib = SoftwareIdentity.create(name="libuv", ecosystem="brew")
    mock_repo.save_software_identity(ident_lib)
    inst_lib = InstallationInstance.create(
        software_id=ident_lib.id,
        name="libuv",
        version="1.48.0",
        manager="brew_formula",
        scope=InstallScope.GLOBAL,
    )
    mock_repo.save_installation(inst_lib, session_id)

    # Create consumer app that depends on libuv
    ident_app = SoftwareIdentity.create(name="node", ecosystem="brew")
    mock_repo.save_software_identity(ident_app)
    inst_app = InstallationInstance.create(
        software_id=ident_app.id,
        name="node",
        version="20.11.0",
        manager="brew_formula",
        scope=InstallScope.GLOBAL,
        metadata={"dependencies": ["libuv", "openssl"]},
    )
    mock_repo.save_installation(inst_app, session_id)

    graph = DependencyGraph(mock_repo, session_id=session_id)

    # libuv reverse dependencies should include node
    revs = graph.get_reverse_dependencies("libuv")
    assert "node" in revs

    # node dependencies should include libuv and openssl
    deps = graph.get_dependencies("node")
    assert "libuv" in deps
    assert "openssl" in deps

    # Why libuv?
    why = graph.get_why("libuv")
    assert "node" in why["reverse_dependencies"]

    # Removal impact on libuv: HIGH risk because node requires it
    impact = graph.analyze_removal_impact("libuv")
    assert impact.risk_level == RiskLevel.HIGH
    assert not impact.can_safely_remove
    assert len(impact.reverse_dependencies) > 0


def test_critical_system_runtime_removal_protection(mock_repo: InventoryRepository) -> None:
    graph = DependencyGraph(mock_repo)
    # python and node must be flagged as CRITICAL risk
    impact_py = graph.analyze_removal_impact("python")
    assert impact_py.risk_level == RiskLevel.CRITICAL
    assert not impact_py.can_safely_remove

    impact_node = graph.analyze_removal_impact("node")
    assert impact_node.risk_level == RiskLevel.CRITICAL
    assert not impact_node.can_safely_remove
