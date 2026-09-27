from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Tuple

from .contracts import ControlScope, SourceReference, require_enum
from .graph import ControlDomain


def _require_source_scope(source_refs: Tuple[SourceReference, ...], scope: ControlScope, error_code: str) -> None:
    for source in source_refs:
        if source.revision != scope.project_revision:
            raise ValueError(error_code)


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
        if not isinstance(self.impact_id, str) or not self.impact_id.strip() or not isinstance(self.source_entity_type, str) or not self.source_entity_type.strip() or not isinstance(self.source_entity_id, str) or not self.source_entity_id.strip():
            raise ValueError("INVALID_CONTROL_IMPACT")
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_CONTROL_IMPACT_SCOPE")
        require_enum(self.source_domain, ControlDomain, "INVALID_CONTROL_IMPACT_SOURCE_DOMAIN")
        require_enum(self.target_domain, ControlDomain, "INVALID_CONTROL_IMPACT_TARGET_DOMAIN")
        require_enum(self.status, ImpactStatus, "INVALID_CONTROL_IMPACT_STATUS")
        require_enum(self.severity, ImpactSeverity, "INVALID_CONTROL_IMPACT_SEVERITY")
        if not isinstance(self.target_entity_type, str) or not self.target_entity_type.strip() or not isinstance(self.target_entity_id, str) or not self.target_entity_id.strip() or not isinstance(self.impact_type, str) or not self.impact_type.strip():
            raise ValueError("INVALID_CONTROL_IMPACT_TARGET")
        if not isinstance(self.detail_key, str) or not self.detail_key.strip() or not self.source_refs:
            raise ValueError("CONTROL_IMPACT_TRACEABILITY_REQUIRED")
        _require_source_scope(self.source_refs, self.scope, "CONTROL_IMPACT_SOURCE_REVISION_MISMATCH")


@dataclass(frozen=True)
class ControlImpactSet:
    scope: ControlScope
    impacts: Tuple[ControlImpact, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ControlScope):
            raise ValueError("INVALID_CONTROL_IMPACT_SET_SCOPE")
        if not self.impacts:
            raise ValueError("CONTROL_IMPACTS_REQUIRED")
        for impact in self.impacts:
            if impact.scope != self.scope:
                raise ValueError("CONTROL_IMPACT_SCOPE_MISMATCH")
