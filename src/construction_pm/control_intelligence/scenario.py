from dataclasses import dataclass, field
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference, require_enum
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
        if not isinstance(self.change_id, str) or not self.change_id.strip() or not isinstance(self.entity_type, str) or not self.entity_type.strip() or not isinstance(self.entity_id, str) or not self.entity_id.strip() or not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("INVALID_SCENARIO_CHANGE")
        require_enum(self.domain, ControlDomain, "INVALID_SCENARIO_CHANGE_DOMAIN")
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
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip() or not isinstance(self.requested_by, str) or not self.requested_by.strip() or not isinstance(self.purpose_key, str) or not self.purpose_key.strip():
            raise ValueError("INVALID_SCENARIO_REQUEST")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_SCENARIO_REQUEST_SCOPE")
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
        if not isinstance(self.entity_type, str) or not self.entity_type.strip() or not isinstance(self.entity_id, str) or not self.entity_id.strip() or not isinstance(self.impact_type, str) or not self.impact_type.strip():
            raise ValueError("INVALID_SCENARIO_IMPACT")
        require_enum(self.domain, ControlDomain, "INVALID_SCENARIO_IMPACT_DOMAIN")
        if not isinstance(self.description_key, str) or not self.description_key.strip() or not self.source_refs:
            raise ValueError("SCENARIO_IMPACT_SOURCE_REQUIRED")


@dataclass(frozen=True)
class ScenarioProposal:
    scenario_id: str
    base_scope: ControlScope
    impacts: Tuple[ScenarioImpact, ...]
    proposed_changes: Tuple[ScenarioChange, ...]
    authoritative_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("INVALID_SCENARIO_PROPOSAL")
        if not isinstance(self.base_scope, ControlScope):
            raise ValueError("INVALID_SCENARIO_PROPOSAL_SCOPE")
        if not isinstance(self.authoritative_mutation_allowed, bool):
            raise ValueError("INVALID_SCENARIO_MUTATION_FLAG")
        if self.authoritative_mutation_allowed:
            raise ValueError("SCENARIO_CANNOT_MUTATE_AUTHORITATIVE_STATE")
