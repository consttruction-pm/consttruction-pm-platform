from __future__ import annotations

from dataclasses import dataclass

from .control_intelligence.graph import (
    ControlDomain,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)
from .control_intelligence.contracts import ControlScope
from .dependency_graph_persistence import DependencyLink


class DependencyProjectionError(ValueError):
    """Raised when persistence data cannot be projected without semantic inference."""


@dataclass(frozen=True)
class DependencyProjection:
    """Versioned, lossless projection from persistence to Shared Core."""

    contract_version: str
    graph: DependencyGraph


# Persistence identifiers are deliberately parsed only by this explicit map.
# Unknown prefixes are rejected instead of being guessed.
_DOMAIN_BY_PREFIX = {
    "schedule": ControlDomain.SCHEDULE,
    "progress": ControlDomain.PROGRESS,
    "evm": ControlDomain.EVM,
    "resource": ControlDomain.RESOURCE,
    "cost": ControlDomain.COST,
    "document": ControlDomain.DOCUMENT,
    "rfi": ControlDomain.DOCUMENT,
    "change": ControlDomain.CHANGE,
    "claim": ControlDomain.CLAIM,
    "procurement": ControlDomain.PROCUREMENT,
    "field": ControlDomain.FIELD,
}

_RELATION_BY_TYPE = {
    "depends_on": DependencyRelation.DEPENDS_ON,
    "impacts": DependencyRelation.IMPACTS,
    "supports": DependencyRelation.SUPPORTS,
    "evidences": DependencyRelation.EVIDENCES,
    "derived_from": DependencyRelation.DERIVED_FROM,
    "allocates": DependencyRelation.ALLOCATES,
    "claims_against": DependencyRelation.CLAIMS_AGAINST,
    "schedule_to_progress": DependencyRelation.IMPACTS,
    "progress_to_evm": DependencyRelation.DERIVED_FROM,
    "resource_to_schedule": DependencyRelation.IMPACTS,
    "cost_to_schedule": DependencyRelation.IMPACTS,
    "change_to_schedule": DependencyRelation.IMPACTS,
    "claim_to_change": DependencyRelation.CLAIMS_AGAINST,
    "schedule_to_change": DependencyRelation.IMPACTS,
    "schedule_to_rfi": DependencyRelation.IMPACTS,
}


def project_dependency_link(
    link: DependencyLink,
    *,
    graph_revision: int,
) -> DependencyProjection:
    link.validate()
    if graph_revision < 0:
        raise DependencyProjectionError("INVALID_GRAPH_REVISION")
    source = _node(link.source_resource_id, link.source_revision if link.source_revision is not None else link.revision)
    target = _node(link.target_resource_id, link.target_revision if link.target_revision is not None else link.revision)
    relation = _relation(link.dependency_type)

    graph = DependencyGraph(
        scope=ControlScope(
            tenant_id=link.tenant_id,
            project_id=link.project_id,
            project_revision=link.revision,
        )
    )
    graph.add_node(source)
    graph.add_node(target)
    graph.add_edge(
        DependencyEdge(
            source_node_id=source.node_id,
            target_node_id=target.node_id,
            relation=relation,
            source_revision=source.revision,
            target_revision=target.revision,
            attributes=dict(link.metadata),
        )
    )
    graph.validate()
    return DependencyProjection("dependency-graph.v1", graph)


def _node(resource_id: str, revision: int) -> DependencyNode:
    try:
        prefix, entity_id = resource_id.split(":", 1)
    except ValueError as exc:
        raise DependencyProjectionError("INVALID_DEPENDENCY_RESOURCE_ID") from exc
    domain = _DOMAIN_BY_PREFIX.get(prefix)
    if domain is None or not entity_id.strip():
        raise DependencyProjectionError("UNMAPPABLE_DEPENDENCY_DOMAIN")
    return DependencyNode(
        node_id=resource_id,
        domain=domain,
        entity_type=prefix,
        entity_id=entity_id,
        revision=revision,
    )


def _relation(dependency_type: str) -> DependencyRelation:
    relation = _RELATION_BY_TYPE.get(dependency_type)
    if relation is None:
        raise DependencyProjectionError("UNMAPPABLE_DEPENDENCY_RELATION")
    return relation
