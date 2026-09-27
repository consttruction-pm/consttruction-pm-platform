import pytest

from construction_pm.control_intelligence.contracts import ControlScope
from construction_pm.control_intelligence.graph import (
    ControlDomain,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)


@pytest.mark.parametrize(
    ("source_domain", "target_domain", "relation"),
    [
        (ControlDomain.SCHEDULE, ControlDomain.PROGRESS, DependencyRelation.IMPACTS),
        (ControlDomain.PROGRESS, ControlDomain.EVM, DependencyRelation.DERIVED_FROM),
        (ControlDomain.RESOURCE, ControlDomain.SCHEDULE, DependencyRelation.IMPACTS),
        (ControlDomain.COST, ControlDomain.SCHEDULE, DependencyRelation.IMPACTS),
        (ControlDomain.CHANGE, ControlDomain.SCHEDULE, DependencyRelation.IMPACTS),
        (ControlDomain.CLAIM, ControlDomain.CHANGE, DependencyRelation.CLAIMS_AGAINST),
        (ControlDomain.DOCUMENT, ControlDomain.SCHEDULE, DependencyRelation.EVIDENCES),
        (ControlDomain.PROCUREMENT, ControlDomain.COST, DependencyRelation.ALLOCATES),
        (ControlDomain.FIELD, ControlDomain.PROGRESS, DependencyRelation.SUPPORTS),
    ],
)
def test_cross_domain_conformance_matrix_accepts_typed_links(
    source_domain: ControlDomain,
    target_domain: ControlDomain,
    relation: DependencyRelation,
) -> None:
    scope = ControlScope("tenant-1", "project-1", 11)
    graph = DependencyGraph(scope=scope)
    source = DependencyNode(f"{source_domain.value}:source", source_domain, "entity", "source", 11)
    target = DependencyNode(f"{target_domain.value}:target", target_domain, "entity", "target", 11)
    graph.add_node(source)
    graph.add_node(target)
    graph.add_edge(
        DependencyEdge(source.node_id, target.node_id, relation, source.revision, target.revision)
    )

    graph.validate()

    assert graph.edges[0].relation is relation
    assert graph.nodes[source.node_id].domain is source_domain
    assert graph.nodes[target.node_id].domain is target_domain


def test_conformance_matrix_rejects_edge_revision_drift_across_domains() -> None:
    scope = ControlScope("tenant-1", "project-1", 11)
    graph = DependencyGraph(scope=scope)
    source = DependencyNode("schedule:source", ControlDomain.SCHEDULE, "activity", "A-1", 11)
    target = DependencyNode("progress:target", ControlDomain.PROGRESS, "progress", "A-1", 12)
    graph.add_node(source)
    graph.add_node(target)
    graph.add_edge(
        DependencyEdge(
            source.node_id,
            target.node_id,
            DependencyRelation.IMPACTS,
            source.revision,
            11,
        )
    )

    with pytest.raises(ValueError, match="DEPENDENCY_TARGET_REVISION_MISMATCH"):
        graph.validate()


def test_conformance_matrix_is_typed_not_string_based() -> None:
    scope = ControlScope("tenant-1", "project-1", 11)
    graph = DependencyGraph(scope=scope)
    graph.add_node(DependencyNode("schedule:source", ControlDomain.SCHEDULE, "activity", "A-1", 11))
    graph.add_node(DependencyNode("progress:target", ControlDomain.PROGRESS, "progress", "A-1", 11))

    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_RELATION"):
        graph.add_edge(
            DependencyEdge(
                "schedule:source",
                "progress:target",
                "schedule_to_progress",  # type: ignore[arg-type]
                11,
                11,
            )
        )
