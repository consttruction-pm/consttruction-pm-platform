from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference
from .graph import ControlDomain

class ImpactStatus(str, Enum):
    OBSERVED = "observed"
    POTENTIAL = "potential"
    CONFIRMED = "confirmed"

class ImpactSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass(frozen=True)
class ControlImpact:
    impact_id: str
    scope: ControlScope
    source_domain: ControlDomain
    source_entity_type: str
    source_entity_id: str
    target_domain: ControlDomain
    target_entity_type: str
    target_entity_id: str
    impact_type: str
    status: ImpactStatus
    severity: ImpactSeverity
    detail_key: str
    source_refs: Tuple[SourceReference, ...] = ()
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.impact_id or not self.source_entity_type or not self.source_entity_id:
            raise ValueError("INVALID_CONTROL_IMPACT")
        if not self.target_entity_type or not self.target_entity_id or not self.impact_type:
            raise ValueError("INVALID_CONTROL_IMPACT_TARGET")
        if not self.detail_key or not self.source_refs:
            raise ValueError("CONTROL_IMPACT_TRACEABILITY_REQUIRED")

@dataclass(frozen=True)
class ControlImpactSet:
    scope: ControlScope
    impacts: Tuple[ControlImpact, ...]

    def __post_init__(self) -> None:
        if not self.impacts:
            raise ValueError("CONTROL_IMPACTS_REQUIRED")
