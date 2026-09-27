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
        ("schedule:task-1", "change:chg-1", "schedule_to_change", ControlDomain.SCHEDULE, ControlDomain.CHANGE, DependencyRelation.IMPACTS),
        ("schedule:task-1", "rfi:rfi-1", "schedule_to_rfi", ControlDomain.SCHEDULE, ControlDomain.DOCUMENT, DependencyRelation.IMPACTS),
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


def test_unknown_domain_is_rejected_at_persistence_boundary():
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_SOURCE_RESOURCE_ID"):
        link(source_resource_id="unknown:task-1").validate()


def test_unknown_relation_is_rejected_at_persistence_boundary():
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_TYPE"):
        link(dependency_type="invented_relation").validate()


def test_graph_revision_is_not_conflated_with_project_revision():
    projected = project_dependency_link(link(revision=6), graph_revision=7)

    assert projected.graph.scope.project_revision == 6
    assert projected.graph.nodes["schedule:task-1"].revision == 6
    assert projected.graph.nodes["progress:task-1"].revision == 6
    assert projected.graph.edges[0].source_revision == 6
    assert projected.graph.edges[0].target_revision == 6


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



@pytest.mark.parametrize("domain", list(ControlDomain))
def test_every_control_domain_has_explicit_prefix_mapping(domain):
    projected = project_dependency_link(
        link(source_resource_id=f"{domain.value}:entity-1"),
        graph_revision=7,
    )
    assert projected.graph.nodes[f"{domain.value}:entity-1"].domain is domain


def test_rfi_prefix_maps_explicitly_to_document_domain():
    projected = project_dependency_link(
        link(
            source_resource_id="schedule:task-1",
            target_resource_id="rfi:rfi-1",
            dependency_type="schedule_to_rfi",
        ),
        graph_revision=7,
    )
    assert projected.graph.nodes["rfi:rfi-1"].domain is ControlDomain.DOCUMENT
