from dataclasses import dataclass, field
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference
from .graph import ControlDomain

@dataclass(frozen=True)
class ScenarioChange:
    change_id: str
    domain: ControlDomain
    entity_type: str
    entity_id: str
    operation: str
    proposed_value: Mapping[str, object]
    source_refs: Tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        if not self.change_id or not self.entity_type or not self.entity_id or not self.operation:
            raise ValueError("INVALID_SCENARIO_CHANGE")
        if not self.source_refs:
            raise ValueError("SCENARIO_CHANGE_SOURCE_REQUIRED")

@dataclass(frozen=True)
class ScenarioRequest:
    scenario_id: str
    scope: ControlScope
    requested_by: str
    purpose_key: str
    changes: Tuple[ScenarioChange, ...]
    assumptions: Mapping[str, object] = field(default_factory=dict)
    source_refs: Tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.requested_by or not self.purpose_key:
            raise ValueError("INVALID_SCENARIO_REQUEST")
        if not self.changes:
            raise ValueError("SCENARIO_CHANGES_REQUIRED")
        if not self.source_refs:
            raise ValueError("SCENARIO_REQUEST_SOURCE_REQUIRED")

@dataclass(frozen=True)
class ScenarioImpact:
    domain: ControlDomain
    entity_type: str
    entity_id: str
    impact_type: str
    description_key: str
    source_refs: Tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        if not self.entity_type or not self.entity_id or not self.impact_type:
            raise ValueError("INVALID_SCENARIO_IMPACT")
        if not self.source_refs:
            raise ValueError("SCENARIO_IMPACT_SOURCE_REQUIRED")

@dataclass(frozen=True)
class ScenarioProposal:
    scenario_id: str
    base_scope: ControlScope
    impacts: Tuple[ScenarioImpact, ...]
    proposed_changes: Tuple[ScenarioChange, ...]
    authoritative_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if self.authoritative_mutation_allowed:
            raise ValueError("SCENARIO_CANNOT_MUTATE_AUTHORITATIVE_STATE")
