import pytest

from construction_pm.control_intelligence.graph import ControlDomain, DependencyRelation
from construction_pm.dependency_graph_conformance import (
    DependencyProjectionError,
    project_dependency_link,
)
from construction_pm.dependency_graph_persistence import DependencyLink


def link(**overrides):
    values = dict(
        resource_id="dep-1",
        tenant_id="T-1",
        project_id="P-1",
        revision=7,
        source_resource_id="schedule:task-1",
        target_resource_id="progress:task-1",
        dependency_type="schedule_to_progress",
        metadata={"relation": "impacts"},
    )
    values.update(overrides)
    return DependencyLink(**values)


@pytest.mark.parametrize(
    ("source", "target", "dependency_type", "source_domain", "target_domain", "relation"),
    [
        ("schedule:task-1", "progress:task-1", "schedule_to_progress", ControlDomain.SCHEDULE, ControlDomain.PROGRESS, DependencyRelation.IMPACTS),
        ("progress:task-1", "evm:period-1", "progress_to_evm", ControlDomain.PROGRESS, ControlDomain.EVM, DependencyRelation.DERIVED_FROM),
        ("resource:crew-1", "schedule:task-1", "resource_to_schedule", ControlDomain.RESOURCE, ControlDomain.SCHEDULE, DependencyRelation.IMPACTS),
        ("cost:cost-1", "schedule:task-1", "cost_to_schedule", ControlDomain.COST, ControlDomain.SCHEDULE, DependencyRelation.IMPACTS),
        ("change:chg-1", "schedule:task-1", "change_to_schedule", ControlDomain.CHANGE, ControlDomain.SCHEDULE, DependencyRelation.IMPACTS),
        ("claim:claim-1", "change:chg-1", "claim_to_change", ControlDomain.CLAIM, ControlDomain.CHANGE, DependencyRelation.CLAIMS_AGAINST),
    ],
)
def test_persistence_projection_is_typed_and_lossless(
    source, target, dependency_type, source_domain, target_domain, relation
):
    projected = project_dependency_link(
        link(
            source_resource_id=source,
            target_resource_id=target,
            dependency_type=dependency_type,
        ),
        graph_revision=7,
    )

    graph = projected.graph
    assert projected.contract_version == "dependency-graph.v1"
    assert graph.scope.tenant_id == "T-1"
    assert graph.scope.project_id == "P-1"
    assert graph.scope.project_revision == 7
    assert graph.nodes[source].domain is source_domain
    assert graph.nodes[target].domain is target_domain
    assert graph.nodes[source].entity_id == source.split(":", 1)[1]
    assert graph.nodes[target].entity_id == target.split(":", 1)[1]
    assert graph.edges[0].relation is relation
    assert graph.edges[0].source_revision == 7
    assert graph.edges[0].target_revision == 7


def test_unknown_domain_is_rejected_without_inference():
    with pytest.raises(DependencyProjectionError, match="UNMAPPABLE_DEPENDENCY_DOMAIN"):
        project_dependency_link(
            link(source_resource_id="unknown:task-1"),
            graph_revision=7,
        )


def test_unknown_relation_is_rejected_without_inference():
    with pytest.raises(DependencyProjectionError, match="UNMAPPABLE_DEPENDENCY_RELATION"):
        project_dependency_link(link(dependency_type="invented_relation"), graph_revision=7)


def test_graph_revision_mismatch_is_rejected():
    with pytest.raises(DependencyProjectionError, match="DEPENDENCY_GRAPH_REVISION_MISMATCH"):
        project_dependency_link(link(revision=6), graph_revision=7)


def test_projection_is_deterministic():
    first = project_dependency_link(link(), graph_revision=7)
    second = project_dependency_link(link(), graph_revision=7)

    assert first == second


def test_projection_preserves_distinct_source_and_target_revisions():
    projected = project_dependency_link(link(source_revision=11, target_revision=13), graph_revision=7)
    assert projected.graph.nodes["schedule:task-1"].revision == 11
    assert projected.graph.nodes["progress:task-1"].revision == 13
    assert projected.graph.edges[0].source_revision == 11
    assert projected.graph.edges[0].target_revision == 13


def test_invalid_source_or_target_revision_is_rejected():
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_SOURCE_REVISION"):
        link(source_revision=-1).validate()
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_TARGET_REVISION"):
        link(target_revision=9007199254740992).validate()
