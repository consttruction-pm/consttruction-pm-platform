import json
from pathlib import Path

import pytest

from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.graph import (
    ControlDomain, DependencyEdge, DependencyGraph, DependencyNode, DependencyRelation,
)

SCHEMA_PATH = Path("shared/contracts/dependency-graph.v1.schema.json")

def make_graph() -> DependencyGraph:
    graph = DependencyGraph(scope=ControlScope("tenant-1", "project-1", 12))
    graph.add_node(DependencyNode("schedule:activity-1", ControlDomain.SCHEDULE, "activity", "activity-1", 4))
    graph.add_node(DependencyNode("progress:activity-1", ControlDomain.PROGRESS, "activity", "activity-1", 9))
    graph.add_edge(DependencyEdge("schedule:activity-1", "progress:activity-1", DependencyRelation.IMPACTS, 4, 9))
    return graph

def test_dependency_graph_contract_is_versioned_and_matches_shared_core() -> None:
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert payload["$id"].endswith("/dependency-graph.v1")
    assert payload["properties"]["contract_version"]["const"] == "dependency-graph.v1"
    assert set(payload["properties"]["scope"]["required"]) == {"tenant_id", "project_id", "project_revision"}

def test_shared_graph_preserves_source_and_target_revisions() -> None:
    graph = make_graph()
    graph.validate()
    edge = graph.edges[0]
    assert edge.source_revision == graph.nodes[edge.source_node_id].revision
    assert edge.target_revision == graph.nodes[edge.target_node_id].revision

@pytest.mark.parametrize("domain", list(ControlDomain))
def test_all_control_domains_are_representable(domain: ControlDomain) -> None:
    node = DependencyNode(f"{domain.value}:entity-1", domain, "entity", "entity-1", 1)
    assert node.domain is domain

def test_revision_mismatch_is_rejected_without_recalculation() -> None:
    graph = make_graph()
    graph.edges[0] = DependencyEdge("schedule:activity-1", "progress:activity-1", DependencyRelation.IMPACTS, 999, 9)
    with pytest.raises(ValueError, match="DEPENDENCY_SOURCE_REVISION_MISMATCH"):
        graph.validate()
