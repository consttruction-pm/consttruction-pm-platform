import pytest

from construction_pm.control_intelligence.graph import ControlDomain, DependencyEdge, DependencyGraph, DependencyNode, DependencyRelation

def node(node_id: str, entity_id: str) -> DependencyNode:
    return DependencyNode(node_id, ControlDomain.SCHEDULE, "activity", entity_id, 3)

def edge(source: str, target: str) -> DependencyEdge:
    return DependencyEdge(source, target, DependencyRelation.IMPACTS, 3, 3)

def test_graph_accepts_cross_domain_dependency() -> None:
    graph = DependencyGraph()
    schedule = node("schedule:A1", "A1")
    cost = DependencyNode("cost:C1", ControlDomain.COST, "commitment", "C1", 3)
    graph.add_node(schedule)
    graph.add_node(cost)
    graph.add_edge(edge(schedule.node_id, cost.node_id))
    graph.validate()
    assert len(graph.edges) == 1

def test_graph_rejects_duplicate_node() -> None:
    graph = DependencyGraph()
    graph.add_node(node("schedule:A1", "A1"))
    with pytest.raises(ValueError, match="DUPLICATE_DEPENDENCY_NODE"):
        graph.add_node(node("schedule:A1", "A1"))

def test_graph_rejects_edge_to_unknown_node() -> None:
    graph = DependencyGraph()
    graph.add_node(node("schedule:A1", "A1"))
    with pytest.raises(ValueError, match="UNKNOWN_TARGET_NODE"):
        graph.add_edge(edge("schedule:A1", "cost:C1"))

def test_graph_rejects_self_dependency() -> None:
    with pytest.raises(ValueError, match="SELF_DEPENDENCY_NOT_ALLOWED"):
        edge("schedule:A1", "schedule:A1")
