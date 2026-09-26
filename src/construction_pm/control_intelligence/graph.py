from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

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
        if not self.node_id or not self.entity_type or not self.entity_id:
            raise ValueError("INVALID_DEPENDENCY_NODE_IDENTITY")
        if isinstance(self.revision, bool) or self.revision < 0:
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
        if not self.source_node_id or not self.target_node_id:
            raise ValueError("INVALID_DEPENDENCY_EDGE_IDENTITY")
        if self.source_node_id == self.target_node_id:
            raise ValueError("SELF_DEPENDENCY_NOT_ALLOWED")
        if isinstance(self.source_revision, bool) or self.source_revision < 0:
            raise ValueError("INVALID_SOURCE_REVISION")
        if isinstance(self.target_revision, bool) or self.target_revision < 0:
            raise ValueError("INVALID_TARGET_REVISION")

@dataclass
class DependencyGraph:
    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    edges: list[DependencyEdge] = field(default_factory=list)

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
        for edge in self.edges:
            if edge.source_node_id not in self.nodes:
                raise ValueError("UNKNOWN_SOURCE_NODE")
            if edge.target_node_id not in self.nodes:
                raise ValueError("UNKNOWN_TARGET_NODE")
