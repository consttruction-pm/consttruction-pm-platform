from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

MAX_SAFE_REVISION = 9_007_199_254_740_991


class ControlDomain(str, Enum):
    SCHEDULE = "schedule"
    PROGRESS = "progress"
    EVM = "evm"
    RESOURCE = "resource"
    COST = "cost"
    DOCUMENT = "document"
    CHANGE = "change"
    CLAIM = "claim"
    PROCUREMENT = "procurement"
    FIELD = "field"


class DependencyRelation(str, Enum):
    DEPENDS_ON = "depends_on"
    IMPACTS = "impacts"
    SUPPORTS = "supports"
    EVIDENCES = "evidences"
    DERIVED_FROM = "derived_from"
    ALLOCATES = "allocates"
    CLAIMS_AGAINST = "claims_against"


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    domain: ControlDomain
    entity_type: str
    entity_id: str
    revision: int
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id.strip() or not isinstance(self.entity_type, str) or not self.entity_type.strip() or not isinstance(self.entity_id, str) or not self.entity_id.strip():
            raise ValueError("INVALID_DEPENDENCY_NODE_IDENTITY")
        if not isinstance(self.domain, ControlDomain):
            raise ValueError("INVALID_DEPENDENCY_NODE_DOMAIN")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or not 0 <= self.revision <= MAX_SAFE_REVISION
        ):
            raise ValueError("INVALID_DEPENDENCY_NODE_REVISION")


@dataclass(frozen=True)
class DependencyEdge:
    source_node_id: str
    target_node_id: str
    relation: DependencyRelation
    source_revision: int
    target_revision: int
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source_node_id, str) or not self.source_node_id.strip() or not isinstance(self.target_node_id, str) or not self.target_node_id.strip():
            raise ValueError("INVALID_DEPENDENCY_EDGE_IDENTITY")
        if self.source_node_id == self.target_node_id:
            raise ValueError("SELF_DEPENDENCY_NOT_ALLOWED")
        if not isinstance(self.relation, DependencyRelation):
            raise ValueError("INVALID_DEPENDENCY_RELATION")
        if (
            isinstance(self.source_revision, bool)
            or not isinstance(self.source_revision, int)
            or not 0 <= self.source_revision <= MAX_SAFE_REVISION
        ):
            raise ValueError("INVALID_SOURCE_REVISION")
        if (
            isinstance(self.target_revision, bool)
            or not isinstance(self.target_revision, int)
            or not 0 <= self.target_revision <= MAX_SAFE_REVISION
        ):
            raise ValueError("INVALID_TARGET_REVISION")


@dataclass
class DependencyGraph:
    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)
    scope: object | None = None

    def add_node(self, node: DependencyNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError("DUPLICATE_DEPENDENCY_NODE")
        self.nodes[node.node_id] = node

    def add_edge(self, edge: DependencyEdge) -> None:
        if edge.source_node_id not in self.nodes:
            raise ValueError("UNKNOWN_SOURCE_NODE")
        if edge.target_node_id not in self.nodes:
            raise ValueError("UNKNOWN_TARGET_NODE")
        if edge in self.edges:
            raise ValueError("DUPLICATE_DEPENDENCY_EDGE")
        self.edges.append(edge)

    def validate(self) -> None:
        from .contracts import ControlScope

        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_DEPENDENCY_GRAPH_SCOPE")
        for edge in self.edges:
            source = self.nodes.get(edge.source_node_id)
            target = self.nodes.get(edge.target_node_id)
            if source is None:
                raise ValueError("UNKNOWN_SOURCE_NODE")
            if target is None:
                raise ValueError("UNKNOWN_TARGET_NODE")
            if edge.source_revision != source.revision:
                raise ValueError("DEPENDENCY_SOURCE_REVISION_MISMATCH")
            if edge.target_revision != target.revision:
                raise ValueError("DEPENDENCY_TARGET_REVISION_MISMATCH")
