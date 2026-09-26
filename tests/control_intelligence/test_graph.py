import pytest

from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.graph import (
    ControlDomain,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)


def scope() -> ControlScope:
    return ControlScope("tenant-1", "project-1", 3)


def node(node_id: str, entity_id: str, revision: int = 3) -> DependencyNode:
    return DependencyNode(node_id, ControlDomain.SCHEDULE, "activity", entity_id, revision)


def edge(source: str, target: str, source_revision: int = 3, target_revision: int = 3) -> DependencyEdge:
    return DependencyEdge(source, target, DependencyRelation.IMPACTS, source_revision, target_revision)


def test_graph_accepts_cross_domain_dependency() -> None:
    graph = DependencyGraph(scope=scope())
    schedule = node("schedule:A1", "A1")
    cost = DependencyNode("cost:C1", ControlDomain.COST, "commitment", "C1", 3)
    graph.add_node(schedule)
    graph.add_node(cost)
    graph.add_edge(edge(schedule.node_id, cost.node_id))
    graph.validate()
    assert graph.scope == scope()
    assert len(graph.edges) == 1


def test_graph_rejects_duplicate_node() -> None:
    graph = DependencyGraph(scope=scope())
    graph.add_node(node("schedule:A1", "A1"))
    with pytest.raises(ValueError, match="DUPLICATE_DEPENDENCY_NODE"):
        graph.add_node(node("schedule:A1", "A1"))


def test_graph_rejects_edge_to_unknown_node() -> None:
    graph = DependencyGraph(scope=scope())
    graph.add_node(node("schedule:A1", "A1"))
    with pytest.raises(ValueError, match="UNKNOWN_TARGET_NODE"):
        graph.add_edge(edge("schedule:A1", "cost:C1"))


def test_graph_rejects_self_dependency() -> None:
    with pytest.raises(ValueError, match="SELF_DEPENDENCY_NOT_ALLOWED"):
        edge("schedule:A1", "schedule:A1")


def test_graph_rejects_missing_scope() -> None:
    graph = DependencyGraph()
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_GRAPH_SCOPE"):
        graph.validate()


def test_graph_rejects_source_revision_mismatch() -> None:
    graph = DependencyGraph(scope=scope())
    graph.add_node(node("schedule:A1", "A1", revision=3))
    graph.add_node(node("cost:C1", "C1", revision=3))
    graph.add_edge(edge("schedule:A1", "cost:C1", source_revision=4))
    with pytest.raises(ValueError, match="DEPENDENCY_SOURCE_REVISION_MISMATCH"):
        graph.validate()


def test_graph_rejects_target_revision_mismatch() -> None:
    graph = DependencyGraph(scope=scope())
    graph.add_node(node("schedule:A1", "A1", revision=3))
    graph.add_node(node("cost:C1", "C1", revision=3))
    graph.add_edge(edge("schedule:A1", "cost:C1", target_revision=4))
    with pytest.raises(ValueError, match="DEPENDENCY_TARGET_REVISION_MISMATCH"):
        graph.validate()


def test_graph_rejects_string_enum_values() -> None:
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_NODE_DOMAIN"):
        DependencyNode("n-1", "schedule", "activity", "A1", 3)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_RELATION"):
        DependencyEdge("n-1", "n-2", "impacts", 3, 3)  # type: ignore[arg-type]
