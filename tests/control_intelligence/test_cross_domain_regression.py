import pytest

from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.graph import (
    ControlDomain,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)


@pytest.fixture
def cross_domain_graph() -> DependencyGraph:
    scope = ControlScope("tenant-1", "project-1", 7)
    graph = DependencyGraph(scope=scope)
    nodes = [
        DependencyNode("schedule:A1", ControlDomain.SCHEDULE, "activity", "A1", 7),
        DependencyNode("progress:P1", ControlDomain.PROGRESS, "progress_record", "P1", 7),
        DependencyNode("evm:E1", ControlDomain.EVM, "evm_snapshot", "E1", 7),
        DependencyNode("resource:R1", ControlDomain.RESOURCE, "resource_assignment", "R1", 7),
        DependencyNode("cost:C1", ControlDomain.COST, "cost_record", "C1", 7),
        DependencyNode("change:CH1", ControlDomain.CHANGE, "change_event", "CH1", 7),
        DependencyNode("claim:CL1", ControlDomain.CLAIM, "claim", "CL1", 7),
    ]
    for node in nodes:
        graph.add_node(node)
    graph.add_edge(DependencyEdge("progress:P1", "schedule:A1", DependencyRelation.IMPACTS, 7, 7))
    graph.add_edge(DependencyEdge("evm:E1", "progress:P1", DependencyRelation.DERIVED_FROM, 7, 7))
    graph.add_edge(DependencyEdge("resource:R1", "schedule:A1", DependencyRelation.ALLOCATES, 7, 7))
    graph.add_edge(DependencyEdge("cost:C1", "resource:R1", DependencyRelation.DERIVED_FROM, 7, 7))
    graph.add_edge(DependencyEdge("change:CH1", "schedule:A1", DependencyRelation.IMPACTS, 7, 7))
    graph.add_edge(DependencyEdge("claim:CL1", "change:CH1", DependencyRelation.CLAIMS_AGAINST, 7, 7))
    return graph


def test_cross_domain_regression_fixture_is_typed_and_revision_consistent(
    cross_domain_graph: DependencyGraph,
) -> None:
    cross_domain_graph.validate()
    assert len(cross_domain_graph.nodes) == 7
    assert len(cross_domain_graph.edges) == 6
    assert {node.domain for node in cross_domain_graph.nodes.values()} == {
        ControlDomain.SCHEDULE,
        ControlDomain.PROGRESS,
        ControlDomain.EVM,
        ControlDomain.RESOURCE,
        ControlDomain.COST,
        ControlDomain.CHANGE,
        ControlDomain.CLAIM,
    }


@pytest.mark.parametrize(
    ("edge_index", "error"),
    [
        (0, "DEPENDENCY_SOURCE_REVISION_MISMATCH"),
        (1, "DEPENDENCY_TARGET_REVISION_MISMATCH"),
    ],
)
def test_cross_domain_fixture_rejects_revision_drift(
    cross_domain_graph: DependencyGraph,
    edge_index: int,
    error: str,
) -> None:
    edge = cross_domain_graph.edges[edge_index]
    replacement = DependencyEdge(
        edge.source_node_id,
        edge.target_node_id,
        edge.relation,
        edge.source_revision + 1 if edge_index == 0 else edge.source_revision,
        edge.target_revision + 1 if edge_index == 1 else edge.target_revision,
    )
    cross_domain_graph.edges[edge_index] = replacement
    with pytest.raises(ValueError, match=error):
        cross_domain_graph.validate()
